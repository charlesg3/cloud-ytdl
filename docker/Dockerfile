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
RUN mkdir -p /data

# Set the working directory to /downloads
WORKDIR /data

CMD ["/bin/bash"]
