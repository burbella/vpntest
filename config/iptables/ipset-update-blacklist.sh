#!/bin/bash
#-----updates the blacklist ipset-----
# create/add/swap/destroy
# create and add commands are in the restore file
ipset restore -file /etc/iptables/ipset-update-blacklist.conf -quiet
ipset swap blacklist blacklist2 -quiet
ipset destroy blacklist2 -quiet
