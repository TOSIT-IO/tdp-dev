#!/bin/bash

while IFS=";" read -r uri_file_name file_name
do
    if [[ -n "$file_name" ]]
    then
        curl -v -L -o "files/${file_name}" "${uri_file_name}"
    else
        curl -v -L -O --output-dir "files" "${uri_file_name}"
    fi
done < scripts/tdp-release-uris.txt

echo "Download complete!"
