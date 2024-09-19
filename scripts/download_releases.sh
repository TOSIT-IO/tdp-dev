#!/bin/bash

while IFS=";" read -r uri_file_name file_name
do
if [[ -n "$file_name" ]]
then
    wget --no-clobber --output-document=files/${file_name} ${uri_file_name}
else
    wget --no-clobber --directory-prefix="files" ${uri_file_name}
fi
done < scripts/tdp-release-uris.txt

echo "Download complete!"
