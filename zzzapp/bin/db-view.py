#!/opt/zzz/venv/bin/python3

#-----view DB schema and table data for debugging/testing-----

import argparse
import os
import pprint
import site
import sqlite_utils
import sys

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

db = zzzevpn.DB(ConfigData)
#-----use readonly for safety-----
connected_ok = db.db_connect(ConfigData['DBFilePath']['Services'], readonly=True)
#-----quit if we couldn't connect to the DB-----
if not connected_ok:
    sys.exit('ERROR: failed to connect to DB')
sqlite_utils_db = sqlite_utils.Database(db.dbh)

util = zzzevpn.Util(ConfigData, db)

#--------------------------------------------------------------------------------

default_format = 'double_grid'
formats_available = [
    'asciidoc',
    'double_grid',
    'double_outline',
    'fancy_grid',
    'fancy_outline',
    'github',
    'grid',
    'heavy_grid',
    'heavy_outline',
    'html',
    'jira',
    'latex',
    'latex_booktabs',
    'latex_longtable',
    'latex_raw',
    'mediawiki',
    'mixed_grid',
    'mixed_outline',
    'moinmoin',
    'orgtbl',
    'outline',
    'pipe',
    'plain',
    'presto',
    'pretty',
    'psql',
    'rounded_grid',
    'rounded_outline',
    'rst',
    'simple',
    'simple_grid',
    'simple_outline',
    'textile',
    'tsv',
    'unsafehtml',
    'youtrack',
]

def show_formats_available():
    print('formats available:')
    pprint.pprint(formats_available)

#--------------------------------------------------------------------------------

def test(sqlite_utils_db):
    output = sqlite_utils_db.query('''
        select * from zzz_system
    ''')
    if output:
        # array of dicts
        for row in output:
            print(row)

#--------------------------------------------------------------------------------

def list_tables(sqlite_utils_db, print_tables=False):
    table_names = sqlite_utils_db.table_names()
    if table_names and print_tables:
        print(table_names)
    return table_names

def show_schema(sqlite_utils_db):
    print(sqlite_utils_db.schema)

def show_table(sqlite_utils_db, ConfigData, util, table_name='', format=default_format, max_rows=10):
    if not format:
        format = default_format
    if format not in formats_available:
        print('ERROR: invalid format')
        show_formats_available()
        return
    
    if util.is_int(max_rows):
        if len(max_rows)>6:
            max_rows = 1000
        max_rows = int(max_rows)
        if max_rows>1000:
            max_rows = 1000
    else:
        max_rows = 10
    
    if not table_name:
        print('ERROR: no table specified')
        return
    table_names = list_tables(sqlite_utils_db)
    if table_name not in table_names:
        print('ERROR: invalid table')
        return

    #TEST:
    # sudo /opt/zzz/venv/bin/sqlite-utils rows --limit 10 --fmt pretty /opt/zzz/sqlite/services.sqlite3 zzz_system
    db_filepath = ConfigData['DBFilePath']['Services']
    subprocess_commands = [ConfigData['Subprocess']['sqlite-utils'], 'rows', '--limit', str(max_rows), '--fmt', format, db_filepath, table_name]
    if util.run_script(subprocess_commands):
        print(util.subprocess_output.stdout)
    else:
        print(util.script_output)

#--------------------------------------------------------------------------------

#-----read command-line options-----
# total schema
# table schema
# indexes
# 100 rows from a table
parser = argparse.ArgumentParser(description='Zzz DB Viewer')
parser.add_argument('--list-tables', dest='list_tables', action='store_true', help='list the table names')
parser.add_argument('--schema', dest='schema', action='store_true', help='show the complete schema')

#-----table data display-----
parser.add_argument('--show-table', dest='show_table', action='store', help='list the table names')
parser.add_argument('--format', dest='format', action='store', help='select a table display format')
parser.add_argument('--max-rows', dest='max_rows', action='store', help='max number of rows of output (1-1000)')

parser.add_argument('--test', dest='test', action='store_true', help='test output')

args = parser.parse_args()

#--------------------------------------------------------------------------------

count_args = 0

if args.list_tables:
    list_tables(sqlite_utils_db, print_tables=True)
    count_args += 1

if args.schema:
    show_schema(sqlite_utils_db)
    count_args += 1

if args.show_table:
    format = default_format
    max_rows = 10
    if args.format:
        format = args.format
    if args.max_rows:
        max_rows = args.max_rows
    show_table(sqlite_utils_db, ConfigData, util, table_name=args.show_table, format=format, max_rows=max_rows)
    count_args += 1

if args.test:
    test(sqlite_utils_db)
    count_args += 1

if count_args==0:
    parser.print_help()
    show_formats_available()
