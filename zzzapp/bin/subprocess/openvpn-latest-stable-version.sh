#!/bin/bash
#-----find the latest stable version of OpenVPN-----

SRC_DIR=/home/ubuntu/src
OPENVPN_SRC=$SRC_DIR/openvpn

cd $OPENVPN_SRC

#-----update the tag list-----
git fetch >> /dev/null

OPENVPN_LATEST_STABLE_VERSION=`git tag | grep -v '_' | sort --version-sort | tail -1`

echo $OPENVPN_LATEST_STABLE_VERSION
