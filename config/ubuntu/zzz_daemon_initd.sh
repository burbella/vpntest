#!/bin/bash -e

### BEGIN INIT INFO
# Provides:          zzz
# Required-Start:    $local_fs $remote_fs $network $syslog $named
# Required-Stop:     $local_fs $remote_fs $network $syslog $named
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# X-Interactive:     true
# Short-Description: Zzz daemon
# Description:       Start the Zzz daemon
#  This script will start the Zzz daemon.
### END INIT INFO

# After installing a new version of this file, run this to make it work:
#   systemctl daemon-reload
#
# Monitor system output/error logs:
#   systemctl status zzz
#   journalctl -xe
#
# References:
#   https://refspecs.linuxbase.org/LSB_3.0.0/LSB-PDA/LSB-PDA/iniscrptfunc.html

DESC="Zzz daemon"
NAME=zzz

SCRIPTNAME="${0##*/}"
SCRIPTNAME="${SCRIPTNAME##[KS][0-9][0-9]}"

# disable localization
LANG=C
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

#-----source the LSB daemon functions-----
. /lib/lsb/init-functions

PIDFILE=/var/run/zzz-test.pid
PYTHON_DIR=/opt/zzz/python
START_STOP_SCRIPT=/opt/zzz/python/bin/start-stop-zzz.sh

PID_WAIT_TIMEOUT=5
PID=0
if [ -f $PIDFILE ]; then
    PID=`cat $PIDFILE`
fi

#--------------------------------------------------------------------------------

start() {
    log_daemon_msg "Starting $DESC" "$NAME"
    echo "START"
    $START_STOP_SCRIPT
}

stop() {
    log_daemon_msg "Stopping $DESC" "$NAME"
    echo "STOP"
    #/home/ubuntu/bin/kill-daemon -k
    
    #-----make sure the PID exists, exit with error if it doesn't-----
    if [ "$PID" == "0" ]; then
        echo "ERROR: no PIDFILE"
        #echo "ERROR: parent process not found"
        exit 1
    fi
    
    #-----send the shutdown signal to the daemon-----
    kill -s SIGTERM $PID
    
    echo "Waiting for daemon to stop"
    #-----give up waiting after the timeout, so we don't wait forever-----
    timeout $PID_WAIT_TIMEOUT tail --pid=$PID -f /dev/null
    
    echo "STOPPED"
}

#--------------------------------------------------------------------------------

case "$1" in
    'start')
        log_daemon_msg "Starting $DESC" "$NAME"
        start
        ;;
    'stop')
        log_daemon_msg "Stopping $DESC" "$NAME"
        stop
        ;;
    'reload')
        log_daemon_msg "(UNDEFINED)Reloading $DESC" "$NAME"
        echo "RELOAD UNDEFINED"
        ;;
    'restart')
        log_daemon_msg "Restarting $DESC" "$NAME"
        echo "RESTART"
        stop
        start
        ;;
    'status')
        echo "STATUS"
        /home/ubuntu/bin/is-daemon-running
        ;;
    *)
        echo "Usage: $NAME {start|stop|restart|status}" >&2
        exit 1
        ;;
esac

exit 0
