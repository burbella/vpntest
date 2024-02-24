#!/bin/bash
#-----provide the cert pass to squid-----

SQUID_PASS_DATA=`cat /opt/zzz/data/ssl-private/ca-squid.pass`
echo -n $SQUID_PASS_DATA
