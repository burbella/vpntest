#!/bin/bash
#-----find all available versions of the Zzz System-----

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

cd $REPOS_DIR

#-----update the tag list-----
sudo -H -u ubuntu git fetch >> /dev/null

#ZZZ_LATEST_STABLE_VERSION=`git tag | grep -P '^\d+$' | sort -g | tail -1`

INCLUDE_ALPHA=$1
if [ "$INCLUDE_ALPHA" == "--dev" ]; then
    #ZZZ_VERSIONS=`git tag | grep -P '\.' | sort --reverse`
    #ZZZ_VERSIONS=`git tag | sort --reverse`
    git tag | sort --reverse
else
    #ZZZ_VERSIONS=`git tag | grep -P '\.' | grep -v 'a' | sort --reverse`
    #ZZZ_VERSIONS=`git tag | grep -v 'a' | sort --reverse`
    git tag | grep -v 'a' | sort --reverse
fi

#echo $ZZZ_VERSIONS
