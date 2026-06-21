# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install Python 3.13
RUN apt-get update && apt-get install -y \
    software-properties-common \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.13 \
    python3.13-dev \
    python3.13-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.13 as default and install pip
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.13 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1 && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13 && \
    rm -f /usr/local/bin/pip && \
    ln -s /usr/local/bin/pip3 /usr/local/bin/pip

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run as a non-root user (created after deps are installed). /app and the writable
# uploads dir are chowned so the app can persist images.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads/batches \
    && chown -R appuser:appuser /app
USER appuser

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Container healthcheck hits the liveness probe (falls back to / on older images).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || curl -fsS http://localhost:8000/ || exit 1

# Use the entrypoint (waits for DB, runs migrations) then starts the server.
ENTRYPOINT ["./docker-entrypoint.sh"]
