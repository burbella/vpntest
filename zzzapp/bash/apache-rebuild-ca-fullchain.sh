#!/bin/bash
#-----Apache fullchain fix-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: MINIMAL_DEFAULT_PUBLIC_CERT, MINIMAL_OPENVPN_PUBLIC_CERT, REPOS_DIR, ZZZ_CERT_DATA_DIR

PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
OPENVPN_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/OpenVPN'`

#--------------------------------------------------------------------------------

ZZZ_APACHE_DOMAIN=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
APACHE_CERT=/etc/ssl/certs/$ZZZ_APACHE_DOMAIN.crt
DEFAULT_PUBLIC_CERT=$PKI_DIR/ca.crt
OPENVPN_PUBLIC_CERT=$OPENVPN_PKI_DIR/ca.crt
ZZZ_APACHE_ALL_CERTS=`/opt/zzz/python/bin/config-parse.py --var 'PKI/apache_all_certs'`

#--------------------------------------------------------------------------------

#-----use the minimal certs to make the fullchain file-----
/opt/zzz/util/output_minimal_cert_data.sh apache
MINIMAL_APACHE_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/$ZZZ_APACHE_DOMAIN.crt

#-----install apache by itself-----
cp $MINIMAL_APACHE_PUBLIC_CERT $APACHE_CERT
chown root.root $APACHE_CERT
chmod 644 $APACHE_CERT

#-----install the fullchain file-----
# APACHE_CERT + OPENVPN_PUBLIC_CERT + DEFAULT_PUBLIC_CERT --> ZZZ_APACHE_ALL_CERTS
cp $APACHE_CERT $ZZZ_APACHE_ALL_CERTS
cat $MINIMAL_OPENVPN_PUBLIC_CERT >> $ZZZ_APACHE_ALL_CERTS
cat $MINIMAL_DEFAULT_PUBLIC_CERT >> $ZZZ_APACHE_ALL_CERTS
chown root.root $ZZZ_APACHE_ALL_CERTS
chmod 644 $ZZZ_APACHE_ALL_CERTS
