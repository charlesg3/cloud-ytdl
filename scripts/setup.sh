#!/bin/bash


# Amazon Linux 2023 Docker Installation Script
# This script installs Docker on an Amazon Linux 2023 instance
# and performs basic configuration and setup.

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header function
print_header() {
    echo -e "${BLUE}=======================================================${NC}"
    echo "$1"
    echo -e "${BLUE}=======================================================${NC}"
}

print_single() {
    echo -e "${BLUE}$1${YELLOW}$2${NC}"
}

# Update system packages
update_system() {
    print_header "Updating System Packages"
    dnf update -y
    dnf install -y wget tar gzip shadow-utils util-linux
}


install_ffmpeg() {
    print_single "Installing: " "ffmpeg"
    mkdir -p /tmp/ffmpeg
    curl -s -L https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz -o - | \
    tar -xJ -C /tmp/ffmpeg --strip-components=1
    cp /tmp/ffmpeg/bin/ffmpeg /usr/local/bin/
    cp /tmp/ffmpeg/bin/ffprobe /usr/local/bin/
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe
}

install_ytdlp() {
    # Install yt-dlp as a standalone binary
    print_single "Installing: " "yt-dlp"
    curl -s -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp --output /usr/local/bin/yt-dlp
    chmod +x /usr/local/bin/yt-dlp
}

retrieve_cookies() {
    bucket=$1
    print_single "Getting ${YELLOW}cookies.txt${BLUE} from: " "${bucket}"
    aws s3 cp s3://${bucket}/cookies.txt .
}

retrieve_video() {
    video_id=$1
    output_dir=$2
    print_single "Retrieving: " "${video_id} ${BLUE} to: ${YELLOW}${output_dir}"
    yt-dlp ${video_id} --output "${output_dir}/%(title)s.%(ext)s" --yes-playlist \
        --cookies ./cookies.txt --no-cache-dir --extract-audio --audio-format mp3
}


upload_data() {
    dir=$1
    bucket=$2
    path=$3
    find ${dir} -type f -name "*.mp3" | sort | while IFS= read -r file; do
        filename=$(basename "${file}")
        echo -e "${BLUE}Uploading: \"${YELLOW}$file${BLUE}\" to: \"${YELLOW}s3://${bucket}/${path}/${filename}\"${NC}"
        aws s3 cp "${file}" "s3://${bucket}/${path}/${filename}"
    done
    echo -e "${BLUE}Done.${NC}"
}


# Main execution
main() {
    bucket=$1
    video_id=$2
    path=$3
    echo "Video ID: " ${video_id}
    update_system
    install_ffmpeg
    install_ytdlp
    retrieve_cookies ${bucket}
    mkdir -p ./data
    retrieve_video $video_id ./data
    upload_data ./data $bucket $path
}

# Execute main function
main "$@"

echo "Script execution completed!"
