#!/bin/bash
#-----creates empty country ipsets-----
#ipset restore -file /etc/iptables/ipset-create-countries.conf
#-----creates an empty country ipset-----
ipset create countries hash:net family inet hashsize 1024 maxelem 250000 -exist -quiet
