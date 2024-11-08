FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
        wget \
        gnupg2 \
        krb5-user \
        libcanberra-gtk-module \
        libcanberra-gtk3-module \
        libdbus-glib-1-2 \
        libgl1 \
        libegl1 \
        libpci3 \
        libnss3-tools \
        dbus-x11 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Firefox
RUN mkdir -p /etc/apt/keyrings && \
    wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- | tee /etc/apt/keyrings/packages.mozilla.org.asc > /dev/null && \
    echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" | tee /etc/apt/sources.list.d/mozilla.list > /dev/null && \
    echo "Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000" | tee /etc/apt/preferences.d/mozilla && \
    apt-get update && \
    apt-get install -y firefox && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy configuration and entrypoint files
COPY krb5.conf /etc/krb5.conf
COPY setup_for_tdp.sh /root/setup_for_tdp.sh
RUN chmod +x /root/setup_for_tdp.sh

CMD ["/bin/bash"]
