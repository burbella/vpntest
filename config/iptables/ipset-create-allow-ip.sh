#!/bin/bash
#-----creates empty allow-ip ipset-----
ipset create allow-ip hash:net family inet hashsize 1024 maxelem 500000 -exist -quiet
