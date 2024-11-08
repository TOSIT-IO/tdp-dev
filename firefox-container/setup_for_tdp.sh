#!/bin/bash

# Define the VM IP addresses in /etc/hosts
echo "Updating /etc/hosts with TDP Cluster IPs..."
echo "
# TDP Cluster
192.168.56.10   edge-01.tdp
192.168.56.11   master-01.tdp
192.168.56.12   master-02.tdp
192.168.56.13   master-03.tdp
192.168.56.14   worker-01.tdp
192.168.56.15   worker-02.tdp
192.168.56.16   worker-03.tdp" >> /etc/hosts

# Locate or create the Firefox profile
BASE_PROFILE_DIR="/root/.mozilla/firefox"
PROFILE_DIR=$(find "$BASE_PROFILE_DIR" -maxdepth 1 -name "*.tdp-profile" -print -quit)

if [ -z "$PROFILE_DIR" ]; then
    echo "Creating Firefox profile..."
    firefox -CreateProfile "tdp-profile" &
    sleep 5 
    pkill -15 -f firefox
    PROFILE_DIR=$(find "$BASE_PROFILE_DIR" -maxdepth 1 -name "*.tdp-profile" -print -quit)
fi

# Verify prefs.js existence
PREFS_JS="$PROFILE_DIR/prefs.js"
if [ ! -f "$PREFS_JS" ]; then
    echo "Initializing Firefox profile..."
    firefox -no-remote -P "tdp-profile" &
    sleep 5
    pkill -15 -f firefox
fi

# Check for prefs.js again
if [ ! -f "$PREFS_JS" ]; then
    echo "Error: prefs.js not found. Exiting..."
    exit 1
fi

# Check if the certificate file exists
CERT_PATH="/root/files/tdp_getting_started_certs/tdp_ca.crt"
if [ ! -f "$CERT_PATH" ]; then
    echo "Error: Certificate not found at $CERT_PATH."
    echo "Please run the TDP prerequisites playbook to generate the TDP Cluster certificate."
    exit 1
fi

# Add certificate to Firefox
echo "Adding TDP Cluster certificate to Firefox..."
certutil -A -n "tdp_ca.crt" -t "CT,C,C" -i "$CERT_PATH" -d sql:"$PROFILE_DIR"

# Add the Kerberos REALM to Firefox prefs
echo "Adding TDP Kerberos REALM to Firefox..."
echo 'user_pref("network.negotiate-auth.trusted-uris", ".tdp");' >> "$PREFS_JS"
