#!/bin/bash
#-----find the latest stable version of the Zzz System-----

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

cd $REPOS_DIR

#-----update the tag list-----
sudo -H -u ubuntu git fetch >> /dev/null

ZZZ_LATEST_STABLE_VERSION=`git tag | grep -P '^\d+$' | sort -g | tail -1`

echo $ZZZ_LATEST_STABLE_VERSION
