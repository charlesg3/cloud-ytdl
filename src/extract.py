import json
import logging
import os
import subprocess
import uuid
import boto3
from pathlib import Path
from typing import Dict, Any, List
from botocore.exceptions import ClientError


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
    ffmpeg_version = None
    try:
        ytdlp_version = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
        ffmpeg_version = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
        logger.info(f"yt-dlp version: {ytdlp_version.stdout.strip()}")
        logger.info(f"ffmpeg version: {ffmpeg_version.stdout.splitlines()[0] if ffmpeg_version.stdout else 'unknown'}")
        return True
    except Exception as e:
        logger.error(f"Failed to verify tools: {str(e)}")
        logger.error(ffmpeg_version.stdout)
        logger.error(ffmpeg_version.stderr)
        return False


def download_cookies():
    """
    Downloads the cookies.txt file from the S3 bucket specified in the OUTPUT_BUCKET
    environment variable and saves it to /tmp/cookies.txt

    Returns:
        bool: True if successful, False otherwise
    """
    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Get bucket name from environment variable
    bucket_name = os.environ.get("OUTPUT_BUCKET")

    if not bucket_name:
        logger.error("OUTPUT_BUCKET environment variable is not set")
        return False

    # Define file paths
    s3_key = "cookies.txt"  # The path to cookies.txt in the bucket
    local_path = "/tmp/cookies.txt"

    try:
        logger.info(f"Downloading cookies.txt from bucket {bucket_name}")

        # Create S3 client
        s3 = boto3.client("s3")

        # Download the file
        s3.download_file(bucket_name, s3_key, local_path)
        logger.info(f"Successfully downloaded cookies.txt to {local_path}")

        # Verify file exists and has content
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            logger.info(f"Verification successful - file exists and contains data")
            return True
        else:
            logger.warning(f"File exists but may be empty")
            return False

    except Exception as e:
        logger.error(f"Error downloading cookies.txt: {str(e)}")
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


def extract_audio(
    video_url: str, output_filename: str = None, path: str = "audio", output_format: str = "mp3"
) -> Dict[str, Any]:
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
        output_template = f"{output_filename}.%(ext)s" if output_filename else "%(title)s.%(ext)s"

        # Prepare command args - use the best audio quality, convert to mp3
        command_args = [
            "-x",  # Extract audio
            "--audio-format",
            output_format,  # Set audio format
            "--cookies",
            "/tmp/cookies.txt",
            "--no-cache-dir",
            "--audio-quality",
            "0",  # Best quality
            "-o",
            output_template,  # Output filename template
            "--yes-playlist",  # Don't download playlists
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
        s3_key = f"{path}/{audio_file.name}"
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

    if "body" in event:
        event = {**event, **json.loads(event["body"])}

    if "video_url" in event:
        video_url = event["video_url"]
        output_filename = event.get("output_filename")
        path = event.get("path", "audio")
        output_format = event.get("format", "mp3")

        bucket_name = os.environ.get("OUTPUT_BUCKET")

        # check for file
        try:
            params = {"Bucket": bucket_name, "Key": f"{path}/{output_filename}.mp3"}
            s3.head_object(**params)
            logger.info(f"Found existing file: s3://{bucket_name}/{path}/{output_filename}.mp3")
            presigned_url = s3.generate_presigned_url("get_object", Params=params)
            result = {
                "success": True,
                "message": "Audio extracted successfully",
                "file_name": f"{output_filename}.mp3",
                "s3_key": params["Key"],
                "bucket": bucket_name,
                "download_url": presigned_url,
            }
            logger.info(f"Returning success: {json.dumps(result)}")
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT,DELETE",
                },
                "body": json.dumps(result),
            }

        except ClientError as e:
            pass

        if "cookies" in event:
            output_path = "/tmp/cookies.txt"

            # Save cookies to file
            logger.info(f"Saving cookies data to {output_path}")
            with open(output_path, "w") as file:
                file.write(f"{event['cookies']}")

            with open(output_path, "r") as file:
                logger.info(file.read())
        else:
            download_cookies()

        result = extract_audio(video_url, output_filename, path, output_format)

        return {
            "statusCode": 200 if result["success"] else 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT,DELETE",
            },
            "body": json.dumps(result),
        }
    else:
        return {
            "statusCode": 400,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT,DELETE",
            },
            "body": json.dumps({"success": False, "message": "Missing required parameter: video_url"}),
        }
