#!/bin/bash

echo "Find Large Files/Directories"
echo
echo "This may take a while to find all the largest files on the server."
echo "Each version of squid compiled will have a separate 900MB directory under /home/ubuntu/src/"
echo "It is normal for these directories to be large:
    /home
    /home/ubuntu
    /home/ubuntu/src
    /usr
    /var
    /var/log
"

# sudo nice -n 19 find /. -size +10M -type f | head -100

SHOW_ALL_FILES=$1

if [[ "$SHOW_ALL_FILES" == "--show-all" ]]; then
    sudo nice -n 19 du -a --threshold=1M --exclude='proc' --exclude='snap' --exclude='snapd' --exclude='*.journal' / | sort -n -r
else
    sudo nice -n 19 du -a --threshold=1M --exclude='proc' --exclude='snap' --exclude='snapd' --exclude='*.journal' / | sort -n -r | head -100
fi

# Type(File/Directory) - Size - Name

