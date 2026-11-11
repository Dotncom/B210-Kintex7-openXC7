#!/bin/bash
set -eu
upstream=$(realpath -- "$1")
db=$2
mkdir -- "$db"
mkdir "$db/kintex7"
for path in "$upstream"/*; do
    if [ "${path##*/}" != kintex7 ]; then
        ln -s "$path" "$db/"
    fi
done
for path in "$upstream/kintex7"/*; do
    ln -s "$path" "$db/kintex7/"
done

part=xc7k325tffg676-2
package_ref=xc7k325tffg676-1
speed_ref=xc7k325tffg900-2
if [ ! -d "$db/kintex7/$part" ]; then
    # These part.yaml records are byte-identical. The package bank map
    # and pin CSV belong to FFG676.
    cmp "$db/kintex7/$package_ref/part.yaml" "$db/kintex7/$speed_ref/part.yaml"
    mkdir "$db/kintex7/$part"
    for file in package_pins.csv part.json part.yaml; do
        ln -s "$db/kintex7/$package_ref/$file" "$db/kintex7/$part/$file"
    done
    echo "Using FFG676 physical map and generic openXC7 timing" >&2
fi
printf '%s\n' "$db"
