FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    python3-tk \
    curl \
    git \
    gosu \
    graphviz \
    openssh-client \
    vim \ 
    && rm -rf /var/lib/apt/lists/*

# Location of poetry installation
ENV POETRY_HOME=/usr/local

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# Create the tdp directory
RUN mkdir -p /home/tdp/tdp-dev

# Set tdp as working directory
WORKDIR /home/tdp/tdp-dev

# Use docker-entrypoint.sh as entrypoint
COPY . /usr/local/bin
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
