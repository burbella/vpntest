#!/bin/bash
#-----creates empty blacklist ipset-----
ipset create blacklist hash:net family inet hashsize 1024 maxelem 500000 -exist -quiet
