#!/bin/bash
#-----compare requirements files for different venv's-----
# /home/ubuntu/repos/test/install/requirements.txt
# /home/ubuntu/repos/test/install/requirements-alt.txt
# /home/ubuntu/repos/test/install/requirements-test.txt

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

echo diff requirements.txt requirements-test.txt
echo
diff $REPOS_DIR/install/requirements.txt $REPOS_DIR/install/requirements-test.txt

echo
echo "--------------------------------------------------------------------------------"
echo

echo diff requirements.txt requirements-alt.txt
echo
diff $REPOS_DIR/install/requirements.txt $REPOS_DIR/install/requirements-alt.txt
