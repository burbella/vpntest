#!/bin/bash
#-----initialize PKI for squid with an intermediate CA-----
# assumes the main CA has been created already
# vars-squid-ca should contain a new PKI name: pki-squid
# vars-squid-top-ca should contain a new PKI name: pki-squid-top
# CA's: root --> squid-top --> squid

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR, VARS_FILENAME_DEFAULT_CA, VARS_FILENAME_SQUID_TOP_CA
source /opt/zzz/util/pki_utils.sh

EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
SQUID_TOP_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid-Top'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA
VARS_SQUID_TOP_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_SQUID_TOP_CA

cd $EASYRSA_DIR

zzzConfig_CA_Pass_Root=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-root'`
zzzConfig_CA_Pass_Squid_Top=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-squid-top'`
ZZZ_TWO=2
zzzConfig_CA_Pass_Root2=$zzzConfig_CA_Pass_Root$ZZZ_TWO
zzzConfig_CA_Pass_Squid_Top2=$zzzConfig_CA_Pass_Squid_Top$ZZZ_TWO

#-----make new random passwords for squid-top key-----
zzz_make_cert_pass_file $zzzConfig_CA_Pass_Squid_Top
chmod 600 $zzzConfig_CA_Pass_Squid_Top
chmod 600 $zzzConfig_CA_Pass_Squid_Top2

#--------------------------------------------------------------------------------

#-----Build a new squid-top PKI: (switch to squid-top VARS file)-----
# ./easyrsa --vars=$VARS_SQUID_TOP_CA init-pki
./easyrsa --pki-dir="$SQUID_TOP_PKI_DIR" --batch init-pki hard-reset

#-----copy openssl-easyrsa.cnf to the pki directory-----
cp $EASYRSA_VARS_DIR/openssl-easyrsa-int-ca.cnf $SQUID_TOP_PKI_DIR/openssl-easyrsa.cnf

./easyrsa --vars=$VARS_SQUID_TOP_CA --passin="file:$zzzConfig_CA_Pass_Squid_Top" --passout="file:$zzzConfig_CA_Pass_Squid_Top2" build-ca intca

# Intermediate CA request ends up here: /pki-squid-top/reqs/ca.req
# Copy the request to here: (pki-squid-top --> pki)
#   /pki/reqs/squid-top-ca.req
cp -p $SQUID_TOP_PKI_DIR/reqs/ca.req $PKI_DIR/reqs/squid-top-ca.req

# Parent CA must sign the request: (switch CA's by switching VARS files)
./easyrsa --vars=$VARS_DEFAULT_CA --passin="file:$zzzConfig_CA_Pass_Root" --passout="file:$zzzConfig_CA_Pass_Root2" sign-req ca squid-top-ca

# Intermediate CA's signed cert ends up here: /pki/issued/squid-top-ca.crt
# Copy the signed cert to here: (pki --> pki-squid-top)
#   /pki-squid-top/ca.crt
cp -p $PKI_DIR/issued/squid-top-ca.crt $SQUID_TOP_PKI_DIR/ca.crt
/opt/zzz/util/output_minimal_cert_data.sh squid-top-ca

#--------------------------------------------------------------------------------

#-----Build a new squid PKI:-----
/opt/zzz/util/init-squid-pki.sh
