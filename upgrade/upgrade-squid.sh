#!/bin/bash
#-----upgrade squid to the latest version-----
# user specifies the version to upgrade to on the command line
# protect against accidental downgrades or invalid version numbers
# this will operate similar to /install/100_install-squid.sh

#TEST - set to "n" when going live
SQUID_INSTALL_TEST=n

#--------------------------------------------------------------------------------
# get version param:
#   http://www.squid-cache.org/Versions/
# Version 4 page:
#   http://www.squid-cache.org/Versions/v4/
# 1/1/2019:
#   4.5 patch file:
#       http://www.squid-cache.org/Versions/v4/squid-4.5.patch
#   4.5 source:
#       http://www.squid-cache.org/Versions/v4/squid-4.5.tar.gz
# 2/19/2019:
#   4.6 source:
#       http://www.squid-cache.org/Versions/v4/squid-4.6.tar.gz
#   4.6 signature:
#       http://www.squid-cache.org/Versions/v4/squid-4.6.tar.gz.asc
# 9/25/2021:
#   4.16 source:
#       http://www.squid-cache.org/Versions/v4/squid-4.16.tar.gz
#   4.16 signature:
#       http://www.squid-cache.org/Versions/v4/squid-4.16.tar.gz.asc
#   5.1 source:
#       http://www.squid-cache.org/Versions/v5/squid-5.1.tar.gz
#   5.1 signature:
#       http://www.squid-cache.org/Versions/v5/squid-5.1.tar.gz.asc
# 10/3/2021: version 5.2
# 4/13/2022: version 5.5
# 6/6/2022: version 5.6
# 9/16/2022: version 5.7
# 2/28/2023: version 5.8
#
#--------------------------------------------------------------------------------

echo "upgrade-squid.sh - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: RUN_AS_UBUNTU, SQUID_INSTALLER_STATUS_FILE

SRC_DIR=/home/ubuntu/src
cd $SRC_DIR

#-----get the latest production version of Squid-----
# version number is hardcoded or user-specified on the command line
# EXAMPLE: "Squid Cache: Version 4.4"
calc_squid_version_tag $ZZZ_SQUID_VERSION_TAG
NEW_VERSION=$SQUID_DISPLAY_VERSION
REQUESTED_VERSION=$1
SKIP_COMPILE=$2

if [ "$REQUESTED_VERSION" == "" ]; then
    echo "ERROR: version number not specified"
    exit
fi

# version 5+ is required for the zzz squid config to work
if [[ $REQUESTED_VERSION =~ ^[5-6]\.[0-9]$ ]]; then
    NEW_VERSION=$REQUESTED_VERSION
else
    # minor version number may go over 9
    if [[ $REQUESTED_VERSION =~ ^[5-6]\.[0-9][0-9]$ ]]; then
        NEW_VERSION=$REQUESTED_VERSION
    else
        #-----ERROR-----
        echo "ERROR: bad version number (must be 5.x-6.x)"
        exit
    fi
fi

SQUID_MAJOR_VERSION=`echo $NEW_VERSION | cut -d '.' -f 1`
SQUID_MINOR_VERSION=`echo $NEW_VERSION | cut -d '.' -f 2`
SQUID_DOWNLOAD_URL="http://www.squid-cache.org/Versions/v"

#-----get the current installed version-----
# Example: Squid Cache: Version 4.10-VCS
# "-VCS" is only there if it was installed from github
INSTALLED_VERSION=`squid -v | grep -P 'Version \d+\.\d+' | cut -d ' ' -f 4 | cut -d '-' -f 1`
INSTALLED_MAJOR_VERSION=`echo $INSTALLED_VERSION | cut -d '.' -f 1`
INSTALLED_MINOR_VERSION=`echo $INSTALLED_VERSION | cut -d '.' -f 2`

# calc_squid_version provides vars: SQUID_MAJOR_VERSION, SQUID_MINOR_VERSION, SQUID_PATCH_VERSION, SQUID_CALC_VERSION
calc_squid_version $INSTALLED_VERSION
CALC_INSTALLED_VERSION=$SQUID_CALC_VERSION

# calc_squid_version provides vars: SQUID_MAJOR_VERSION, SQUID_MINOR_VERSION, SQUID_PATCH_VERSION, SQUID_CALC_VERSION
calc_squid_version $NEW_VERSION
CALC_NEW_VERSION=$SQUID_CALC_VERSION
DISPLAY_NEW_VERSION=$SQUID_DISPLAY_VERSION

if [ "$SQUID_INSTALL_TEST" == "y" ]; then
    echo "SQUID_MAJOR_VERSION=$SQUID_MAJOR_VERSION"
    echo "SQUID_MINOR_VERSION=$SQUID_MINOR_VERSION"
    echo "SRC_DIR: $SRC_DIR"
    echo
fi

echo "INSTALLED_VERSION: $INSTALLED_VERSION"
echo "NEW_VERSION: $NEW_VERSION"

#-----if ($INSTALLED_VERSION>=$NEW_VERSION) { print warning }-----
if (( $(echo "$CALC_INSTALLED_VERSION > $CALC_NEW_VERSION" |bc -l) ))
then
    echo
    echo "WARNING: installed squid version($INSTALLED_VERSION) is greater than the new version($NEW_VERSION)"
fi

if [ "$INSTALLED_VERSION" == "$NEW_VERSION" ]
then
    echo
    echo "NOTE: installed squid version($INSTALLED_VERSION) is the same as the new version($NEW_VERSION)"
fi

SQUID_NAME_VERSION=squid-$NEW_VERSION
SQUID_SRC=$SRC_DIR/$SQUID_NAME_VERSION
SQUID_FILE=$SQUID_NAME_VERSION.tar.gz
SQUID_SIGNATURE_FILE=$SQUID_FILE.asc
SQUID_URL="$SQUID_DOWNLOAD_URL$SQUID_MAJOR_VERSION/$SQUID_FILE"
SQUID_SIGNATURE_URL="$SQUID_URL.asc"

if [ "$SQUID_INSTALL_TEST" == "y" ]; then
    echo
    echo "SQUID_NAME_VERSION: $SQUID_NAME_VERSION"
    echo "SQUID_SRC: $SQUID_SRC"
    echo "SQUID_FILE: $SQUID_FILE"
    echo "SQUID_URL: $SQUID_URL"
    echo "SQUID_SIGNATURE_FILE: $SQUID_SIGNATURE_FILE"
    echo "SQUID_SIGNATURE_URL: $SQUID_SIGNATURE_URL"
fi

echo
echo "This app will take about 20 minutes to compile squid."
echo "After compiling, it will install."
echo "Squid will be shut down during installation, then started afterwards."
echo

zzz_proceed_or_exit

#-----run the download/verify/install, check for errors-----
if [[ "$SKIP_COMPILE" == "--skip-compile" ]]; then
    echo -n "OK" > $SQUID_INSTALLER_STATUS_FILE
else
    /opt/zzz/util/squid_download_verify_compile.sh $NEW_VERSION
fi
ZZZ_SQUID_DOWNLOAD_VERIFY_COMPILE=`cat $SQUID_INSTALLER_STATUS_FILE`
if [ "$ZZZ_SQUID_DOWNLOAD_VERIFY_COMPILE" != "OK" ]; then
    echo "$ZZZ_SQUID_DOWNLOAD_VERIFY_COMPILE"
    exit
fi

if [ "$SQUID_INSTALL_TEST" == "y" ]; then
    echo "TEST - exiting early..."
    exit
fi

#-----var is set by squid_download_verify_compile.sh-----
cd $SQUID_SRC

#-----install and restart-----
echo "Stopping squid..."
systemctl stop squid
systemctl stop squid-icap

echo "Installing squid..."
make install

echo "Starting squid..."
systemctl start squid
systemctl start squid-icap

echo
echo "upgrade-squid.sh - END"
