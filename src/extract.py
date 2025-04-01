import json
import logging
import os
import subprocess
import uuid
import boto3
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Setup S3 client
s3 = boto3.client("s3")


def setup_environment():
    """Setup environment for FFmpeg and yt-dlp"""
    logger.info("Setting up environment variables")
    # Add the layer binaries to PATH
    os.environ["PATH"] = f"/opt/bin:{os.environ.get('PATH', '')}"
    # Add the layer libraries to LD_LIBRARY_PATH
    os.environ["LD_LIBRARY_PATH"] = f"/opt/lib:{os.environ.get('LD_LIBRARY_PATH', '')}"

    # Make sure we can run the tools
    try:
        ytdlp_version = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
        ffmpeg_version = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        logger.info(f"yt-dlp version: {ytdlp_version.stdout.strip()}")
        logger.info(f"ffmpeg version: {ffmpeg_version.stdout.splitlines()[0] if ffmpeg_version.stdout else 'unknown'}")
        return True
    except Exception as e:
        logger.error(f"Failed to verify tools: {str(e)}")
        return False


def run_ytdlp(command_args: List[str], working_dir: str) -> bool:
    """
    Run yt-dlp command and stream the output through logging.

    Args:
        command_args: yt-dlp command arguments as a list of strings
        working_dir: Directory to run the command in

    Returns:
        True if successful, False otherwise
    """
    command = ["yt-dlp"] + command_args

    logger.info(f"Running yt-dlp command: {' '.join(command)}")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            cwd=working_dir,
        )

        # Stream the output
        while True:
            output_line = process.stdout.readline()
            if output_line == "" and process.poll() is not None:
                break
            if output_line:
                # Strip trailing whitespace (including newlines)
                output_line = output_line.rstrip()
                logger.info(f"yt-dlp: {output_line}")

        return_code = process.poll()

        if return_code == 0:
            logger.info("yt-dlp command completed successfully")
            return True
        else:
            logger.error(f"yt-dlp command failed with return code {return_code}")
            return False
    except Exception as e:
        logger.error(f"Error executing yt-dlp: {str(e)}")
        return False


def extract_audio(video_url: str, output_format: str = "mp3") -> Dict[str, Any]:
    """
    Extract audio from a YouTube video URL.

    Args:
        video_url: YouTube video URL
        output_format: Audio format (default: mp3)

    Returns:
        Dictionary with results
    """
    # Create a unique working directory in /tmp
    working_dir = f"/tmp/{uuid.uuid4()}"
    os.makedirs(working_dir, exist_ok=True)
    logger.info(f"Working directory: {working_dir}")

    try:
        # Use yt-dlp to download and extract audio
        output_template = "%(title)s.%(ext)s"

        # Prepare command args - use the best audio quality, convert to mp3
        command_args = [
            "-x",  # Extract audio
            "--audio-format",
            output_format,  # Set audio format
            "--audio-quality",
            "0",  # Best quality
            "-o",
            output_template,  # Output filename template
            "--no-playlist",  # Don't download playlists
            "--progress",  # Show progress
            video_url,  # The video URL
        ]

        # Run yt-dlp
        success = run_ytdlp(command_args, working_dir)

        if not success:
            return {"success": False, "message": "Failed to download and extract audio"}

        # Find the generated mp3 file
        audio_files = list(Path(working_dir).glob(f"*.{output_format}"))
        if not audio_files:
            return {"success": False, "message": f"No {output_format} file found after processing"}

        audio_file = audio_files[0]
        logger.info(f"Found audio file: {audio_file}")

        # Upload to S3
        s3_key = f"audio/{audio_file.name}"
        s3.upload_file(str(audio_file), os.environ["OUTPUT_BUCKET"], s3_key)

        # Generate a presigned URL for easy access
        presigned_url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": os.environ["OUTPUT_BUCKET"], "Key": s3_key}, ExpiresIn=86400  # 24 hours
        )

        return {
            "success": True,
            "message": "Audio extracted successfully",
            "file_name": audio_file.name,
            "s3_key": s3_key,
            "bucket": os.environ["OUTPUT_BUCKET"],
            "download_url": presigned_url,
        }

    except Exception as e:
        logger.error(f"Error in extract_audio: {str(e)}")
        return {"success": False, "message": f"Error extracting audio: {str(e)}"}
    finally:
        # Clean up temporary files
        logger.info(f"Cleaning up temporary directory: {working_dir}")
        # List all files before cleanup for debugging
        for file in Path(working_dir).glob("*"):
            logger.info(f"File in working directory: {file}")


def lambda_handler(event, context):
    """
    Lambda entry point

    Expected event format:
    {
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "format": "mp3"  # optional
    }

    Or for direct yt-dlp commands:
    {
        "command_args": ["--extract-audio", "--audio-format", "mp3", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Set up environment
    if not setup_environment():
        return {"statusCode": 500, "body": json.dumps({"success": False, "message": "Failed to set up environment"})}

    # Check if we're running a direct command or extracting audio
    if "command_args" in event:
        if not isinstance(event["command_args"], list):
            return {
                "statusCode": 400,
                "body": json.dumps({"success": False, "message": "command_args must be an array"}),
            }

        # Create a working directory
        working_dir = f"/tmp/{uuid.uuid4()}"
        os.makedirs(working_dir, exist_ok=True)

        # Run the command
        success = run_ytdlp(event["command_args"], working_dir)

        # Try to find any generated files
        files = list(Path(working_dir).glob("*"))
        file_list = [str(file.name) for file in files]

        # Upload files to S3 if successful
        s3_files = []
        if success and files:
            for file in files:
                if file.is_file():
                    s3_key = f"downloads/{file.name}"
                    try:
                        s3.upload_file(str(file), os.environ["OUTPUT_BUCKET"], s3_key)
                        s3_files.append({"name": file.name, "s3_key": s3_key, "bucket": os.environ["OUTPUT_BUCKET"]})
                    except Exception as e:
                        logger.error(f"Error uploading {file.name}: {str(e)}")

        return {
            "statusCode": 200 if success else 500,
            "body": json.dumps({"success": success, "files": file_list, "s3_files": s3_files}),
        }

    # Process video extraction
    elif "video_url" in event:
        video_url = event["video_url"]
        output_format = event.get("format", "mp3")

        result = extract_audio(video_url, output_format)

        return {"statusCode": 200 if result["success"] else 500, "body": json.dumps(result)}
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"success": False, "message": "Missing required parameter: video_url or command_args"}),
        }
