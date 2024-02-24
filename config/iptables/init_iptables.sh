#!/bin/sh
#-----initializes iptables on Zzz app install-----
# makes routing work
# install this file in /etc/iptables

# Save Rules:
# netfilter-persistent save

# Restore Rules:
# netfilter-persistent start

#-----flush rules and import fresh rules to avoid duplicates-----
cp /etc/iptables/iptables-zzz.conf /etc/iptables/iptables.conf
cat /etc/iptables/ip-blacklist-empty.conf >> /etc/iptables/iptables.conf
chmod 444 /etc/iptables/iptables.conf

iptables -F
iptables-restore < /etc/iptables/iptables.conf

netfilter-persistent save
