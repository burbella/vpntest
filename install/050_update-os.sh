#!/bin/bash

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----Update OS-----
# use "upgrade" instead of "dist-upgrade"
# we're doing just package upgrades, not a full OS distro upgrade
# presumably the VM initialized with the correct distro
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade

echo "$ZZZ_SCRIPTNAME - END"
