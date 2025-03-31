#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOCAL_IMAGE="ytdlp-downloader-lambda"
ECR_REPOSITORY_NAME="ytdlp-downloader-lambda"
AWS_REGION=$(aws configure get region)

# Print header
echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}     Pushing Docker Image to Amazon ECR      ${NC}"
echo -e "${BLUE}==============================================${NC}"
echo -e "${YELLOW}Local Image:${NC} $LOCAL_IMAGE"
echo -e "${YELLOW}ECR Repository:${NC} $ECR_REPOSITORY_NAME"
echo -e "${YELLOW}AWS Region:${NC} $AWS_REGION"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker daemon.${NC}"
    exit 1
fi

# Check if image exists locally
if [[ "$(docker images -q $LOCAL_IMAGE 2> /dev/null)" == "" ]]; then
    echo -e "${RED}Error: Docker image '$LOCAL_IMAGE' not found locally.${NC}"
    echo -e "${YELLOW}Have you built the image with './build.sh'?${NC}"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed.${NC}"
    echo -e "${YELLOW}Please install AWS CLI: https://aws.amazon.com/cli/${NC}"
    exit 1
fi

# Get AWS account ID
echo -e "${BLUE}Getting AWS account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to get AWS account ID.${NC}"
    echo -e "${YELLOW}Please check your AWS credentials and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# Set the full ECR repository URI
ECR_REPOSITORY_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME"

# Check if repository exists, if not, create it
echo -e "${BLUE}Checking if ECR repository exists...${NC}"
if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${YELLOW}Repository does not exist. Creating repository $ECR_REPOSITORY_NAME...${NC}"
    aws ecr create-repository --repository-name "$ECR_REPOSITORY_NAME" --region "$AWS_REGION"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to create ECR repository.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Repository created successfully.${NC}"
else
    echo -e "${GREEN}Repository already exists.${NC}"
fi

# Login to ECR
echo -e "${BLUE}Logging in to Amazon ECR...${NC}"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to authenticate with Amazon ECR.${NC}"
    exit 1
fi

# Tag the Docker image for ECR
echo -e "${BLUE}Tagging local image for ECR...${NC}"
docker tag "$LOCAL_IMAGE:latest" "$ECR_REPOSITORY_URI:latest"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to tag Docker image.${NC}"
    exit 1
fi

# Push the image to ECR
echo -e "${BLUE}Pushing image to Amazon ECR...${NC}"
docker push "$ECR_REPOSITORY_URI:latest"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to push image to ECR.${NC}"
    exit 1
fi

# Success message with instructions
echo -e "${GREEN}Successfully pushed image to Amazon ECR!${NC}"
echo -e "${BLUE}==============================================${NC}"
echo -e "${YELLOW}Image URI:${NC} $ECR_REPOSITORY_URI:latest"
echo -e "${BLUE}==============================================${NC}"

# Optional instructions for pulling the image
echo -e "${BLUE}To pull this image on another machine:${NC}"
echo -e "${YELLOW}aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com${NC}"
echo -e "${YELLOW}docker pull $ECR_REPOSITORY_URI:latest${NC}"

# Optional cleanup instructions
echo -e "${BLUE}To clean up local Docker images (optional):${NC}"
echo -e "${YELLOW}docker image rm $ECR_REPOSITORY_URI:latest${NC}"
echo -e "${YELLOW}docker image prune -f${NC}"
