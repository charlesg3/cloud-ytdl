#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Image name
IMAGE_NAME="ytdlp-downloader"


run() {
    # Check if VIDEO_ID environment variable is set
    if [ -z "$VIDEO_ID" ]; then
        echo -e "${RED}ERROR: VIDEO_ID environment variable is not set!${NC}"
        echo -e "${YELLOW}Usage: ${BLUE}VIDEO_ID=<youtube-url-or-id> ./run.sh${NC}"
        exit 1
    fi

    # Create the data directory if it doesn't exist
    mkdir -p ./data

    echo -e "${BLUE}Starting download for video: ${YELLOW}${VIDEO_ID}${NC}"
    echo -e "${BLUE}Videos will be saved to: ${YELLOW}./data/${NC}"

    # Run the Docker container with the mounted data directory
    # Pass all script arguments to yt-dlp
    docker run --rm \
        -e VIDEO_ID="$VIDEO_ID" \
        -v "$(pwd)/data:/downloads" \
        $IMAGE_NAME "$@"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Process completed successfully!${NC}"
    else
        echo -e "${RED}Process failed. Please check the error messages above.${NC}"
        exit 1
    fi
}

_error_exit() {
   echo "$1"
   exit 1
}

_help() {
    local -- _cmd=$(basename "$0")

    cat <<EOF
  This script will rund the docker container to download a video.
  Usage: ${_cmd} [OPTION]...


  --video-id <video-id>     YouTube video id to download.
  -h, --help                Print this help message

  Examples:
  ${_cmd}
  $_cmd --video-id https://www.youtube.com/watch?v=3sONSUu16bM
EOF
}

parse_options(){

   while [ $# -gt 0 ] ; do
          case "$1" in
              --video-id)          VIDEO_ID="$2"; shift;;
              -h|--help|help)      _help; exit 0;;
              *)                   _help; _error_exit "[error] Unrecognized option '$1'";;
          esac
          shift
      done

}

main(){
  parse_options "$@"
  run
}

main "$@"
