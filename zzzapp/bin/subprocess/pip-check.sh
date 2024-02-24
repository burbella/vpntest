#!/bin/bash
#-----check installed pip versions, including pip itself-----

PIP_LIST_NOTICES=`nice -n 19 /opt/zzz/venv/bin/pip3 list 2>&1 | grep -P '^\[notice\] '`
PYTHON_PATH="run: python3"
VENV_PYTHON_PATH="run: /opt/zzz/venv/bin/python3"
echo "${PIP_LIST_NOTICES//$PYTHON_PATH/$VENV_PYTHON_PATH}"

#-----Sample warning-----
# [notice] A new release of pip available: 22.1.2 -> 22.2.2
# [notice] To update, run: python3 -m pip install --upgrade pip

echo

# options: --hide-unchanged, --local, --not-required
nice -n 19 /opt/zzz/venv/bin/pip-check --cmd /opt/zzz/venv/bin/pip3 --ascii $1 $2 $3

