# Use NVIDIA PyTorch base image for TotalSegmentator compatibility
FROM nvcr.io/nvidia/pytorch:23.05-py3

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with numpy compatibility
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "numpy<2.0" && \
    pip install --no-cache-dir pandas && \
    pip install --no-cache-dir fury && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Install TotalSegmentator first
RUN cd TotalSegmentator && pip install -e .

# Download TotalSegmentator pretrained weights
RUN python TotalSegmentator/totalsegmentator/download_pretrained_weights.py

# Install the medview package in development mode
RUN pip install -e .
