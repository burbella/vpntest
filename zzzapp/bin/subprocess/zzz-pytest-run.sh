#!/bin/bash

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_PYTHON_DIR, ZZZ_PYTEST_DIR

ZZZ_COVERAGE_HTML_DIR=/var/www/html/coverage
ZZZ_COVERAGE_DATA_FILE=/opt/zzz/python/test/.coverage
ZZZ_COVERAGE_JSON_FILE=$ZZZ_COVERAGE_HTML_DIR/coverage.json

#-----option to include coverage-----
ZZZ_INCLUDE_COVERAGE=$1

export COLUMNS=200

#-----run pytest-----
if [[ "$ZZZ_INCLUDE_COVERAGE" == "--include-coverage" ]]; then
    sudo --user=www-data -H /opt/zzz/venv/bin/coverage run --data-file=$ZZZ_COVERAGE_DATA_FILE --module pytest --pyargs $ZZZ_PYTHON_DIR
    
    #-----HTML format-----
    sudo --user=www-data -H /opt/zzz/venv/bin/coverage html --data-file=$ZZZ_COVERAGE_DATA_FILE --directory=$ZZZ_COVERAGE_HTML_DIR
    chmod 644 $ZZZ_COVERAGE_HTML_DIR/*

    #-----cleanup deprecated JS-----
    COVERAGE_JS_FILEPATH=$ZZZ_COVERAGE_HTML_DIR/coverage_html.js
    sed --in-place 's/window.addEventListener("unload"/window.addEventListener("pagehide"/g' $COVERAGE_JS_FILEPATH

    #-----JSON format?-----
    # sudo --user=www-data -H /opt/zzz/venv/bin/coverage json --data-file=$ZZZ_COVERAGE_DATA_FILE -o $ZZZ_COVERAGE_JSON_FILE --pretty-print
    # sudo --user=www-data -H /opt/zzz/venv/bin/coverage json --data-file=$ZZZ_COVERAGE_DATA_FILE -o $ZZZ_COVERAGE_JSON_FILE
    # chmod 644 $ZZZ_COVERAGE_JSON_FILE
else
    sudo --user=www-data -H /opt/zzz/venv/bin/pytest --pyargs $ZZZ_PYTHON_DIR
fi

#-----look for import cycles in modules-----
echo "--------------------------------------------------------------------------------"
echo
echo "PyCycle Tests"
echo "============="
echo
cd $REPOS_DIR/zzzapp/lib/zzzevpn
pycycle --here --verbose

#-----make sure all class functions contain "self" variable-----
echo "--------------------------------------------------------------------------------"
echo
echo "Search for missing self var in module functions (no output below is good)"
echo "==============================================="
echo
grep -rn 'def ' $REPOS_DIR/zzzapp/lib/zzzevpn | grep -vP '\(self'

#-----make sure there are no python functions with duplicate names-----
echo "--------------------------------------------------------------------------------"
echo
echo "Search for duplicate function names (no output below is good)"
echo "==================================="
echo
/opt/zzz/python/bin/find-duplicate-functions.py

#-----report javascript functions with duplicate names-----
echo "--------------------------------------------------------------------------------"
echo
echo "Search for duplicate javascript function names (may be OK in some cases)"
echo "=============================================="
echo
grep -rnP '^\s*function ' $REPOS_DIR/zzzapp/www/html/js | cut -d ':' -f 3 | cut -d ' ' -f 2 | cut -d '(' -f 1 | sort | uniq -c | grep -vP '^\s*1\s'
# Example:
# grep -rnP '^\s*function ' /home/ubuntu/repos/vpntest/zzzapp/www/html/js | cut -d ':' -f 3 | cut -d ' ' -f 2 | cut -d '(' -f 1 | sort | uniq -c | grep -vP '^\s*1\s'

#-----report python functions with duplicate names-----
echo "--------------------------------------------------------------------------------"
echo
echo "Search for duplicate python function names (may be OK in many cases)"
echo "=========================================="
echo
grep -rnP '^\s*def ' $REPOS_DIR/zzzapp/lib/zzzevpn | cut -d ':' -f 3 | sed --quiet --regexp-extended 's/.*def (.+?)\(.*/\1/p' | sort | uniq -c | grep -vP '^\s*1\s'
# Example:
# grep -rnP '^\s*def ' /home/ubuntu/repos/vpntest/zzzapp/lib/zzzevpn | cut -d ':' -f 3 | sed --quiet --regexp-extended 's/.*def (.+?)\(.*/\1/p' | sort | uniq -c | grep -vP '^\s*1\s'
