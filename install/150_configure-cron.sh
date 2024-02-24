#!/bin/bash

# install custom cron files in appropriate directories:
#   /etc/cron.d/
#   /etc/cron.daily/
#   /etc/cron.weekly/
#   /etc/cron.monthly/

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_CONFIG_DIR

SKIP_VERSION_CHECK=$1

CRON_DIR=/etc/cron.d
CRON_HOURLY_DIR=/etc/cron.hourly
CRON_DAILY_DIR=/etc/cron.daily
CRON_WEEKLY_DIR=/etc/cron.weekly
CRON_MONTHLY_DIR=/etc/cron.monthly

# All Crons:
#   zzz-check-latest-version
#   zzz-disk-cleanup
#   zzz-ipdeny
#   zzz-logrotate-iptables
#   zzz-re-issue-certs
#   zzz-update-ip-log
#   zzz-update-ip-log-summary

# crons with custom timing: zzz-logrotate-iptables, zzz-update-ip-log

#-----process IP logs every few minutes-----
cp $ZZZ_CONFIG_DIR/cron/zzz-update-ip-log $CRON_DIR
chmod 644 $CRON_DIR/zzz-update-ip-log
dos2unix -q $CRON_DIR/zzz-update-ip-log

#-----rotate iptables logs every minute-----
# ZZZ_CONFIG_DIR/logrotated/zzz-iptables-log --> /etc/logrotate.d
# /etc/cron.d/zzz-logrotate-iptables
cp $ZZZ_CONFIG_DIR/cron/zzz-logrotate-iptables $CRON_DIR
chmod 644 $CRON_DIR/zzz-logrotate-iptables
dos2unix -q $CRON_DIR/zzz-logrotate-iptables

#-----hourly crons-----
# zzz-memory-check
for i in \
    zzz-memory-check ; do
    cp $ZZZ_CONFIG_DIR/cron/$i $CRON_HOURLY_DIR
    chmod 755 $CRON_HOURLY_DIR/$i
    dos2unix -q $CRON_HOURLY_DIR/$i
done

#-----daily crons-----
# IP log summaries
# check for updates: zzz, openvpn, squid
for i in \
    zzz-download-lists \
    zzz-update-ip-log-summary \
    zzz-check-latest-version ; do
    cp $ZZZ_CONFIG_DIR/cron/$i $CRON_DAILY_DIR
    chmod 755 $CRON_DAILY_DIR/$i
    dos2unix -q $CRON_DAILY_DIR/$i
done

if [[ "$SKIP_VERSION_CHECK" != "--skip-version-check" ]]; then
    #-----run the version check now-----
    $CRON_DAILY_DIR/zzz-check-latest-version
fi

#-----weekly crons-----
for i in \
    zzz-disk-check \
    zzz-disk-cleanup \
    zzz-ipdeny \
    zzz-maxmind \
    zzz-openvpn-restart \
    zzz-update-tld ; do
    cp $ZZZ_CONFIG_DIR/cron/$i $CRON_WEEKLY_DIR
    chmod 755 $CRON_WEEKLY_DIR/$i
    dos2unix -q $CRON_WEEKLY_DIR/$i
done

#TODO: set a custom monthly cron at least 8 days in the future so the next auto-update does not happen too soon after initial installation
#-----monthly auto-update: ipdeny files, apache certs-----
for i in \
    zzz-re-issue-certs ; do
    cp $ZZZ_CONFIG_DIR/cron/$i $CRON_MONTHLY_DIR
    chmod 755 $CRON_MONTHLY_DIR/$i
    dos2unix -q $CRON_MONTHLY_DIR/$i
done

# install-zzz-tools.sh installs ipdeny files now
#-----run the ipdeny cron to get the latest update-----
# apache certs were just created on install, so no need to re-issue them
# we'll re-use this script for cron re-installs, but we don't need to re-load the ipdeny files in that case
#SKIP_IPDENY=$1
#if [[ "$SKIP_IPDENY" != "--skip-ipdeny" ]]; then
#    $CRON_WEEKLY_DIR/zzz-ipdeny
#fi

echo "$ZZZ_SCRIPTNAME - END"
