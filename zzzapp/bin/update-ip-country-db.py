#!/opt/zzz/venv/bin/python3

#-----iptables processing by command line-----
# populate the DB with data from ipdeny files
# lookup the country for a given IP: IP=ip1.ip2.ip3.ip4
#
# init DB:
#   sqlite3 /opt/zzz/sqlite/ip-country.sqlite3 < /home/ubuntu/repos/test/install/database_setup_ip_country.sql
#
# DB filesize: 21MB
#
# sample IP to lookup: 6.1.40.3
#    6*256*256*256 + 256*256 + 40*256 + 3 = 100663296+65536+10240+3 = 100739075 (use this twice in SELECT)
# DB data: 6.0.0.0/8, 100663296, 117440511, US
# query:
#   select * from ip_country_map where cidr='6.0.0.0/8'
#   select country_code from ip_country_map where ip_min<=100739075 and ip_max>=100739075

import argparse
import datetime
import os
import pprint
import site
import sys
import time

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz IP-Country DB Util', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.IPtables

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

db_ip_country = zzzevpn.DB(ConfigData)
db_ip_country.db_connect(ConfigData['DBFilePath']['IPCountry'])

iptables = zzzevpn.IPtables(ConfigData)
settings = zzzevpn.Settings(ConfigData)
util = zzzevpn.Util(ConfigData)

settings.get_settings()

TEST_MODE = False

max_lines = 100
max_params = 10000

#--------------------------------------------------------------------------------

def process_line(country_code, line):
    cidr = line.rstrip('\n').rstrip('\r')
    cidr_obj = util.is_cidr(cidr)
    if not cidr_obj:
        print(f'not a valid CIDR: {line}')
        return None
    if cidr_obj.is_private or cidr_obj.is_reserved:
        print(f'private/reserved CIDR: {line}')
        return None
    
    ip_min = int(cidr_obj.network_address)
    ip_max = int(cidr_obj.broadcast_address)
    
    params = (cidr, ip_min, ip_max, country_code)
    
    if TEST_MODE:
        print(line)
        pprint.pprint(params)
    return params

#--------------------------------------------------------------------------------

#-----calculate the seconds between 2 dates-----
# pass-in a datetime object
def datetime_diff(date1_obj):
    if date1_obj is None:
        return 0
    current_date_obj = datetime.datetime.now()
    timedelta = current_date_obj - date1_obj
    return timedelta.total_seconds()

#--------------------------------------------------------------------------------

def do_sleep(runtime_seconds, start_query_datetime, max_seconds=1):
    #-----we don't want apps to get stuck too long waiting to read the DB-----
    # sleep 1 second for every second of DB writing
    runtime_seconds += datetime_diff(start_query_datetime)
    print(f'runtime_seconds={runtime_seconds}')
    if runtime_seconds>=max_seconds:
        time.sleep(max_seconds)
        runtime_seconds = 0
        print(f'runtime_seconds={runtime_seconds}')
    return runtime_seconds

#--------------------------------------------------------------------------------

#-----process file list entries output from scandir-----
def process_file(entry, db_params, sql_insert):
    if (not entry.is_file()) or (entry.stat().st_size==0) or not entry.path.endswith('.zone'):
        return db_params
    filename = entry.name
    
    #-----ipdeny files are lowercase, but all country codes in the DB are uppercase-----
    country_code = filename.split('.')[0].upper()
    
    if TEST_MODE:
        #-----test with a country that has some /14's for cidr-breakup functions-----
        if country_code!='CL':
            return db_params
    
    print(f'filename: {filename}, country_code: {country_code}')
    lines_parsed = 0
    runtime_seconds = 0
    with open(entry.path, 'r') as read_file:
        for line in read_file:
            lines_parsed += 1
            if TEST_MODE and lines_parsed>=max_lines:
                print(f'TEST: over {max_lines} lines, exiting...')
                break
            params = process_line(country_code, line)
            if params:
                db_params.append(params)
            #-----write to DB 10,000 entries at a time-----
            if len(db_params)>max_params:
                start_query_datetime = datetime.datetime.now()
                db_ip_country.query_exec_many(sql_insert, db_params)
                db_params = []
                runtime_seconds = do_sleep(runtime_seconds, start_query_datetime, 1)
                if TEST_MODE:
                    print('db_params:')
                    pprint.pprint(db_params)
    return db_params

#--------------------------------------------------------------------------------

def update_ip_country_db():
    # skip unless enabled
    if not ConfigData['EnableSqliteIPCountry']:
        return
    
    sql_insert = 'insert into ip_country_map_new (cidr, ip_min, ip_max, country_code) values (?, ?, ?, ?)'
    
    #-----create new table-----
    # Execute SQL File (scripts) using cursor's executescript function
    db_ip_country.exec_script(ConfigData['IPv4']['IPCountry']['new'])
    
    #-----populate new table-----
    # /opt/zzz/data/ipdeny-ipv4/*.zone
    # this is similar to IPset.update_country_lists()
    db_params = []
    for entry in os.scandir(ConfigData['IPdeny']['ipv4']['src_dir']):
        db_params = process_file(entry, db_params, sql_insert)
    
    #-----final insert-----
    if db_params:
        db_ip_country.query_exec_many(sql_insert, db_params)
        if TEST_MODE:
            print('db_params:')
            pprint.pprint(db_params)
    
    #-----rename live table to old, rename new table to live, drop old table-----
    db_ip_country.exec_script(ConfigData['IPv4']['IPCountry']['swap'])

#--------------------------------------------------------------------------------

def make_ip_log_params(ip):
    country_code = util.lookup_ip_country(ip)
    params = (country_code, ip)
    return params

#--------------------------------------------------------------------------------

# DB writes lock the DB, so sleep often to allow other processes to have DB access
def rebuild_country_logs():
    #TODO: finish this later
    print('rebuild is not ready, returning...')
    return
    
    sql = 'select distinct ip from ip_log_daily order by last_updated desc'
    sql_update = '''update ip_log_daily set country_code=?, country_updated=datetime('now') where ip=?'''
    
    ip_log_params = []
    rows_updated = 0
    runtime_seconds = 0
    (colnames, data, data_with_colnames) = settings.db.select_all(sql, params)
    if not data_with_colnames:
        return
    for row in data_with_colnames:
        rows_updated += 1
        params = make_ip_log_params(row['ip'])
        if params:
            ip_log_params.append(params)
        if len(db_params)>max_params:
            start_query_datetime = datetime.datetime.now()
            settings.db.query_exec_many(sql_update, ip_log_params)
            ip_log_params = []
            runtime_seconds = do_sleep(runtime_seconds, start_query_datetime, 1)

#--------------------------------------------------------------------------------

#TODO: figure out how soon this should run during install
#      need to have ipdeny files installed first
#      need to have python apps fully installed

#TODO: write a flag or service_request to the DB somewhere to indicate when this is running/done
#      processes that use these tables should not try to do lookups while the indexes are rebuilding because it will be very slow

#-----read command-line options-----
#TODO: init, update
arg_parser = argparse.ArgumentParser(description='IP-Country DB Tools')
arg_parser.add_argument('--init', dest='init', action='store_true', help='clear the DB and initialize it')
arg_parser.add_argument('--rebuild', dest='rebuild', action='store_true', help='rebuild the country data in IP Logs (not ready)')
arg_parser.add_argument('--update', dest='update', action='store_true', help='update the IP-Country map')
args = arg_parser.parse_args()

action_count = 0
if args.init:
    action_count += 1
    print('  action: INIT')
if args.rebuild:
    action_count += 1
    print('  action: REBUILD (not ready)')
if args.update:
    action_count += 1
    print('  action: UPDATE')
if action_count == 0:
    arg_parser.print_help()
    sys.exit()

#-----order of multiple operations: init, update, rebuild-----
if args.init:
    #-----run the DB init here-----
    settings.init_ip_country_db()
if args.update:
    update_ip_country_db()
if args.rebuild:
    rebuild_country_logs()

#-----close cursor and DB when done using them-----
db_ip_country.db_disconnect()

print("Done", flush=True)
