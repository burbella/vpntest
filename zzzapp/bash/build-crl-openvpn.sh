#!/bin/bash
#-----build/install the CRL for OpenVPN-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# set in util: VARS_FILENAME_OPENVPN_CA, ZZZ_OPENVPN_CRLS_DIR

OPENVPN_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/OpenVPN'`
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

zzzConfig_CA_Pass_OpenVPN=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-openvpn'`
ZZZ_TWO=2
zzzConfig_CA_Pass_OpenVPN2=$zzzConfig_CA_Pass_OpenVPN$ZZZ_TWO

VARS_OPENVPN_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_OPENVPN_CA

OPENVPN_CRL_EASYRSA=$OPENVPN_PKI_DIR/crl.pem
OPENVPN_CRL_INSTALLED=/etc/openvpn/crl.pem

cd $EASYRSA_DIR

#-----make the OpenVPN CA CRL-----
./easyrsa --vars=$VARS_OPENVPN_CA --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" gen-crl
cp $OPENVPN_CRL_EASYRSA $OPENVPN_CRL_INSTALLED
chmod 644 $OPENVPN_CRL_INSTALLED

HASH_OPENVPN_CRL=`openssl crl -hash -noout -in $OPENVPN_CRL_INSTALLED`
FILENAME_HASH_OPENVPN_CRL=$HASH_OPENVPN_CRL.r0
cp $OPENVPN_CRL_INSTALLED $ZZZ_OPENVPN_CRLS_DIR/$FILENAME_HASH_OPENVPN_CRL

#--------------------------------------------------------------------------------

#-----make a root CA CRL so the entire chain can be verified------
# set in util: VARS_FILENAME_DEFAULT_CA
VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA
zzzConfig_CA_Pass_Root=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-root'`
zzzConfig_CA_Pass_Root2=$zzzConfig_CA_Pass_Root$ZZZ_TWO

PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
DEFAULT_CRL_EASYRSA=$PKI_DIR/crl.pem
DEFAULT_CRL_INSTALLED=/etc/openvpn/crl-root.pem

./easyrsa --vars=$VARS_DEFAULT_CA --passin="file:$zzzConfig_CA_Pass_Root" --passout="file:$zzzConfig_CA_Pass_Root2" gen-crl
cp $DEFAULT_CRL_EASYRSA $DEFAULT_CRL_INSTALLED
chmod 644 $DEFAULT_CRL_INSTALLED

HASH_DEFAULT_CRL=`openssl crl -hash -noout -in $DEFAULT_CRL_INSTALLED`
FILENAME_HASH_DEFAULT_CRL=$HASH_DEFAULT_CRL.r0
cp $DEFAULT_CRL_INSTALLED $ZZZ_OPENVPN_CRLS_DIR/$FILENAME_HASH_DEFAULT_CRL
