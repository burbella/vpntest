#!/bin/bash
#-----upgrade TLD DB list to the latest version-----
# weekly cron?

echo "upgrade-tld.sh - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

SRC_DIR=/home/ubuntu/src

TLD_FILE=TLD-list.txt
TLD_FILEPATH=$SRC_DIR/$TLD_FILE
TLD_URL="https://data.iana.org/TLD/tlds-alpha-by-domain.txt"

cd $SRC_DIR

#-----download from iana.org-----
# https://data.iana.org/TLD/tlds-alpha-by-domain.txt
# /opt/zzz/data/TLD-list.txt
wget -q --output-document=$TLD_FILEPATH $TLD_URL

#-----zero-size file means the download failed-----
if [ ! -s $TLD_FILEPATH ]
then
    echo "ERROR: download failed, file is zero-size"
    echo "$TLD_FILEPATH"
    echo "Check if the file is on the IANA website:"
    echo "$TLD_URL"
    exit
fi

cp $TLD_FILEPATH /opt/zzz/data/

#-----update the TLD DB table and configs that depend on it-----
/opt/zzz/python/bin/build-config.py --tld

echo
echo "upgrade-tld.sh - END"
