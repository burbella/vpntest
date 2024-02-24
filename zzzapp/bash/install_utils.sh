#!/bin/bash
#-----shell script utility functions for use in the installer script-----
# USAGE:
#   source $REPOS_DIR/zzzapp/bash/install_utils.sh
# anything that needs to be added to the install.sh can be added here instead
# this avoid messing with the main install.sh file and risking problems:
#   execute permission becoming unset
#   line endings getting messed up

ZZZ_REPOS_NAME=vpntest
REPOS_DIR=/home/ubuntu/repos/$ZZZ_REPOS_NAME
ZZZ_CONFIG_FILE=/etc/zzz.conf
#ZZZ_INSTALLER_DIR=$REPOS_DIR/install
ZZZ_INSTALLER_DIR=/opt/zzz/install
ZZZ_LOG_DIR=/var/log/zzz/install
ZZZ_LOG_FILEPATH=$ZZZ_LOG_DIR/install.log
ZZZ_LOG_OPENVPN_FILEPATH=$ZZZ_LOG_DIR/install-openvpn.log
ZZZ_LOG_SQUID_FILEPATH=$ZZZ_LOG_DIR/install-squid.log
DB_FILE=/opt/zzz/sqlite/services.sqlite3

#--------------------------------------------------------------------------------

#TODO: replace this function with a python script
zzz_prepare_to_install() {
    #-----exit if the user did not install the config-----
    if [[ ! -e "$ZZZ_CONFIG_FILE" ]]; then
       echo "You must install the config file before running install: $ZZZ_CONFIG_FILE"
       exit 1
    fi
    
    check_os_version
    if [[ "$ZZZ_OS_RELEASE_STATUS" != "True" ]]; then
        echo "$ZZZ_OS_RELEASE_ERROR"
        echo "OS must be Ubuntu 20.04"
        exit 1
    fi

    for i in \
        init-squid-pki.sh \
        init-squid-top-pki.sh \
        pki_utils.sh ; do
        cp $REPOS_DIR/zzzapp/bash/$i /opt/zzz/util
        chmod 755 /opt/zzz/util/$i
        dos2unix -q /opt/zzz/util/$i
    done
    
    #-----log installation outputs to the log directory-----
    # redirect STDERR to STDOUT for logging
    #TODO: separate log files for each installer command?
    #      separate error logs from output logs?
    mkdir -p $ZZZ_LOG_DIR
    
    #-----copy installer files out of repos and make them runnable-----
    mkdir -p $ZZZ_INSTALLER_DIR
    cp $REPOS_DIR/install/* $ZZZ_INSTALLER_DIR
    
    #-----cleanup any line endings issues on installer files and make sure they can execute-----
    find $ZZZ_INSTALLER_DIR -type f -exec dos2unix -q {} \;
    chmod 755 $ZZZ_INSTALLER_DIR/*.sh

}

#--------------------------------------------------------------------------------

zzz_ask_user_to_verify_config() {
    exit_if_configtest_invalid
    
    local zzzConfig_PhysicalNetworkInterfaces_internal=`/opt/zzz/python/bin/config-parse.py --var 'PhysicalNetworkInterfaces/internal'`
    local zzzConfig_VPNserver=`/opt/zzz/python/bin/config-parse.py --var 'IPv4/VPNserver' --yaml`
    #local zzzConfig_VPNusers=`/opt/zzz/python/bin/config-parse.py --var 'VPNusers' --yaml`
    local zzzConfig_Domain=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
    local zzzConfig_CA_Default=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/Default'`
    
    #-----get the physical network interfaces-----
    if [[ $zzzConfig_PhysicalNetworkInterfaces_internal == "AUTODETECT" ]]; then
        lookup_physical_network_interface
        zzzConfig_PhysicalNetworkInterfaces_internal=$ZZZ_PHYSICAL_NETWORK_INTERFACE
        echo "Autodetected network interface: '$zzzConfig_PhysicalNetworkInterfaces_internal'"
    fi
    
    echo "--------------------------------------------------------------------------------"
    
    #-----get the server IP's if needed-----
    echo "VPNserver: $zzzConfig_VPNserver"
    if [[ $zzzConfig_VPNserver == "AUTODETECT" ]]; then
        autodetect_ipv4
        zzzConfig_VPNserver=$ZZZ_AUTODETECT_IPV4
        echo "Autodetected VPNserver IPv4: '$zzzConfig_VPNserver'"
    fi
    
    echo
    echo "The install process may take over 30 minutes."
    echo "Run this app in 'screen' in case of lost connection."
    echo
    echo "Here is the config data in $ZZZ_CONFIG_FILE:"
    echo "  Domain: $zzzConfig_Domain (apache SSL cert uses this)"
    echo "  CA Default name: $zzzConfig_CA_Default"
    echo "  Network interface: $zzzConfig_PhysicalNetworkInterfaces_internal"
    echo "  VPNserver: $zzzConfig_VPNserver (VPN clients connect to this - must be externally available)"
    echo "If these are not the correct settings, exit this app and update the config file, then run the app again."
    echo
    echo "VPN users list:"
    /opt/zzz/python/bin/build-config.py --openvpn-users -q
    cat /opt/zzz/data/openvpn_users.txt
    #echo $zzzConfig_VPNusers | tr "," "\n"
    echo
    
    zzz_proceed_or_exit
}

#--------------------------------------------------------------------------------

#-----install just enough things to run the Config check in python-----
zzz_installer_part1() {
    echo "--------------------------------------------------------------------------------"
    echo "Preparing Apps"
    echo "After preparation, you will need to verify the config values and approve/deny the installation"
    echo "This should take a few minutes"
    echo "--------------------------------------------------------------------------------"
    
    echo "SSH User Config"
    ./001_ssh-user-config.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "make app directories"
    ./010_make-app-directories.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Ubuntu repos apps"
    ./020_install-apps-from-repos.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "SQLite"
    ./030_configure-sqlite.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Zzz Tools"
    ./040_install-zzz-tools.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Update OS"
    ./050_update-os.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    #-----set a flag to indicate that part1 is done-----
    touch /opt/zzz/install_part1

    #-----reboot before part2-----
    echo
    echo "Exiting for first reboot..."
    echo "Exiting for first reboot..." >> $ZZZ_LOG_FILEPATH 2>&1
    /usr/sbin/reboot
    exit
}

#--------------------------------------------------------------------------------

zzz_call_installer_scripts() {
    echo "Installing..."
    
    #-----ran the entire install before? just return-----
    if [[ -e '/opt/zzz/install_part2' ]]; then
        echo "Skipping the install, looks like it was done already"
        exit
    fi
    
    cd $ZZZ_INSTALLER_DIR
    
    #-----ran the first part of the install before? skip the first part of it this time-----
    if [[ -e '/opt/zzz/install_part1' ]]; then
        echo "Skipping part 1, looks like it was done already"
    else
        zzz_installer_part1
    fi
    
    #-----check config file here and wait for user confirmation-----
    zzz_ask_user_to_verify_config
    
    echo "Configure Zzz System"
    ./055_configure-zzz-system.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"

    #-----EasyRSA and PKI before OpenVPN, because OpenVPN needs the certs-----
    #TODO: need a config option to skip this if an existing PKI is being used
    echo "EasyRSA"
    ./060_install-easyrsa.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    echo "PKI"
    ./070_setup-pki.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    #-----install OpenVPN FIRST, then BIND-----
    # OpenVPN creates the tunnel interfaces with virtual IP's that BIND uses
    echo "OpenVPN (takes about 3 minutes)"
    echo "OpenVPN-start" >> $ZZZ_LOG_FILEPATH
    echo "output logged to $ZZZ_LOG_OPENVPN_FILEPATH" >> $ZZZ_LOG_FILEPATH
    ./080_install-openvpn.sh >> $ZZZ_LOG_OPENVPN_FILEPATH 2>&1
    echo "OpenVPN-Done" >> $ZZZ_LOG_FILEPATH
    echo "Done"
    echo "BIND"
    ./090_configure-bind.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Squid (takes about 20 minutes)"
    echo "Squid-start" >> $ZZZ_LOG_FILEPATH
    echo "output logged to $ZZZ_LOG_SQUID_FILEPATH" >> $ZZZ_LOG_FILEPATH
    ./100_install-squid.sh >> $ZZZ_LOG_SQUID_FILEPATH 2>&1
    echo "Squid-Done" >> $ZZZ_LOG_FILEPATH
    echo "Done"
    
    echo "Apache"
    ./110_configure-apache.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Zzz custom apps"
    ./120_install-custom-apps.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "iptables"
    ./130_setup-iptables.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Logrotate"
    ./140_logrotate.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    echo "Cron"
    ./150_configure-cron.sh >> $ZZZ_LOG_FILEPATH 2>&1
    echo "Done"
    
    # set a flag to indicate that part2 is done
    touch /opt/zzz/install_part2
    
    # set a flag to indicate that a reboot is needed
    touch /opt/zzz/apache/reboot_needed
    chown www-data.www-data /opt/zzz/apache/reboot_needed
}

#--------------------------------------------------------------------------------

zzz_cleanup_after_install() {
    echo
    echo "User Instructions:"
    cat /opt/zzz/user_instructions.txt
    
    echo
    echo "ZZZEVPN INSTALLER DONE"
    echo

    #-----reboot after install is done-----
    # ask user first, so they have a chance to read the instructions before reboot
    local YES_NO_REPLY=n
    read -p "Copy the info above, then press any key to reboot to finish the installation" -n 1 -r YES_NO_REPLY
    echo
    echo
    echo "Exiting for final reboot..."
    echo "Exiting for final reboot..." >> $ZZZ_LOG_FILEPATH 2>&1
    /usr/sbin/reboot
    exit
}

#--------------------------------------------------------------------------------

zzz_full_system_install() {
    source /opt/zzz/util/util.sh
    # vars set in util.sh: REPOS_DIR
    
    exit_if_not_running_as_root
    
    #-----run installer functions-----
    zzz_prepare_to_install
    
    zzz_call_installer_scripts
    
    zzz_cleanup_after_install
}

#--------------------------------------------------------------------------------

