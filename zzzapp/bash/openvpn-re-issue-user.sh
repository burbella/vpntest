#!/bin/bash
#-----OpenVPN re-issue a user cert-----

echo "OpenVPN re-issue a user cert"
echo "checking username..."

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid

source /opt/zzz/util/pki_utils.sh

#--------------------------------------------------------------------------------

OPENVPN_USERNAME=$1
zzz_pki_check_if_user_exists $OPENVPN_USERNAME

echo
echo "Ready to re-issue cert for user: $OPENVPN_USERNAME"
zzz_proceed_or_exit

#-----do a revoke/add to re-issue the cert-----
echo "Re-issuing cert..."
zzz_pki_delete_user $OPENVPN_USERNAME
zzz_pki_add_user $OPENVPN_USERNAME
echo "--------------------------------------------------------------------------------"

#-----build OpenVPN client files-----
/opt/zzz/python/bin/build-config.py --openvpn-client
echo "--------------------------------------------------------------------------------"

#-----build/install CRL-----
/opt/zzz/util/build-crl-openvpn.sh
echo "--------------------------------------------------------------------------------"
/home/ubuntu/bin/openvpn-restart

echo "DONE"
