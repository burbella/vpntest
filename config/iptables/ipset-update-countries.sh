#!/bin/bash
#-----updates the country ipsets-----
# create/add/swap/destroy
# all commands are in the restore file
# the restore file starts empty, until a user adds countries in the Settings page
ipset restore -file /etc/iptables/ipset-update-countries.conf -quiet

