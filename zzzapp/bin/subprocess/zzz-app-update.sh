#!/bin/bash
#-----install the latest app updates-----

source /opt/zzz/util/util.sh
# vars set in util: REPOS_DIR, ZZZ_CONFIG_DIR, ZZZ_INSTALLER_DIR

DATA_DIR=/opt/zzz/data
HTML_DIR=/var/www/html
WSGI_DIR=/var/www/wsgi
PYTHON_DIR=/opt/zzz/python
UPGRADE_DIR=/opt/zzz/upgrade
UTIL_DIR=/opt/zzz/util

echo "Zzz app update START"

#-----general linux bin files-----
echo "general linux bin files"
cp $REPOS_DIR/bin/* /home/ubuntu/bin
chown -R ubuntu.ubuntu /home/ubuntu/bin
chmod 755 /home/ubuntu/bin/*

#-----utilities-----
echo "utilities"
cp $REPOS_DIR/install/* $ZZZ_INSTALLER_DIR
cp -R $REPOS_DIR/upgrade/* $UPGRADE_DIR
cp $REPOS_DIR/zzzapp/bash/*.sh $UTIL_DIR
chmod 755 $ZZZ_INSTALLER_DIR/*.sh
chmod -R 755 $UPGRADE_DIR/*.sh
chmod 755 $UTIL_DIR/*

#-----config-----
echo "config files"
cp -R $REPOS_DIR/config/* $ZZZ_CONFIG_DIR

#-----ipset/iptables scripts-----
IPTABLES_REPOS_DIR=$REPOS_DIR/config/iptables
IPTABLES_INSTALL_DIR=/etc/iptables
cp $IPTABLES_REPOS_DIR/*.sh $IPTABLES_INSTALL_DIR
chmod 755 $IPTABLES_INSTALL_DIR/*.sh
find $IPTABLES_INSTALL_DIR -type f -exec dos2unix -q {} \;

#-----Python-----
echo "Python"
cp -R $REPOS_DIR/zzzapp/bin/* $PYTHON_DIR/bin
cp -R $REPOS_DIR/zzzapp/lib/* $PYTHON_DIR/lib
cp -R $REPOS_DIR/zzzapp/templates/* $PYTHON_DIR/templates
cp -R $REPOS_DIR/zzzapp/test/* $PYTHON_DIR/test
cp $REPOS_DIR/zzzapp/pytest.ini $PYTHON_DIR

#-----make bin files executable-----
#TODO: make a python-only daemon that doesn't need a shell script to start it
echo "make bin files executable"
chmod 755 $PYTHON_DIR/bin/*.py
chmod 755 $PYTHON_DIR/bin/*.sh
chmod 755 $PYTHON_DIR/bin/subprocess/*.sh
chmod 755 $PYTHON_DIR/test/*.py

#-----fix line ending issues to prevent execution problems-----
#TODO: Github on Windows does windows \r\n's by default
#      override the defaults in the Windows Github config
echo "fix line ending issues"
find /home/ubuntu/bin -type f -exec dos2unix -q {} \;
# find $PYTHON_DIR -type f -exec dos2unix -q {} \;
find $PYTHON_DIR -type f -regex '.+?.py' -exec dos2unix -q {} \;
find $PYTHON_DIR -type f -regex '.+?.sh' -exec dos2unix -q {} \;
find $PYTHON_DIR -type f -regex '.+?.template' -exec dos2unix -q {} \;
find $UPGRADE_DIR -type f -exec dos2unix -q {} \;
find $UTIL_DIR -type f -exec dos2unix -q {} \;
find $ZZZ_INSTALLER_DIR -type f -exec dos2unix -q {} \;

#-----HTML/JS/CSS/WSGI(python)-----
echo "HTML/JS/CSS/WSGI"
cp -R $REPOS_DIR/zzzapp/www/html/* $HTML_DIR
cp -R $REPOS_DIR/zzzapp/www/wsgi/* $WSGI_DIR
# overwrite default ubuntu file
cp $HTML_DIR/index.htm $HTML_DIR/index.html

ZZZ_USE_CUSTOM_FAVICON=`/opt/zzz/python/bin/config-parse.py --var 'Favicon/use_custom'`
if [[ "$ZZZ_USE_CUSTOM_FAVICON" == "False" ]]; then
    cp $REPOS_DIR/zzzapp/www/html/zzz_default.webmanifest $HTML_DIR/zzz.webmanifest
fi

echo "Zzz app update DONE"
