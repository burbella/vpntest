#!/bin/bash
#-----updates the country ipsets for ipv6-----
# create/add/swap/destroy
# all commands are in the restore file
# the restore file starts empty, until a user adds countries in the Settings page
ipset restore -file /etc/iptables/ipset-ipv6-update-countries.conf -quiet

