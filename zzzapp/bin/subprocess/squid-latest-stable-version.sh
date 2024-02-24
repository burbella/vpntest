#!/bin/bash
#-----find the latest stable version of Squid-----

source /opt/zzz/util/util.sh

SRC_DIR=/home/ubuntu/src
SQUID_SRC=$SRC_DIR/squid

cd $SQUID_SRC

#-----update the tag list-----
git fetch >> /dev/null

#SQUID_LATEST_STABLE_VERSION=`git tag|grep 'SQUID_'|tail -1`
SQUID_LATEST_STABLE_VERSION=$ZZZ_SQUID_VERSION_TAG

echo $SQUID_LATEST_STABLE_VERSION
