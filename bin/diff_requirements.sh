#!/bin/bash
#-----compare requirements files for different venv's-----
# /home/ubuntu/repos/test/install/requirements.txt
# /home/ubuntu/repos/test/install/requirements-alt.txt
# /home/ubuntu/repos/test/install/requirements-test.txt

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

ZZZ_DIFF_ERROR_TEST="Files /tmp/requirements-diff-main-test.txt and $REPOS_DIR/install/requirements-diff-main-test.txt differ"

ZZZ_DIFF_MAIN_TEST_RESULT_FILE="/tmp/requirements-diff-main-test.txt"
echo
diff $REPOS_DIR/install/requirements.txt $REPOS_DIR/install/requirements-test.txt > $ZZZ_DIFF_MAIN_TEST_RESULT_FILE
cat $ZZZ_DIFF_MAIN_TEST_RESULT_FILE

# are there any unexpected differences?
ZZZ_DIFF_MAIN_TEST_EXPECTED="$REPOS_DIR/install/requirements-diff-main-test.txt"
ZZZ_COMPARE_RESULT_TO_EXPECTED=`diff -q $ZZZ_DIFF_MAIN_TEST_RESULT_FILE $ZZZ_DIFF_MAIN_TEST_EXPECTED`
echo
if [ "$ZZZ_COMPARE_RESULT_TO_EXPECTED" == "$ZZZ_DIFF_ERROR_TEST" ]; then
    echo "***ERROR: unexpected differences in MAIN and TEST***"
    diff $ZZZ_DIFF_MAIN_TEST_RESULT_FILE $ZZZ_DIFF_MAIN_TEST_EXPECTED
else
    echo "***LOOKS OK***"
fi

echo
echo "--------------------------------------------------------------------------------"
echo

ZZZ_DIFF_ERROR_ALT="Files /tmp/requirements-diff-main-alt.txt and $REPOS_DIR/install/requirements-diff-main-alt.txt differ"

ZZZ_DIFF_MAIN_ALT_RESULT_FILE="/tmp/requirements-diff-main-alt.txt"
echo
diff $REPOS_DIR/install/requirements.txt $REPOS_DIR/install/requirements-alt.txt > $ZZZ_DIFF_MAIN_ALT_RESULT_FILE
cat $ZZZ_DIFF_MAIN_ALT_RESULT_FILE

# are there any unexpected differences? compare the $ZZZ_DIFF_MAIN_ALT to the contents of requirements-diff-main-alt.txt
ZZZ_DIFF_MAIN_ALT_EXPECTED="$REPOS_DIR/install/requirements-diff-main-alt.txt"
ZZZ_COMPARE_RESULT_TO_EXPECTED=`diff -q $ZZZ_DIFF_MAIN_ALT_RESULT_FILE $ZZZ_DIFF_MAIN_ALT_EXPECTED`
echo
if [ "$ZZZ_COMPARE_RESULT_TO_EXPECTED" == "$ZZZ_DIFF_ERROR_ALT" ]; then
    echo "***ERROR: unexpected differences in MAIN and ALT***"
    diff $ZZZ_DIFF_MAIN_ALT_RESULT_FILE $ZZZ_DIFF_MAIN_ALT_EXPECTED
else
    echo "***LOOKS OK***"
fi
