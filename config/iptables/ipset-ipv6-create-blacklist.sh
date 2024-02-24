#!/bin/bash
#-----creates empty blacklist ipset for ipv6-----
ipset create blacklist-ipv6 hash:net family inet6 hashsize 1024 maxelem 65536 -exist -quiet
