#!/bin/bash
#-----upgrade python pip3 packages to the latest version-----
# standard upgrade:
#   sudo /opt/zzz/upgrade/upgrade-pip.sh
# don't restart apps:
#   sudo /opt/zzz/upgrade/upgrade-pip.sh -s
# use the test venv: (and don't restart apps)
#   sudo /opt/zzz/upgrade/upgrade-pip.sh -s -t

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_PIP_VERSION
exit_if_not_running_as_root

#--------------------------------------------------------------------------------

show_usage() {
    echo
    echo "Usage: $(basename $0) [-a] [-c] [-f] [-h] [-s] [-t] [-v]"
    echo "  -a install PIP to alternate venv"
    echo "  -c check all package dependencies"
    echo "  -f force re-install of all packages"
    echo "  -h help (show this message)"
    echo "  -s skip app restarts after install"
    echo "  -t install PIP to test venv"
    echo "  -v install PIP to main venv"
}

#--------------------------------------------------------------------------------

ZZZ_OPTS_PROVIDED=False
ZZZ_ERROR_EXIT=False
ZZZ_CHECK_DEP=False
ZZZ_FORCE_REINSTALL=""
ZZZ_SKIP_RESTART=False
ZZZ_ALT_VENV=False
ZZZ_MAIN_VENV=False
ZZZ_TEST_VENV=False
while getopts ":hacfstv" opt; do
    ZZZ_OPTS_PROVIDED=True
    case ${opt} in
        a )
            echo "installing PIP to alternate venv"
            ZZZ_ALT_VENV=True
            ;;
        c )
            echo "checking all package dependencies"
            ZZZ_CHECK_DEP=True
            ;;
        f )
            echo "forcing re-install of all packages (test venv only)"
            ZZZ_FORCE_REINSTALL="--force-reinstall"
            ;;
        h )
            show_usage
            ;;
        s )
            echo "skipping app restarts after install"
            ZZZ_SKIP_RESTART=True
            ;;
        t )
            echo "installing PIP to test venv"
            ZZZ_TEST_VENV=True
            ;;
        v )
            echo "installing PIP to main venv"
            ZZZ_MAIN_VENV=True
            ;;
        \? )
            echo "INVALID OPTION: $OPTARG" 1>&2
            show_usage
            ZZZ_ERROR_EXIT=True
            ;;
        : )
            echo "INVALID OPTION: $OPTARG requires an argument" 1>&2
            show_usage
            ZZZ_ERROR_EXIT=True
            ;;
    esac
done
shift $((OPTIND -1))

#-----require at least one option to be selected-----
if [[ "$ZZZ_OPTS_PROVIDED" == "False" ]]; then
    show_usage
    exit
fi

if [[ "$ZZZ_ERROR_EXIT" == "True" ]]; then
    exit
fi

echo

#--------------------------------------------------------------------------------

#-----check if packages have all their dependencies-----
#
# /opt/zzz/venv/bin/python3 -m pip check
# --force-reinstall
# /opt/zzz/venv/bin/pipdeptree

if [[ "$ZZZ_CHECK_DEP" == "True" ]]; then
    echo "main venv:"
    /opt/zzz/venv/bin/python3 -m pip check
    echo "--------------------------------------------------------------------------------"

    echo "alternate venv:"
    /opt/zzz/venv_alt/bin/python3 -m pip check
    echo "--------------------------------------------------------------------------------"

    echo "test venv:"
    /opt/zzz/venvtest/bin/python3 -m pip check
    echo "--------------------------------------------------------------------------------"
fi

if [[ "$ZZZ_TEST_VENV" == "True" ]]; then
    echo "TEST pip upgrade"
    sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install --upgrade $ZZZ_FORCE_REINSTALL $ZZZ_PIP_VERSION
    echo "--------------------------------------------------------------------------------"
    sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install $ZZZ_FORCE_REINSTALL -r $REPOS_DIR/install/requirements-tools.txt
    echo "--------------------------------------------------------------------------------"
    sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install $ZZZ_FORCE_REINSTALL -r $REPOS_DIR/install/requirements-test.txt

    #-----fix a bug that makes ICAP crash in python 3.10-----
    # alternative:
    #   replace isinstance(method, collections.Callable)
    #   with callable(method)
    perl -pi -e "s/collections.Callable/collections.abc.Callable/g" /opt/zzz/venvtest/lib/python3.10/site-packages/pyicap.py

    exit
fi

if [[ "$ZZZ_ALT_VENV" == "True" ]]; then
    echo "Upgrading python PIP apps for alternate venv"
    sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install --upgrade $ZZZ_PIP_VERSION
    echo "--------------------------------------------------------------------------------"
    sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
    echo "--------------------------------------------------------------------------------"
    sudo --user=ubuntu -H /opt/zzz/venv_alt/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-alt.txt

    #-----fix a bug that makes ICAP crash in python 3.10-----
    perl -pi -e "s/collections.Callable/collections.abc.Callable/g" /opt/zzz/venv_alt/lib/python3.10/site-packages/pyicap.py
fi

if [[ "$ZZZ_MAIN_VENV" == "True" ]]; then
    echo "Upgrading python PIP apps for main venv"
    sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install --upgrade $ZZZ_PIP_VERSION
    echo "--------------------------------------------------------------------------------"
    sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
    echo "--------------------------------------------------------------------------------"
    sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements.txt

    #-----fix a bug that makes ICAP crash in python 3.10-----
    perl -pi -e "s/collections.Callable/collections.abc.Callable/g" /opt/zzz/venv/lib/python3.10/site-packages/pyicap.py

    #-----restart apps that use the main venv, unless told not to restart-----
    if [[ "$ZZZ_SKIP_RESTART" == "False" ]]; then
        echo
        echo "Restarting apache ..."
        systemctl restart apache2

        echo
        echo "Restarting zzz daemons ..."
        systemctl restart zzz
        /home/ubuntu/bin/icap-restart
    fi
fi

echo
echo "$ZZZ_SCRIPTNAME - END"
