#!/bin/bash
#-----upgrade ipdeny.com to the latest version-----
# weekly cron?

echo "upgrade-ipdeny.sh - START"
date

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

SRC_DIR=/home/ubuntu/src

# 2/21/2024:
# https://www.ipdeny.com/ipblocks/data/countries/all-zones.tar.gz
IPV4_FILE=ipdeny-ipv4-all-zones.tar.gz
# IPV4_URL="https://ipdeny.com/ipblocks/data/countries/all-zones.tar.gz"
IPV4_URL="https://www.ipdeny.com/ipblocks/data/countries/all-zones.tar.gz"

# 2/21/2024:
# https://www.ipdeny.com/ipv6/ipaddresses/blocks/ipv6-all-zones.tar.gz
IPV6_FILE=ipdeny-ipv6-all-zones.tar.gz
# IPV6_URL="https://ipdeny.com/ipv6/ipaddresses/blocks/ipv6-all-zones.tar.gz"
IPV6_URL="https://www.ipdeny.com/ipv6/ipaddresses/blocks/ipv6-all-zones.tar.gz"

cd $SRC_DIR

#-----download from ipdeny.com-----
# http://ipdeny.com/ipblocks/data/countries/all-zones.tar.gz
# http://ipdeny.com/ipv6/ipaddresses/blocks/ipv6-all-zones.tar.gz
# MD5 Checksum:
#   http://ipdeny.com/ipblocks/data/countries/MD5SUM

#-----IPv4-----
# ipdeny.com SSL cert expired 5/19/2021, use --no-check-certificate until they fix it
# wget -q --no-check-certificate --output-document=$SRC_DIR/$IPV4_FILE $IPV4_URL
wget -q --output-document=$SRC_DIR/$IPV4_FILE $IPV4_URL
#-----zero-size file means the download failed-----
if [ ! -s $SRC_DIR/$IPV4_FILE ]
then
    echo "ERROR: download failed, file is zero-size"
    echo "$SRC_DIR/$IPV4_FILE"
    echo "Check if the file is on the ipdeny website:"
    echo "https://www.ipdeny.com/ipblocks/"
    echo "$IPV4_URL"
    exit
else
    cp $SRC_DIR/$IPV4_FILE /opt/zzz/data/ipdeny-ipv4
    cd /opt/zzz/data/ipdeny-ipv4
    tar -zxf $IPV4_FILE
fi

sleep 1

#-----IPv6-----
# wget -q --no-check-certificate --output-document=$SRC_DIR/$IPV6_FILE $IPV6_URL
wget -q --output-document=$SRC_DIR/$IPV6_FILE $IPV6_URL
#-----zero-size file means the download failed-----
if [ ! -s $SRC_DIR/$IPV6_FILE ]
then
    echo "ERROR: download failed, file is zero-size"
    echo "$SRC_DIR/$IPV6_FILE"
    echo "Check if the file is on the ipdeny website:"
    echo "https://www.ipdeny.com/ipblocks/"
    echo "$IPV6_URL"
    exit
else
    cp $SRC_DIR/$IPV6_FILE /opt/zzz/data/ipdeny-ipv6
    cd /opt/zzz/data/ipdeny-ipv6
    tar -zxf $IPV6_FILE
fi

echo
echo "upgrade-ipdeny.sh - END"
