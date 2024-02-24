#!/bin/bash
#-----list versions of installed software-----

ZZZ_OS_CURRENT=`grep DISTRIB_DESCRIPTION /etc/lsb-release | cut -d '"' -f 2`
echo "OS - current: $ZZZ_OS_CURRENT"
echo
echo "apt-get packages:"

apt list apache2 bind9 certbot geoipupdate openssl redis-server sqlite3 2>/dev/null

echo
echo "--------------------------------------------------"
echo

/opt/zzz/venv/bin/python3 --version

echo
openvpn --version | grep OpenSSL

echo
squid -v | grep Version

# get jquery version
# latest installed:
# JQUERY_VERSION=`ls -1 /var/www/html/js/jquery-*.min.js | tail -1 | cut -d '-' -f 2 | cut -d '.' -f 1-3`
# actually loaded in browser:
JQUERY_VERSION=`grep -o -P 'jquery-\d+\.\d+\.\d+' /opt/zzz/python/templates/header.template | cut -d '-' -f 2`
echo
echo "jquery $JQUERY_VERSION"

echo
echo "--------------------------------------------------"
echo

# EasyRSA_VERSION=`grep branch /home/ubuntu/src/easy-rsa/.git/config | cut -d '"' -f 2`
# echo EasyRSA $EasyRSA_VERSION
echo "EasyRSA 3.1.6"

MAXMIND_DB_FILE=/usr/share/GeoIP/GeoLite2-Country.mmdb
MAXMIND_DB_DATE=
if [[ -f $MAXMIND_DB_FILE ]]; then
    MAXMIND_DB_DATE=`ls -l --time-style=long-iso $MAXMIND_DB_FILE | cut -d ' ' -f 6-7`
else
    MAXMIND_DB_DATE="Not Installed (follow step 8 in INSTALL.txt to setup)"
fi
echo
echo "maxmind DB: $MAXMIND_DB_DATE"

ZZZ_IPDENY_DATE=`ls -l --time-style=long-iso /opt/zzz/data/ipdeny-ipv4/ipdeny-ipv4-all-zones.tar.gz | cut -d ' ' -f 6-7`
echo
echo "ipdeny: $ZZZ_IPDENY_DATE"

# echo
# echo "--------------------------------------------------"
# echo

# should match the list in requirements.txt
# echo "Python PIP packages:"
#/opt/zzz/venv/bin/pip3 --version
ZZZ_PIP_PACKAGES=`/opt/zzz/venv/bin/pip3 list 2>&1`

# echo "$ZZZ_PIP_PACKAGES" | grep -P '^(ansi2html|Brotli|coverage|datapackage|dnspython|docutils|file\-read\-backwards|flake8|Flask|ifcfg|ipwhois|maxminddb|netaddr|nslookup|pep8|pip|pip-check|psutil|pycodestyle|pycycle|pyflakes|pyicap|pylint|pytest|python\-magic|python\-whois|pytz|PyYAML|rdap|redis|requests|tldextract|unidecode|Werkzeug|wizard\_whois|WARNING\: You are using|You should consider upgrading) '

#-----Sample warning-----
# WARNING: You are using pip version 20.0.2; however, version 20.1.1 is available.
# You should consider upgrading via the '/usr/bin/python3 -m pip install --upgrade pip' command.

echo
echo "--------------------------------------------------"
echo

echo "All Python Packages:"
echo "$ZZZ_PIP_PACKAGES"
echo
echo "--------------------------------------------------"
echo
