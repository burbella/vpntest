#!/bin/bash
#-----Zzz daemon utility functions-----
# supports daemon interactions
# functions based on this script: zzzapp/bin/start-stop-zzz.sh
# USAGE: source /opt/zzz/util/daemon_utils.sh

bash_PIDFILE=/var/run/zzz-test.pid
python_PIDFILE=/var/run/zzz-test-python.pid
START_STOP_SCRIPT=/opt/zzz/python/bin/start-stop-zzz.sh
PYTHON_DAEMON=/opt/zzz/python/bin/services_zzz.py
DAEMON_OUTFILE=/var/log/zzz/daemon-test-outfile
DAEMON_ERRFILE=/var/log/zzz/daemon-test-errfile

PID=0
python_PID=0

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

init_daemon_utils() {
    get_bash_pid_from_pidfile
    get_python_pid_from_pidfile
}

#--------------------------------------------------------------------------------

#-----make sure the PID exists, exit with error if it doesn't-----
check_pid_or_exit() {
    if [ "$PID" == "0" ]; then
        echo "ERROR: no bash_PIDFILE"
        exit 1
    fi
}

check_python_PID_or_exit() {
    if [ "$python_PID" == "0" ]; then
        echo "ERROR: no python_PIDFILE"
        exit 1
    fi
}

double_check_python_PID_or_exit() {
    get_python_pid_from_pidfile
    get_python_pid_from_ps
    if [[ "$python_PID" -eq "0" ]]; then
        echo "ERROR: python PIDFILE not found"
        exit 1
    else
        if [[ "$python_PID" -ne "$PID_FROM_PS" ]]; then
            echo "ERROR: python script is not running"
            exit 1
        fi
    fi
}

#--------------------------------------------------------------------------------

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

#-----send the checkwork signal to the python daemon-----
send_signal_SIGUSR1() {
    SIGNAL_TO_SEND=SIGUSR1
    process_send_signal
}

