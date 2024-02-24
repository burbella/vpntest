#!/bin/bash
#-----Zzz full system restore from backup-----
# backups restore from here: /home/ubuntu/backup/
# both the backup (.gz) and checksum (.sha512) files must be there
# certain features will only restore if the appropriate command-line option is added

#-----import bash utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR

lookup_zzz_db_version

ZZZ_BACKUP_DIR=/home/ubuntu/backup
ZZZ_CONFIG_FILE=/etc/zzz.conf
ZZZ_MAIN_DIR=/opt/zzz

#TODO: fetch the installed version from the DB

#--------------------------------------------------------------------------------

show_usage() {
    echo
    echo "Usage: $(basename $0) [-f BACKUP_FILENAME] [-c] [-h] [-g] [-k]"
    echo "  -c install config file from backup"
    echo "  -f BACKUP_FILENAME"
    echo "     BACKUP_FILENAME must be in $ZZZ_BACKUP_DIR"
    echo "     BACKUP_FILENAME.sha512 must also be in $ZZZ_BACKUP_DIR"
    echo "  -g install GeoIP file from backup"
    echo "  -h help (show this message)"
    echo "  -k keep the unzipped backup directory after restore"
}

show_backup_file_requirements() {
    echo "Make sure the backup and sha512 files are here:"
    echo "/home/ubuntu/backup/"
}

#--------------------------------------------------------------------------------

cd $ZZZ_BACKUP_DIR

echo "Zzz full system restore from backup"
echo "Make sure the install process has been done on this server before running this restore"
echo

ZZZ_OPTS_PROVIDED=False
ZZZ_ERROR_EXIT=False
ZZZ_INSTALL_CONFIG=False
ZZZ_INSTALL_GEOIP=False
ZZZ_KEEP_BACKUP_DIR=False
while getopts ":hcf:gk" opt; do
    ZZZ_OPTS_PROVIDED=True
    case ${opt} in
        c )
            echo "installing config from backup"
            ZZZ_INSTALL_CONFIG=True
            ;;
        f )
            ZZZ_BACKUP_FILENAME=$OPTARG
            ;;
        g )
            echo "installing GeoIP from backup"
            ZZZ_INSTALL_GEOIP=True
            ;;
        h )
            show_usage
            ;;
        k )
            echo "keeping the unzipped backup directory after restore"
            ZZZ_KEEP_BACKUP_DIR=True
            ;;
        \? )
            echo "INVALID OPTION: $OPTARG" 1>&2
            show_usage
            ZZZ_ERROR_EXIT=True
            ;;
        : )
            echo "INVALID OPTION: $OPTARG requires an argument" 1>&2
            show_usage
            ZZZ_ERROR_EXIT=True
            ;;
    esac
done
shift $((OPTIND -1))

if [[ "$ZZZ_OPTS_PROVIDED" == "False" ]]; then
    show_usage
    exit
fi

if [[ "$ZZZ_ERROR_EXIT" == "True" ]]; then
    exit
fi

echo

ZZZ_TEST_FILEPATH_REGEX="^$ZZZ_BACKUP_DIR"
if [[ "$ZZZ_BACKUP_FILENAME" =~ $ZZZ_TEST_FILEPATH_REGEX ]]; then
    # take the directory out of the filename
    ZZZ_BACKUP_FILENAME=`echo "$ZZZ_BACKUP_FILENAME" | cut -d '/' -f 5`
fi
ZZZ_BACKUP_FILEPATH=$ZZZ_BACKUP_DIR/$ZZZ_BACKUP_FILENAME
ZZZ_CHECKSUM_FILEPATH=$ZZZ_BACKUP_FILEPATH.sha512

#--------------------------------------------------------------------------------

ZZZ_FOUND_INSTALLED_STUFF=True
if [ ! -f "$ZZZ_CONFIG_FILE" ]; then
    ZZZ_FOUND_INSTALLED_STUFF=False
fi
if [ ! -d "$ZZZ_MAIN_DIR" ]; then
    ZZZ_FOUND_INSTALLED_STUFF=False
fi
if [ "$ZZZ_FOUND_INSTALLED_STUFF" != "True" ]; then
    echo "ERROR: Zzz System appears to be missing files"
    echo "Make sure the Zzz install process has been completed on this server before running this restore"
    exit
fi

if [ "$ZZZ_BACKUP_FILENAME" == "" ]; then
    echo "ERROR: no backup file specified"
    show_backup_file_requirements
    exit
fi

if [ ! -f "$ZZZ_BACKUP_FILEPATH" ]; then
    echo "ERROR: Backup file not found"
    echo "  $ZZZ_BACKUP_FILEPATH"
    show_backup_file_requirements
    exit
fi

echo "Found backup file: $ZZZ_BACKUP_FILEPATH"

if [ ! -f "$ZZZ_CHECKSUM_FILEPATH" ]; then
    echo "ERROR: Checksum file not found"
    echo "  $ZZZ_CHECKSUM_FILEPATH"
    show_backup_file_requirements
    exit
fi

echo "Found checksum file: $ZZZ_CHECKSUM_FILEPATH"

#-----directory name matches filename, just take off the .tar.gz-----
ZZZ_BACKUP_CUSTOM_DIR=`echo $ZZZ_BACKUP_FILEPATH | cut -d '.' -f 1`

#-----check the backup file name format-----
ZZZ_TEST_REGEX='^backup\-([0-9]+)\-([0-9]+)\-([0-9]+)\-([0-9]+)\-([0-9]+)\-([0-9]+)\-([0-9]+)\.tar\.gz$'
if [[ ! "$ZZZ_BACKUP_FILENAME" =~ $ZZZ_TEST_REGEX ]]; then
    echo "ERROR: filename not in the expected format:"
    echo "  backup-VERSION-YYYY-MM-DD-HH24-MI-SS.tar.gz"
    exit
fi
echo "Backup filename pattern looks OK"

#-----filename contains version and backup date-----
# ZZZ_CUSTOM_DIR=backup-$ZZZ_VERSION-$DATETIME.tar.gz
# EX: backup-20-2021-01-01-06-26-47.tar.gz
ZZZ_BACKUP_VERSION=`echo $ZZZ_BACKUP_FILENAME | cut -d '-' -f 2`
ZZZ_BACKUP_DATE=`echo $ZZZ_BACKUP_FILENAME | cut -d '.' -f 1 | cut -d '-' -f 3-8`

if [[ "$ZZZ_BACKUP_VERSION" != "$ZZZ_VERSION" ]]; then
    echo "ERROR: backup version does not match installed version"
    echo "  backup version: $ZZZ_BACKUP_VERSION"
    echo "  installed version: $ZZZ_VERSION"
    echo "  make sure to install Zzz version $ZZZ_BACKUP_VERSION before restoring from backup"
    exit
fi
echo "backup version matches installed version"

#-----check the filetype-----
ZZZ_TEST_FILETYPE=`file -b $ZZZ_BACKUP_FILEPATH`
ZZZ_TEST_REGEX='^gzip compressed data'
echo "File format check: $ZZZ_TEST_FILETYPE"
if [[ ! "$ZZZ_TEST_FILETYPE" =~ $ZZZ_TEST_REGEX ]]; then
    echo "ERROR: Expecting a gzip file"
    exit
fi
echo "Backup file content type looks OK"

#-----check the backup checksum-----
/usr/bin/sha512sum --check --strict --status $ZZZ_CHECKSUM_FILEPATH
ZZZ_CHECKSUM_RESULT=$?
if [[ $ZZZ_CHECKSUM_RESULT -ne 0 ]]; then
    echo "ERROR: Backup file checksum failed to verify"
    exit
fi
echo "Backup file checksum verified OK"

#TODO: check the volume label?
#  tar --gzip --test-label --file backup-2020-08-18-03-52-21.tar.gz
#  should return "backup-2020-08-18-03-52-21"

#-----unzip the backup file into the restore directory-----
# /home/ubuntu/backup/zzz_full_backup_YYYY-MM-DD-HH-MI-SS.tar.gz --> /home/ubuntu/backup/zzz_full_backup_YYYY-MM-DD-HH-MI-SS/
tar --gzip --extract --overwrite --file $ZZZ_BACKUP_FILENAME

#-----check the VPNserver IP for appropriate config-----
# ZZZ_CONFIG_FILE_TO_USE value is set by check_autodetect_matches_hardcoded()
if [[ "$ZZZ_INSTALL_CONFIG" == "True" ]]; then
    check_autodetect_matches_hardcoded "$ZZZ_BACKUP_CUSTOM_DIR/config/zzz.conf"
    echo "Using backup config: $ZZZ_CONFIG_FILE_TO_USE"
else
    check_autodetect_matches_hardcoded
    echo "Keeping installed config: $ZZZ_CONFIG_FILE_TO_USE"
fi

if [[ "$ZZZ_AUTODETECT_MATCHES_HARDCODED" == "True" ]]; then
    echo "Backup config VPNserver setting verified"
else
    echo
    echo "WARNING: VPNserver value in zzz.conf may not point to this server"
    # zzzConfig_VPNserver value is set by check_autodetect_matches_hardcoded()
    echo "  VPNserver: $zzzConfig_VPNserver"
    if [[ "$ZZZ_DNS_LOOKUP" != "" ]]; then
        echo "  VPNserver DNS lookup: $ZZZ_DNS_LOOKUP"
    fi
    echo "  Auto-detected IP: $ZZZ_AUTODETECT_IPV4"
fi

echo
echo "--------------------------------------------------"
echo "Config File Differences: (BACKUP vs INSTALLED)"
echo
diff $ZZZ_BACKUP_CUSTOM_DIR/config/zzz.conf $ZZZ_CONFIG_FILE
echo "--------------------------------------------------"
echo
echo "Ready to do Zzz System Restore"

zzz_proceed_or_exit

#--------------------------------------------------------------------------------

echo
echo "Restoring Zzz System from Backup . . ."

#-----stop crons in case one of them want to write to the DB while it is copying-----
systemctl stop cron

#-----stop services (zzz_icap will not go down as long as squid is running)-----
echo
echo "Stopping Services: apache2, squid, zzz, zzz_icap"
systemctl stop zzz
systemctl stop apache2
systemctl stop squid
systemctl stop zzz_icap

#-----give the zzz daemon a chance to shut down-----
sleep 3

#TODO:
#  finish this
#  need to chown/chmod everything?  or will usernames/permissions transfer between systems safely?
#  make a restore directory?  restore to the same backup directory?
#  what if the new machine has a different IP?
#    auto-detect the new IP if zzz.conf allows it, then fix IP's in the relevant configs
#    need a reset-IP script:
#       openvpn user configs
#       ?
#  confirm with user about which config settings should be used (new or old)

#--------------------------------------------------------------------------------

#-----copy files into place-----
echo
echo "Copying Files"

#-----backup zzz.conf if we're over-writing it with the backup-----
DATE_TODAY=`date '+%Y%m%d'`
if [[ "$ZZZ_INSTALL_CONFIG" == "True" ]]; then
    cp -p $ZZZ_CONFIG_FILE $ZZZ_CONFIG_FILE.$DATE_TODAY
    cp -p $ZZZ_BACKUP_CUSTOM_DIR/config/zzz.conf /etc
    cp $ZZZ_BACKUP_CUSTOM_DIR/openvpn_users.txt /opt/zzz/data
fi

#TODO: detect if any DB-accessing python apps are still running (daemon, icap, crons)
#-----restore the DB early since DB data will be used to rebuild iptables files-----
cp -p $ZZZ_BACKUP_CUSTOM_DIR/sqlite/* /opt/zzz/sqlite

rm -rf /home/ubuntu/easyrsa3/pki
rm -rf /home/ubuntu/easyrsa3/pki-openvpn-int
rm -rf /home/ubuntu/easyrsa3/pki-squid
rm -rf /home/ubuntu/easyrsa3/pki-squid-top
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki /home/ubuntu/easyrsa3
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki-openvpn-int /home/ubuntu/easyrsa3
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki-squid /home/ubuntu/easyrsa3
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki-squid-top /home/ubuntu/easyrsa3

#-----BIND-----
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/config/bind/* /etc/bind

#-----reload iptables-----
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/iptables /etc/iptables
/opt/zzz/python/bin/init-iptables.py
/etc/iptables/ipset-update-allow-ip.sh
/etc/iptables/ipset-update-blacklist.sh
/etc/iptables/ipset-update-countries.sh

#-----squid-----
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/squid/* /etc/squid

#-----openvpn-----
cp -pR $ZZZ_BACKUP_CUSTOM_DIR/openvpn/* /etc/openvpn

if [[ "$ZZZ_INSTALL_GEOIP" == "True" ]]; then
    cp -p $ZZZ_BACKUP_CUSTOM_DIR/GeoIP/GeoLite2-Country.mmdb /usr/share/GeoIP
fi

#-----don't need the unzipped backup directory, now that the files have been installed-----
if [[ "$ZZZ_KEEP_BACKUP_DIR" == "False" ]]; then
    rm -rf $ZZZ_BACKUP_CUSTOM_DIR
fi

####################################
# TODO: FINISH THE REBUILD SCRIPTS #
####################################

#-----re-build files with hardcoded IP's/DNS-----
# apache configs:
#   /etc/apache2/*
# openvpn server configs:
#   /etc/openvpn/*
# openvpn client configs:
#   /home/ubuntu/openvpn/*
#/opt/zzz/python/bin/openvpn-build-config.py --client -q
/opt/zzz/python/bin/build-config.py --openvpn-client -q
# bind configs
#   /etc/bind/*
# squid configs
#   /etc/squid/*

#TODO: re-use code from these scripts
#   070_setup-pki.sh
#   080_install-openvpn.sh
#   090_configure-bind.sh
#   100_install-squid.sh
#   110_configure-apache.sh
#   source /opt/zzz/util/pki_utils.sh

#-----restart cron-----
systemctl start cron

#--------------------------------------------------------------------------------

#-----restart services-----
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
echo
echo "Restarting Services: bind, openvpn"
echo "Starting Services: apache2, squid, zzz, zzz_icap"
systemctl restart bind9
/opt/zzz/python/bin/subprocess/openvpn-restart.sh
systemctl restart apache2
systemctl start zzz
systemctl start zzz_icap
systemctl start squid
systemctl start squid-icap

if [[ "$ZZZ_INSTALL_CONFIG" == "True" ]]; then
    echo
    echo "Restored vs old config file differences:"
    echo "  $ZZZ_CONFIG_FILE vs $ZZZ_CONFIG_FILE.$DATE_TODAY"
    echo
    diff $ZZZ_CONFIG_FILE $ZZZ_CONFIG_FILE.$DATE_TODAY
fi

#-----user instructions-----
cat << EndOfMessage

Instructions for Finishing the Restore

If the IP is different on the restored server:
    re-build client certs:
        sudo /opt/zzz/python/bin/build-config.py --openvpn-client
If usernames are different on the restored server:
    replace the OpenVPN PKI:
        sudo /opt/zzz/upgrade/re-issue-ca-openvpn.sh

Install the openvpn client config files on each client
    Instructions are in INSTALL.txt - Step 6

Update Settings:
    Browse to the Settings page
        Save Settings
    Browse to the Edit IP page:
        ADD any random IP
        this rebuilds the needed files
    Browse to the Edit DNS page:
        ADD any random domain
        this rebuilds the needed files

EndOfMessage

