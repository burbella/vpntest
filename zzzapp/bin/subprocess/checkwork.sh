#!/bin/bash
#-----send the checkwork signal to a daemon-----
source /opt/zzz/util/daemon_utils.sh

init_daemon_utils

send_signal_SIGUSR1
