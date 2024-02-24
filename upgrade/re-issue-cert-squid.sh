#!/bin/bash
#-----SSL certs over 1 year duration are not accepted in some browsers, so re-issue squid intermediate CA every month-----
# Reference: /upgrade/replace_pki.sh
#            /install/070_setup-pki.sh
# EasyRSA Var File: /config/easyrsa/vars-squid
#
#--------------------------------------------------------------------------------

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR, VARS_FILENAME_SQUID_TOP_CA

EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`
VARS_SQUID_TOP_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_SQUID_TOP_CA

SQUID_INSTALL_DIR=/etc/squid/ssl_cert
SQUID_COMBINED_FILENAME=squid-ca-nopass.pem
SQUID_INSTALLED_CERT=$SQUID_INSTALL_DIR/$SQUID_COMBINED_FILENAME

zzzConfig_CA_Pass_Squid_Top=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-squid-top'`
ZZZ_TWO=2
zzzConfig_CA_Pass_Squid_Top2=$zzzConfig_CA_Pass_Squid_Top$ZZZ_TWO

cd $EASYRSA_DIR

#-----flush squid SSL cert cache-----
/home/ubuntu/bin/squid-clear-cert-cache no-restart

#-----backup the old squid CA-----
# The old squid CA will be destroyed!
TODAY_YYYYMMDD=`date '+%Y%m%d'`
cp -p $SQUID_INSTALLED_CERT $SQUID_INSTALLED_CERT.$TODAY_YYYYMMDD

#-----revoke the old squid intermediate CA cert in the squid-top CA-----
./easyrsa --vars=$VARS_SQUID_TOP_CA --passin="file:$zzzConfig_CA_Pass_Squid_Top" --passout="file:$zzzConfig_CA_Pass_Squid_Top2" revoke squid-ca

#TODO: instead of replacing both squid CA's, just replace the lower one
#      that way, the root CA is not involved
#-----Build a new PKI for the intermediate CA-----
/opt/zzz/util/init-squid-pki.sh

systemctl start squid
systemctl start squid-icap

