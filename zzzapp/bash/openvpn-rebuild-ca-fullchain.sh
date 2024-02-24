#!/bin/bash
#-----OpenVPN fullchain fix-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: MINIMAL_DEFAULT_PUBLIC_CERT, MINIMAL_OPENVPN_PUBLIC_CERT, REPOS_DIR, ZZZ_OPENVPN_CRLS_DIR

#--------------------------------------------------------------------------------

#-----make the CA cert hash files that OpenVPN requires for CRL verify to work-----
HASH_DEFAULT_PUBLIC_CERT=`openssl x509 -hash -noout -in $MINIMAL_DEFAULT_PUBLIC_CERT`
HASH_OPENVPN_PUBLIC_CERT=`openssl x509 -hash -noout -in $MINIMAL_OPENVPN_PUBLIC_CERT`
FILENAME_HASH_DEFAULT=$HASH_DEFAULT_PUBLIC_CERT.2
FILENAME_HASH_OPENVPN=$HASH_OPENVPN_PUBLIC_CERT.1
cp $MINIMAL_DEFAULT_PUBLIC_CERT $ZZZ_OPENVPN_CRLS_DIR/$FILENAME_HASH_DEFAULT
cp $MINIMAL_OPENVPN_PUBLIC_CERT $ZZZ_OPENVPN_CRLS_DIR/$FILENAME_HASH_OPENVPN

#--------------------------------------------------------------------------------

#-----install OpenVPN CA cert-----
OPENVPN_INSTALL_DIR=/etc/openvpn
OPENVPN_INSTALLED_CERT=$OPENVPN_INSTALL_DIR/ca-fullchain.crt

#-----use the minimal certs to make the fullchain file-----
cp $MINIMAL_DEFAULT_PUBLIC_CERT $OPENVPN_INSTALLED_CERT
echo "" >> $OPENVPN_INSTALLED_CERT
cat $MINIMAL_OPENVPN_PUBLIC_CERT >> $OPENVPN_INSTALLED_CERT
chown root.root $OPENVPN_INSTALLED_CERT
chmod 600 $OPENVPN_INSTALLED_CERT

