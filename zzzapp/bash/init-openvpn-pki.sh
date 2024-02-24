#!/bin/bash
#-----initialize PKI for openvpn with an intermediate CA-----
# assumes the main CA has been created already
# vars-openvpn should contain a new PKI name: pki-openvpn-int

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# set in util: REPOS_DIR, VARS_FILENAME_APACHE, VARS_FILENAME_DEFAULT_CA, VARS_FILENAME_OCSP, VARS_FILENAME_OPENVPN_CA, VARS_FILENAME_OPENVPN_SERVER, ZZZ_CONFIG_DIR
source /opt/zzz/util/pki_utils.sh

APACHE_SERVERNAME=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`

# Directory/EasyRSA
# Directory/PKI/Default
# Directory/PKI/OpenVPN
# Directory/PKI/Squid
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
OPENVPN_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/OpenVPN'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

zzzConfig_CA_Pass_OpenVPN=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-openvpn'`
zzzConfig_CA_Pass_Root=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-root'`
APACHE_CERT_PASS_FILE=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/server-pass-apache'`
VPN_CERT_PASS_FILE=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/server-pass-openvpn'`
ZZZ_TWO=2
zzzConfig_CA_Pass_OpenVPN2=$zzzConfig_CA_Pass_OpenVPN$ZZZ_TWO
zzzConfig_CA_Pass_Root2=$zzzConfig_CA_Pass_Root$ZZZ_TWO
APACHE_CERT_PASS_FILE2=$APACHE_CERT_PASS_FILE$ZZZ_TWO
VPN_CERT_PASS_FILE2=$VPN_CERT_PASS_FILE$ZZZ_TWO

#-----make a new random password for openvpn CA key-----
zzz_make_cert_pass_file $zzzConfig_CA_Pass_OpenVPN
chmod 600 $zzzConfig_CA_Pass_OpenVPN
chmod 600 $zzzConfig_CA_Pass_OpenVPN2

#-----make a new random password for apache server key-----
zzz_make_cert_pass_file $APACHE_CERT_PASS_FILE
chmod 600 $APACHE_CERT_PASS_FILE
chmod 600 $APACHE_CERT_PASS_FILE2

#-----Save the VPN PEM password to a file and secure it-----
zzz_make_cert_pass_file $VPN_CERT_PASS_FILE
chmod 600 $VPN_CERT_PASS_FILE
chmod 600 $VPN_CERT_PASS_FILE2

#-----cert pass script for apache to call-----
ZZZ_APACHE_CERT_PASS_FILEPATH=/opt/zzz/data/ssl-private/apache-cert-pass.sh
cp $ZZZ_CONFIG_DIR/httpd/apache-cert-pass.sh $ZZZ_APACHE_CERT_PASS_FILEPATH
chmod 700 $ZZZ_APACHE_CERT_PASS_FILEPATH
chown root.root $ZZZ_APACHE_CERT_PASS_FILEPATH

#vars-apache
#vars-ocsp
#vars-openvpn-ca
#vars-openvpn-server
#vars-openvpn-user-USERNAME
#vars-squid
#vars-zzz
VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA
VARS_OPENVPN_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_OPENVPN_CA
VARS_OPENVPN_SERVER=$EASYRSA_VARS_DIR/$VARS_FILENAME_OPENVPN_SERVER
VARS_OCSP=$EASYRSA_VARS_DIR/$VARS_FILENAME_OCSP
VARS_APACHE=$EASYRSA_VARS_DIR/$VARS_FILENAME_APACHE

#--------------------------------------------------------------------------------

#-----update the webserver_domain in the DB with the latest entry from zzz.conf-----
/opt/zzz/python/bin/init-db.py --domain

#-----Build a new PKI: (switch to openvpn VARS file)-----
cd $EASYRSA_DIR
# vars param no longer allowed with init-pki in easyrsa version 3.1.0
# ./easyrsa --vars=$VARS_OPENVPN_CA init-pki
./easyrsa --pki-dir="$OPENVPN_PKI_DIR" --batch init-pki hard-reset

#-----copy openssl-easyrsa.cnf to the pki directory-----
cp $EASYRSA_VARS_DIR/openssl-easyrsa-int-ca.cnf $OPENVPN_PKI_DIR/openssl-easyrsa.cnf

./easyrsa --vars=$VARS_OPENVPN_CA --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" build-ca intca

# Intermediate CA request ends up here: /pki-openvpn-int/reqs/ca.req
# Copy the request to here: (pki-openvpn-int --> pki)
#   /pki/reqs/openvpn-int-ca.req
cp -p $OPENVPN_PKI_DIR/reqs/ca.req $PKI_DIR/reqs/openvpn-int-ca.req

# Parent CA must sign the request: (switch CA's by switching VARS files)
./easyrsa --vars=$VARS_DEFAULT_CA --passin="file:$zzzConfig_CA_Pass_Root" --passout="file:$zzzConfig_CA_Pass_Root2" sign-req ca openvpn-int-ca

# Intermediate CA's signed cert ends up here: /pki/issued/openvpn-int-ca.crt
# Copy the signed cert to here: (pki --> pki-openvpn-int)
#   /pki-openvpn-int/ca.crt
cp -p $PKI_DIR/issued/openvpn-int-ca.crt $OPENVPN_PKI_DIR/ca.crt
/opt/zzz/util/output_minimal_cert_data.sh openvpn-ca

#-----install OpenVPN CA cert-----
/opt/zzz/util/openvpn-rebuild-ca-fullchain.sh

#--------------------------------------------------------------------------------

#-----build the DH (Diffie-Helllman) parameters (takes about 33 seconds)-----
./easyrsa --vars=$VARS_OPENVPN_CA gen-dh
DH_FILE=$OPENVPN_PKI_DIR/dh.pem
cp $DH_FILE /etc/openvpn

echo "---------------------------------------------------------------"

#-----OpenVPN server cert-----
# vpn.zzz.zzz
OPENVPN_SERVERNAME=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/VpnServerName'`

#-----make a CSR-----
./easyrsa --vars=$VARS_OPENVPN_SERVER --subject-alt-name="DNS:$OPENVPN_SERVERNAME" --passin="file:$VPN_CERT_PASS_FILE" --passout="file:$VPN_CERT_PASS_FILE2" gen-req $OPENVPN_SERVERNAME

#-----Sign the cert as a server cert:-----
./easyrsa --vars=$VARS_OPENVPN_SERVER --subject-alt-name="DNS:$OPENVPN_SERVERNAME" --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" sign-req server $OPENVPN_SERVERNAME

#-----OpenVPN requires the certs and keys to be under /etc/openvpn-----
# CA cert: $OPENVPN_PKI_DIR/ca.crt
# req: $OPENVPN_PKI_DIR/reqs/vpn.zzz.zzz.req
# crt: $OPENVPN_PKI_DIR/issued/vpn.zzz.zzz.crt
# key: $OPENVPN_PKI_DIR/private/vpn.zzz.zzz.key
#cp $OPENVPN_PKI_DIR/issued/$OPENVPN_SERVERNAME.crt /etc/openvpn
#cp $OPENVPN_PKI_DIR/private/$OPENVPN_SERVERNAME.key /etc/openvpn

#-----install OpenVPN server cert and server key files-----
OPENVPN_INSTALL_DIR=/etc/openvpn
cp $OPENVPN_PKI_DIR/issued/vpn.zzz.zzz.crt $OPENVPN_INSTALL_DIR
chown root.root $OPENVPN_INSTALL_DIR/vpn.zzz.zzz.crt
chmod 600 $OPENVPN_INSTALL_DIR/vpn.zzz.zzz.crt
/opt/zzz/util/output_minimal_cert_data.sh openvpn-server

cp $OPENVPN_PKI_DIR/private/vpn.zzz.zzz.key $OPENVPN_INSTALL_DIR
chown root.root $OPENVPN_INSTALL_DIR/vpn.zzz.zzz.key
chmod 600 $OPENVPN_INSTALL_DIR/vpn.zzz.zzz.key

echo "---------------------------------------------------------------"

#-----OpenVPN user certs-----

#-----user .ovpn files go here-----
OPENVPN_DIR=/home/ubuntu/openvpn
chown ubuntu.ubuntu $OPENVPN_DIR
chmod 700 $OPENVPN_DIR

#-----file containing the list of OpenVPN users to be created-----
OPENVPN_USERS_FILE="/opt/zzz/data/openvpn_users.txt"
#USER_INSTRUCTIONS="/opt/zzz/user_instructions.txt"

#-----build openvpn users textfile-----
/opt/zzz/python/bin/build-config.py --openvpn-users

#TODO: replace all this code with a call to /opt/zzz/util/openvpn-add-delete-users.sh

#-----split up the users config var into a textfile that can be consumed below-----
#zzzConfig_VPNusers=`/opt/zzz/python/bin/config-parse.py --var 'VPNusers' --yaml`
#echo $zzzConfig_VPNusers | tr "," "\n" > $OPENVPN_USERS_FILE

if [ -f $OPENVPN_USERS_FILE ]; then
    echo "creating OpenVPN user certs"
    
    while read OPENVPN_USERNAME; do
        VARS_OPENVPN_USER=$EASYRSA_VARS_DIR/vars-openvpn-user-$OPENVPN_USERNAME
        
        #-----make user cert-----
        ./easyrsa --vars=$VARS_OPENVPN_USER gen-req $OPENVPN_USERNAME nopass
        ./easyrsa --vars=$VARS_OPENVPN_USER --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" sign-req client $OPENVPN_USERNAME
        
        #echo "--------------------------------------------------" >> $USER_INSTRUCTIONS
        #echo "OpenVPN files for user '$OPENVPN_USERNAME'" >> $USER_INSTRUCTIONS
    done <$OPENVPN_USERS_FILE
else
    echo "ERROR: config file $OPENVPN_USERS_FILE not found, not creating any OpenVPN user certs"
fi

echo "---------------------------------------------------------------"

#-----OpenVPN CRL-----
/opt/zzz/util/build-crl-openvpn.sh

#--------------------------------------------------------------------------------

#TODO: finish this
#      switch from nopass to passin/passout

#-----OCSP Server-----
#OCSP_SERVER_CERT=ocsp.zzz.zzz
#OCSP_SERVER_CERT=10.7.0.1
#OCSP_SERVER_CERT_INSTALLED=
#OCSP_SERVERNAME=
#./easyrsa --vars=$VARS_OCSP gen-req $OCSP_SERVERNAME nopass
#./easyrsa --vars=$VARS_OCSP sign-req code-signing $OCSP_SERVERNAME


#--------------------------------------------------------------------------------

#-----apache server cert-----

#-----make & sign the request-----
./easyrsa --vars=$VARS_APACHE --subject-alt-name="DNS:$APACHE_SERVERNAME" --passin="file:$APACHE_CERT_PASS_FILE" --passout="file:$APACHE_CERT_PASS_FILE2" gen-req $APACHE_SERVERNAME
./easyrsa --vars=$VARS_APACHE --subject-alt-name="DNS:$APACHE_SERVERNAME" --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" sign-req server $APACHE_SERVERNAME

#-----apache ssl cert directory-----
APACHE_CERT_DIR=/etc/ssl/certs
APACHE_KEY_DIR=/etc/ssl/private

#-----apache cert/key files-----
APACHE_PUBLIC_CERT=$OPENVPN_PKI_DIR/issued/$APACHE_SERVERNAME.crt
cp $APACHE_PUBLIC_CERT $APACHE_CERT_DIR
chown root.root $APACHE_CERT_DIR/$APACHE_SERVERNAME.crt
chmod 644 $APACHE_CERT_DIR/$APACHE_SERVERNAME.crt

APACHE_PRIVATE_KEY=$OPENVPN_PKI_DIR/private/$APACHE_SERVERNAME.key
cp $APACHE_PRIVATE_KEY $APACHE_KEY_DIR
chown root.ssl-cert $APACHE_KEY_DIR/$APACHE_SERVERNAME.key
chmod 640 $APACHE_KEY_DIR/$APACHE_SERVERNAME.key

#-----apache fullchain file-----
/opt/zzz/util/apache-rebuild-ca-fullchain.sh

#--------------------------------------------------------------------------------

#-----OpenVPN user certs-----
# get these from a config file?
# separate install script for these?

#--------------------------------------------------------------------------------

