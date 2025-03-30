#!/bin/bash
set -e

# ============= Configuration =============
# You can pass these as arguments or edit the defaults here
LAMBDA_FUNCTION_NAME=${1:-"api-backend-service"}
S3_BUCKET=${2:-"cloudytdl"}
S3_KEY=${3:-"lambda.zip"}
SOURCE_DIR=${5:-"src"}
# ========================================

BUILD_DIR="./build_$(date +%s)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}       Lambda Function Update Script            ${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}Function:${NC} $LAMBDA_FUNCTION_NAME"
echo -e "${YELLOW}S3 Bucket:${NC} $S3_BUCKET"
echo -e "${YELLOW}S3 Key:${NC} $S3_KEY"
echo -e "${YELLOW}Source Directory:${NC} $SOURCE_DIR"
echo -e "${BLUE}================================================${NC}"

trap 'error' ERR

error(){
  echo -e "${RED}An error has occurred while uploading. Cleaning up.${NC}"
  rm -fr ${BUILD_DIR}
  rm -f "$S3_KEY"
  echo -e "${GREEN}Done with errors.${NC}"
}


# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo -e "${RED}Error: Source directory '$SOURCE_DIR' not found${NC}"
  exit 1
fi

# Create a clean build directory
echo -e "${BLUE}Creating build directory...${NC}"
mkdir -p "$BUILD_DIR"

# Copy source files to build directory
echo -e "${BLUE}Copying source files...${NC}"
cp -r "$SOURCE_DIR"/* "$BUILD_DIR"

# Create zip file
echo -e "${BLUE}Creating zip archive...${NC}"
pushd "$BUILD_DIR"
zip -r "../$S3_KEY" .
popd

# Check if zip was created successfully
if [ ! -f "$S3_KEY" ]; then
  echo -e "${RED}Error: Failed to create zip archive${NC}"
  rm -rf "$BUILD_DIR"
  exit 1
fi

# Upload to S3
echo -e "${BLUE}Uploading to S3 bucket...${NC}"
if aws s3 cp "$S3_KEY" "s3://$S3_BUCKET/$S3_KEY"; then
  echo -e "${GREEN}Upload successful!${NC}"
else
  echo -e "${RED}Error: Failed to upload to S3. Verify bucket exists and you have permission.${NC}"
  rm -rf "$BUILD_DIR"
  rm -f "$S3_KEY"
  exit 1
fi

# Update Lambda function
echo -e "${BLUE}Updating Lambda function...${NC}"
if aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --s3-bucket "$S3_BUCKET" \
  --s3-key "$S3_KEY" \
  --publish; then
  
  echo -e "${GREEN}Lambda function updated successfully!${NC}"
  
  # Get function details
  echo -e "${BLUE}Getting updated function details...${NC}"
  aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --query 'Configuration.[FunctionName,Version,LastModified]' \
    --output table
else
  echo -e "${RED}Error: Failed to update Lambda function.${NC}"
  echo -e "${YELLOW}Verify that the function exists and you have permission to update it.${NC}"
fi

# Cleanup
echo -e "${BLUE}Cleaning up temporary files...${NC}"
rm -rf "$BUILD_DIR"
rm -f "$S3_KEY"

echo -e "${GREEN}Done!${NC}"
