#!/bin/bash

# Define the VM IP addresses in /etc/hosts

if [[ -z "$EDGE_01_IP" ]]; then export EDGE_01_IP="192.168.56.10"; fi
if [[ -z "$MASTER_01_IP" ]]; then export MASTER_01_IP="192.168.56.11"; fi
if [[ -z "$MASTER_02_IP" ]]; then export MASTER_02_IP="192.168.56.12"; fi
if [[ -z "$MASTER_03_IP" ]]; then export MASTER_03_IP="192.168.56.13"; fi
if [[ -z "$WORKER_01_IP" ]]; then export WORKER_01_IP="192.168.56.14"; fi
if [[ -z "$WORKER_02_IP" ]]; then export WORKER_02_IP="192.168.56.15"; fi
if [[ -z "$WORKER_03_IP" ]]; then export WORKER_03_IP="192.168.56.16"; fi

echo "
# TDP Cluster
$EDGE_01_IP     edge-01.tdp
$MASTER_01_IP   master-01.tdp
$MASTER_02_IP   master-02.tdp
$MASTER_03_IP   master-03.tdp
$WORKER_01_IP   worker-01.tdp
$WORKER_02_IP   worker-02.tdp
$WORKER_03_IP   worker-03.tdp
$OTHER_1_IP     $OTHER_1_DOMAIN
$OTHER_2_IP     $OTHER_2_DOMAIN" >> /etc/hosts

# Create the Firefox profile
gosu ubuntu firefox-esr -CreateProfile "tdp" .mozilla/firefox-esr --headless

# Insert the TDP Cluster certificate in Firefox
gosu ubuntu certutil -A -n "tdp_ca.crt" -t "CT,C,C" -i /home/ubuntu/tdp_ca.crt -d $(ls -d .mozilla/firefox-esr/*.tdp)

# Add The Kerberos tdp Realm to Firefox
gosu ubuntu echo '
# Add tdp Realm in Firefox
user_pref("network.negotiate-auth.trusted-uris", ".tdp");' > $(ls -d .mozilla/firefox-esr/*.tdp)/user.js

# Set an alias for firefox to use firefox-esr with tdp profile
gosu ubuntu echo "alias firefox='firefox-esr -P tdp'" >> .bashrc

# Switch to user ubuntu
if [[ -z "$@" ]]; then
    exec gosu ubuntu /bin/bash
else
    exec gosu ubuntu "$@"
fi

exec "$@"
