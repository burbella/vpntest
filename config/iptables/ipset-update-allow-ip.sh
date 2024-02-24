#!/bin/bash
#-----updates the allow-ip ipset-----
# create/add/swap/destroy
# create and add commands are in the restore file
ipset restore -file /etc/iptables/ipset-update-allow-ip.conf -quiet
ipset swap allow-ip allow-ip2 -quiet
ipset destroy allow-ip2 -quiet
