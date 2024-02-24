#!/bin/bash
#-----upgrade various zzz configs to the latest version-----
# must do a git-pull first

echo "upgrade-configs.sh - START"

#-----import bash utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR

echo "installing BIND settings"
cp $ZZZ_CONFIG_DIR/named/settings/* /etc/bind/settings

echo "restarting BIND"
systemctl restart bind9

echo
echo "upgrade-configs.sh - END"
