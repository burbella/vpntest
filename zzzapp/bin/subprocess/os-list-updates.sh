#!/bin/bash
#-----list the OS updates available-----
apt-get -y -qq update
sudo DEBIAN_FRONTEND=noninteractive apt-get -s -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade

