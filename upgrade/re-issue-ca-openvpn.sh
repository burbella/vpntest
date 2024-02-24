#!/bin/bash
#-----re-issue the OpenVPN intermediate CA and associated certs manually-----
# Reference: /upgrade/replace_pki.sh
#            /install/070_setup-pki.sh
# EasyRSA Var File: /config/easyrsa/vars-squid
#
#--------------------------------------------------------------------------------

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR, VARS_FILENAME_DEFAULT_CA

zzzConfig_Domain=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

zzzConfig_CA_Pass_Root=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-root'`
ZZZ_TWO=2
zzzConfig_CA_Pass_Root2=$zzzConfig_CA_Pass_Root$ZZZ_TWO

VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA

#TODO: check if the root CA private key file is in place
#      re-issuing the OpenVPN CA is the only operation that should require the root CA private key

cd $EASYRSA_DIR

echo "Re-Issuing the OpenVPN intermediate CA"
echo

#-----in case the domain or user list changed, make new easyrsa vars files-----
/opt/zzz/python/bin/build-config.py --easyrsa -q

#-----stop services-----
echo "Stopping services"
systemctl stop apache2
# must stop squid before zzz_icap
systemctl stop squid
systemctl stop squid-icap
systemctl stop zzz
systemctl stop zzz_icap
/opt/zzz/python/bin/subprocess/openvpn-stop.sh

#-----revoke the old intermediate CA cert in the main CA-----
echo "Revoking existing OpenVPN intermediate CA"
./easyrsa --vars=$VARS_DEFAULT_CA --passin="file:$zzzConfig_CA_Pass_Root" --passout="file:$zzzConfig_CA_Pass_Root2" revoke openvpn-int-ca

#-----Build a new PKI for the intermediate CA-----
# init-openvpn-pki will also do a DB update: init-db.py --domain
echo "Building new OpenVPN intermediate CA"
echo
/opt/zzz/util/init-openvpn-pki.sh

#-----rebuild apache configs-----
/opt/zzz/python/bin/build-config.py --apache -q

#-----rebuild bind configs-----
/opt/zzz/python/bin/build-config.py --bind
#-----add a BIND soft link to fix file-not-found errors-----
extract_domain_from_subdomain $zzzConfig_Domain
if [[ "$ZZZ_DOMAIN_EXTRACTED" != "zzz.zzz" ]]; then
    ZZZ_ZONE_SOFT_LINK=/var/cache/bind/$ZZZ_DOMAIN_EXTRACTED.zone.file
    #-----only do this if the soft link does not exist already-----
    if [[ ! -e "$ZZZ_ZONE_SOFT_LINK" ]]; then
        ln -s /etc/bind/$ZZZ_DOMAIN_EXTRACTED.zone.file $ZZZ_ZONE_SOFT_LINK
    fi
fi

#-----rebuild openvpn client/server configs-----
/opt/zzz/python/bin/build-config.py --openvpn-client -q
/opt/zzz/python/bin/build-config.py --openvpn-server -q

#-----start services-----
echo
echo "Starting services"
systemctl restart bind9
systemctl restart zzz
# this will restart ICAP and squid
/home/ubuntu/bin/icap-restart
# restart works better than start for apache
systemctl restart apache2
/opt/zzz/python/bin/subprocess/openvpn-start.sh

