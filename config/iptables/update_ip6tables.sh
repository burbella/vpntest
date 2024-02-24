#!/bin/sh
#-----updates iptables with the latest settings-----
# the daemon will save custom IP's to ip-blacklist.conf
# makes routing work
# install this file in /etc/iptables

# Save Rules:
# netfilter-persistent save

# Restore Rules:
# netfilter-persistent start

#-----IPv6 - flush/reload-----
cp /etc/iptables/ip6tables-zzz.conf /etc/iptables/ip6tables.conf
cat /etc/iptables/ip6-blacklist.conf >> /etc/iptables/ip6tables.conf
cat /etc/iptables/ip6-countries.conf >> /etc/iptables/ip6tables.conf
# the footer has the same commands for IPv4 and IPv6
cat /etc/iptables/ip-blacklist-footer.conf >> /etc/iptables/ip6tables.conf
chmod 444 /etc/iptables/ip6tables.conf

ip6tables -F
ip6tables-restore < /etc/iptables/ip6tables.conf

#-----save config so it loads on boot-----
netfilter-persistent save
