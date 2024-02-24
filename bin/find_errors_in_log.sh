#!/bin/bash

# Installer logs:
#   /home/ubuntu/bin/find_errors_in_log.sh /var/log/zzz/install/bind.log
#   /home/ubuntu/bin/find_errors_in_log.sh /var/log/zzz/install/install.log
#   /home/ubuntu/bin/find_errors_in_log.sh /var/log/zzz/install/install-openvpn.log
#   /home/ubuntu/bin/find_errors_in_log.sh /var/log/zzz/install/install-squid.log
# All installer logs:
#   grep -inP '(err|warn|fail|missing|invalid)' /var/log/zzz/install/bind.log /var/log/zzz/install/install{,-openvpn,-squid}.log

echo "Find Errors In Log"
echo

ZZZ_LOGFILE=$1

if [[ "$ZZZ_LOGFILE" == "" ]]; then
    echo "ERROR: no file specified"
    exit
fi

if [[ ! -e $ZZZ_LOGFILE ]]; then
    echo "ERROR: file does not exist"
    exit
fi

if [[ ! -f $ZZZ_LOGFILE ]]; then
    echo "ERROR: not a file"
    exit
fi

grep -inP '(err|warn|fail|missing|invalid|cannot access|no such file)' $ZZZ_LOGFILE
