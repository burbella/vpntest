#!/bin/bash
#-----minimal cert data for efficiency-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: MINIMAL_DEFAULT_PUBLIC_CERT, MINIMAL_OPENVPN_PUBLIC_CERT, MINIMAL_SQUID_PUBLIC_CERT, MINIMAL_SQUID_TOP_PUBLIC_CERT, ZZZ_CERT_DATA_DIR

PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
OPENVPN_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/OpenVPN'`
SQUID_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid'`
SQUID_TOP_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid-Top'`

DEFAULT_PUBLIC_CERT=$PKI_DIR/ca.crt
OPENVPN_PUBLIC_CERT=$OPENVPN_PKI_DIR/ca.crt
SQUID_PUBLIC_CERT=$SQUID_PKI_DIR/ca.crt
SQUID_TOP_PUBLIC_CERT=$SQUID_TOP_PKI_DIR/ca.crt

#--------------------------------------------------------------------------------

#-----functions defined here-----

zzz_option_to_rebuild_hashes() {
    if [[ "$SKIP_REBUILD_HASHES" == "yes" ]]; then
        #-----no need to rehash for each cert when building all certs below-----
        return
    fi
    #-----rebuild hashes in /etc/ssl/certs to make the trusted cert usable by openssl-----
    c_rehash
}

# openssl x509 -in /home/ubuntu/easyrsa3/pki-squid-top/ca.crt -outform PEM
zzz_output_cert_squid_top() {
    openssl x509 -in $SQUID_TOP_PUBLIC_CERT -outform PEM > $MINIMAL_SQUID_TOP_PUBLIC_CERT
    
    #-----make the CA trusted by openssl-----
    cp $MINIMAL_SQUID_TOP_PUBLIC_CERT /etc/ssl/certs
    zzz_option_to_rebuild_hashes
}

zzz_output_cert_squid() {
    openssl x509 -in $SQUID_PUBLIC_CERT -outform PEM > $MINIMAL_SQUID_PUBLIC_CERT
    
    #-----make the CA trusted by openssl-----
    cp $MINIMAL_SQUID_PUBLIC_CERT /etc/ssl/certs
    zzz_option_to_rebuild_hashes
}

zzz_output_cert_root() {
    openssl x509 -in $DEFAULT_PUBLIC_CERT -outform PEM > $MINIMAL_DEFAULT_PUBLIC_CERT
    
    #-----make the CA trusted by openssl-----
    cp $MINIMAL_DEFAULT_PUBLIC_CERT /etc/ssl/certs
    zzz_option_to_rebuild_hashes
}

zzz_output_cert_openvpn_ca() {
    openssl x509 -in $OPENVPN_PUBLIC_CERT -outform PEM > $MINIMAL_OPENVPN_PUBLIC_CERT
    
    #-----make the CA trusted by openssl-----
    cp $MINIMAL_OPENVPN_PUBLIC_CERT /etc/ssl/certs
    zzz_option_to_rebuild_hashes
}

zzz_output_cert_apache_server() {
    ZZZ_APACHE_DOMAIN=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
    APACHE_PUBLIC_CERT=$OPENVPN_PKI_DIR/issued/$ZZZ_APACHE_DOMAIN.crt
    MINIMAL_APACHE_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/$ZZZ_APACHE_DOMAIN.crt
    
    openssl x509 -in $APACHE_PUBLIC_CERT -outform PEM > $MINIMAL_APACHE_PUBLIC_CERT
    
    # zzz_option_to_rebuild_hashes
}

zzz_output_cert_openvpn_server() {
    OPENVPN_SERVER_PUBLIC_CERT=$OPENVPN_PKI_DIR/issued/vpn.zzz.zzz.crt
    MINIMAL_OPENVPN_SERVER_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/vpn.zzz.zzz.crt
    
    openssl x509 -in $OPENVPN_SERVER_PUBLIC_CERT -outform PEM > $MINIMAL_OPENVPN_SERVER_PUBLIC_CERT
    
    # zzz_option_to_rebuild_hashes
}

#--------------------------------------------------------------------------------

#-----execution continues here-----

CERT_TO_OUTPUT=$1

# must be "--do-rebuild-hashes"
SKIP_REBUILD_HASHES=no

# return only works inside functions
# exit kills the parent process also
# so just wrap this entire thing in a function and call it to have usable returns
zzz_do_output_minimal_cert_data() {
    if [[ "$CERT_TO_OUTPUT" == "squid-top-ca" ]]; then
        zzz_output_cert_squid_top
        return
    fi

    if [[ "$CERT_TO_OUTPUT" == "squid-ca" ]]; then
        zzz_output_cert_squid
        return
    fi

    if [[ "$CERT_TO_OUTPUT" == "root-ca" ]]; then
        zzz_output_cert_root
        return
    fi

    if [[ "$CERT_TO_OUTPUT" == "openvpn-ca" ]]; then
        zzz_output_cert_openvpn_ca
        return
    fi

    if [[ "$CERT_TO_OUTPUT" == "apache" ]]; then
        zzz_output_cert_apache_server
        return
    fi

    if [[ "$CERT_TO_OUTPUT" == "openvpn-server" ]]; then
        zzz_output_cert_openvpn_server
        return
    fi

    #-----all certs-----
    if [[ "$CERT_TO_OUTPUT" == "all" ]]; then
        SKIP_REBUILD_HASHES=yes

        #-----make CA certs-----
        zzz_output_cert_squid_top
        zzz_output_cert_squid
        zzz_output_cert_root
        zzz_output_cert_openvpn_ca
        
        #-----make other certs-----
        zzz_output_cert_apache_server
        zzz_output_cert_openvpn_server
        
        #-----rebuild hashes in /etc/ssl/certs-----
        c_rehash

        return
    fi
}

zzz_do_output_minimal_cert_data
