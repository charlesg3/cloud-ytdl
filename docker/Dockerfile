# Start with the AWS Lambda Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

# Set environment variables
ENV YTDLP_VERSION=2025.03.31

# Install necessary tools
RUN dnf install -y tar xz gzip && \
    dnf clean all

# Set working directory
WORKDIR /tmp

# Download and install ffmpeg using statically linked version
# This eliminates the need to deal with shared libraries
RUN curl -L  "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz" | \
        tar -xJ --strip-components=1 \
        --exclude="*/doc/*" \
        --exclude="*/share/man/*" \
        --exclude="*/share/ffmpeg/examples/*" && \
    # Move just the binaries to a location in PATH
    cp bin/ffmpeg bin/ffprobe /usr/local/bin/ && \
    # Clean up
    rm -rf bin include share

# Download and install yt-dlp
RUN curl -L "https://github.com/yt-dlp/yt-dlp/releases/download/${YTDLP_VERSION}/yt-dlp" -o /usr/local/bin/yt-dlp && \
    chmod +x /usr/local/bin/yt-dlp

# Return to Lambda task directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy your Lambda function code
#COPY requirements.txt .
#RUN pip install -r requirements.txt

# Copy the rest of your function code
COPY src .

# Set the CMD to your handler
CMD [ "extract.lambda_handler" ]
