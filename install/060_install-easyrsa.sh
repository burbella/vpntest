#!/bin/bash

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

SRC_DIR=/home/ubuntu/src
EASYRSA_SRC=$SRC_DIR/easy-rsa
EASYTLS_SRC=$SRC_DIR/easy-tls

cd $SRC_DIR
git clone https://github.com/OpenVPN/easy-rsa.git
cd $EASYRSA_SRC

#-----future versions might require programming edits, so hardcode a known-working version-----
EASYRSA_LATEST_STABLE_VERSION=`git tag|tail -1`
#git checkout tags/$EASYRSA_LATEST_STABLE_VERSION
git checkout tags/v3.1.6

cp -rp $SRC_DIR/easy-rsa/easyrsa3 /home/ubuntu
#-----version number is near the top of the ChangeLog-----
cp $EASYRSA_SRC/ChangeLog /home/ubuntu/easyrsa3

#--------------------------------------------------------------------------------

#-----Easy-TLS-----
cd $SRC_DIR
git clone https://github.com/TinCanTech/easy-tls.git

cd $EASYTLS_SRC
git checkout tags/v2.7.0

echo "$ZZZ_SCRIPTNAME - END"
