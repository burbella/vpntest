#!/bin/bash
#-----creates empty countries ipset for ipv6-----
ipset create countries-ipv6 hash:net family inet6 hashsize 64 maxelem 50000 -exist -quiet
