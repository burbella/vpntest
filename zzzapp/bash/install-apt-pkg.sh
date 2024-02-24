#!/bin/bash
#-----install an OS package with apt-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

PKG_NAME=$1

if [[ "$PKG_NAME" == "" ]]; then
    echo "ERROR: no package specified"
    exit
fi

if [[ "$PKG_NAME" =~ ^([A-Za-z0-9.+-])*$ ]]; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install $PKG_NAME
else
    echo "invalid package name"
fi
