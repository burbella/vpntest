#!/bin/bash
#-----provide the cert pass to apache-----

#TEST
# ZZZ_PARAM1=$1
# ZZZ_PARAM2=$2
# ZZZ_PARAM3=$3
# echo "ZZZ_PARAM1=$ZZZ_PARAM1" > /tmp/zzz_apache-cert-pass_params.txt
# echo "ZZZ_PARAM2=$ZZZ_PARAM2" >> /tmp/zzz_apache-cert-pass_params.txt
# echo "ZZZ_PARAM3=$ZZZ_PARAM3" >> /tmp/zzz_apache-cert-pass_params.txt
#ENDTEST

APACHE_PASS_DATA=`cat /opt/zzz/data/ssl-private/apache-server.pass`
echo -n $APACHE_PASS_DATA
