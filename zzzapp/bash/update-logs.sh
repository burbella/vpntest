#!/bin/bash
#-----process squid and IP logfile data into DB tables-----
# call this script once a minute from this cron: zzz-update-ip-log

/opt/zzz/python/bin/update-ip-log.py --update >>/var/log/zzz/cron/update-ip-log.log 2>&1
sleep 0.5
/opt/zzz/python/bin/update-squid-log.py --update >>/var/log/zzz/cron/update-squid-log.log 2>&1
