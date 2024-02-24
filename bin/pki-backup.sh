#!/bin/bash
#-----backup the PKI-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

BACKUP_DIR=/home/ubuntu/backup
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`

mkdir -p $BACKUP_DIR

# clear old backups
if [[ -e $BACKUP_DIR/pki ]]; then
    echo "clearing pki backup"
    rm -rf $BACKUP_DIR/pki
fi

if [[ -e $BACKUP_DIR/pki-openvpn-int ]]; then
    echo "clearing pki-openvpn-int backup"
    rm -rf $BACKUP_DIR/pki-openvpn-int
fi

if [[ -e $BACKUP_DIR/pki-squid-int ]]; then
    echo "clearing pki-squid-int backup"
    rm -rf $BACKUP_DIR/pki-squid-int
fi

echo "backing up pki"
cp -Rp $EASYRSA_DIR/pki $BACKUP_DIR

echo "backing up pki-openvpn-int"
cp -Rp $EASYRSA_DIR/pki-openvpn-int $BACKUP_DIR

echo "backing up pki-squid-int"
cp -Rp $EASYRSA_DIR/pki-squid-int $BACKUP_DIR

