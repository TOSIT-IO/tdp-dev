FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Kerberos client and common properties software
RUN apt-get update && apt-get install -y \
    krb5-user \
    sssd-krb5 \
    software-properties-common \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install firefox-esr and libnss3-tools for certificate management
RUN add-apt-repository ppa:mozillateam/ppa
RUN apt install -y firefox-esr libnss3-tools

# Copy Kerberos configuration files if you have any (optional)
ADD firefox-container/krb5.conf /etc/krb5.conf

# Add the SSL certificate
ADD files/tdp_getting_started_certs/tdp_ca.crt /home/ubuntu/tdp_ca.crt

# Add the docker-entrypoint.sh script.
ADD firefox-container/docker-entrypoint.sh /usr/local/bin

# Add the inventory/hosts file to later add the VM IPs to /etc/hosts
ADD inventory/hosts /home/ubuntu/hosts

WORKDIR /home/ubuntu

# Script preparing /etc/hosts SSL certificate and firefox config
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
