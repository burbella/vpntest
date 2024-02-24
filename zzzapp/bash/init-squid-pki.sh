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
# vars set in util.sh: REPOS_DIR, VARS_FILENAME_DEFAULT_CA, VARS_FILENAME_SQUID_CA, VARS_FILENAME_SQUID_TOP_CA
source /opt/zzz/util/pki_utils.sh

EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
SQUID_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid'`
SQUID_TOP_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid-Top'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

VARS_SQUID_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_SQUID_CA
VARS_SQUID_TOP_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_SQUID_TOP_CA

cd $EASYRSA_DIR

zzzConfig_CA_Pass_Squid=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-squid'`
zzzConfig_CA_Pass_Squid_Top=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-squid-top'`
ZZZ_TWO=2
zzzConfig_CA_Pass_Squid2=$zzzConfig_CA_Pass_Squid$ZZZ_TWO
zzzConfig_CA_Pass_Squid_Top2=$zzzConfig_CA_Pass_Squid_Top$ZZZ_TWO

#-----make new random passwords for squid key-----
zzz_make_cert_pass_file $zzzConfig_CA_Pass_Squid
chmod 640 $zzzConfig_CA_Pass_Squid
chmod 640 $zzzConfig_CA_Pass_Squid2
chown root.proxy $zzzConfig_CA_Pass_Squid
chown root.proxy $zzzConfig_CA_Pass_Squid2

#--------------------------------------------------------------------------------

#-----Build a new squid PKI: (switch to squid VARS file)-----
# ./easyrsa --vars=$VARS_SQUID_CA init-pki
./easyrsa --pki-dir="$SQUID_PKI_DIR" --batch init-pki hard-reset

#-----copy openssl-easyrsa.cnf to the pki directory-----
cp $EASYRSA_VARS_DIR/openssl-easyrsa-int-ca.cnf $SQUID_PKI_DIR/openssl-easyrsa.cnf

./easyrsa --vars=$VARS_SQUID_CA --passin="file:$zzzConfig_CA_Pass_Squid" --passout="file:$zzzConfig_CA_Pass_Squid2" build-ca intca

# Intermediate CA request ends up here: /pki-squid/reqs/ca.req
# Copy the request to here: (pki-squid --> pki-squid-top)
#   /pki-squid-top/reqs/squid-ca.req
cp -p $SQUID_PKI_DIR/reqs/ca.req $SQUID_TOP_PKI_DIR/reqs/squid-ca.req

# Parent CA must sign the request: (switch CA's by switching VARS files)
./easyrsa --vars=$VARS_SQUID_TOP_CA --passin="file:$zzzConfig_CA_Pass_Squid_Top" --passout="file:$zzzConfig_CA_Pass_Squid_Top2" sign-req ca squid-ca

# Intermediate CA's signed cert ends up here: /pki-squid-top/issued/squid-ca.crt
# Copy the signed cert to here: (pki-squid-top --> pki-squid)
#   /pki-squid/ca.crt
cp -p $SQUID_TOP_PKI_DIR/issued/squid-ca.crt $SQUID_PKI_DIR/ca.crt
/opt/zzz/util/output_minimal_cert_data.sh squid-ca

/opt/zzz/util/squid-rebuild-ca-fullchain.sh
