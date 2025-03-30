# Use latest Ubuntu as base image
FROM alpine:latest AS builder

# Install dependencies
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    git \
    make \
    pandoc \
    zip \
    ffmpeg \
    gcc \
    musl-dev \
    python3-dev \
    curl \
    bash \
    aws-cli \
    groff \
    less

# Verify AWS CLI installation
RUN aws --version

# Set up SSH for GitHub (needed for git@ URLs)
RUN mkdir -p /root/.ssh && \
    echo "Host github.com\n\tStrictHostKeyChecking no\n" > /root/.ssh/config

# Set a working directory
WORKDIR /build/

# Clone the yt-dlp repository (using HTTPS instead of SSH to avoid authentication issues)
RUN git clone https://github.com/yt-dlp/yt-dlp.git

# Build yt-dlp
WORKDIR /build/yt-dlp
RUN make
RUN make install

# Stage 2: Create the runtime image
FROM alpine:latest

# Install runtime dependencies
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    bash \
    aws-cli \
    groff \
    less

# Copy the built yt-dlp from the builder stage
COPY --from=builder /usr/local/bin/yt-dlp /usr/local/bin/yt-dlp

# Verify yt-dlp installation
RUN yt-dlp --version

WORKDIR /app/yt-dlp

COPY cookies.txt .

# Create a directory for downloads
RUN mkdir -p /downloads

# Set the working directory to /downloads
WORKDIR /downloads


# Create an entrypoint script
RUN echo -e '#!/bin/bash\n\
if [ -z "$VIDEO_ID" ]; then\n\
    echo "ERROR: VIDEO_ID environment variable is not set!"\n\
    echo "Usage: VIDEO_ID=<youtube-url-or-id> ./run.sh"\n\
    exit 1\n\
fi\n\
\n\
echo "Downloading video: $VIDEO_ID"\n\
yt-dlp  --output "/downloads/%(title)s.%(ext)s" --yes-playlist --cookies /app/yt-dlp/cookies.txt -x --audio-format mp3 "$@" "$VIDEO_ID"\n\
\n\
# Fix permissions since Docker might run as root\n\
chmod -R 777 /downloads/\n\
echo "Download complete! Video saved in data directory."\n\
' > /entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
#CMD ["/bin/bash"]
