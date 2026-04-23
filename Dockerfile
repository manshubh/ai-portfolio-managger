# Dockerfile — skills-env container for the AI Portfolio Manager skill layer.
# Provides Python 3.11, sqlite3, shellcheck, jq, and pyyaml.
# See plans/M0/M0.9-docker-env.md for design rationale.

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    sqlite3 \
    shellcheck \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies globally for the skill layer
# (Will be populated further in later milestones like M3, M4, M6)
RUN pip install --no-cache-dir pyyaml --break-system-packages

WORKDIR /workspace

# Set default command
CMD ["bash"]
