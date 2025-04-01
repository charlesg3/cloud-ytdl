#!/bin/bash

set -e

# Create a temporary directory for our work
TEMP_DIR=$(mktemp -d)
echo "Working in temporary directory: $TEMP_DIR"

# Create the structure for Lambda Layer
LAYER_DIR="$TEMP_DIR/layer"
BIN_DIR="$LAYER_DIR/bin"
mkdir -p "$BIN_DIR"

# Determine system architecture
ARCH=$(uname -m)
if [ "$ARCH" == "x86_64" ]; then
    FFMPEG_ARCH="amd64"
    YTDLP_ARCH="x86_64"
elif [ "$ARCH" == "aarch64" ] || [ "$ARCH" == "arm64" ]; then
    FFMPEG_ARCH="arm64"
    YTDLP_ARCH="aarch64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

echo "Detected architecture: $ARCH (FFmpeg: $FFMPEG_ARCH, yt-dlp: $YTDLP_ARCH)"

# Download and extract static FFmpeg for Linux
echo "Downloading and extracting FFmpeg..."

mkdir -p "$TEMP_DIR/ffmpeg"
FFMPEG_URL="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl-shared.tar.xz"
curl -s -L ${FFMPEG_URL} -o - | tar -xvJ  --exclude=*/LICENSE.txt --exclude=*/doc --exclude=*/man --exclude=*/bin/ffplay --exclude=*/include --exclude=*/pkgconfig --exclude=*/libavdevice* --exclude=*/libavfilter* -C $LAYER_DIR --strip-components=1 

# Download the latest yt-dlp binary
echo "Downloading yt-dlp..."
YTDLP_URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
curl -s -L "$YTDLP_URL" -o "$BIN_DIR/yt-dlp"

# Make binaries executable
echo "Setting executable permissions..."
chmod 755 "$BIN_DIR/ffmpeg" "$BIN_DIR/ffprobe" "$BIN_DIR/yt-dlp"

# Create zip file for the Lambda Layer
LAYER_ZIP="ffmpeg-ytdlp-lambda-layer.zip"
echo "Creating Lambda layer zip: $LAYER_ZIP"
pushd "$LAYER_DIR"
zip -r -y "$TEMP_DIR/$LAYER_ZIP" .
popd
cp $TEMP_DIR/$LAYER_ZIP .

# Clean up
echo "Cleaning up temporary files..."
#rm -rf "$TEMP_DIR"

echo "Done! Layer zip created: $LAYER_ZIP"
echo ""
echo "To deploy this layer to AWS Lambda:"
echo "aws lambda publish-layer-version \\"
echo "  --layer-name ffmpeg-ytdlp \\"
echo "  --zip-file fileb://$LAYER_ZIP \\"
echo "  --compatible-runtimes python3.11 \\"
echo "  --compatible-architectures x86_64"
