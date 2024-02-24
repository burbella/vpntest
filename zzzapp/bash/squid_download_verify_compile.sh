#!/bin/bash
#-----squid installer uses a .tar.gz file-----
# gets source code from www.squid-cache.org
# verifies the file against its gpg signature
# runs the compiler/installer

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util: RUN_AS_UBUNTU, SQUID_INSTALLER_STATUS_FILE, ZZZ_LINEFEED, ZZZ_SQUID_VERSION_INSTALL

echo -n "OK" > $SQUID_INSTALLER_STATUS_FILE

# input required: version number (EX: 5.7)
NEW_VERSION=$ZZZ_SQUID_VERSION_INSTALL
REQUESTED_VERSION=$1

#--------------------------------------------------------------------------------

# return only works inside functions
# exit kills the parent process also
# so just wrap this entire thing in a function and call it to have usable returns
zzz_squid_do_download_verify_compile() {
    if [ "$REQUESTED_VERSION" == "" ]; then
        echo "ERROR: version number not specified" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi

    # version 5+ is required for the zzz squid config to work
    if [[ $REQUESTED_VERSION =~ ^[5-6]\.[0-9]$ ]]; then
        NEW_VERSION=$REQUESTED_VERSION
    else
        # minor version number may go over 9
        if [[ $REQUESTED_VERSION =~ ^[5-6]\.[0-9][0-9]$ ]]; then
            NEW_VERSION=$REQUESTED_VERSION
        else
            #-----ERROR-----
            echo "ERROR: bad version number (must be 5.x-6.x)" > $SQUID_INSTALLER_STATUS_FILE
            return
        fi
    fi

    # calc_squid_version provides vars: SQUID_MAJOR_VERSION, SQUID_MINOR_VERSION, SQUID_PATCH_VERSION, SQUID_CALC_VERSION
    calc_squid_version $NEW_VERSION

    SRC_DIR=/home/ubuntu/src
    cd $SRC_DIR

    SQUID_DOWNLOAD_URL="http://www.squid-cache.org/Versions/v"
    SQUID_NAME_VERSION=squid-$NEW_VERSION
    
    #-----the calling process also needs this var-----
    # /home/ubuntu/src/squid-5.7
    SQUID_SRC=$SRC_DIR/$SQUID_NAME_VERSION
    
    SQUID_FILE=$SQUID_NAME_VERSION.tar.gz
    SQUID_SIGNATURE_FILE=$SQUID_FILE.asc
    SQUID_URL="$SQUID_DOWNLOAD_URL$SQUID_MAJOR_VERSION/$SQUID_FILE"
    SQUID_SIGNATURE_URL="$SQUID_URL.asc"

    #-----tar.gz download-----
    echo "Downloading..."
    if [ -e $SRC_DIR/$SQUID_FILE ]; then
        echo "squid file already exists"
    else
        wget -q --output-document=$SRC_DIR/$SQUID_FILE $SQUID_URL
    fi

    if [ ! -e $SRC_DIR/$SQUID_FILE ]
    then
        echo "ERROR: download failed, file not found$ZZZ_LINEFEED$SRC_DIR/$SQUID_FILE" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi

    #-----zero-size file means the download failed-----
    if [ ! -s $SRC_DIR/$SQUID_FILE ]
    then
        local ZZZTMP1="ERROR: download failed, file is zero-size$ZZZ_LINEFEED"
        local ZZZTMP2="$SRC_DIR/$SQUID_FILE$ZZZ_LINEFEED"
        local ZZZTMP3="Check if the file is on the squid website:$ZZZ_LINEFEED"
        local ZZZTMP4="http://www.squid-cache.org/Versions/$ZZZ_LINEFEED"
        local ZZZTMP5="File URL expected:$ZZZ_LINEFEED"
        local ZZZTMP6="$SQUID_URL"
        echo "$ZZZTMP1$ZZZTMP2$ZZZTMP3$ZZZTMP4$ZZZTMP5$ZZZTMP6" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi

    #-----sig file download-----
    if [ -e $SRC_DIR/$SQUID_SIGNATURE_FILE ]; then
        echo "squid signature file already exists"
    else
        wget -q --output-document=$SRC_DIR/$SQUID_SIGNATURE_FILE $SQUID_SIGNATURE_URL
    fi

    if [ ! -e $SRC_DIR/$SQUID_SIGNATURE_FILE ]
    then
        local ZZZTMP1="ERROR: signature file download failed, file not found$ZZZ_LINEFEED"
        local ZZZTMP2="$SRC_DIR/$SQUID_SIGNATURE_FILE"
        echo "$ZZZTMP1$ZZZTMP2" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi

    #-----zero-size file means the download failed-----
    if [ ! -s $SRC_DIR/$SQUID_SIGNATURE_FILE ]
    then
        local ZZZTMP1="ERROR: signature file download failed, file is zero-size$ZZZ_LINEFEED"
        local ZZZTMP2="$SRC_DIR/$SQUID_SIGNATURE_FILE$ZZZ_LINEFEED"
        local ZZZTMP3="Check if the file is on the squid website:$ZZZ_LINEFEED"
        local ZZZTMP4="http://www.squid-cache.org/Versions/"
        echo "$ZZZTMP1$ZZZTMP2$ZZZTMP3$ZZZTMP4" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi

    #--------------------------------------------------------------------------------

    #-----auto-verify signature after downloading-----
    echo
    echo "Verifying Signature..."
    SQUID_VERIFY_SIGNATURE=`$RUN_AS_UBUNTU gpg --homedir /home/ubuntu/.gnupg --status-fd 1 --verify $SRC_DIR/$SQUID_SIGNATURE_FILE 2>/dev/null | grep VALIDSIG | cut -d ' ' -f 3`

    if [ "$SQUID_INSTALL_TEST" == "y" ]; then
        echo "VALIDSIG=$SQUID_VERIFY_SIGNATURE"
    fi
    if [[ "$SQUID_VERIFY_SIGNATURE" != "$ZZZ_SQUID_VALIDATION_KEY" ]]; then
        echo "    ERROR: failed to verify squid signature, exiting" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi
    echo

    #--------------------------------------------------------------------------------

    #-----remove old src dir if it's there-----
    if [ -d $SQUID_SRC ]; then
        echo "Clearing old squid src directory..."
        rm -rf $SQUID_SRC
    fi

    #-----unzip the squid file-----
    echo "Unzipping squid..."
    tar -xzf $SQUID_FILE

    if [ -d $SQUID_SRC ]; then
        cd $SQUID_SRC

        #-----configure and compile-----
        # NOTE: compiling takes about 20 minutes
        ./bootstrap.sh
        ./configure --with-openssl --enable-ssl-crtd --enable-icap-client \
            --prefix=/usr \
            --localstatedir=/var \
            --libexecdir=${prefix}/lib/squid \
            --datadir=${prefix}/share/squid \
            --sysconfdir=/etc/squid \
            --with-default-user=proxy \
            --with-logdir=/var/log/squid \
            --with-pidfile=/var/run/squid.pid
        make -j `nproc` all
    else
        echo "    ERROR: failed to unzip squid gz file to a directory" > $SQUID_INSTALLER_STATUS_FILE
        return
    fi
}

zzz_squid_do_download_verify_compile
