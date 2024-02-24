#!/bin/bash
#-----Squid fullchain file rebuild-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: MINIMAL_DEFAULT_PUBLIC_CERT, MINIMAL_SQUID_PUBLIC_CERT, MINIMAL_SQUID_TOP_PUBLIC_CERT, REPOS_DIR

PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
SQUID_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid'`
SQUID_TOP_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid-Top'`

#--------------------------------------------------------------------------------

DEFAULT_PUBLIC_CERT=$PKI_DIR/ca.crt

#--------------------------------------------------------------------------------

#-----separate Squid crt and key files-----
# FILES: /etc/squid/ssl_cert/squid-ca-nopass.crt
#        /etc/squid/ssl_cert/squid-ca-nopass.key
SQUID_INSTALL_DIR=/etc/squid/ssl_cert

SQUID_PRIVATE_KEY=$SQUID_PKI_DIR/private/ca.key
SQUID_INSTALLED_KEY=$SQUID_INSTALL_DIR/squid-ca-nopass.key

#-----install Squid CA key file-----
cp $SQUID_PRIVATE_KEY $SQUID_INSTALLED_KEY
chown proxy.proxy $SQUID_INSTALLED_KEY
chmod 640 $SQUID_INSTALLED_KEY

SQUID_INSTALLED_CERT=$SQUID_INSTALL_DIR/squid-ca-nopass.crt

#-----install Squid CA crt file-----
cp $MINIMAL_SQUID_PUBLIC_CERT $SQUID_INSTALLED_CERT
chown proxy.proxy $SQUID_INSTALLED_CERT
chmod 640 $SQUID_INSTALLED_CERT

#-----make a fullchain file for squid, with the Squid CA cert at the top-----
SQUID_FULLCHAIN_INSTALLED_CERT=$SQUID_INSTALL_DIR/squid-ca-nopass-fullchain.crt
cp $SQUID_INSTALLED_CERT $SQUID_FULLCHAIN_INSTALLED_CERT
cat $MINIMAL_SQUID_TOP_PUBLIC_CERT >> $SQUID_FULLCHAIN_INSTALLED_CERT
cat $MINIMAL_DEFAULT_PUBLIC_CERT >> $SQUID_FULLCHAIN_INSTALLED_CERT

chown proxy.proxy $SQUID_FULLCHAIN_INSTALLED_CERT
chmod 640 $SQUID_FULLCHAIN_INSTALLED_CERT
