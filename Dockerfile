FROM docker.1ms.run/alpine:latest

LABEL org.opencontainers.image.title="pdfcraft" \
      org.opencontainers.image.vendor="PoxenStudio" \
      org.opencontainers.image.source="https://github.com/PoxenStudio/pdf-craft"

# Install system dependencies
# gcompat provides basic glibc compatibility needed by PyTorch wheels
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    poppler-utils \
    build-base \
    libffi-dev \
    jpeg-dev \
    zlib-dev \
    libpng-dev \
    openjpeg-dev \
    freetype-dev \
    libwebp-dev \
    tiff-dev \
    gcompat \
    && rm -rf /var/cache/apk/*

# Use a virtual environment to isolate Python packages
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install PyTorch CPU build first (required before project dependencies)
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy and install the project
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

ENTRYPOINT ["/bin/sh"]
