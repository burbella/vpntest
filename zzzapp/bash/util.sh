#!/bin/bash
#-----shell script utility functions-----

#-----activate the virtual env-----
if [[ -e '/opt/zzz/venv/bin/activate' ]]; then
    source /opt/zzz/venv/bin/activate
fi

#TODO: move this to "zzzevpn"
ZZZ_REPOS_NAME=vpntest
# assume the repos will be in this directory:
REPOS_DIR=/home/ubuntu/repos/$ZZZ_REPOS_NAME
#ZZZ_INSTALLER_DIR=$REPOS_DIR/install
ZZZ_CONFIG_DIR=/opt/zzz/config
ZZZ_INSTALLER_DIR=/opt/zzz/install
ZZZ_PYTHON_DIR=/opt/zzz/python
ZZZ_PYTEST_DIR=$ZZZ_PYTHON_DIR/test
# needed early in the install process, so reference the repos instead of /opt/zzz/config
UBUNTU_CONFIG_DIR=$REPOS_DIR/config/ubuntu

ZZZ_CONFIG_FILE=/etc/zzz.conf
DB_FILE=/opt/zzz/sqlite/services.sqlite3
MAXMIND_DB_FILE=/usr/share/GeoIP/GeoLite2-Country.mmdb
RUN_AS_UBUNTU="sudo -H -u ubuntu"
ZZZ_LINEFEED=$'\n'
ZZZ_SQUID_VALIDATION_KEY="B06884EDB779C89B044E64E3CD6DBF8EF3B17D3E"
SQUID_INSTALLER_STATUS_FILE="/opt/zzz/install_squid_status"

#-----pip 23.3 started generating errors, so install the last known good version-----
# 10/21/2023 - fixed in version 23.3.1
#   https://pip.pypa.io/en/stable/news/
# WARNING: There was an error checking the latest version of pip.
# the temporary fix is:
#   pip cache purge
# github issue:
#   https://github.com/pypa/pip/issues/12357
# set the version to just "pip" to get the latest
ZZZ_PIP_VERSION="pip==24.1.2"
# ZZZ_PIP_VERSION="pip"

# github tag
ZZZ_SQUID_VERSION_TAG=SQUID_4_13
# version to download from www.squid-cache.org
ZZZ_SQUID_VERSION_INSTALL="6.6"

#-----easyrsa vars filenames-----
VARS_FILENAME_APACHE=vars-apache
VARS_FILENAME_DEFAULT_CA=vars-zzz
VARS_FILENAME_OCSP=vars-ocsp
VARS_FILENAME_OPENVPN_CA=vars-openvpn-ca
VARS_FILENAME_OPENVPN_SERVER=vars-openvpn-server
VARS_FILENAME_OPENVPN_USER=vars-openvpn-user
VARS_FILENAME_SQUID_CA=vars-squid-ca
VARS_FILENAME_SQUID_TOP_CA=vars-squid-top-ca
ZZZ_CERT_DATA_DIR=/opt/zzz/data/ssl-public
ZZZ_OPENVPN_CRLS_DIR=/etc/openvpn/crls
ZZZ_SSL_PRIVATE_DIR=/opt/zzz/data/ssl-private

#-----filepaths for minimized certs-----
MINIMAL_DEFAULT_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/root-ca.crt
MINIMAL_OPENVPN_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/openvpn-ca.crt
MINIMAL_SQUID_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/squid-ca.crt
MINIMAL_SQUID_TOP_PUBLIC_CERT=$ZZZ_CERT_DATA_DIR/squid-top-ca.crt

#--------------------------------------------------------------------------------

zzz_venv_activate() {
    source /opt/zzz/venv/bin/activate
}

#--------------------------------------------------------------------------------

zzz_is_using_venv() {
    if [ -z ${VIRTUAL_ENV+x} ]; then
        echo "VIRTUAL_ENV is unset"
    else
        # expect /opt/zzz/venv
        echo "VIRTUAL_ENV is set to '$VIRTUAL_ENV'"
    fi
}

#--------------------------------------------------------------------------------

exit_if_not_running_as_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root" 
        exit 1
    fi
}

exit_if_not_running_as_ubuntu() {
    local CHECK_WHOAMI=`/usr/bin/whoami`
    if [[ "$CHECK_WHOAMI" != "ubuntu" ]]; then
        echo "ERROR: must run as user ubuntu, exiting..."
        exit 1
    fi
}

#--------------------------------------------------------------------------------

exit_if_configtest_invalid() {
    local zzzConfigTest=`/opt/zzz/python/bin/config-parse.py --test`
    if [[ "$zzzConfigTest" != "valid" ]]; then
        echo "ERROR: Config test failed"
        echo "$zzzConfigTest"
        echo "Exiting..."
        exit 1
    fi
}

convert_string_to_uppercase() {
    local ZZZ_STRING=$1
    ZZZ_UPPERCASE_RESULT=`echo ${ZZZ_STRING^^}`
}

#--------------------------------------------------------------------------------

zzz_proceed_or_exit() {
    local YES_NO_REPLY=n
    read -p "Proceed? (y/n) " -n 1 -r YES_NO_REPLY
    echo
    echo
    if [[ ! $YES_NO_REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit
    fi
}

#--------------------------------------------------------------------------------

lookup_physical_network_interface() {
    ZZZ_PHYSICAL_NETWORK_INTERFACE=`/sbin/ip -oneline -brief link show | cut -d ' ' -f 1 | grep -vP '^(tun|lo)' | head -1`
}

#--------------------------------------------------------------------------------

autodetect_ipv4() {
    ZZZ_AUTODETECT_IPV4=`dig -4 TXT +short o-o.myaddr.l.google.com @ns1.google.com | tr -d '"'`
}

#--------------------------------------------------------------------------------

check_ipv6_activate() {
    ZZZ_IPV6_ACTIVATE=`/opt/zzz/python/bin/config-parse.py --var 'IPv6/Activate'`
}

#--------------------------------------------------------------------------------

autodetect_ipv6() {
    ZZZ_AUTODETECT_IPV6=`dig -6 TXT +short o-o.myaddr.l.google.com @ns1.google.com | tr -d '"'`
}

#--------------------------------------------------------------------------------

extract_domain_from_subdomain() {
    ZZZ_DOMAIN_EXTRACTED=`echo "$1"| cut -d '.' -f 2,3`
}

#--------------------------------------------------------------------------------

lookup_zzz_db_version() {
    ZZZ_VERSION=`sqlite3 $DB_FILE "select version from zzz_system"`
}

#--------------------------------------------------------------------------------

#-----fetch the installed version from the DB-----
lookup_zzz_latest_stable_version() {
    cd $REPOS_DIR
    sudo -H -u ubuntu git fetch >> /dev/null
    ZZZ_LATEST_STABLE_VERSION=`git tag | grep -P '^\d+$' | sort -g | tail -1`
}

#--------------------------------------------------------------------------------

#-----get the latest stable version of the Zzz system-----
checkout_zzz_latest_stable_version() {
    lookup_zzz_latest_stable_version
    sudo -H -u ubuntu git checkout tags/$ZZZ_LATEST_STABLE_VERSION
}

#--------------------------------------------------------------------------------

calc_squid_version() {
    SQUID_DISPLAY_VERSION=$1
    SQUID_MAJOR_VERSION=`echo $SQUID_DISPLAY_VERSION | cut -d '.' -f 1`
    
    SQUID_MINOR_VERSION=`echo $SQUID_DISPLAY_VERSION | cut -d '.' -f 2`
    SQUID_MINOR_VERSION=`printf %02d $SQUID_MINOR_VERSION`
    
    SQUID_PATCH_VERSION=`echo $SQUID_DISPLAY_VERSION | cut -d '.' -f 3`
    SQUID_PATCH_VERSION=`printf %02d $SQUID_PATCH_VERSION`
    
    SQUID_CALC_VERSION="$SQUID_MAJOR_VERSION$SQUID_MINOR_VERSION$SQUID_PATCH_VERSION"
}

calc_squid_version_tag() {
    local TAG_VERSION_TO_CHECK=$1
    SQUID_DISPLAY_VERSION=`echo $TAG_VERSION_TO_CHECK | tr '_' '.' | cut -d '.' -f 2-4`
    
    calc_squid_version $SQUID_DISPLAY_VERSION
}

#--------------------------------------------------------------------------------

calc_openvpn_version() {
    OPENVPN_DISPLAY_VERSION=$1
    OPENVPN_MAJOR_VERSION=`echo $OPENVPN_DISPLAY_VERSION | cut -d '.' -f 1`
    
    OPENVPN_MINOR_VERSION=`echo $OPENVPN_DISPLAY_VERSION | cut -d '.' -f 2`
    OPENVPN_MINOR_VERSION=`printf %02d $OPENVPN_MINOR_VERSION`
    
    OPENVPN_PATCH_VERSION=`echo $OPENVPN_DISPLAY_VERSION | cut -d '.' -f 3`
    OPENVPN_PATCH_VERSION=`printf %02d $OPENVPN_PATCH_VERSION`
    
    OPENVPN_CALC_VERSION="$OPENVPN_MAJOR_VERSION$OPENVPN_MINOR_VERSION$OPENVPN_PATCH_VERSION"
}

calc_openvpn_version_tag() {
    local TAG_VERSION_TO_CHECK=$1
    OPENVPN_DISPLAY_VERSION=`echo $TAG_VERSION_TO_CHECK | cut -d 'v' -f 2`
    
    calc_openvpn_version $OPENVPN_DISPLAY_VERSION
}

# make sure an openvpn version number exists in github
# note: working directory will change when running this
validate_openvpn_version(){
    local TEST_VERSION=$1
    cd /home/ubuntu/src/openvpn
    VALIDATE_OPENVPN_VERSION_FOUND=`git tag | grep -v '_' | grep $TEST_VERSION`
}

#--------------------------------------------------------------------------------

#-----warn if our apparent auto-detected IP does not match the hardcoded IP/DNS in zzz.conf-----
# usage: check $ZZZ_AUTODETECT_MATCHES_HARDCODED for "True" or "False" after calling this function
check_autodetect_matches_hardcoded() {
    ZZZ_CONFIG_FILE_TO_USE=$1
    if [[ "$ZZZ_CONFIG_FILE_TO_USE" == "" ]]; then
        ZZZ_CONFIG_FILE_TO_USE=$ZZZ_CONFIG_FILE
    fi
    
    zzzConfig_VPNserver=`/opt/zzz/python/bin/config-parse.py --var 'IPv4/VPNserver' --yaml`
    
    ZZZ_AUTODETECT_MATCHES_HARDCODED=False
    
    #-----config file already set to AUTODETECT? OK-----
    if [[ "$zzzConfig_VPNserver" == "AUTODETECT" ]]; then
        ZZZ_AUTODETECT_MATCHES_HARDCODED=True
        return
    fi
    
    autodetect_ipv4
    
    #-----config file has a hardcoded IP that matches what we auto-detected-----
    if [[ "$zzzConfig_VPNserver" == "$ZZZ_AUTODETECT_IPV4" ]]; then
        ZZZ_AUTODETECT_MATCHES_HARDCODED=True
        return
    fi
    
    #-----DNS lookup to get the IP from a domain name-----
    # EX: www.google.com has address 172.217.3.196
    #     www.google.com has IPv6 address 2607:f8b0:400a:800::2004
    ZZZ_DNS_LOOKUP=`dig $zzzConfig_VPNserver +short`
    if [[ "$ZZZ_DNS_LOOKUP" == "$ZZZ_AUTODETECT_IPV4" ]]; then
        ZZZ_AUTODETECT_MATCHES_HARDCODED=True
        return
    fi
}

#--------------------------------------------------------------------------------

# /etc/lsb-release
# ubuntu 20.04:
#   DISTRIB_ID=Ubuntu
#   DISTRIB_RELEASE=20.04
#   DISTRIB_CODENAME=focal
#   DISTRIB_DESCRIPTION="Ubuntu 20.04.4 LTS"
# ubuntu 22.04:
#   DISTRIB_ID=Ubuntu
#   DISTRIB_RELEASE=22.04
#   DISTRIB_CODENAME=jammy
#   DISTRIB_DESCRIPTION="Ubuntu 22.04 LTS"
check_os_version(){
    ZZZ_OS_RELEASE_STATUS=False
    ZZZ_OS_RELEASE_ERROR=
    
    local UBUNTU_LSB_RELEASE_FILE=/etc/lsb-release
    if [[ ! -e "$UBUNTU_LSB_RELEASE_FILE" ]]; then
        ZZZ_OS_RELEASE_ERROR="ERROR: missing file /etc/lsb-release"
        return
    fi

    local ZZZ_OS_DISTRIB_ID=`grep DISTRIB_ID $UBUNTU_LSB_RELEASE_FILE | tr -d '\n' | cut -d '=' -f 2`
    if [[ "$ZZZ_OS_DISTRIB_ID" != "Ubuntu" ]]; then
        ZZZ_OS_RELEASE_ERROR="ERROR: OS is not Ubuntu in /etc/lsb-release"
        return
    fi

    ZZZ_OS_DISTRIB_RELEASE=`grep DISTRIB_RELEASE $UBUNTU_LSB_RELEASE_FILE | tr -d '\n' | cut -d '=' -f 2`
    #TODO: allow version 22.04 when easyrsa, openvpn, and squid work with openssl 3.0
    if [[ "$ZZZ_OS_DISTRIB_RELEASE" != "22.04" ]]; then
    # if [[ "$ZZZ_OS_DISTRIB_RELEASE" != "20.04" && "$ZZZ_OS_DISTRIB_RELEASE" != "22.04" ]]; then
    # if [[ "$ZZZ_OS_DISTRIB_RELEASE" != "20.04" ]]; then
        ZZZ_OS_RELEASE_ERROR="ERROR: wrong OS version /etc/lsb-release"
        return
    fi

    ZZZ_OS_RELEASE_STATUS=True
}

#--------------------------------------------------------------------------------

