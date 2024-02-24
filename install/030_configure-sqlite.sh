#!/bin/bash
#-----setup DB w/empty tables-----

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

#TODO: get these values from the config file
DB_FILE=/opt/zzz/sqlite/services.sqlite3
COUNTRY_IP_DB_FILE=/opt/zzz/sqlite/country-IP.sqlite3
IP_COUNTRY_DB_FILE=/opt/zzz/sqlite/ip-country.sqlite3

#-----allow both the SSH user and apache user to read/write the DB-----
chown www-data.www-data /opt/zzz/sqlite/
chmod 770 /opt/zzz/sqlite/

#-----create empty tables-----
# sqlite3 /opt/zzz/sqlite/services.sqlite3
# run DB commands in this file: $ZZZ_INSTALLER_DIR/database_setup.sql
sqlite3 $DB_FILE < $ZZZ_INSTALLER_DIR/database_setup.sql
chown www-data.www-data $DB_FILE

sqlite3 $COUNTRY_IP_DB_FILE < $ZZZ_INSTALLER_DIR/database_setup_country_ip.sql
chown www-data.www-data $COUNTRY_IP_DB_FILE

sqlite3 $IP_COUNTRY_DB_FILE < $ZZZ_INSTALLER_DIR/database_setup_ip_country.sql
chown www-data.www-data $IP_COUNTRY_DB_FILE

echo "$ZZZ_SCRIPTNAME - END"
