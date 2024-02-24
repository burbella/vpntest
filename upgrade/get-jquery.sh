#!/bin/bash
#-----get jquery from github-----

echo "get-jquery.sh - START"

source /opt/zzz/util/util.sh

exit_if_not_running_as_root

SRC_DIR=/home/ubuntu/src
cd $SRC_DIR

#-----download-----
# JQUERY_URL="https://code.jquery.com"
# JQUERY_FILE="jquery-3.7.0.js"
# JQUERY_MIN_FILE="jquery-3.7.0.min.js"
# JQUERY_MAP_FILE="jquery-3.7.0.min.map"
# JQUERY_SAVED_FILE=$SRC_DIR/$JQUERY_FILE
# JQUERY_SAVED_MIN_FILE=$SRC_DIR/$JQUERY_MIN_FILE
# JQUERY_SAVED_MAP_FILE=$SRC_DIR/$JQUERY_MAP_FILE
JQUERY_VERSION="3.7.1"
JQUERY_URL="https://ajax.googleapis.com/ajax/libs/jquery/$JQUERY_VERSION/jquery.min.js"
JQUERY_MIN_FILE="jquery-$JQUERY_VERSION.min.js"
JQUERY_SAVED_MIN_FILE=$SRC_DIR/$JQUERY_MIN_FILE
echo "Downloading..."
# wget -q --output-document=$JQUERY_SAVED_FILE $JQUERY_URL/$JQUERY_FILE
# wget -q --output-document=$JQUERY_SAVED_MIN_FILE $JQUERY_URL/$JQUERY_MIN_FILE
# wget -q --output-document=$JQUERY_SAVED_MAP_FILE $JQUERY_URL/$JQUERY_MAP_FILE
wget --output-document=$JQUERY_SAVED_MIN_FILE $JQUERY_URL

if [ ! -e $SRC_DIR/$SQUID_FILE ]; then
    echo "ERROR: download failed, file not found"
    echo "$SRC_DIR/$SQUID_FILE"
    exit
fi

#-----zero-size file means the download failed-----
if [ ! -s $JQUERY_SAVED_MIN_FILE ]; then
    echo "ERROR: download failed, file is zero-size"
    echo "$JQUERY_SAVED_MIN_FILE"
    echo "Check if the file is on the jquery website:"
    echo "$JQUERY_URL"
    # echo "$JQUERY_URL/$JQUERY_MIN_FILE"
    exit
fi

echo "Installing..."
cp $JQUERY_SAVED_MIN_FILE /var/www/html/js/

# if [ -s $JQUERY_SAVED_FILE ]; then
#     cp $JQUERY_SAVED_FILE /var/www/html/js/
# fi

# if [ -s $JQUERY_SAVED_MAP_FILE ]; then
#     cp $JQUERY_SAVED_MAP_FILE /var/www/html/js/
# fi

echo
echo "get-jquery.sh - END"
