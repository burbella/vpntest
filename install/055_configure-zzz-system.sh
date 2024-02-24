#!/bin/bash

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

source /opt/zzz/util/util.sh

echo "Configuring Zzz System"

#-----initialize DB tables-----
# most other python scripts depend on the settings that are updated by this script
/opt/zzz/python/bin/init-db.py --domain --settings --country --tld --ip-country --zzz-list-all

#-----get the latest TLD list-----
echo "upgrade the TLD list"
/opt/zzz/upgrade/upgrade-tld.sh

#TODO: finish this
#-----get the latest country list-----
#echo "get the country list"
#/opt/zzz/python/bin/update-country-codes.py

echo "$ZZZ_SCRIPTNAME - END"
