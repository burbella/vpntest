#!/bin/sh
#-----updates iptables with the latest settings-----
# the daemon will save custom IP's to ip-blacklist.conf
# makes routing work
# install this file in /etc/iptables

# Save Rules:
# netfilter-persistent save

# Restore Rules:
# netfilter-persistent start

#-----flush rules and import fresh rules to avoid duplicates-----
# NAT rules
cp /etc/iptables/iptables-zzz.conf /etc/iptables/iptables.conf
# FILTER rules
cat /etc/iptables/ip-allowlist.conf >> /etc/iptables/iptables.conf
cat /etc/iptables/ip-blacklist.conf >> /etc/iptables/iptables.conf
cat /etc/iptables/ip-countries.conf >> /etc/iptables/iptables.conf
cat /etc/iptables/ip-log-accepted.conf >> /etc/iptables/iptables.conf
cat /etc/iptables/ip-blacklist-footer.conf >> /etc/iptables/iptables.conf
chmod 444 /etc/iptables/iptables.conf

#-----flush all rules from all tables-----
iptables -F

#-----create/recreate custom chains without errors-----
# -X only works after -F is used to dump the linked rules
# -N only works if you're sure the the chain is gone
iptables -t filter -X LOGACCEPT 2>/dev/null
iptables -t filter -N LOGACCEPT
iptables -t filter -X LOGREJECT 2>/dev/null
iptables -t filter -N LOGREJECT
iptables -t filter -X CUSTOMRULES 2>/dev/null
iptables -t filter -N CUSTOMRULES

#-----load rules from the auto-generated config file-----
iptables-restore < /etc/iptables/iptables.conf

#-----save config so it loads on boot-----
netfilter-persistent save
