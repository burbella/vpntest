#!/bin/bash
#-----show the contents of all cron files-----

# ls /etc/cron.d /etc/cron.daily /etc/cron.hourly /etc/cron.monthly /etc/cron.weekly /etc/crontab

ZZZ_CRON_DIR_OUTPUT_FILE=/tmp/cron_dir_output.txt

echo "/etc/crontab" > $ZZZ_CRON_DIR_OUTPUT_FILE
for cron_dir in \
    /etc/cron.d \
    /etc/cron.daily \
    /etc/cron.hourly \
    /etc/cron.monthly \
    /etc/cron.weekly ; do
    ls -1d $cron_dir/* >> $ZZZ_CRON_DIR_OUTPUT_FILE
done

while read CRON_FILENAME; do
    echo "$CRON_FILENAME"
    echo
    cat $CRON_FILENAME
    echo
    echo "--------------------------------------------------------------------------------"
    echo
done <$ZZZ_CRON_DIR_OUTPUT_FILE

