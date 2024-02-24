#!/bin/bash
# 001_ssh-user-config.sh
# (specify username in a var/config?)
# installs files:
# 	/home/ubuntu/.bash_profile
# 	/home/ubuntu/.vimrc
# 	/root/.bashrc
# 	/root/.vimrc
# makes directories: (? maybe store everything under /opt/zzz ?)
# 	mkdir /home/ubuntu/bin
# 	mkdir /home/ubuntu/openvpn
# 	mkdir /home/ubuntu/src
# 	mkdir /home/ubuntu/www

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, UBUNTU_CONFIG_DIR

TEMP_HOSTS_FILE=/home/ubuntu/hosts

#-----set ENV vars for ubuntu user-----
cp $UBUNTU_CONFIG_DIR/.bash_profile /home/ubuntu/
cp $UBUNTU_CONFIG_DIR/zzz_env_ubuntu /home/ubuntu/
source /home/ubuntu/zzz_env_ubuntu

#-----set ENV vars for root user-----
cp $UBUNTU_CONFIG_DIR/zzz_env_ubuntu /root
echo '' >> /root/.bashrc
echo 'source /root/zzz_env_ubuntu' >> /root/.bashrc


#-----brighter colors for the VIM editor-----
cp $UBUNTU_CONFIG_DIR/.vimrc /root
cp $UBUNTU_CONFIG_DIR/.vimrc /home/ubuntu

#-----top mem display in MB, sorts by mem usage-----
cp $UBUNTU_CONFIG_DIR/.toprc /root
cp $UBUNTU_CONFIG_DIR/.toprc /home/ubuntu

#-----user directories-----
mkdir -p /home/ubuntu/backup
mkdir -p /home/ubuntu/bin
mkdir -p /home/ubuntu/easyrsa3/zzz_vars
mkdir -p /home/ubuntu/openvpn
mkdir -p /home/ubuntu/public_certs
mkdir -p /home/ubuntu/src
mkdir -p /home/ubuntu/www

#-----fix permissions-----
chown -R ubuntu.ubuntu /home/ubuntu/

#-----fix sudo warning-----
cat $UBUNTU_CONFIG_DIR/hosts-part1 > $TEMP_HOSTS_FILE
STR1="127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4"
#-----7/31/2019 - STR2 now causes errors in DNS, so leave it out-----
#STR2=`cat /etc/hostname`
#echo "$STR1 $STR2" >> $TEMP_HOSTS_FILE
echo "$STR1" >> $TEMP_HOSTS_FILE
cat $UBUNTU_CONFIG_DIR/hosts-part2 >> $TEMP_HOSTS_FILE
cp $TEMP_HOSTS_FILE /etc/hosts

echo "$ZZZ_SCRIPTNAME - END"
