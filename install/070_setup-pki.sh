#!/bin/bash

# option to skip cert creation if an existing PKI is available
# 	initializes the PKI system
# 	make certs WITHOUT passwords:
# 		OpenVPN CA (for OpenVPN user certs)
# 		Squid server intermediate CA - built from OpenVPN CA
# 		OpenVPN server cert (OpenVPN CA)
# 		Apache server cert (OpenVPN CA)
#       User certs for each user (OpenVPN CA)
#
# include SAN in the cert setup
# install certs: openvpn, squid, apache
#
# EasyRSA Configs:
#   openssl-easyrsa.cnf
#   vars.example
#
# Cert Passwords:
#   make all keys without passwords for now
#   manual-run a script to add passwords at the end of the install process

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, VARS_FILENAME_DEFAULT_CA, ZZZ_CONFIG_DIR
source /opt/zzz/util/pki_utils.sh

EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

#-----install the EasyRSA configs-----
# config file: openssl-easyrsa.cnf
# default directory: pki
# config variables: vars-openvpn
#####
# squid directory: pki-squid-int
# squid config variables: vars-squid

#-----generate the EasyRSA vars files-----
/opt/zzz/python/bin/build-config.py --easyrsa

cd $EASYRSA_DIR

#---------------------------------------------------------------------------------------------------

zzzConfig_CA_Default=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/Default'`
zzzConfig_CA_OpenVPN=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/OpenVPN'`
zzzConfig_CA_Squid=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/Squid'`
zzzConfig_Domain=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`

zzzConfig_CA_Pass_Root=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-root'`
ZZZ_TWO=2
zzzConfig_CA_Pass_Root2=$zzzConfig_CA_Pass_Root$ZZZ_TWO

echo "CA Default: $zzzConfig_CA_Default"
echo "CA OpenVPN: $zzzConfig_CA_OpenVPN"
echo "CA Squid: $zzzConfig_CA_Squid"

#-----get the server domain from the config-----
APACHE_SERVERNAME=$zzzConfig_Domain
echo "APACHE_SERVERNAME=$APACHE_SERVERNAME"

#---------------------------------------------------------------------------------------------------

#-----Root CA (Default)-----
# initialize with minimum required fields
# take info from a user config file?
# need a python script for this?
#
# The SAN must be in the Squid CA cert for Chrome to allow connections involving the Squid auto-generated certs
#   --subject-alt-name=DNS:vpn.example.net
#   Make sure the DNS server name matches the one used for connecting to OpenVPN
#   The SAN is not required by OpenVPN, but we will put it in all certs for consistency
#   It must be a subdomain, not an IP address

echo "Generating root CA"

#TODO: passwords for all CA's
#-----make a new random password for root key-----
zzz_make_cert_pass_file $zzzConfig_CA_Pass_Root
chmod 600 $zzzConfig_CA_Pass_Root
chmod 600 $zzzConfig_CA_Pass_Root2

VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA
# vars param no longer allowed with init-pki in easyrsa version 3.1.0
# ./easyrsa --vars=$VARS_DEFAULT_CA init-pki
./easyrsa --pki-dir="$PKI_DIR" --batch init-pki hard-reset

#-----copy openssl-easyrsa.cnf to the pki directory-----
cp $EASYRSA_VARS_DIR/openssl-easyrsa-root-ca.cnf $PKI_DIR/openssl-easyrsa.cnf

./easyrsa --vars=$VARS_DEFAULT_CA --passin="file:$zzzConfig_CA_Pass_Root" --passout="file:$zzzConfig_CA_Pass_Root2" build-ca

/opt/zzz/util/output_minimal_cert_data.sh root-ca

#-----make directories accessible-----
chown root.root /etc/openvpn
chown root.root /etc/openvpn/server
chmod 755 /etc/openvpn
chmod 755 /etc/openvpn/server

#---------------------------------------------------------------------------------------------------

#-----OpenVPN intermediate CA-----
# make a separate PKI directory for the OpenVPN CA
# no password on the OpenVPN CA cert
# all certs will be built from this intermediate CA

echo "Generating OpenVPN intermediate CA"
/opt/zzz/util/init-openvpn-pki.sh

#---------------------------------------------------------------------------------------------------

#-----squid ssl cert directory permissions-----
SQUID_INSTALL_DIR=/etc/squid/ssl_cert
chown proxy.proxy $SQUID_INSTALL_DIR
chmod 755 $SQUID_INSTALL_DIR

#-----Squid intermediate CA-----
# make a separate PKI directory for the Squid CA
# no password on the squid CA cert
# combine the crt and key files into a pem file or keep them separate?
echo "Generating Squid intermediate CA"
/opt/zzz/util/init-squid-top-pki.sh

#-----cert pass script for squid to call-----
ZZZ_SQUID_CERT_PASS_FILEPATH=/opt/zzz/data/ssl-private/squid-cert-pass.sh
cp $ZZZ_CONFIG_DIR/squid/squid-cert-pass.sh $ZZZ_SQUID_CERT_PASS_FILEPATH
chmod 700 $ZZZ_SQUID_CERT_PASS_FILEPATH
chown proxy.proxy $ZZZ_SQUID_CERT_PASS_FILEPATH

#---------------------------------------------------------------------------------------------------

#-----make the CA cert available for SSH/iphone download-----

PUBLIC_CERTS_DIR=/home/ubuntu/public_certs
cp -p "$PKI_DIR/ca.crt" $PUBLIC_CERTS_DIR
chmod 644 $PUBLIC_CERTS_DIR/*
cp -p $PUBLIC_CERTS_DIR/* /var/www/html/

#TODO: rename the ca in $PUBLIC_CERTS_DIR to reflect the CA name?
#      remove all chars except letters/numbers
#      file in /var/www/html should stay as ca.crt for ease of use in iPhone installs
#ZZZ_CA_FILENAME=`echo "$zzzConfig_CA_Default" | tr -cd '[:alnum:]'`
#ZZZ_CA_FILENAME="$ZZZ_CA_FILENAME.crt"

USER_INSTRUCTIONS="/opt/zzz/user_instructions.txt"
echo -e "Download and insert this as a Trusted Root Certificate on all devices that use the VPN\n" > $USER_INSTRUCTIONS
echo "SSH directory:" >> $USER_INSTRUCTIONS
echo "$PUBLIC_CERTS_DIR/ca.crt" >> $USER_INSTRUCTIONS
echo "HTTPS download:" >> $USER_INSTRUCTIONS
echo "https://$APACHE_SERVERNAME/ca.crt" >> $USER_INSTRUCTIONS

#---------------------------------------------------------------------------------------------------

# Files:
# ./pki/private/ca.key
# ./pki/ca.crt

#-----download and insert this as a Trusted Root Cert on all devices using the VPN-----
#/home/ubuntu/easyrsa3/pki/ca.crt

echo "$ZZZ_SCRIPTNAME - END"
