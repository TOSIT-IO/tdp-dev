#!/bin/bash

# Define the VM IP addresses in /etc/hosts

input_file=/home/ubuntu/hosts

echo -e "\n#TDP Cluster" >> /etc/hosts

while read -r line; do
    if echo "$line" | grep -q "ansible_host"; then
        node=$(echo "$line" | awk '{print $1}')
        ip=$(echo "$line" | grep -oP "ip=\K[^\s]+")
        domain=$(echo "$line" | grep -oP "domain=\K[^\s]+")
        echo "$ip   $node.$domain" >> /etc/hosts
    fi
done < $input_file

# Remove the the initial hosts file
rm -f $input_file

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
