#!/bin/bash
#-----setup the pytest DB with tables containing test data-----

ZZZ_SCRIPTNAME=`basename "$0"`
#echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_PYTHON_DIR, ZZZ_PYTEST_DIR

# /opt/zzz/python/test/sqlite
DB_FILE=$ZZZ_PYTEST_DIR/sqlite/pytest-services.sqlite3
COUNTRY_IP_DB_FILE=$ZZZ_PYTEST_DIR/sqlite/pytest-country-IP.sqlite3
IP_COUNTRY_DB_FILE=$ZZZ_PYTEST_DIR/sqlite/pytest-ip-country.sqlite3

#-----create empty tables-----
#sqlite3 $DB_FILE < $ZZZ_INSTALLER_DIR/database_setup.sql
sqlite3 $DB_FILE < $REPOS_DIR/install/database_setup.sql
chown www-data.www-data $DB_FILE

#sqlite3 $COUNTRY_IP_DB_FILE < $ZZZ_INSTALLER_DIR/database_setup_country_ip.sql
sqlite3 $COUNTRY_IP_DB_FILE < $REPOS_DIR/install/database_setup_country_ip.sql
chown www-data.www-data $COUNTRY_IP_DB_FILE

#sqlite3 $IP_COUNTRY_DB_FILE < $ZZZ_INSTALLER_DIR/database_setup_ip_country.sql
sqlite3 $IP_COUNTRY_DB_FILE < $REPOS_DIR/install/database_setup_ip_country.sql
chown www-data.www-data $IP_COUNTRY_DB_FILE

#-----add static test data from a SQL file-----
sqlite3 $DB_FILE < $ZZZ_PYTEST_DIR/pytest_db_data.sql

#-----add dynamically-created test data from a python script-----
$ZZZ_PYTEST_DIR/init-db-pytest.py

#echo "$ZZZ_SCRIPTNAME - END"
