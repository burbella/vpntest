#!/bin/bash
#-----restore the PKI from backup-----
#TODO: option to install it and restart apps?

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

BACKUP_DIR=/home/ubuntu/backup
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
PKI_DIR=$EASYRSA_DIR/pki
OPENVPN_PKI_DIR=$EASYRSA_DIR/pki-openvpn-int
SQUID_PKI_DIR=$EASYRSA_DIR/pki-squid-int

if [[ ! -e $BACKUP_DIR ]]; then
    echo "ERROR: backup dir does not exist $BACKUP_DIR"
    exit 1
fi

if [[ -e $BACKUP_DIR/pki ]]; then
    echo "clearing pki"
    rm -rf $EASYRSA_DIR/pki
    
    echo "restoring pki backup"
    cp -Rp $BACKUP_DIR/pki $EASYRSA_DIR
fi

if [[ -e $BACKUP_DIR/pki-openvpn-int ]]; then
    echo "clearing pki-openvpn-int"
    rm -rf $EASYRSA_DIR/pki-openvpn-int
    
    echo "restoring pki-openvpn-int backup"
    cp -Rp $BACKUP_DIR/pki-openvpn-int $EASYRSA_DIR
fi

if [[ -e $BACKUP_DIR/pki-squid-int ]]; then
    echo "clearing pki-squid-int"
    rm -rf $EASYRSA_DIR/pki-squid-int
    
    echo "restoring pki-squid-int backup"
    cp -Rp $BACKUP_DIR/pki-squid-int $EASYRSA_DIR
fi

