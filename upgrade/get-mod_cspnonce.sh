#!/bin/bash
#-----get mod_cspnonce from github-----

echo "get-mod_cspnonce.sh - START"

source /opt/zzz/util/util.sh
# set in util: ZZZ_CONFIG_DIR

exit_if_not_running_as_root

SRC_DIR=/home/ubuntu/src
MOD_CSPNONCE_SRC=$SRC_DIR/mod_cspnonce

cd $SRC_DIR

#-----get mod_cspnonce from the official repos on GitHub-----
git clone https://github.com/wyday/mod_cspnonce.git
cd $MOD_CSPNONCE_SRC
git checkout tags/1.4

#-----compile it with the apache extension app-----
/usr/bin/apxs2 -ci $MOD_CSPNONCE_SRC/mod_cspnonce.c

cp $ZZZ_CONFIG_DIR/httpd/cspnonce.load /etc/apache2/mods-available
chmod 644 /etc/apache2/mods-available/cspnonce.load

echo
echo "get-mod_cspnonce.sh - END"
