#!/bin/bash
#-----updates the blacklist ipset for ipv6-----
# create/add/swap/destroy
# create and add commands are in the restore file
ipset restore -file /etc/iptables/ipset-ipv6-update-blacklist.conf -quiet
ipset swap blacklist-ipv6 blacklist-ipv6-new -quiet
ipset destroy blacklist-ipv6-new -quiet
