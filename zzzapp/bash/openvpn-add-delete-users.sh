#!/bin/bash
#-----OpenVPN add/delete users-----

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid

source /opt/zzz/util/pki_utils.sh
# vars set in pki_utils: OPENVPN_LIST_USERS_TO_DELETE

#-----check for user list changes-----
/opt/zzz/python/bin/openvpn-add-delete-users.py --verify-users
zzz_pki_exit_if_no_updates
echo
zzz_proceed_or_exit

/opt/zzz/python/bin/openvpn-add-delete-users.py --verify-users --update-db

#-----do the add/delete-----
echo "--------------------------------------------------------------------------------"
/opt/zzz/python/bin/build-config.py --easyrsa
echo "--------------------------------------------------------------------------------"
zzz_pki_add_selected_users
echo "--------------------------------------------------------------------------------"
zzz_pki_delete_selected_users
echo "--------------------------------------------------------------------------------"

#-----clear all old OVPN files-----
rm /home/ubuntu/openvpn/*

#-----build OpenVPN client files-----
/opt/zzz/python/bin/build-config.py --openvpn-client
/opt/zzz/python/bin/build-config.py --openvpn-users
echo "--------------------------------------------------------------------------------"

#-----build/install CRL-----
if [[ -f $OPENVPN_LIST_USERS_TO_DELETE ]]; then
    /opt/zzz/util/build-crl-openvpn.sh
    echo "--------------------------------------------------------------------------------"
    # only need an openvpn restart if a user was deleted, to load the latest CRL
    /home/ubuntu/bin/openvpn-restart
fi

#-----restart apps: apache, zzz, zzz_icap-----
systemctl restart apache2
systemctl restart zzz
/home/ubuntu/bin/icap-restart
