#!/bin/bash

if [ -z "${tdp_release_script_path}" ]; then
    tdp_release_script_path=scripts/tdp-v2-release-uris.txt
fi

while IFS=";" read -r uri_file_name file_name
do
    if [[ -n "$file_name" ]]
    then
        curl -v -L -o "files/${file_name}" "${uri_file_name}"
    else
        curl -v -L -O --output-dir "files" "${uri_file_name}"
    fi
done < ${tdp_release_script_path}

echo "Download complete!"
