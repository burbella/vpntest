#!/bin/bash
#-----upgrade squid to the latest version-----
# find the latest version available in github
# protect against accidental downgrades or invalid version numbers
# this will operate similar to /install/100_install-squid.sh

#--------------------------------------------------------------------------------
# get version param:
#
# cd /home/ubuntu/src/squid
# git fetch
# SQUID_LATEST_STABLE_VERSION=`git tag|grep 'SQUID_'|tail -1`
# git checkout $SQUID_LATEST_STABLE_VERSION
#--------------------------------------------------------------------------------

echo "upgrade-squid-github.sh - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

SRC_DIR=/home/ubuntu/src
SQUID_SRC=$SRC_DIR/squid
cd $SQUID_SRC

REQUESTED_VERSION=$1

#TODO: use python script to get the versions

#-----get the latest production version of Squid (version 4 tree for now)-----
# 4_0_* is not needed
# 5_0_* is not needed
git fetch
SQUID_RECENT_VERSIONS=`git tag|grep -P '^SQUID_([4-9]_\d+)$'`
echo "squid recent versions:"
echo "$SQUID_RECENT_VERSIONS"
#SQUID_LATEST_STABLE_VERSION=SQUID_4_10
SQUID_LATEST_STABLE_VERSION=$ZZZ_SQUID_VERSION_TAG
NEW_VERSION=$SQUID_LATEST_STABLE_VERSION
if [ -n "$REQUESTED_VERSION" ] ; then
    NEW_VERSION=$REQUESTED_VERSION
fi

calc_squid_version_tag $NEW_VERSION
CALC_NEW_VERSION=$SQUID_CALC_VERSION
DISPLAY_NEW_VERSION=$SQUID_DISPLAY_VERSION

#-----get the current installed version-----
# Example: Squid Cache: Version 4.8-VCS --> 4.8
INSTALLED_VERSION=`squid -v | grep -P 'Version \d+\.\d+' | cut -d ' ' -f 4 | cut -d '-' -f 1`
calc_squid_version $INSTALLED_VERSION
CALC_INSTALLED_VERSION=$SQUID_CALC_VERSION

#TEST
#echo "TEST: CALC_NEW_VERSION=$CALC_NEW_VERSION CALC_INSTALLED_VERSION=$CALC_INSTALLED_VERSION"

echo "SRC_DIR: $SRC_DIR"
echo "INSTALLED_VERSION: $INSTALLED_VERSION"
echo "NEW_VERSION: $DISPLAY_NEW_VERSION"

#-----if ($INSTALLED_VERSION>=$DISPLAY_NEW_VERSION) { show warning }-----
if (( $(echo "$CALC_INSTALLED_VERSION > $CALC_NEW_VERSION" |bc -l) ))
then
    echo
    echo "WARNING: installed squid version($INSTALLED_VERSION) is greater than the new version($DISPLAY_NEW_VERSION)"
fi

if [ "$CALC_INSTALLED_VERSION" == "$CALC_NEW_VERSION" ]
then
    echo
    echo "NOTE: installed squid version($INSTALLED_VERSION) is the same as the new version($DISPLAY_NEW_VERSION)"
fi

echo
echo "This app will take about 20 minutes to compile squid."
echo "The currently-installed version of squid will still be running during compiling."
echo "Squid will be shut down during installation, then started afterwards."
echo "It should be down for under 30 seconds."
echo

zzz_proceed_or_exit

echo "SQUID_SRC: $SQUID_SRC"

#-----checkout the latest version-----
git checkout tags/$NEW_VERSION

#-----configure and compile-----
# NOTE: compiling takes about 20 minutes
./bootstrap.sh
./configure --with-openssl --enable-ssl-crtd --enable-icap-client \
  --prefix=/usr \
  --localstatedir=/var \
  --libexecdir=${prefix}/lib/squid \
  --datadir=${prefix}/share/squid \
  --sysconfdir=/etc/squid \
  --with-default-user=proxy \
  --with-logdir=/var/log/squid \
  --with-pidfile=/var/run/squid.pid
make -j `nproc` all

#-----verify and install-----
echo "Stopping squid..."
systemctl stop squid
systemctl stop squid-icap

echo "Installing squid..."
make install

echo "Starting squid..."
systemctl start squid
systemctl start squid-icap

echo
echo "upgrade-squid-github.sh - END"
