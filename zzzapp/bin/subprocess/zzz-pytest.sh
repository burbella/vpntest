#!/bin/bash

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_PYTHON_DIR, ZZZ_PYTEST_DIR

#-----option to include coverage-----
ZZZ_INCLUDE_COVERAGE=$1

export COLUMNS=200

#-----clear old test data-----
if [[ -e "$ZZZ_PYTEST_DIR/db_maintenance" ]]; then
    rm $ZZZ_PYTEST_DIR/db_maintenance
fi
rm -rf $ZZZ_PYTEST_DIR/bin/*
rm -rf $ZZZ_PYTEST_DIR/html/*
rm -rf $ZZZ_PYTEST_DIR/lib/*
rm -rf $ZZZ_PYTEST_DIR/templates/*
rm -rf $ZZZ_PYTEST_DIR/wsgi/*

#-----install repos code and pytest files-----
cp $REPOS_DIR/zzzapp/test/*.{py,template,sql,conf} $ZZZ_PYTEST_DIR
chmod 755 $ZZZ_PYTEST_DIR/*.py
cp -R $REPOS_DIR/zzzapp/bin/* $ZZZ_PYTEST_DIR/bin
cp -R $REPOS_DIR/zzzapp/lib/* $ZZZ_PYTEST_DIR/lib
cp -R $REPOS_DIR/zzzapp/templates/* $ZZZ_PYTEST_DIR/templates
cp -R $REPOS_DIR/zzzapp/www/html/* $ZZZ_PYTEST_DIR/html
cp $REPOS_DIR/zzzapp/www/wsgi/zzz.wsgi $ZZZ_PYTEST_DIR/wsgi

#-----reset the pytest DB-----
nice -n 19 /opt/zzz/util/init-pytest-db.sh

#-----run the tests-----
ZZZ_PYTEST_OUTPUT=/opt/zzz/apache/dev/zzz-pytest.txt
# PyTest Prepared: 2022-11-19 16:24:57
DATETIME=`date '+%Y-%m-%d %H:%M:%S %Z'`
echo "PyTest Prepared: $DATETIME" > $ZZZ_PYTEST_OUTPUT
echo "" >> $ZZZ_PYTEST_OUTPUT
nice -n 19 /opt/zzz/python/bin/subprocess/zzz-pytest-run.sh $ZZZ_INCLUDE_COVERAGE >> $ZZZ_PYTEST_OUTPUT 2>&1
