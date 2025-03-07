#!/bin/bash
#-----upgrade openvpn to the latest version-----
# user specifies the version to upgrade to on the command line
# protect against accidental downgrades or invalid version numbers
# this will operate similar to /install/080_install-openvpn.sh
# it assumes that openvpn has already been cloned from git into ~/src/openvpn/
#
# cmd options:
#   /opt/zzz/upgrade/upgrade-openvpn.sh --latest
#   /opt/zzz/upgrade/upgrade-openvpn.sh 2.6.0
#   /opt/zzz/upgrade/upgrade-openvpn.sh v2.6.0
#
#--------------------------------------------------------------------------------
# get version param:
#   https://openvpn.net/community-downloads/
# 3/13/2019:
#   2.4.7 source:
#       https://swupdate.openvpn.org/community/releases/openvpn-2.4.7.tar.gz
#   2.4.7 signature:
#       https://swupdate.openvpn.org/community/releases/openvpn-2.4.7.tar.gz.asc
#--------------------------------------------------------------------------------

#TODO: auto-verify signature after downloading

echo "upgrade-openvpn.sh - START"

SRC_DIR=/home/ubuntu/src
OPENVPN_SRC=$SRC_DIR/openvpn

#-----import bash utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR

# specify the version number, or "--latest"
REQUESTED_VERSION=$1
if [[ "$REQUESTED_VERSION" == "" ]];then
    echo "ERROR: version not specified"
    echo "use --latest or specify a version number"
    exit
fi

#-----check if the openvpn src directory exists-----
if [[ ! -e "$OPENVPN_SRC" ]]; then
   echo "ERROR: openvpn src directory not found" 
   exit 1
fi

cd $OPENVPN_SRC

#-----update the tag list-----
git fetch --quiet

#-----get the latest production version of OpenVPN-----
# "v2.6.12"
OPENVPN_LATEST_STABLE_VERSION=`git tag | grep -v '_' | sort --version-sort | tail -1`

if [[ "$REQUESTED_VERSION" == "--latest" ]];then
    # for "--latest", get the latest version
    NEW_VERSION=$OPENVPN_LATEST_STABLE_VERSION
else
    # for a version number, make sure the tag exists
    ZZZ_TEST_VERSION_REGEX="^v"
    if [[ "$REQUESTED_VERSION" =~ $ZZZ_TEST_VERSION_REGEX ]]; then
        # remove the "v" if it's there
        REQUESTED_VERSION=`echo "$REQUESTED_VERSION" | cut -d 'v' -f 2`
    fi
    REQUESTED_VERSION=v$REQUESTED_VERSION

    # reference upgrade-squid.sh
    # version 2.5.7+ is required
    if [[ $REQUESTED_VERSION =~ ^v[2]\.[5]\.[7-9]$ ]]; then
        NEW_VERSION=$REQUESTED_VERSION
    elif [[ $REQUESTED_VERSION =~ ^v[2]\.[6-9]\.[0-9]*$ ]]; then
        NEW_VERSION=$REQUESTED_VERSION
    elif [[ $REQUESTED_VERSION =~ ^v[3]\.[0-9]\.[0-9]*$ ]]; then
        NEW_VERSION=$REQUESTED_VERSION
    else
        #-----ERROR-----
        echo "ERROR: bad version number (must be 2.5.7 or later)"
        exit
    fi

    validate_openvpn_version $REQUESTED_VERSION
    if [[ "$VALIDATE_OPENVPN_VERSION_FOUND" == "" ]]; then
        echo "ERROR: version $REQUESTED_VERSION was not found in openvpn's github"
        exit
    fi
fi

calc_openvpn_version_tag $NEW_VERSION
CALC_NEW_VERSION=$OPENVPN_CALC_VERSION
DISPLAY_NEW_VERSION=$OPENVPN_DISPLAY_VERSION

#-----get the current installed version-----
INSTALLED_VERSION=`openvpn --version | grep -P 'OpenVPN \d' | cut -d ' ' -f 2`
calc_openvpn_version $INSTALLED_VERSION
CALC_INSTALLED_VERSION=$OPENVPN_CALC_VERSION
INSTALLED_VERSION="v$INSTALLED_VERSION"

echo "OPENVPN_SRC: $OPENVPN_SRC"
echo "INSTALLED_VERSION: $INSTALLED_VERSION"
echo "OPENVPN_LATEST_STABLE_VERSION: $OPENVPN_LATEST_STABLE_VERSION"

#TEST:
#echo "TEST: CALC_NEW_VERSION=$CALC_NEW_VERSION CALC_INSTALLED_VERSION=$CALC_INSTALLED_VERSION"

#-----if ($INSTALLED_VERSION>=$DISPLAY_NEW_VERSION) { show warning }-----
if (( $(echo "$CALC_INSTALLED_VERSION > $CALC_NEW_VERSION" |bc -l) ))
then
    echo
    echo "WARNING: installed openvpn version($INSTALLED_VERSION) is greater than the new version($DISPLAY_NEW_VERSION)"
fi

if [ "$CALC_INSTALLED_VERSION" == "$CALC_NEW_VERSION" ]
then
    echo
    echo "NOTE: installed openvpn version($INSTALLED_VERSION) is the same as the new version($DISPLAY_NEW_VERSION)"
fi

echo
echo "This app will take about 3 minutes to compile OpenVPN."
echo "The currently-installed version of OpenVPN will still be running during compiling."
echo "OpenVPN will be shut down during installation, then started afterwards."
echo

zzz_proceed_or_exit

#-----git checkout-----
git checkout tags/$NEW_VERSION

#-----initialize the Git submodule inside openvpn (required for the compile to work)-----
git submodule update --recursive
autoreconf -i

#-----configure and compile-----
./configure --enable-systemd
make -j `nproc`

#-----verify and install-----
make check
echo "Stopping openvpn..."
/opt/zzz/python/bin/subprocess/openvpn-stop.sh

echo "Installing openvpn..."
make install

# avoid this error:
#   Warning: The unit file, source configuration file or drop-ins of openvpn-server@server.service changed on disk. Run 'systemctl daemon-reload' to reload units.
systemctl daemon-reload

echo "Starting openvpn..."
/opt/zzz/python/bin/subprocess/openvpn-start.sh

# re-run the daily version check
/opt/zzz/python/bin/check-latest-version.py

echo
echo "upgrade-openvpn.sh - END"
