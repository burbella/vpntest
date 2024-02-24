#!/bin/bash
#-----PKI utils-----
# useful when working with a long list of users

EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`

PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Default'`
OPENVPN_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/OpenVPN'`
SQUID_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid'`
SQUID_TOP_PKI_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/PKI/Squid-Top'`

#-----CA's-----
VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA
VARS_OPENVPN_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_OPENVPN_CA
VARS_SQUID_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_SQUID_CA
VARS_SQUID_TOP_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_SQUID_TOP_CA

#-----certs-----
VARS_APACHE=$EASYRSA_VARS_DIR/$VARS_FILENAME_APACHE
VARS_OCSP=$EASYRSA_VARS_DIR/$VARS_FILENAME_OCSP
VARS_OPENVPN_SERVER=$EASYRSA_VARS_DIR/$VARS_FILENAME_OPENVPN_SERVER

#-----user lists-----
OPENVPN_LIST_USERS_TO_ADD=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/openvpn/users_to_add'`
OPENVPN_LIST_USERS_TO_DELETE=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/openvpn/users_to_delete'`

zzzConfig_CA_Pass_OpenVPN=`/opt/zzz/python/bin/config-parse.py --var 'UpdateFile/easyrsa/ca-pass-openvpn'`
ZZZ_TWO=2
zzzConfig_CA_Pass_OpenVPN2=$zzzConfig_CA_Pass_OpenVPN$ZZZ_TWO

#--------------------------------------------------------------------------------

#-----openssl cert password file generator-----
zzz_make_cert_pass_file() {
    local ZZZ_CERT_PASS_FILEPATH=$1

    # safety check
    if [[ "$ZZZ_CERT_PASS_FILEPATH" =~ ^\/opt\/zzz\/data\/ssl\-private\/[A-Za-z0-9_-]+\.pass$ ]]; then
        echo `openssl rand -hex 32` > $ZZZ_CERT_PASS_FILEPATH
        # filename --> filename2
        cp $ZZZ_CERT_PASS_FILEPATH $ZZZ_CERT_PASS_FILEPATH$ZZZ_TWO
    else
        if [[ "$ZZZ_CERT_PASS_FILEPATH" == "/etc/openvpn/vpn.zzz.zzz_pem_pass.txt" ]]; then
            echo `openssl rand -hex 32` > $ZZZ_CERT_PASS_FILEPATH
            # filename --> filename2
            cp $ZZZ_CERT_PASS_FILEPATH $ZZZ_CERT_PASS_FILEPATH$ZZZ_TWO
        else
            echo "ERROR: invalid pass filepath"
        fi
    fi
}

#--------------------------------------------------------------------------------

zzz_pki_check_username_regex() {
    local OPENVPN_USERNAME=$1
    if [[ "$OPENVPN_USERNAME" == "" ]]; then
        echo "ERROR: no username provided"
        exit
    fi
    
    ZZZ_TEST_USERNAME_REGEX="^([A-Za-z0-9][A-Za-z0-9\-]{1,48}[A-Za-z0-9])$"
    if ! [[ "$OPENVPN_USERNAME" =~ $ZZZ_TEST_USERNAME_REGEX ]]; then
        echo "ERROR: invalid username"
        exit
    fi
}

#--------------------------------------------------------------------------------

zzz_pki_check_if_user_exists() {
    local OPENVPN_USERNAME=$1
    zzz_pki_check_username_regex $OPENVPN_USERNAME
    
    local OPENVPN_SELECTED_USER_CERT=$OPENVPN_PKI_DIR/issued/$OPENVPN_USERNAME.crt
    if [[ ! -e $OPENVPN_SELECTED_USER_CERT ]]; then
        echo "ERROR: user does not exist"
        exit
    fi
}

#--------------------------------------------------------------------------------

zzz_pki_add_user() {
    local OPENVPN_USERNAME=$1
    local VARS_OPENVPN_USER=$EASYRSA_VARS_DIR/vars-openvpn-user-$OPENVPN_USERNAME
    if [[ -e "$VARS_OPENVPN_USER" ]]; then
        #-----make user cert-----
        echo "  new user: $OPENVPN_USERNAME"
        cd $EASYRSA_DIR
        ./easyrsa --vars=$VARS_OPENVPN_USER gen-req $OPENVPN_USERNAME nopass
        ./easyrsa --vars=$VARS_OPENVPN_USER --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" sign-req client $OPENVPN_USERNAME
    else
        echo "ERROR: vars file not found $VARS_OPENVPN_USER"
    fi
}

#--------------------------------------------------------------------------------

zzz_pki_delete_user() {
    local OPENVPN_USERNAME=$1
    local VARS_OPENVPN_USER=$EASYRSA_VARS_DIR/vars-openvpn-user-$OPENVPN_USERNAME
    if [[ -e "$VARS_OPENVPN_USER" ]]; then
        echo "  deleting user: $OPENVPN_USERNAME"
        cd $EASYRSA_DIR
        ./easyrsa --vars=$VARS_OPENVPN_USER --passin="file:$zzzConfig_CA_Pass_OpenVPN" --passout="file:$zzzConfig_CA_Pass_OpenVPN2" revoke $OPENVPN_USERNAME
    else
        echo "ERROR: vars file not found $VARS_OPENVPN_USER"
    fi
}

#--------------------------------------------------------------------------------

zzz_pki_exit_if_no_updates() {
    if [[ ! -f $OPENVPN_LIST_USERS_TO_ADD ]] && [[ ! -f $OPENVPN_LIST_USERS_TO_DELETE ]]; then
        echo "no openvpn user updates needed"
        exit
    fi
}

#--------------------------------------------------------------------------------

zzz_pki_add_selected_users() {
    if [ ! -f $OPENVPN_LIST_USERS_TO_ADD ]; then
        echo "add-user list $OPENVPN_LIST_USERS_TO_ADD not found, not creating any OpenVPN user certs"
        return
    fi

    if [ ! -s $OPENVPN_LIST_USERS_TO_ADD ]; then
        # this should never happen
        echo "empty add-user list $OPENVPN_LIST_USERS_TO_ADD, not creating any OpenVPN user certs"
        return
    fi
    
    echo "creating OpenVPN user certs"
    
    local OPENVPN_USERNAME=
    while read OPENVPN_USERNAME; do
        zzz_pki_add_user $OPENVPN_USERNAME
    done <$OPENVPN_LIST_USERS_TO_ADD
}

#--------------------------------------------------------------------------------

zzz_pki_delete_selected_users() {
    if [ ! -f $OPENVPN_LIST_USERS_TO_DELETE ]; then
        echo "delete-user list $OPENVPN_LIST_USERS_TO_DELETE not found, not revoking any OpenVPN user certs"
        return
    fi

    if [ ! -s $OPENVPN_LIST_USERS_TO_DELETE ]; then
        # this should never happen
        echo "empty delete-user list $OPENVPN_LIST_USERS_TO_DELETE, not revoking any OpenVPN user certs"
        return
    fi
    
    echo "revoking OpenVPN user certs"
    
    local OPENVPN_USERNAME=
    while read OPENVPN_USERNAME; do
        zzz_pki_delete_user $OPENVPN_USERNAME
    done <$OPENVPN_LIST_USERS_TO_DELETE
}

