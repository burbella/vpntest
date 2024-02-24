#!/bin/bash
#-----show details of pip modules from requirements files-----

source /opt/zzz/util/util.sh
# set in util: REPOS_DIR

REQUIREMENTS_FILE=$REPOS_DIR/install/requirements.txt
while read PIP_MODULE_ENTRY; do
    PIP_MODULE_NAME=`echo "$PIP_MODULE_ENTRY" | cut -d '=' -f 1 | cut -d '<' -f 1 | cut -d '>' -f 1`
    /opt/zzz/venv/bin/pip3 show $PIP_MODULE_NAME
    echo "--------------------------------------------------"
done <$REQUIREMENTS_FILE

