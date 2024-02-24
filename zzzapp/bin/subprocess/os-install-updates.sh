#!/bin/bash
#-----install the OS updates-----
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade
