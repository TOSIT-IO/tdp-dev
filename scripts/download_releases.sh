#!/bin/bash

# Allowed collections
ALLOWED_COLLECTIONS=("tdp-collection" "tdp-observability" "tdp-extras")
downloads_file="scripts/tdp-release-uris.json"

is_valid_collection() {
    [[ " ${ALLOWED_COLLECTIONS[*]} " =~ " $1 " ]] || [ "$1" == "all" ]
}

download_files() {
    local collection_name="$1"
    if ! jq -e ".\"$collection_name\"" "$downloads_file" > /dev/null; then
        echo "Collection '$collection_name' not found in $downloads_file."
        return
    fi
    jq -c ".\"$collection_name\" | to_entries[]" "$downloads_file" | while read -r entry; do
        dest_file=$(echo "$entry" | jq -r '.value.name')
        download_url=$(echo "$entry" | jq -r '.value.link')
        echo "Downloading: $dest_file"
        wget --quiet --continue --output-document="files/${dest_file}" "$download_url"
    done
}

if [ $# -eq 0 ]; then
    echo "Usage: $0 <collection1> <collection2> ... <collectionN | all>"
    echo "Allowed collections: ${ALLOWED_COLLECTIONS[*]} or 'all'"
    exit 1
fi

for collection in "$@"; do
    if ! is_valid_collection "$collection"; then
        echo "Error: '$collection' is not a valid collection."
        echo "Allowed collections: ${ALLOWED_COLLECTIONS[*]} or 'all'"
        exit 1
    fi
done

if [[ " $* " == *" all "* ]]; then
    echo "Downloading all collections..."
    for collection in "${ALLOWED_COLLECTIONS[@]}"; do
        download_files "$collection"
    done
else
    for collection in "$@"; do
        download_files "$collection"
    done
fi
