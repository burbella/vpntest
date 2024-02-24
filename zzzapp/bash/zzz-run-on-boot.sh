#!/bin/bash
# run this script on boot as a systemd service

#-----import the utils-----
source /opt/zzz/util/util.sh

exit_if_not_running_as_root

#-----clear the reboot_needed flag-----
rm /opt/zzz/apache/reboot_needed

# ubuntu reboot-needed flag? /var/run/reboot-required

#-----clear the db_maintenance flag-----
rm /opt/zzz/db_maintenance

#-----regenerate MOTD-----
# it tends to go blank when rebooting after system security updates
# then it does not regenerate until an SSH login happens
/home/ubuntu/bin/regen-motd
