#!/bin/bash
set -euo pipefail
#set -x

root=/group_workspaces/jasmin2/cp4cds1/data/c3s-cmip5/output1

ens='r[12]i1p1'


for freq in mon day; do
    file="${freq}_files.txt"
    rm -f "$file"
    for model in $(cat models.txt); do
	for exp in historical rcp85; do
            for var in $(cat "${freq}_variables.txt"); do
		path="$root/*/$model/$exp/$freq/*/*/$ens/$var/latest/*.nc"
		echo Reading "$path"
		du -hscL $path | tail -n 1
		ls -1 $path >> "$file"
            done
	done
    done
    sort -u "$file" > tmp.txt
    mv tmp.txt "$file"
    tr '\n' '\0' < "$file" > "${file}0"
    du -hscL --files0-from="${file}0" | tail -n 1
done
