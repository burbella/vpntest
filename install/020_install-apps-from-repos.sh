#!/bin/bash
# 010_install-apps-from-repos.sh
# all support apps available in the Ubuntu repos that don't need custom compiling
#
# we must install squid here even though it is an old version (4.10) because this is the only way to get the init.d and apparmor scripts installed
# the latest version (4.13) will be compiled/installed later from the squid github
# optional upgrade to 5.1 by command-line script: upgrade-squid.sh

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_PIP_VERSION

#-----get maxmind software from their PPA-----
# software available: geoipupdate, libmaxminddb-dev, libmaxminddb0
add-apt-repository -y ppa:maxmind/ppa

#-----update the repos installer with the latest list of apps from maxmind-----
apt-get -y -q update

echo "Installing ubuntu repos apps"

#-----install all the apps-----
# this list was built for a series of OS's:
#   CentOS 6 --> Ubuntu 16 --> Ubuntu 18.04 --> Ubuntu 20.04 --> Ubuntu 22.04
# "force-confold" below deals with an issue where some config(s) mismatch during updating
# it automatically keeps the old config file(s) so no user intervention is needed to choose a config file
# Ubuntu 20.04: (8/2/2020)
#   net-tools and pkg-config are not installed by default
#   They are required by the openvpn compiler, so they need to be added
# pypi packages that need to be loaded here:
#   python3-docutils - for openvpn to compile
#   python3-maxminddb - comes from the maxmind PPA added above
for i in \
    apache2 \
    apache2-dev \
    autoconf \
    automake \
    bind9 \
    bind9-doc \
    bind9-host \
    bind9-utils \
    brotli \
    build-essential \
    cmake \
    dos2unix \
    fonts-roboto \
    gcc \
    geoipupdate \
    ipset \
    iptables-persistent \
    libapache2-mod-wsgi-py3 \
    libbrotli-dev \
    libbrotli1 \
    libcap-dev \
    libcap-ng-dev \
    libcmocka0 \
    libcmocka-dev \
    libcppunit-1.15-0 \
    libcppunit-dev \
    libffi-dev \
    libgmp-dev \
    libicapapi-dev \
    libltdl-dev \
    liblz4-dev \
    liblzo2-dev \
    libmaxminddb-dev \
    libmaxminddb0 \
    libnl-genl-3-dev \
    libpam0g-dev \
    libssl-dev \
    libsystemd-dev \
    libtool \
    libtool-bin \
    libxml2 \
    libxml2-dev \
    libyaml-0-2 \
    libyaml-dev \
    libyaml-cpp0.5v5 \
    libyaml-cpp-dev \
    lynx \
    lzop \
    mlocate \
    netfilter-persistent \
    net-tools \
    openssl \
    pkg-config \
    python3 \
    python3-dev \
    python3-docutils \
    python3-maxminddb \
    python3-pip \
    python3-setuptools \
    python3-testresources \
    python3-testtools \
    python3-venv \
    python3-virtualenv \
    redis-server \
    software-properties-common \
    sqlite \
    squid \
    tcpdump \
    telnet \
    unzip \
    virtualenv \
    whois \
    wireguard \
    zip ; do
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install $i
done

#-----don't allow these to auto-upgrade with OS upgrades in the future-----
# the custom-compiled version of squid will be replaced by the (older) repos version if we allow it to install with "apt-get -y upgrade"
# we only need the init.d script from this (no init.d script included with the github source code)
apt-mark hold squid
apt-mark hold squid-common
apt-mark hold squid-langpack

#--------------------------------------------------------------------------------

#TODO: option to install the latest stable OpenSSL from github
# https://github.com/openssl/openssl
# Ubuntu 18.04 has a 12-month old version
# compatibility issues may make it unsafe to get the latest version, so have a rollback plan
# OpenSSL claims that minor version changes should NOT require re-compiling any apps
#   EXAMPLE: version 1.1.0 --> 1.1.1

#--------------------------------------------------------------------------------

echo "Creating python venv and installing PIP apps"

# installing as user=ubuntu puts the pip cache in /home/ubuntu/.cache/pip
#
sudo --user=ubuntu /usr/bin/python3 -m venv /opt/zzz/venv
source /opt/zzz/venv/bin/activate

#-----upgrade PIP itself first-----
sudo --user=ubuntu -H /opt/zzz/venv/bin/pip3 install --upgrade $ZZZ_PIP_VERSION

#-----first do the PIP package installer tools-----
# other PIP packages report various errors/warnings if these tools are not present and updated
# setuptools, testresources, testtools, wheel
# sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r /home/ubuntu/repos/test/install/requirements-tools.txt
sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt

#TODO: generate a thorough requirements.txt file from a running system, then save it to the repos
#  /opt/zzz/venv/bin/python3 -m pip freeze > requirements-full.txt
#TODO: load all pip apps with the requirements-full.txt file
# sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r /home/ubuntu/repos/test/install/requirements.txt
sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements.txt

#-----make a second venv for testing-----
# sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install -r /home/ubuntu/repos/test/install/requirements-tools.txt
# sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install -r /home/ubuntu/repos/test/install/requirements.txt
sudo --user=ubuntu /usr/bin/python3 -m venv /opt/zzz/venvtest
sudo --user=ubuntu -H /opt/zzz/venvtest/bin/pip3 install --upgrade $ZZZ_PIP_VERSION
sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-test.txt

#-----make a third venv for an alternate codebase-----
# some old pypi packages are not compatible with modern packages, so they can go here if they are still needed
# sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install -r /home/ubuntu/repos/test/install/requirements-tools.txt
# sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install -r /home/ubuntu/repos/test/install/requirements-alt.txt
sudo --user=ubuntu /usr/bin/python3 -m venv /opt/zzz/venv_alt
sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/pip3 install --upgrade $ZZZ_PIP_VERSION
sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-alt.txt

#-----fix a bug that makes ICAP crash in python 3.10-----
for i in venv venv_alt venvtest ; do
    perl -pi -e "s/collections.Callable/collections.abc.Callable/g" /opt/zzz/$i/lib/python3.10/site-packages/pyicap.py
done

echo "$ZZZ_SCRIPTNAME - END"
