#!/bin/bash
#-----SSL certs over 1 year duration are not accepted in some browsers, so re-issue 1-year certs for apache every month-----
# Reference: /upgrade/replace_pki.sh
#            /install/070_setup-pki.sh
# EasyRSA Var File: /home/ubuntu/easyrsa/zzz_vars/vars-apache

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid

# check new domain in zzz.conf file
zzzConfig_Domain=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
# check old domain in zzz_system table
zzzDB_domain=`sqlite3 $DB_FILE "select webserver_domain from zzz_system"`

# detect domain change
if [[ "$zzzConfig_Domain" != "$zzzDB_domain" ]]; then
    echo "NOTE: apache domain will change from $zzzDB_domain to $zzzConfig_Domain"
else
    echo "NOTE: using the existing apache domain $zzzConfig_Domain"
fi
echo

EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
OPENVPN_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/OpenVPN'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

# vars set in util: REPOS_DIR, VARS_FILENAME_APACHE
APACHE_SERVERNAME=$zzzConfig_Domain
VARS_APACHE=$EASYRSA_VARS_DIR/$VARS_FILENAME_APACHE

zzzConfig_CA_Pass_OpenVPN=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-openvpn'`
APACHE_CERT_PASS_FILE=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/server-pass-apache'`
ZZZ_TWO=2
zzzConfig_CA_Pass_OpenVPN2=$zzzConfig_CA_Pass_OpenVPN$ZZZ_TWO
APACHE_CERT_PASS_FILE2=$APACHE_CERT_PASS_FILE$ZZZ_TWO

#-----make a new random password for apache server key-----
zzz_make_cert_pass_file $APACHE_CERT_PASS_FILE
chmod 600 $APACHE_CERT_PASS_FILE
chmod 600 $APACHE_CERT_PASS_FILE2

cd $EASYRSA_DIR

#-----apache server cert-----

#-----revoke the old cert first-----
APACHE_SERVERNAME=$zzzDB_domain
./easyrsa --vars=$VARS_APACHE --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" revoke $APACHE_SERVERNAME

#-----switch to using the new domain for making the new cert (may be the same as the old domain)-----
APACHE_SERVERNAME=$zzzConfig_Domain
if [[ "$zzzConfig_Domain" != "$zzzDB_domain" ]]; then
    /opt/zzz/python/bin/build-config.py --easyrsa
fi

#-----make & sign the request-----
./easyrsa --vars=$VARS_APACHE --subject-alt-name="DNS:$APACHE_SERVERNAME" --passin="file:$APACHE_CERT_PASS_FILE" --passout="file:$APACHE_CERT_PASS_FILE2" gen-req $APACHE_SERVERNAME
./easyrsa --vars=$VARS_APACHE --subject-alt-name="DNS:$APACHE_SERVERNAME" --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" sign-req server $APACHE_SERVERNAME

#-----apache ssl cert directory-----
APACHE_CERT_DIR=/etc/ssl/certs
APACHE_KEY_DIR=/etc/ssl/private

systemctl stop apache2

#-----apache cert/key files-----
APACHE_PUBLIC_CERT=$OPENVPN_PKI_DIR/issued/$APACHE_SERVERNAME.crt
cp $APACHE_PUBLIC_CERT $APACHE_CERT_DIR
chown root.root $APACHE_CERT_DIR/$APACHE_SERVERNAME.crt
chmod 644 $APACHE_CERT_DIR/$APACHE_SERVERNAME.crt

APACHE_PRIVATE_KEY=$OPENVPN_PKI_DIR/private/$APACHE_SERVERNAME.key
cp $APACHE_PRIVATE_KEY $APACHE_KEY_DIR
chown root.ssl-cert $APACHE_KEY_DIR/$APACHE_SERVERNAME.key
chmod 640 $APACHE_KEY_DIR/$APACHE_SERVERNAME.key

DEFAULT_PUBLIC_CERT=$PKI_DIR/ca.crt
OPENVPN_PUBLIC_CERT=$OPENVPN_PKI_DIR/ca.crt

#-----apache fullchain file-----
/opt/zzz/util/apache-rebuild-ca-fullchain.sh

#-----rebuild apache configs-----
/opt/zzz/python/bin/build-config.py --apache

#-----did the domain change? make some extra updates-----
if [[ "$zzzConfig_Domain" != "$zzzDB_domain" ]]; then
    #-----update the webserver_domain in the DB with the latest entry from zzz.conf-----
    /opt/zzz/python/bin/init-db.py --domain
    
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
    
    systemctl restart bind9
    systemctl restart zzz
    /home/ubuntu/bin/icap-restart
fi

# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2

