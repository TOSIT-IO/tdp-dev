# Start with the vagrantlibvirt/vagrant-libvirt image as base
FROM vagrantlibvirt/vagrant-libvirt:latest

ENV DEBIAN_FRONTEND=noninteractive

# Add deadsnakes PPA for installing Python 3.9 on Ubuntu 22.04
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update

# Install required packages including Python 3.9, venv, and other tools
RUN apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-venv \
    python3.9-distutils \
    ansible \
    vim \
    jq \
    wget \
    git \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Set up Python 3.9 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

CMD ["/bin/bash"]