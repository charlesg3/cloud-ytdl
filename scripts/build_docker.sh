#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Image name
IMAGE_NAME="ytdlp-downloader"

echo -e "${BLUE}Building Docker image: ${YELLOW}${IMAGE_NAME}${NC}"
echo -e "${BLUE}This might take a few minutes...${NC}"

# set container runtime preferring finch
command -v docker &> /dev/null && container_runtime=docker
command -v finch &> /dev/null && container_runtime=finch
if [ -z "${container_runtime}" ]; then
    echo "Coldn't find docker or finch. Please install a container runtime."
    echo "see: https://github.com/runfinch/finch for finch or https://docs.docker.com/engine/install/"
    exit 1
fi

# Build the Docker image
${container_runtime} build -t $IMAGE_NAME -f docker/Dockerfile .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Build successful!${NC}"
    echo -e "${YELLOW}You can now use the run.sh script to download videos:${NC}"
    echo -e "${BLUE}VIDEO_ID=https://www.youtube.com/watch?v=dQw4w9WgXcQ ./run.sh${NC}"
else
    echo -e "${YELLOW}Build failed. Please check the error messages above.${NC}"
    exit 1
fi

