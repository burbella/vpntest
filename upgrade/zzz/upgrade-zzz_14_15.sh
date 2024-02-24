#!/bin/bash
#-----upgrade zzz system from version 14 to 15-----

#-----EDIT THIS-----
CURRENT_VERSION=14
NEW_VERSION=15

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

simple_upgrade $CURRENT_VERSION $NEW_VERSION
