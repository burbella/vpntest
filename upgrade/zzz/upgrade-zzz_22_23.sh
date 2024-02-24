#!/bin/bash
#-----upgrade zzz system from version 22 to 23-----

CURRENT_VERSION=22
NEW_VERSION=23

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the zzz daemon a chance to shut down-----
sleep 3

touch /etc/bind/settings/tlds.conf
chown root.bind /etc/bind/settings/tlds.conf
chmod 644 /etc/bind/settings/tlds.conf

#-----ubuntu needs to write here to manage the venv directory-----
chmod 775 /opt/zzz
chown root.ubuntu /opt/zzz

# prep for virtualenv
for i in \
    libcmocka0 \
    libcmocka-dev \
    python3-venv \
    python3.9 \
    python3.9-dbg \
    python3.9-dev \
    python3.9-full \
    python3.9-venv ; do
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install $i
done

#-----do the standard upgrade process-----
simple_upgrade_custom_db $CURRENT_VERSION $NEW_VERSION

#-----setup python venv for zzzevpn apps-----
# must do this before running anything else installed with this release
sudo --user=ubuntu /usr/bin/python3.9 -m venv /opt/zzz/venv
source /opt/zzz/venv/bin/activate
sudo --user=ubuntu -H /opt/zzz/venv/bin/pip3 install --upgrade pip
sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements.txt

#-----don't proceed unless the config is OK-----
source /opt/zzz/util/util.sh
exit_if_configtest_invalid

#-----initialize the webserver_domain DB field with the current domain in the zzz.conf-----
/opt/zzz/python/bin/init-db.py --domain

#-----install the new TLD file, initialize the TLD DB table-----
cp $REPOS_DIR/install/TLD-list.txt /opt/zzz/data/
/opt/zzz/python/bin/init-db.py --tld

#-----install the TLD update cron-----
cp $REPOS_DIR/config/cron/zzz-update-tld /etc/cron.weekly/

#-----rebuild configs and queue up a settings bind config reload-----
NAMED_DIR=$REPOS_DIR/config/named
cp $NAMED_DIR/settings/* /etc/bind/settings
/opt/zzz/python/bin/build-config.py --bind
DB_FILE=/opt/zzz/sqlite/services.sqlite3
sqlite3 $DB_FILE "insert into service_request (req_date, service_name, action, details, status) values (datetime('now'), 'settings', 'settings', '', 'Requested')"
sqlite3 $DB_FILE "insert into service_request (req_date, service_name, action, details, status) values (datetime('now'), 'zzz', 'version_checks', '', 'Requested')"
systemctl restart zzz

#-----make the openvpn intermediate CA and its certs-----
/opt/zzz/util/init-openvpn-pki.sh
#TODO: manually re-install openvpn client certs on all clients

#-----rebuild apache configs-----
/opt/zzz/python/bin/build-config.py --apache -q
systemctl restart apache2

#-----rebuild openvpn client/server configs-----
/opt/zzz/python/bin/build-config.py --openvpn-client -q
/opt/zzz/python/bin/build-config.py --openvpn-server -q
/opt/zzz/python/bin/subprocess/openvpn-restart.sh

#-----remove old modules that were moved to the zzzevpn package-----
PYTHON_LIB_DIR=/opt/zzz/python/lib
for i in \
    BIND.py \
    CheckLatestVersion.py \
    Config.py \
    DataValidation.py \
    DB.py \
    DNSservice.py \
    IndexPage.py \
    IPset.py \
    IPutil.py \
    IPtables.py \
    IPtablesLogParser.py \
    ListManager.py \
    LogParser.py \
    NetworkService.py \
    ServiceRequest.py \
    Settings.py \
    SettingsPage.py \
    SystemCommand.py \
    SystemStatus.py \
    TaskHistory.py \
    UpdateFile.py \
    UpdateOS.py \
    UpdateZzz.py \
    Util.py \
    Webpage.py \
    WhoisService.py \
    ZzzHTMLParser.py \
    ZzzICAPserver.py \
    ZzzTemplate.py \
    ZzzTest.py; do
    rm $PYTHON_LIB_DIR/$i
done
