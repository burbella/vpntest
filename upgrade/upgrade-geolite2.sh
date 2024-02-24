#!/bin/bash
#-----upgrade Maxmind GeoLite2 to the latest version-----
# weekly cron?
# auto-update app from maxmind?

echo "upgrade-geolite2.sh - START"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

SRC_DIR=/home/ubuntu/src
cd $SRC_DIR

echo "upgrade-geolite2.sh - UNFINISHED"

echo
echo "upgrade-geolite2.sh - END"
