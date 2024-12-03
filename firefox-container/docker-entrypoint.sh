#!/bin/bash

# Define the VM IP addresses in /etc/hosts
echo "
# TDP Cluster
192.168.56.10   edge-01.tdp
192.168.56.11   master-01.tdp
192.168.56.12   master-02.tdp
192.168.56.13   master-03.tdp
192.168.56.14   worker-01.tdp
192.168.56.15   worker-02.tdp
192.168.56.16   worker-03.tdp" >> /etc/hosts

# Open firefox to create .mozilla in /home/ubuntu which contains the profile and extensions and close it
gosu ubuntu firefox-esr --headless &
sleep 1
pkill -15 -f firefox-esr

# Insert the TDP Cluster certificate in Firefox
certutil -A -n "tdp_ca.crt" -t "CT,C,C" -i /home/ubuntu/tdp_ca.crt -d $(ls -d /home/ubuntu/.mozilla/firefox-esr/*.default-*)

# Set the Kerberos REALM name in Firefox preferences
echo 'user_pref("network.negotiate-auth.trusted-uris", ".tdp");' >> $(ls -d /home/ubuntu/.mozilla/firefox-esr/*.default-*/prefs.js)

# Switch to user ubuntu
if [[ -z "$@" ]]; then
    exec gosu ubuntu /bin/bash
else
    exec gosu ubuntu "$@"
fi

exec "$@"
