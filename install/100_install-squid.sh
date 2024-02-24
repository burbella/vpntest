#!/bin/bash

# download
# compile w/SSL support
# install
# add configs
#
# Required Build Tools:
#    https://wiki.squid-cache.org/DeveloperResources#Required_Build_Tools
#    wget http://www.squid-cache.org/Versions/v4/squid-4.1.tar.gz
#    GitHub: https://github.com/squid-cache/squid
#    autoconf 2.64 or later
#    automake 1.10 or later
#    libtool 2.6 or later
#    libltdl-dev
#    awk
#    ed
#    CppUnit for unit testing:
#       CppUnit - C++ port of JUnit
#       http://cppunit.sourceforge.net/cppunit-wiki
#       https://sourceforge.net/projects/cppunit/

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, RUN_AS_UBUNTU, SQUID_INSTALLER_STATUS_FILE, ZZZ_CONFIG_DIR, ZZZ_SQUID_VERSION_INSTALL

SRC_DIR=/home/ubuntu/src
cd $SRC_DIR

#-----GPG setup (in case an upgrade from .tar.gz is done later)-----
# 4.16 - fingerprint=B06884EDB779C89B044E64E3CD6DBF8EF3B17D3E
# 5.1 - fingerprint=B06884EDB779C89B044E64E3CD6DBF8EF3B17D3E
wget --output-document=/home/ubuntu/src/squid-pgp.asc http://www.squid-cache.org/pgp.asc
$RUN_AS_UBUNTU gpg --homedir /home/ubuntu/.gnupg --import /home/ubuntu/src/squid-pgp.asc
$RUN_AS_UBUNTU gpg --homedir /home/ubuntu/.gnupg --keyserver keyserver.ubuntu.com --recv-keys $ZZZ_SQUID_VALIDATION_KEY

#-----get the latest production version of Squid-----
#  the official repos on GitHub: https://github.com/squid-cache/squid
#  the development version(5.0) is checked-out by default
#  we want the latest stable release(version 4.9 as of 11/6/2019)
#  only 4.8 is available in GitHub - this is 5 months old
#  getting 4.9 requires downloading the tar.gz file, so don't use GitHub for that
#
#  8/5/2018: 4.2 is available in tar.gz now
#  10/27/2018: 4.4 is available now
#  1/1/2019: 4.5 is available now
#  2/19/2019: 4.6 is available now
#  5/7/2019: 4.7 is available now
#  7/9/2019: 4.8 is available now
#  11/6/2019: 4.9 is available on www
#  1/20/2020: 4.10 is available on www
#  8/9/2021: 4.16 and 5.1 are available on www
#            4.13 is in github (from 8/22/2020)
#  10/12/2021: 5.2 is available on www
#  6/17/2022: 5.6 is available on www
#  9/16/2022: 5.7 is available on www
#  2/28/2023: 5.8 is available on www
#    The current zzz squid config only works with version 5.5+
#    The latest squid release on github is still 4.13, so the www download must be used instead to get the 5.7 release
#    The github will still be cloned here in case it is useful later.
git clone https://github.com/squid-cache/squid.git
SQUID_SRC=$SRC_DIR/squid
SQUID_LATEST_STABLE_VERSION=`git tag|grep 'SQUID_'|tail -1`
DISPLAY_NEW_VERSION=`echo $SQUID_LATEST_STABLE_VERSION | tr '_' '.' | cut -d '.' -f 2,3`
cd $SQUID_SRC
#git checkout $SQUID_LATEST_STABLE_VERSION
calc_squid_version_tag $ZZZ_SQUID_VERSION_TAG
DISPLAY_NEW_VERSION=$SQUID_DISPLAY_VERSION
git checkout tags/$ZZZ_SQUID_VERSION_TAG

# echo "Squid version to install: $DISPLAY_NEW_VERSION"

#-----stop the pre-installed squid process from 020_install-apps-from-repos.sh-----
# prevents this error: 
echo "stopping old squid process . . ."
systemctl stop squid
systemctl stop squid-icap
echo "squid stopped"

#-----tar.gz download/verify/install-----
NEW_VERSION=$ZZZ_SQUID_VERSION_INSTALL
echo "Squid version to install: $NEW_VERSION"
/opt/zzz/util/squid_download_verify_compile.sh $NEW_VERSION
ZZZ_SQUID_DOWNLOAD_VERIFY_COMPILE=`cat $SQUID_INSTALLER_STATUS_FILE`
if [ "$ZZZ_SQUID_DOWNLOAD_VERIFY_COMPILE" != "OK" ]; then
    echo "$ZZZ_SQUID_DOWNLOAD_VERIFY_COMPILE"
    #TODO: move the stuff below into a function so we can do "return" here
    #  "exit" would crash the calling script
    #  if the squid install is skipped, the rest of the system should still work, so no need to give up on the remaining system install/setup
fi

SQUID_SRC=$SRC_DIR/squid-$NEW_VERSION
cd $SQUID_SRC

#-----compile and install-----
# NOTE: compiling takes about 20 minutes
# ./bootstrap.sh
# ./configure --with-openssl --enable-ssl-crtd --enable-icap-client \
#     --prefix=/usr \
#     --localstatedir=/var \
#     --libexecdir=${prefix}/lib/squid \
#     --datadir=${prefix}/share/squid \
#     --sysconfdir=/etc/squid \
#     --with-default-user=proxy \
#     --with-logdir=/var/log/squid \
#     --with-pidfile=/var/run/squid.pid
# make -j `nproc` all

make install

#-----Log directory accessible to both apache and squid-----
# apache runs under the username "www-data"
#drwxr-s--- 2 proxy www-data 4096 Jul 30 03:46 /var/log/squid_access/
chown proxy.www-data /var/log/squid_access
chmod 2750 /var/log/squid_access

#-----Setup custom rotation for the squid_access directory-----
# /var/log/squid/*.log /var/log/squid_access/*.log
# /etc/logrotate.d/squid

#-----install squid configs-----
CONFIG_DIR=$ZZZ_CONFIG_DIR/squid
cp $CONFIG_DIR/squid.conf /etc/squid
cp $CONFIG_DIR/blocked-sites.txt /etc/squid
cp $CONFIG_DIR/blocked-ips.txt /etc/squid
cp $CONFIG_DIR/nobumpsites.acl /etc/squid

#-----DH params-----
openssl dhparam -outform PEM -out /etc/squid/ssl_cert/dhparam.pem 2048
chown proxy.proxy /etc/squid/ssl_cert/dhparam.pem
chmod 640 /etc/squid/ssl_cert/dhparam.pem

#-----rebuild the squid config-----
/opt/zzz/python/bin/build-config.py --squid -q

#-----cache for SSL intercept certs-----
chown proxy.proxy /var/cache/squid
chmod 755 /var/cache/squid
chown proxy.proxy /var/cache/squid_icap
chmod 755 /var/cache/squid_icap

#-----generate the cache directory with the necessary files-----
/lib/squid/security_file_certgen -c -s /var/cache/squid/ssl_db -M 16MB
/lib/squid/security_file_certgen -c -s /var/cache/squid_icap/ssl_db -M 16MB

#-----fix dir/file permissions so squid can use the cache when it runs as user "proxy"-----
chown -R proxy.proxy /var/cache/squid/ssl_db
chown -R proxy.proxy /var/cache/squid_icap/ssl_db

#-----initialize swap directories-----
squid -z
squid -f /etc/squid/squid-icap.conf -z

#-----systemd service (fails?)-----
#cp $ZZZ_CONFIG_DIR/ubuntu/squid-icap.service /etc/systemd/system
#systemctl daemon-reload
#systemctl enable squid-icap.service

#-----install ICAP init.d script, make the daemon auto-start on boot-----
#cp $ZZZ_CONFIG_DIR/ubuntu/squid-icap-initd.sh /etc/init.d/squid-icap
SQUID_ICAP_FILE=/etc/init.d/squid-icap
cp -p /etc/init.d/squid $SQUID_ICAP_FILE
check_os_version
if [[ "$ZZZ_OS_DISTRIB_RELEASE" == "22.04" ]]; then
    patch $SQUID_ICAP_FILE $ZZZ_CONFIG_DIR/squid/squid-icap-initd-ubuntu22.patch
else
    # ubuntu 20.04
    patch $SQUID_ICAP_FILE $ZZZ_CONFIG_DIR/squid/squid-icap-initd.patch
fi

chmod 755 $SQUID_ICAP_FILE
dos2unix -q $SQUID_ICAP_FILE
update-rc.d squid-icap defaults

systemctl restart squid
systemctl restart squid-icap

echo "$ZZZ_SCRIPTNAME - END"
