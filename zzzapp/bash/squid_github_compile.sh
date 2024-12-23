#!/bin/bash

#-----compiles source code from the squid-cache github repo-----
# assumes the source code is already downloaded and the branch is checked out
# this should happen in install/100_install-squid.sh or upgrade/upgrade-squid-github.sh

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util: RUN_AS_UBUNTU, SQUID_INSTALLER_STATUS_FILE, SRC_DIR, ZZZ_LINEFEED, ZZZ_SQUID_VERSION_INSTALL


#-----init the status file-----
echo -n "START" > $SQUID_INSTALLER_STATUS_FILE

# input required: version number (EX: 5.7)
# NEW_VERSION=$ZZZ_SQUID_VERSION_INSTALL
# REQUESTED_VERSION=$1

SQUID_SRC=$SRC_DIR/squid
cd $SQUID_SRC

#--------------------------------------------------------------------------------

# return only works inside functions
# exit kills the parent process also
# so just wrap this entire thing in a function and call it to have usable returns
squid_github_compile() {
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

    #-----passed all checks-----
    echo -n "OK" > $SQUID_INSTALLER_STATUS_FILE
}

squid_github_compile

echo "$ZZZ_SCRIPTNAME - END"
