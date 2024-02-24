#!/bin/bash
# Zzz Services daemon - Ubuntu start-stop script

bash_PIDFILE=/var/run/zzz-test.pid
python_PIDFILE=/var/run/zzz-test-python.pid
START_STOP_SCRIPT=/opt/zzz/python/bin/start-stop-zzz.sh
PYTHON_DAEMON=/opt/zzz/python/bin/services_zzz.py
DAEMON_OUTFILE=/var/log/zzz/daemon-test-outfile
DAEMON_ERRFILE=/var/log/zzz/daemon-test-errfile

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root" 
    exit 1
fi

#--------------------------------------------------------------------------------

get_bash_pid_from_pidfile() {
    PID=0
    if [ -f "$bash_PIDFILE" ]; then
        PID=`cat $bash_PIDFILE`
    fi
}

get_python_pid_from_pidfile() {
    python_PID=0
    if [ -f "$python_PIDFILE" ]; then
        python_PID=`cat $python_PIDFILE`
    fi
}

get_python_pid_from_ps() {
    PID_FROM_PS=`ps --no-headers -o pid -p $python_PID | sed 's/ //g'`
}

#--------------------------------------------------------------------------------

#-----Signal Handling-----
# the signal will be acted upon only after the sleep is done in the WHILE loop
# there must be at least one other command in the WHILE loop for this to work, so a junk echo is there
# SIGHUP - tell the python process to reload its config
# SIGUSR1 - tell the python process to check for work in the DB
# SIGTERM - tell the python process to exit

process_shutdown() {
    echo "caught $SIGNAL_TO_SEND"
    if [ -f "$python_PIDFILE" ]; then
        #-----get the PID from the PIDFILE-----
        get_python_pid_from_pidfile
        echo "python_PID: $python_PID"
        
        #-----check if the process is running-----
        get_python_pid_from_ps
        echo "PID_FROM_PS: $PID_FROM_PS"
        
        if [[ "$python_PID" -eq "$PID_FROM_PS" ]]; then
            echo "found python script in process list"
            
            echo "signaling python to exit with $SIGNAL_TO_SEND ..."
            kill -s $SIGNAL_TO_SEND $python_PID
            
            echo "waiting for python to exit..."
            wait $python_PID
            echo "done waiting"
        else
            #-----no signal to send if the process is not running-----
            echo "ERROR: python script is not running"
        fi
        
        echo "removing python pidfile"
        rm $python_PIDFILE
    else
        #-----assume the python process is not running if the pidfile is not there-----
        echo "ERROR - python_PIDFILE not found: $python_PIDFILE"
    fi
    
    echo "removing main pidfile"
    rm $bash_PIDFILE
    
    echo "bash script exiting"
    exit 0
}

#-----forwards a received signal from bash to python-----
process_send_signal() {
    echo "caught $SIGNAL_TO_SEND"
    get_python_pid_from_pidfile
    get_python_pid_from_ps
    if [[ "$python_PID" -eq "0" ]]; then
        echo "ERROR: python PIDFILE not found"
    else
        if [[ "$python_PID" -eq "$PID_FROM_PS" ]]; then
            echo "signaling python with $SIGNAL_TO_SEND . . ."
            kill -s $SIGNAL_TO_SEND $python_PID
        else
            echo "ERROR: python script is not running"
        fi
    fi
}

process_SIGHUP() {
    SIGNAL_TO_SEND=SIGHUP
    process_send_signal
}

process_SIGTERM() {
    SIGNAL_TO_SEND=SIGTERM
    process_shutdown
}

#-----send the checkwork signal to the python daemon-----
process_SIGUSR1() {
    SIGNAL_TO_SEND=SIGUSR1
    process_send_signal
}

trap process_SIGHUP SIGHUP
trap process_SIGTERM SIGTERM
trap process_SIGUSR1 SIGUSR1

#-----End of Signal Handling-----

#--------------------------------------------------------------------------------

#-----cleanup cases where the python script crashes while leaving the pidfile there-----
# check if the python script is still running
# assume the $python_PID is for the python script and not something else that started up after python crashed
# cleanup PID files and exit if it is not running
# post a warning somewhere?  database insert?  textfile?
check_python() {
    ZZZ_CHECK_PYTHON=0
    if [[ "$ZZZ_DO_SHUTDOWN" -eq "1" ]]; then
        #-----no matter how long process_shutdown() ends up waiting for the daemon to exit, we don't want to call this function again-----
        return
    fi
    
    get_python_pid_from_pidfile
    if [[ "$python_PID" -eq "0" ]]; then
        echo "ERROR: python PIDFILE not found, exiting..."
        ZZZ_DO_SHUTDOWN=1
    else
        get_python_pid_from_ps
        if [[ "$python_PID" -ne "$PID_FROM_PS" ]]; then
            echo "ERROR: python script is not running, exiting..."
            ZZZ_DO_SHUTDOWN=1
        fi
    fi
    
    if [[ "$ZZZ_DO_SHUTDOWN" -eq "1" ]]; then
        #-----use "systemctl stop" or systemd will get confused when the process exits on its own-----
        systemctl stop zzz
    fi
}

#--------------------------------------------------------------------------------

#-----make sure no other copies of the script are running-----
if [ -f $bash_PIDFILE ]; then
    get_bash_pid_from_pidfile
    get_python_pid_from_pidfile
    echo "ERROR: app is already running"
    echo "PID: $PID"
    echo "python PID: $python_PID"
    exit 1
fi

me_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
me_FILE=$(basename $0)
me_FILEPATH=$me_DIR/$me_FILE
cd /

#--------------------------------------------------------------------------------

#-----(2) second execution-----
if [ "$1" = "second_execution" ] ; then
    shift; tty="$1"; shift
    umask 0
    $me_FILEPATH third_execution "$tty" "$@" </dev/null >/dev/null 2>/dev/null &
    exit 0
fi

#--------------------------------------------------------------------------------

#-----(1) first execution-----
if [ "$1" != "third_execution" ] ; then
    tty=$(tty)
    setsid $me_FILEPATH second_execution "$tty" "$@" &
    exit 0
fi

#--------------------------------------------------------------------------------

#TODO: change this from overwrite to append after log rotation is implemented
#-----(3) third execution-----
exec >$DAEMON_OUTFILE
exec 2>$DAEMON_ERRFILE
exec 0</dev/null

shift; tty="$1"; shift

#-----store bash PID-----
echo -n $$ > $bash_PIDFILE

#-----run the daemon at minimum priority so it doesn't impact other server operations-----
echo "Calling daemon..."
nice -n 19 $PYTHON_DAEMON &

#-----store python PID-----
echo -n $! > $python_PIDFILE

#-----permissions fix-----
chmod 644 $DAEMON_OUTFILE
chmod 644 $DAEMON_ERRFILE
chmod 644 $bash_PIDFILE
chmod 644 $python_PIDFILE

echo "Done calling daemon"

ZZZ_DO_SHUTDOWN=0
ZZZ_CHECK_PYTHON=0
while true; do
    # loop forever until a SIGTERM tells the process to exit
    echo "z" > /dev/null
    sleep 1
    
    #-----only run this test every 10 seconds-----
    ((ZZZ_CHECK_PYTHON++))
    if [[ "$ZZZ_CHECK_PYTHON" -ge "10" ]]; then
        check_python
    fi
done

echo "end of zzz bash script"

exit 0
