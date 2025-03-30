# Use latest Ubuntu as base image
FROM ubuntu:latest

# Set non-interactive installation mode
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    make \
    pandoc \
    zip \
    ffmpeg \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH for GitHub (needed for git@ URLs)
RUN mkdir -p /root/.ssh && \
    echo "Host github.com\n\tStrictHostKeyChecking no\n" > /root/.ssh/config

# Set a working directory
WORKDIR /app

# Clone the yt-dlp repository (using HTTPS instead of SSH to avoid authentication issues)
RUN git clone https://github.com/yt-dlp/yt-dlp.git

# Build yt-dlp
WORKDIR /app/yt-dlp
RUN make
RUN make install

# Create a directory for downloads
RUN mkdir -p /downloads

# Set the working directory to /downloads
WORKDIR /downloads

# Create an entrypoint script
RUN echo '#!/bin/bash\n\
if [ -z "\$VIDEO_ID" ]; then\n\
    echo "ERROR: VIDEO_ID environment variable is not set!"\n\
    echo "Usage: VIDEO_ID=<youtube-url-or-id> ./run.sh"\n\
    exit 1\n\
fi\n\
\n\
echo "Downloading video: \$VIDEO_ID"\n\
yt-dlp "\$VIDEO_ID" --output "/downloads/%(title)s.%(ext)s" "\$@"\n\
\n\
# Fix permissions since Docker might run as root\n\
chmod -R 777 /downloads/\n\
echo "Download complete! Video saved in data directory."\n\
' > /entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
