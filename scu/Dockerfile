# Corrected the base image to a stable Python version and ensured compatibility with dependencies.
FROM python:3.12-slim-bullseye

LABEL maintainer="Carlos Queiroz"

# Python unbuffered para logs em tempo real
ENV PYTHONUNBUFFERED=1

# Install necessary dependencies
RUN apt-get update && apt-get install -y \
    plastimatch imagemagick dcmtk inotify-tools libgdcm-tools rsync && \
    apt-get clean

# Install Python libraries
RUN pip install --no-cache-dir environs pydicom python-dotenv requests numpy colorama

# Copy the main script to the container
COPY scu_script.py /home/scu_script.py

# Set the default command to execute the script
CMD ["python", "/home/scu_script.py"]


