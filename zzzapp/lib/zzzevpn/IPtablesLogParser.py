#-----IPtables Log Parser-----
# All logs in one file:
#   /var/log/iptables/ipv4.log
# Separate logs for blocked packets and accepted packets
#   /var/log/iptables/ipv4-blocked.log - should be limited size unless an attack/scan is incoming
#   /var/log/iptables/ipv4-accepted.log - should be huge
#   /var/log/iptables/ipv6-blocked.log - future
#   /var/log/iptables/ipv6-accepted.log - future
#
# Rotate logs hourly to prevent disk filling.
# Limit the number of entries per minute to prevent disk I/O overload.
# Keep the 120 latest log files.
#   230 bytes/entry * 500 entries/sec * 60 sec/min * 120 minutes = 230*500*60*120 = 828MB max log size
#   115KB/sec, 6.9MB/min, 414MB/hr
#   500/sec * 60 sec/min = 30,000/min
# iptables rules to limit the number of packets per second written to disk.
# cron job to summarize raw logs into DB tables
# Web page reads DB summary table and displays it
# DB tables: iptables_ipv4, iptables_ipv6
#
# Options:
#   do not display iptables log IP's that are also found in the squid log
#   raw IP log view (last 10,000 entries?)
#
# NEW 11/8/2023:
#   sqlite upsert for efficiency in inserting/updating data
#   process entries in batches of 1000 (should be about 200-500KB of data)

#TEST - used for memory profiling, disable before going live
from memory_profiler import profile

import datetime
# import file_read_backwards
import json
import os
import pathlib
import re
import resource
import shutil
import sys
import time
import urllib.parse

#TEST
import pprint

#-----package with all the Zzz modules-----
import zzzevpn

class IPtablesLogParser:
    'IPtables Log Parser'
    
    #-----objects-----
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    ip_log_raw_data: zzzevpn.IpLogRawData = None
    logparser: zzzevpn.LogParser = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None
    
    #-----vars-----
    client_ips = []
    countries = {}
    db_ip_list = {} # data downloaded from the DB
    db_ip_list_gen_updates = {} # data downloaded from the DB - unique IP's for all relevant dates to make update params
    db_ip_list_by_last_updated = [] # data downloaded from the DB
    db_ip_list_by_num_packets = [] # data downloaded from the DB
    db_summary_ip_list = {} # summary data downloaded from the DB
    filepath = ''
    filepath_accepted = ''
    filepath_blocked = ''
    filepath_list = { 'all': [], 'accepted': [], 'blocked': [], }
    filepath_sizes = {}
    highlight_ips = False
    ip_country_map = []
    ip_user_map = []
    js_ip_list = '[]'
    last_setting_name = ''
    last_time_parsed = { 'all': '', 'accepted': '', 'blocked': '', } # hi-res times from logs, saved to DB zzz_system table
    lines_displayed = 0
    lines_in_logfile = 0
    lines_parsed = 0
    lines_to_analyze = 50000
    max_rows = 50000
    most_recent_rotated_log = None
    params_insert_list = []
    params_update_list = []
    parsed_logs = [] #TEST - list of logs parsed in the order they were parsed
    query_min_age = 0
    query_max_age = None
    rowcolor = ''
    rows_to_upsert = 0
    separator = '-'*80
    sort_by = 'date_ip' # last_updated, date_ip
    
    #-----sort results into different lists-----
    # DB flags: is_ipv4, is_cidr, is_private
    # ips_by_date[date][ip]['num_accepted'] = count
    # ips_by_date[date][ip]['num_blocked'] = count
    # ips_by_date[date][ip]['is_ipv4'] = 0/1
    # ips_by_date[date][ip]['is_cidr'] = 0/1
    # ips_by_date[date][ip]['is_private'] = 0/1
    # ips_by_date[date][ip]['last_updated'] = DATETIME
    # ips_by_date[date][ip]['country_code'] = text
    ips_by_date = {}
    #-----this has the same data as ips_by_date, but gets reset after each call to upsert_ip_log_db()-----
    upsert_ips_by_date = {}
    
    # ips_by_last_updated = [
    #     { 'ip'=ip, 'last_updated'=DATETIME, 'log_date'=date, etc... },
    #     { 'ip'=ip, 'last_updated'=DATETIME, 'log_date'=date, etc... },
    #     { 'ip'=ip, 'last_updated'=DATETIME, 'log_date'=date, etc... },
    #     ]
    ips_by_last_updated = []
    
    # cache data for HTML table rows - IP links, Country, Private
    #   ip: { 'ip_data': '', 'country_code': '', 'private': '', }
    html_cache = {}
    
    full_ip_list = {} # ip: count,
    public_ip_list = {} # ip: count,
    private_ip_list = {} # ip: count,
    protected_ip_list = {} # ip: count,
    mac_address_list = {} # MAC: count,
    
    #-----sort IPv6 results into different lists-----
    server_ip6_list = {} # ip: count,
    
    #-----regex patterns pre-compiled-----
    date_format_day = '%Y-%m-%d'
    date_regex_pattern = None
    #
    regex_complete_pattern = None
    ip_log_regex = None
    #
    msg_regex_pattern = None
    regex_filename_date_pattern = None
    
    #-----POST actions-----
    allowed_actions = ['ip_delete_old', 'ip_delete_all', 'ip_log_view', 'ip_log_parse_now', 'ip_log_last_parsed_time']
    return_page_header = True
    
    IPtablesLogParserHTML = {}
    service_name = 'iptables'
    
    #TEST
    TEST_num_printed = 0
    max_runtime = 0
    no_match_lines = []
    test_mode = False
    test_memory_usage = False
    test_dir = ''
    test_last_time_parsed = ''
    test_start_time = None
    test_max_seconds = 30

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
        if db is None:
            self.db = zzzevpn.DB(self.ConfigData)
            self.db.db_connect(self.ConfigData['DBFilePath']['Services'])
        else:
            self.db = db
        if util is None:
            self.util = zzzevpn.Util(self.ConfigData, self.db)
        else:
            self.util = util
        if settings is None:
            self.settings = zzzevpn.Settings(self.ConfigData, self.db, self.util)
        else:
            self.settings = settings
        if not self.settings.SettingsData:
            self.settings.get_settings()
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'IP Log', self.settings)
        self.logparser = zzzevpn.LogParser(self.ConfigData, self.db, self.util, self.settings)
        self.ip_log_raw_data = zzzevpn.IpLogRawData(self.ConfigData, self.db, self.util, self.settings)
        self.init_vars()

    #--------------------------------------------------------------------------------

    # tail -F /tmp/zzz-debug-iptables-log-parser.log
    def log_debug(self, description: str='', varlist: dict={}):
        if not description:
            return
        #-----only log if test mode is on-----
        if not (self.test_mode or self.test_memory_usage):
            return

        # print(resource.getrusage(resource.RUSAGE_SELF))
        debug_log_filepath = '/tmp/zzz-debug-iptables-log-parser.log'

        items_size = 0
        debug_details = []
        if varlist:
            for item_name in varlist.keys():
                items_size += sys.getsizeof(varlist[item_name])
                if isinstance(varlist[item_name], int):
                    debug_details.append(f'item_name: {varlist[item_name]} seconds runtime')
        debug_details_str = ''
        if debug_details:
            debug_details_str = '\n'.join(debug_details)

        date_now = self.util.current_datetime()
        items_size = self.util.add_commas(items_size)
        with open(debug_log_filepath, 'a') as write_file:
            write_file.write(f'{date_now}\n{description}\nsize={items_size}\n{debug_details_str}\n{self.separator}\n')

    #--------------------------------------------------------------------------------
    
    def init_vars(self):
        #-----init class vars-----
        self.client_ips = []
        self.countries = {}
        self.db_summary_ip_list = {}
        self.full_ip_list = {}
        self.highlight_ips = False
        self.html_cache = {}
        self.ip_country_map = []
        self.ip_user_map = []
        self.ips_by_date = {}
        self.ips_by_last_updated = []
        self.js_ip_list = '[]'
        self.last_setting_name = ''
        self.last_time_parsed = { 'all': '', 'accepted': '', 'blocked': '', }
        self.lines_displayed = 0
        self.lines_in_logfile = 0
        self.lines_parsed = 0
        self.mac_address_list = {}
        self.most_recent_rotated_log = None
        self.no_match_lines = []
        self.parsed_logs = []
        self.private_ip_list = {}
        self.protected_ip_list = {}
        self.public_ip_list = {}
        self.return_page_header = True
        self.server_ip6_list = {}
        self.upsert_ips_by_date = {}

        self.IPtablesLogParserHTML = {
            'CSP_NONCE': '',
            
            #-----load these on first page loading-----
            'load_max_age': '',
            'load_sort_by': '',
            'rows_in_db': '',
            'oldest_entry': '',
            'newest_entry': '',
            #-----end first loading-----
            
            'full_table_html': '',
            
            'summary_table_html': '',
            'summary_start_date': '',
            'summary_end_date': '',
            
            'ip_user_map': '',
            'js_ip_list': self.js_ip_list,
            
            'lines_displayed': str(self.lines_displayed),
            'lines_in_logfile': str(self.lines_in_logfile),
            'lines_to_analyze': str(self.lines_to_analyze),
            'show_last_time_parsed': 'N/A',
            'last_time_parsed_seconds': '0',
            
            'list_of_countries': '',
            'list_of_users': '',
            
            'server_ip': self.ConfigData['AppInfo']['IP'],
            'URL_Services': self.ConfigData['URL']['Services'],
            
            'selected_hour': '',
            'selected_six_hour': '',
            'selected_day': '',
            'selected_three_day': '',
            'selected_week': '',
            'selected_second_week': '',
            'selected_no_limit': '',
            
            'selected_sort_last_updated': '',
            'selected_sort_date_ip': '',
            'selected_sort_num_packets': '',
            
            #####TEST vars below here#####
            'TESTDATA': '',
            
            'last_time': '',
            'last_time_accepted': '',
            'last_time_blocked': '',
            
            'db_last_time_parsed': '',
            'db_ip_list': '',
            'db_ip_list_by_last_updated': '',
            
            'filepath_list': '',
            'parsed_logs': '',
            
            'protected_list_count': '0',
            'protected_ip_list': '',
            
            'private_list_count': '0',
            'private_ip_list': '',
            
            'public_list_count': '0',
            'public_ip_list': '',
            
            'list_count': '0',
            'full_ip_list': '',
            'ips_by_date': '',
            'ips_by_last_updated': '',
            
            'config_protected_ips': '',
        }
        
        #-----assemble IP log regex-----
        # 2020-02-16T00:16:01.844723 [93216.767428] zzz accepted IN=eth0 OUT= MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=172.30.0.2 DST=172.30.0.164 LEN=174 TOS=0x00 PREC=0x00 TTL=255 ID=10659 PROTO=UDP SPT=53 DPT=35500 LEN=154
        regex_date = r'(\d{4}\-\d{2}\-\d{2}T\d{2}\:\d{2}\:\d{2}\.\d{6})' # 2020-02-16T00:16:01.844723
        regex_timestamp = r'\[\s*\d+\.\d+\]' # [ 3216.767428]
        regex_app_prefix = r'zzz (accepted|blocked)'
        #-----assemble msg regex (end part of the IP log line)-----
        regex_interface_pattern = r'(|eth\d|lo|tun\d|{})'.format(self.ConfigData['PhysicalNetworkInterfaces']['internal'])
        regex_ip_pattern = r'([\d.]+)'
        regex_in_interface = r'IN={}'.format(regex_interface_pattern)
        # after "OUT", there may be nothing, or an empty MAC address, or a MAC address
        regex_out_interface = r'OUT={}(| MAC=| MAC=[\da-f:]+) SRC={} DST={} (.+?)'.format(regex_interface_pattern, regex_ip_pattern, regex_ip_pattern)
        self.regex_complete_pattern = r'^{} {} {} {} {}$'.format(regex_date, regex_timestamp, regex_app_prefix, regex_in_interface, regex_out_interface)
        self.ip_log_regex = re.compile(self.regex_complete_pattern, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        #-----break the date into pieces-----
        regex_date_pieces = r'^(\d{4})\-(\d{2})\-(\d{2})T(\d{2})\:(\d{2})\:(\d{2})\.(\d{6})$'
        self.date_regex_pattern = re.compile(regex_date_pieces, re.DOTALL)
        #-----get the timestamp from the filename-----
        regex_filename_date = r'/ipv4.log\-(\d+)'
        self.regex_filename_date_pattern = re.compile(regex_filename_date, re.DOTALL)

        #TEST
        # self.IPtablesLogParserHTML['sample_log_data'] = self.sample_log_data(230*100) + '\n'
        self.TEST_num_printed = 0
        #ENDTEST
    
    #--------------------------------------------------------------------------------
    
    #-----too many features to test with hardcoded tests, so build-in a test mode-----
    def set_test_mode(self, test_mode=False, test_dir=None, test_last_time_parsed='2022-02-01T06:14:00.000000', max_runtime: int=0):
        self.test_mode = test_mode
        if not self.test_mode:
            print('test mode OFF')
            return
        if test_dir:
            if max_runtime:
                self.max_runtime = max_runtime
            path = pathlib.Path(test_dir)
            if not path.is_dir():
                print(f'ERROR: {test_dir} is not a directory, TEST MODE SWITCHING OFF')
                self.test_mode = False
                return
            self.test_dir = test_dir
        self.test_last_time_parsed = test_last_time_parsed
        print('***TEST MODE ON***')
        print('  directory: ' + self.test_dir)
        print('  last_time_parsed: ' + self.test_last_time_parsed)
    
    #-----process POST data-----
    # WSGI entry point for POST requests
    def handle_post(self, environ, request_body_size):
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')
        
        self.init_vars()
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        action = raw_data.get('action', None)
        
        #-----return if missing data-----
        if action is None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        else:
            action = action[0]
        
        max_age = raw_data.get('max_age', None)
        if max_age is None:
            max_age = 'hour'
        else:
            max_age = max_age[0]
        sort_by = raw_data.get('sort_by', None)
        if sort_by is None:
            sort_by = 'last_updated'
        else:
            sort_by = sort_by[0]
        
        #-----highlighting is too slow, so it's off by default for now-----
        self.highlight_ips = False
        highlight_ips = raw_data.get('highlight_ips', None)
        if highlight_ips is not None:
            if highlight_ips[0]=='1':
                self.highlight_ips = True
        
        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
            'highlight_ips': self.highlight_ips,
            'max_age': max_age,
            'sort_by': sort_by,
        }
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')
        
        if not (action in self.allowed_actions):
            self.webpage.error_log(environ, 'allowed_actions: ' + ','.join(self.allowed_actions))
            return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')
        
        if action=='ip_log_view':
            self.return_page_header = False;
            self.process_ip_log_view(max_age, sort_by)
            # return only the body, not the entire HTML page
            return self.make_IPtablesLogParser(environ)
        elif action=='ip_delete_old':
            #-----queue the request-----
            status = self.db.insert_unique_service_request(self.service_name, 'delete_log_old')
            result_str = 'ERROR: pending request in queue, not adding another request to delete old IP logs'
            if status:
                result_str = 'Request to delete old IP logs has been queued'
                self.util.work_available(1)
            return self.util.make_html_display_safe(result_str)
        elif action=='ip_delete_all':
            #-----queue the request-----
            status = self.db.insert_unique_service_request(self.service_name, 'delete_log_all')
            result_str = 'ERROR: pending request in queue, not adding another request to delete ALL IP logs'
            if status:
                result_str = 'Request to delete ALL IP logs has been queued'
                self.util.work_available(1)
            return self.util.make_html_display_safe(result_str)
        elif action=='ip_log_parse_now':
            #-----queue the request-----
            status = self.db.insert_unique_service_request(self.service_name, 'parse_logs')
            result_str = 'ERROR: pending request in queue, not adding another request to parse IP logs'
            if status:
                result_str = 'Request to parse IP logs has been queued'
                self.util.work_available(1)
            return self.util.make_html_display_safe(result_str)
        elif action=='ip_log_last_parsed_time':
            return self.ajax_last_time_parsed();
        
        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')
    
    #--------------------------------------------------------------------------------

    def calc_last_time_parsed_seconds(self, last_time_parsed):
        last_time_parsed_seconds = '0'
        if last_time_parsed:
            last_time_parsed_date_obj = self.str_to_date(last_time_parsed)
            last_time_parsed_seconds = str(int(last_time_parsed_date_obj.timestamp()))
        return last_time_parsed_seconds
    
    def ajax_last_time_parsed(self):
        self.get_last_time_parsed()
        result = {
            'last_time_parsed': '',
            'last_time_parsed_seconds': '0',
            'status': 'error',
            'error_msg': 'ERROR',
        }
        if self.last_time_parsed['all']:
            result = {
                'last_time_parsed': self.parse_datetime_from_hires_datetime(self.last_time_parsed['all']),
                'last_time_parsed_seconds': self.calc_last_time_parsed_seconds(self.last_time_parsed['all']),
                'status': 'success',
                'error_msg': '',
            }
        return json.dumps(result)
    
    #--------------------------------------------------------------------------------
    
    #-----update fields used for HTML display-----
    # also store a param for searching by how old the DB entries are
    def process_ip_log_view(self, max_age='hour', sort_by='last_updated'):
        self.IPtablesLogParserHTML['selected_sort_last_updated'] = ''
        self.IPtablesLogParserHTML['selected_sort_date_ip'] = ''
        self.IPtablesLogParserHTML['selected_sort_num_packets'] = ''
        self.IPtablesLogParserHTML['selected_no_limit'] = ''
        self.IPtablesLogParserHTML['selected_hour'] = ''
        self.IPtablesLogParserHTML['selected_six_hour'] = ''
        self.IPtablesLogParserHTML['selected_day'] = ''
        self.IPtablesLogParserHTML['selected_three_day'] = ''
        self.IPtablesLogParserHTML['selected_week'] = ''
        self.IPtablesLogParserHTML['selected_second_week'] = ''
        
        if (not sort_by) or (sort_by not in ['last_updated', 'date_ip', 'num_packets']):
            sort_by = 'last_updated'
        
        self.sort_by = sort_by
        if self.sort_by=='last_updated':
            self.IPtablesLogParserHTML['selected_sort_last_updated'] = 'selected="selected"'
        elif self.sort_by=='date_ip':
            self.IPtablesLogParserHTML['selected_sort_date_ip'] = 'selected="selected"'
        elif self.sort_by=='num_packets':
            self.IPtablesLogParserHTML['selected_sort_num_packets'] = 'selected="selected"'
        
        if (not max_age) or (max_age not in ['no_limit', 'hour', 'six_hour', 'day', 'three_day', 'week', 'second_week']):
            max_age = 'hour'
        
        #-----store the max age in minutes-----
        self.query_min_age = 0
        self.query_max_age = None
        if max_age=='no_limit':
            self.IPtablesLogParserHTML['selected_no_limit'] = 'selected="selected"'
        elif max_age=='hour':
            self.query_max_age = 60
            self.IPtablesLogParserHTML['selected_hour'] = 'selected="selected"'
        elif max_age=='six_hour':
            self.query_max_age = 6*60
            self.IPtablesLogParserHTML['selected_six_hour'] = 'selected="selected"'
        elif max_age=='day':
            self.query_max_age = 24*60
            self.IPtablesLogParserHTML['selected_day'] = 'selected="selected"'
        elif max_age=='three_day':
            self.query_max_age = 3*24*60
            self.IPtablesLogParserHTML['selected_three_day'] = 'selected="selected"'
        elif max_age=='week':
            self.query_max_age = 7*24*60
            self.IPtablesLogParserHTML['selected_week'] = 'selected="selected"'
        elif max_age=='second_week':
            self.query_max_age = 14*24*60
            self.query_min_age = 7*24*60
            self.IPtablesLogParserHTML['selected_second_week'] = 'selected="selected"'
        
        self.IPtablesLogParserHTML['load_max_age'] = max_age
        self.IPtablesLogParserHTML['load_sort_by'] = sort_by
    
    #--------------------------------------------------------------------------------
    
    def load_db_info(self):
        rows_in_db, oldest_entry, newest_entry = self.db.get_table_date_info('ip_log_daily', 'log_date')
        self.IPtablesLogParserHTML['rows_in_db'] = self.util.add_commas(rows_in_db)
        self.IPtablesLogParserHTML['oldest_entry'] = oldest_entry
        self.IPtablesLogParserHTML['newest_entry'] = newest_entry

    #-----WSGI entry point for GET requests-----
    def make_webpage(self, environ, pagetitle):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        
        #-----init form vars to defaults-----
        self.process_ip_log_view()
        self.load_db_info()

        output = self.webpage.make_webpage(environ, self.make_IPtablesLogParser(environ))

        return output
    
    #--------------------------------------------------------------------------------

    #TODO: finish this
    #-----uses less memory than make_IPtablesLogParser(), safer for large datasets-----
    # load and process DB data in chunks
    def make_IPtablesLogParser_memory_safe(self, environ):
        #-----CSP nonce required for JS to run in browser-----
        self.IPtablesLogParserHTML['CSP_NONCE'] = environ['CSP_NONCE']

        #-----initial page load, just return the page header-----
        if self.return_page_header:
            body = self.webpage.load_template('IPtablesLogParser')
            return body.format(**self.IPtablesLogParserHTML)

        time_start = time.time()

    #--------------------------------------------------------------------------------

    def make_IPtablesLogParser(self, environ):
        #-----CSP nonce required for JS to run in browser-----
        self.IPtablesLogParserHTML['CSP_NONCE'] = environ['CSP_NONCE']
        
        #-----initial page load, just return the page header-----
        if self.return_page_header:
            body = self.webpage.load_template('IPtablesLogParser')
            return body.format(**self.IPtablesLogParserHTML)
        
        #TODO: live parsing is done by cron, not in apache
        #      maybe apache can parse the latest log only if the DB last_updated time is over 10 minutes ago
        # self.parse_latest_logs()
        
        time_start = time.time()
        self.test_start_time = time_start
        
        #-----get DB data, store it in vars for the HTML template-----
        time_get_ip_log_db = time.time()
        self.get_ip_log_db()
        runtime_get_ip_log_db = time.time() - time_get_ip_log_db

        #-----fill up the full_ip_list-----
        time_add_ip_to_list = time.time()
        self.full_ip_list = {}
        if self.db_ip_list:
            for log_date in self.db_ip_list.keys():
                for ip in self.db_ip_list[log_date].keys():
                    self.add_ip_to_list(ip)
        else:
            #-----empty DB? parse logs live instead-----
            self.parse_latest_logs(update_db=False, include_current_log=True, only_current_log=True)
        runtime_add_ip_to_list = time.time() - time_add_ip_to_list
        
        #TODO: needs a binary search tree
        # all IP's
        if self.full_ip_list:
            self.IPtablesLogParserHTML['list_count'] = str(len(self.full_ip_list.keys()))
            for ip in self.full_ip_list.keys():
                found_protected_ip = self.util.is_protected_ip(ip)
                if self.util.ip_util.is_public_ip(ip):
                    if not found_protected_ip:
                        self.public_ip_list[ip] = self.full_ip_list[ip]
                else:
                    self.private_ip_list[ip] = self.full_ip_list[ip]
                if found_protected_ip:
                    self.protected_ip_list[ip] = self.full_ip_list[ip]
        #
        # separate lists for groups of IP's
        if self.ConfigData['ProtectedIPs']:
            self.IPtablesLogParserHTML['config_protected_ips'] = pprint.pformat(self.ConfigData['ProtectedIPs'])
        if self.public_ip_list:
            self.IPtablesLogParserHTML['public_list_count'] = str(len(self.public_ip_list.keys()))
            self.IPtablesLogParserHTML['public_ip_list'] = pprint.pformat(self.public_ip_list)
        if self.private_ip_list:
            self.IPtablesLogParserHTML['private_list_count'] = str(len(self.private_ip_list.keys()))
            self.IPtablesLogParserHTML['private_ip_list'] = pprint.pformat(self.private_ip_list)
        if self.protected_ip_list:
            self.IPtablesLogParserHTML['protected_list_count'] = str(len(self.protected_ip_list.keys()))
            self.IPtablesLogParserHTML['protected_ip_list'] = pprint.pformat(self.protected_ip_list)
        if self.ips_by_date:
            self.IPtablesLogParserHTML['ips_by_date'] = pprint.pformat(self.ips_by_date)
        if self.db_ip_list:
            self.IPtablesLogParserHTML['db_ip_list'] = pprint.pformat(self.db_ip_list)
        if self.ips_by_last_updated:
            self.IPtablesLogParserHTML['ips_by_last_updated'] = pprint.pformat(self.ips_by_last_updated)
        if self.db_ip_list_by_last_updated:
            self.IPtablesLogParserHTML['db_ip_list_by_last_updated'] = pprint.pformat(self.db_ip_list_by_last_updated)
        # self.IPtablesLogParserHTML['full_ip_list'] = pprint.pformat(self.full_ip_list)
        #####ENDTEST#####
        
        #-----make HTML table rows-----
        time_process_parsed_data = time.time()
        num_html_rows = self.process_parsed_data()
        runtime_process_parsed_data = time.time() - time_process_parsed_data
        
        self.get_last_time_parsed()
        self.IPtablesLogParserHTML['db_last_time_parsed'] = self.last_time_parsed['all']
        self.IPtablesLogParserHTML['show_last_time_parsed'] = self.parse_datetime_from_hires_datetime(self.IPtablesLogParserHTML['db_last_time_parsed'])
        
        if self.last_time_parsed['all']:
            last_time_parsed_date_obj = self.str_to_date(self.last_time_parsed['all'])
            last_time_parsed_seconds = last_time_parsed_date_obj.timestamp()
            self.IPtablesLogParserHTML['last_time_parsed_seconds'] = str(int(last_time_parsed_seconds))
        
        #-----get country list-----
        self.IPtablesLogParserHTML['list_of_countries'] = self.logparser.make_country_input_tags(self.countries)
        self.IPtablesLogParserHTML['list_of_countries'] += '<input type="radio" name="limit_by_country" value="all" checked>All Countries'
        
        #-----get a list of unique IP's-----
        ip_list = self.full_ip_list.keys()
        # ip_list = sorted(set(ip_list))
        ip_list = self.util.unique_sort(ip_list)
        #-----encode the array to a JSON array so the JS can work with it-----
        self.js_ip_list = json.dumps(ip_list)
        
        self.IPtablesLogParserHTML['js_ip_list'] = self.js_ip_list
        
        #-----send a JSON back to the AJAX function-----
        data_to_send = {
            'logdata': self.IPtablesLogParserHTML['full_table_html'],
            'last_time_parsed': self.IPtablesLogParserHTML['show_last_time_parsed'],
            'last_time_parsed_seconds': self.IPtablesLogParserHTML['last_time_parsed_seconds'],
            'ip_list': ip_list,
            'list_of_countries': self.IPtablesLogParserHTML['list_of_countries'],
        }
        json_data_to_send = json.dumps(data_to_send)
        processing_time = round(time.time() - time_start, 3)
        data_size = round(len(json_data_to_send)/(1024*1024), 3)
        print(f'make_IPtablesLogParser() processed {num_html_rows} rows in {processing_time} seconds, {data_size} MB data sent')

        log_debug_data = {
            'IPtablesLogParserHTML': self.IPtablesLogParserHTML,
            'time_start': time_start,
            'runtime_get_ip_log_db': runtime_get_ip_log_db,
            'runtime_add_ip_to_list': runtime_add_ip_to_list,
            'runtime_process_parsed_data': runtime_process_parsed_data,
        }
        self.log_debug(f'before init_vars\n', log_debug_data)

        #-----flush memory so apache does not hold onto it-----
        self.init_vars()

        log_debug_data = {
            'IPtablesLogParserHTML': self.IPtablesLogParserHTML,
        }
        self.log_debug(f'after init_vars\n', log_debug_data)

        return json_data_to_send
    
    #--------------------------------------------------------------------------------
    
    # 2020-02-16T21:13:18.277354 --> 2020-02-16
    def parse_date_from_hires_datetime(self, datetime_str):
        # return datetime.datetime.strptime(date_str, self.date_format_day)
        # return datetime_obj.strftime(self.date_format_day)
        parts = datetime_str.split('T')
        return parts[0]
    
    def parse_datetime_from_hires_datetime(self, datetime_str: str=''):
        if not datetime_str:
            return ''
        parts = datetime_str.split('T')
        if len(parts)<2:
            return parts[0]
        show_date = parts[0]
        time_parts = parts[1].split('.')
        show_time = time_parts[0]
        return f'{show_date} {show_time}'
    
    # convert from DB str to hi-res datetime
    def str_to_date(self, date_str):
        return datetime.datetime.strptime(date_str, self.util.date_format_hi_res)
    
    # convert from hi-res datetime to DB str
    def date_to_str(self, datetime_obj):
        return datetime_obj.strftime(self.util.date_format_hi_res)
    
    #--------------------------------------------------------------------------------
    
    #-----consolidate all IP's into one unique list-----
    def add_ip_to_list(self, ip):
        if not ip:
            return
        found_ip = self.full_ip_list.get(ip, None)
        if found_ip:
            self.full_ip_list[ip] += 1
        else:
            self.full_ip_list[ip] = 1

    def add_ip_to_daily_array(self, log_date, ip, datetime_hires, entry_type):
        found_date = self.ips_by_date.get(log_date, None)
        if not found_date:
            #-----first entry of the day-----
            self.ips_by_date[log_date] = {}
        
        found_date_ip = self.ips_by_date[log_date].get(ip, None)
        if not found_date_ip:
            #-----first entry for this IP-----
            # DB flags: is_ipv4, is_cidr, is_private
            is_cidr = True
            if self.util.ip_util.is_ip(ip):
                is_cidr = False
            self.ips_by_date[log_date][ip] = {
                'num_accepted': 0,
                'num_blocked': 0,
                'is_ipv4': True, #TEST - detect IPv4 vs. IPv6 when IPv6 is implemented
                'is_private': not self.util.is_public(ip),
                'is_cidr': is_cidr, #TODO: remove this, it's useless?
                'last_updated': datetime_hires,
                'country_code': self.util.lookup_ip_country(ip),
            }
        
        self.ips_by_date[log_date][ip]['last_updated'] = datetime_hires
        if entry_type=='accepted':
            self.ips_by_date[log_date][ip]['num_accepted'] += 1
            #-----keep track of the last accepted time for testing-----
            if datetime_hires > self.last_time_parsed['accepted']:
                self.last_time_parsed['accepted'] = datetime_hires
                self.IPtablesLogParserHTML['last_time_accepted'] = datetime_hires
        elif entry_type=='blocked':
            self.ips_by_date[log_date][ip]['num_blocked'] += 1
            #-----keep track of the last blocked time for testing-----
            if datetime_hires > self.last_time_parsed['blocked']:
                self.last_time_parsed['blocked'] = datetime_hires
                self.IPtablesLogParserHTML['last_time_blocked'] = datetime_hires

    #TODO: upsert_ips_by_date
    def add_ip_to_daily_array_upsert(self, log_date, ip, datetime_hires, entry_type):
        found_date = self.upsert_ips_by_date.get(log_date, None)
        if not found_date:
            #-----first entry of the day-----
            self.upsert_ips_by_date[log_date] = {}
        
        found_date_ip = self.upsert_ips_by_date[log_date].get(ip, None)
        if not found_date_ip:
            #-----first entry for this IP-----
            # DB flags: is_ipv4, is_cidr, is_private
            is_cidr = True
            if self.util.ip_util.is_ip(ip):
                is_cidr = False
            self.upsert_ips_by_date[log_date][ip] = {
                'num_accepted': 0,
                'num_blocked': 0,
                'is_ipv4': True, #TEST - detect IPv4 vs. IPv6 when IPv6 is implemented
                'is_private': not self.util.is_public(ip),
                'is_cidr': is_cidr, #TODO: remove this, it's useless?
                'last_updated': datetime_hires,
                'country_code': self.util.lookup_ip_country(ip),
            }
        
        self.upsert_ips_by_date[log_date][ip]['last_updated'] = datetime_hires
        if entry_type=='accepted':
            self.upsert_ips_by_date[log_date][ip]['num_accepted'] += 1
            self.rows_to_upsert += 1
            #-----keep track of the last accepted time for testing-----
            if datetime_hires > self.last_time_parsed['accepted']:
                self.last_time_parsed['accepted'] = datetime_hires
                self.IPtablesLogParserHTML['last_time_accepted'] = datetime_hires
        elif entry_type=='blocked':
            self.upsert_ips_by_date[log_date][ip]['num_blocked'] += 1
            self.rows_to_upsert += 1
            #-----keep track of the last blocked time for testing-----
            if datetime_hires > self.last_time_parsed['blocked']:
                self.last_time_parsed['blocked'] = datetime_hires
                self.IPtablesLogParserHTML['last_time_blocked'] = datetime_hires

    #--------------------------------------------------------------------------------
    
    #-----store data from a parsed log entry in internal arrays-----
    def update_ip_arrays(self, entry):
        if not entry:
            return
        self.add_ip_to_list(entry['src'])
        self.add_ip_to_list(entry['dst'])
        
        #-----this is the only time that the datetime actually affects whether we use a given log entry or skip it-----
        # assumes that log entries are processed in order from oldest to newest
        # only process logs that are newer than the last line we processed
        if entry['datetime'] > self.last_time_parsed['all']:
            #TODO: set a boolean var that indicates start/stop
            self.last_time_parsed['all'] = entry['datetime']
            self.IPtablesLogParserHTML['last_time'] = entry['datetime']
            log_date = self.parse_date_from_hires_datetime(entry['datetime'])
            self.add_ip_to_daily_array(log_date, entry['dst'], entry['datetime'], entry['type'])
            self.add_ip_to_daily_array(log_date, entry['src'], entry['datetime'], entry['type'])
    
    #-----store data from a parsed log entry in internal arrays-----
    def update_ip_arrays_upsert(self, entry: dict):
        if not entry:
            return
        self.add_ip_to_list(entry['src'])
        self.add_ip_to_list(entry['dst'])
        
        #-----this is the only time that the datetime actually affects whether we use a given log entry or skip it-----
        # assumes that log entries are processed in order from oldest to newest
        # only process logs that are newer than the last line we processed
        if entry['datetime'] > self.last_time_parsed['all']:
            #TODO: set a boolean var that indicates start/stop
            self.last_time_parsed['all'] = entry['datetime']
            self.IPtablesLogParserHTML['last_time'] = entry['datetime']
            log_date = self.parse_date_from_hires_datetime(entry['datetime'])
            self.add_ip_to_daily_array_upsert(log_date, entry['dst'], entry['datetime'], entry['type'])
            self.add_ip_to_daily_array_upsert(log_date, entry['src'], entry['datetime'], entry['type'])
    
    #--------------------------------------------------------------------------------
    
    #-----parse one line of the logfile-----
    # OS uptime: 1 day,  1:20 --> 25:20 --> 91200 seconds
    # log timestamp: 91229.322382 - number of seconds since last reboot, accurate to 1 microsecond
    #
    # can have more than 5 digits in the brackets:
    #   2020-02-16T21:13:18.277354 [168654.215924] zzz accepted IN=eth0 OUT= MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=172.30.0.164 LEN=40 TOS=0x00 PREC=0x00 TTL=126 ID=61229 DF PROTO=TCP SPT=49411 DPT=22 WINDOW=1027 RES=0x00 ACK URGP=0
    #   uptime: 1 day, 22:50 --> 46:50 --> 168600 seconds
    # less than 5 digits get padded with spaces:
    #   uptime: 1 min --> 60 seconds
    #   2020-02-16T21:18:07.742982 [   79.681538] zzz accepted IN= OUT=eth0 SRC=172.30.0.164 DST=1.2.3.4 LEN=136 TOS=0x10 PREC=0x00 TTL=64 ID=10770 DF PROTO=TCP SPT=22 DPT=49433 WINDOW=471 RES=0x00 ACK PSH URGP=0 
    #
    # Before reboot:
    #   2020-02-16T21:16:10.166070 [168826.103059] zzz accepted IN= OUT=eth0 SRC=172.30.0.164 DST=1.2.3.4 LEN=40 TOS=0x08 PREC=0x00 TTL=64 ID=0 DF PROTO=TCP SPT=22 DPT=49406 WINDOW=473 RES=0x00 ACK URGP=0
    # After reboot: (time in brackets is padded with spaces)
    #   2020-02-16T21:17:01.996989 [    9.936822] zzz accepted IN= OUT=lo SRC=127.0.0.1 DST=127.0.0.1 LEN=72 TOS=0x00 PREC=0x00 TTL=64 ID=19821 DF PROTO=UDP SPT=54294 DPT=53 LEN=52 
    #
    # split on spaces?  regex?
    # optional packet flags (zero or more?)
    # everything after DPT at the end of the line is variable
    #
    ###################################################
    # Multiple Formats:
    #
    #
    ###################################################
    # EXAMPLES:
    #
    # IN/OUT entries: eth0, tunX (where X is 0-9)
    #   2020-02-16T00:16:01.844723 [93216.767428] zzz accepted IN=eth0 OUT= MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=172.30.0.2 DST=172.30.0.164 LEN=174 TOS=0x00 PREC=0x00 TTL=255 ID=10659 PROTO=UDP SPT=53 DPT=35500 LEN=154 
    #   2020-02-16T00:16:01.844725 [93216.767494] zzz accepted IN= OUT=eth0 SRC=172.30.0.164 DST=172.30.0.2 LEN=88 TOS=0x00 PREC=0x00 TTL=64 ID=65271 DF PROTO=UDP SPT=35500 DPT=53 LEN=68
    #
    #   2020-02-16T00:16:05.543887 [93220.469380] zzz accepted IN=tun3 OUT=eth0 MAC= SRC=10.6.0.6 DST=52.34.48.203 LEN=41 TOS=0x00 PREC=0x00 TTL=127 ID=28373 DF PROTO=TCP SPT=59249 DPT=443 WINDOW=1025 RES=0x00 ACK URGP=0 
    #   2020-02-16T00:16:05.544641 [93220.469827] zzz accepted IN=eth0 OUT=tun3 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=52.34.48.203 DST=10.6.0.6 LEN=52 TOS=0x00 PREC=0x00 TTL=253 ID=8036 DF PROTO=TCP SPT=443 DPT=59249 WINDOW=122 RES=0x00 ACK URGP=0
    #
    def parse_line(self, line):
        # TEST_OUTPUT = '--------------------------------------------------\nLINE: {}\n'.format(line)

        #TODO: replace this with self.ip_log_raw_data.ip_log_regex
        match = self.ip_log_regex.match(line)
        if not match:
            #TODO: log no-match lines for debugging?
            # TEST_OUTPUT += 'NO MATCH\n'
            self.no_match_lines.append(line)
            # return TEST_OUTPUT
            return False
        
        #-----regex groups-----
        # 1: datetime hires
        # 2: accepted/blocked
        # 3: IN
        # 4: OUT
        # 5: MAC
        # 6: SRC
        # 7: DST
        # 8: rest of msg
        entry = {
            'datetime': match.group(1),
            'type': match.group(2),
            'in': match.group(3),
            'out': match.group(4),
            'mac': match.group(5),
            'src': match.group(6),
            'dst': match.group(7),
            'msg': match.group(8),
        }
        self.update_ip_arrays(entry)
        
        #TEST
#         TEST_OUTPUT += '''datetime hires: {datetime}
# type: {type}
# IN: {in}
# OUT: {out}
# MAC: {mac}
# SRC: {src}
# DST: {dst}
# rest of msg: {msg}
# '''.format(**entry)
        # return TEST_OUTPUT
        return True

    #TODO: replace this with self.ip_log_raw_data.parse_line_upsert()
    # returns an entry dict created from parsed line data
    def parse_line_upsert(self, line: str) -> dict:
        #TODO: replace this with self.ip_log_raw_data.ip_log_regex
        match = self.ip_log_regex.match(line)
        if not match:
            #TODO: log no-match lines for debugging?
            self.no_match_lines.append(line)
            return None
        
        #-----regex groups-----
        # 1: datetime hires
        # 2: accepted/blocked
        # 3: IN
        # 4: OUT
        # 5: MAC
        # 6: SRC
        # 7: DST
        # 8: rest of msg
        entry = {
            'datetime': match.group(1),
            'type': match.group(2),
            'in': match.group(3),
            'out': match.group(4),
            'mac': match.group(5),
            'src': match.group(6),
            'dst': match.group(7),
            'msg': match.group(8),
        }
        return entry

    #--------------------------------------------------------------------------------
    
    #TODO: check a boolean var that indicates start/stop
    #      disable this function when going live
    #      apply a time limit to make sure the cron finishes in under 4 minutes?
    #      make the cron check for other running processes before starting?
    def should_stop_testing(self):
        #TEST - limit max lines parsed testing
        if self.test_mode:
            return self.lines_parsed > 100000
        return False
    
    #TODO: finish this
    #-----check the file date vs. the last time parsed-----
    def should_parse_file(self, filepath, include_current_log=False):
        # self.last_time_parsed['all']
        match = self.regex_filename_date_pattern.search(filepath)
        if not match:
            print(f'NO MATCH: {filepath}')
            if include_current_log and filepath.endswith('ipv4.log'):
                return True
            if not self.most_recent_rotated_log:
                return False
            #-----most recent log is over 10 minutes old?  OK to parse the latest log-----
            return False
        if self.should_stop_testing():
            return False
        if self.test_mode:
            return True

        filename_timestamp = match.group(1)
        date_str = self.util.timestamp_to_date_hires(filename_timestamp)
        if date_str>=self.last_time_parsed['all']:
            # print('filepath: {}, timestamp: "{}", date: "{}"'.format(filepath, filename_timestamp, date_str))
            # print('   should parse file')
            return True
        
        return False
    
    #-----parse a given iptables logfile-----
    #TEST - @profile is used for memory profiling, disable before going live
    # @profile
    def parse_ip_log(self, filepath: str, do_upsert: bool=False):
        print('parse_ip_log(): ' + filepath)
        current_file_lines_parsed = 0
        with open(filepath, 'r') as read_file:
            self.parsed_logs.append(filepath)
            for line in read_file:
                if self.should_stop_testing():
                    print('TEST - stopping after too many lines')
                    break
                parsed_data = False
                line = line.strip()
                if do_upsert:
                    # entry = self.parse_line_upsert(line)
                    entry = self.ip_log_raw_data.parse_line_complete(line)
                    if entry:
                        parsed_data = True
                        self.update_ip_arrays_upsert(entry)
                else:
                    parsed_data = self.parse_line(line)
                if not parsed_data:
                    continue
                current_file_lines_parsed += 1
            self.lines_parsed += current_file_lines_parsed
        print('  current file lines parsed: ' + str(current_file_lines_parsed))
        print('  total lines parsed: ' + str(self.lines_parsed))
        self.util.force_garbage_collection()

    #--------------------------------------------------------------------------------

    # NEW SELF VARS: rows_to_upsert(int), upsert_ips_by_date(dict)
    #TEST - @profile is used for memory profiling, disable before going live
    # @profile
    def parse_latest_logs_upsert(self, update_db=False, include_current_log=False, only_current_log=False):
        print('parse_latest_logs_upsert(): ', flush=True)
        self.ips_by_date = {}
        self.ips_by_last_updated = []

        self.get_logfiles(include_current_log, only_current_log)
        self.get_ip_user_map()
        self.get_last_time_parsed()
        self.IPtablesLogParserHTML['db_last_time_parsed'] = self.last_time_parsed['all']

        #-----parse from oldest to newest (should have been sorted in get_logfiles())-----
        # for filepath in sorted(self.filepath_list['all']):
        if not self.filepath_list['all']:
            print('ERROR: no files in filepath_list')
            return
        self.rows_to_upsert = 0
        for filepath in self.filepath_list['all']:
            if self.should_parse_file(filepath, include_current_log):
                self.parse_ip_log(filepath, do_upsert=True)
            #-----after each file, check if we have enough rows to do a DB update-----
            if self.rows_to_upsert >= 1000:
                if update_db:
                    self.upsert_ip_log_db()
                else:
                    self.rows_to_upsert = 0
                    self.upsert_ips_by_date = {}

        #-----finally, update to the latest time-----
        if update_db:
            #-----handle any remaining rows-----
            if self.rows_to_upsert:
                self.upsert_ip_log_db()
            #------update the time-----
            self.set_last_time_parsed()

        #TEST - remove before going live
        no_match_count = len(self.no_match_lines)
        if no_match_count:
            print('-'*80)
            print(f'no_match_count: {no_match_count}')
            # print(f'regex: {self.ip_log_regex.pattern}')
            print('first 10 failed matches:')
            print(self.no_match_lines[0:10])
            print('-'*80)
        #ENDTEST

    #-----handle accepted and blocked log entries-----
    # check the DB for the oldest log entry parsed
    # sample log entry: 2020-02-16T21:13:18.277354
    # can SQLite store hi-res time, or must it be stored as a string?
    # params:
    #   update_db - True if we want to write to the DB after parsing
    #   include_current_log - True if we want to parse ipv4.log, in addition to older log files
    #TEST - @profile is used for memory profiling, disable before going live
    # @profile
    def parse_latest_logs(self, update_db=False, include_current_log=False, only_current_log=False):
        print('parse_latest_logs(): ')
        self.ips_by_date = {}
        self.ips_by_last_updated = []
        
        self.get_logfiles(include_current_log, only_current_log)
        self.get_ip_user_map()
        self.get_last_time_parsed()
        self.IPtablesLogParserHTML['db_last_time_parsed'] = self.last_time_parsed['all']
        
        #-----parse from oldest to newest (should have been sorted in get_logfiles())-----
        # for filepath in sorted(self.filepath_list['all']):
        if not self.filepath_list['all']:
            print('ERROR: no files in filepath_list')
            return
        for filepath in self.filepath_list['all']:
            if self.should_parse_file(filepath, include_current_log):
                self.parse_ip_log(filepath)
        if update_db:
            self.set_last_time_parsed()
            self.update_ip_log_db()

    #TODO: finish this? not needed? parse_latest_logs() does everything?
    #-----handle accepted and blocked log entries-----
    # check the DB for the oldest log entry parsed
    # sample log entry: 2020-02-16T21:13:18.277354
    # can SQLite store hi-res time, or must it be stored as a string?
    def parse_all_logs(self, include_current_log=False):
        print('parse_all_logs(): ')
        self.get_logfiles(include_current_log)
        self.get_ip_user_map()
        #TODO: set last time parsed to 2000-01-01
        self.get_last_time_parsed()
        self.IPtablesLogParserHTML['db_last_time_parsed'] = self.last_time_parsed['all']
        if len(self.filepath_list['all'])>1:
            #TODO: look at the second-last entry on the list, not the second from the start
            self.most_recent_rotated_log = self.filepath_list['all'][1]
        else:
            self.most_recent_rotated_log = None
        #-----parse from oldest to newest (should have been sorted in get_logfiles())-----
        if not self.filepath_list['all']:
            print('ERROR: no files in filepath_list')
            return
        for filepath in self.filepath_list['all']:
            self.parse_ip_log(filepath)
            if self.should_stop_testing():
                break

        no_match_str = '\n'.join(self.no_match_lines)
        self.IPtablesLogParserHTML['TESTDATA'] = no_match_str[0:20000] + '\n\n'
        self.IPtablesLogParserHTML['parsed_logs'] = pprint.pformat(self.parsed_logs)

        self.set_last_time_parsed()
        self.update_ip_log_db()
    
    #--------------------------------------------------------------------------------
    
    #-----scan the log directory for logs-----
    # /var/log/iptables/ipv4.log
    # no longer used:
    #   /var/log/iptables/ipv4-accepted.log
    #   /var/log/iptables/ipv4-blocked.log
    def get_logfiles(self, include_current_log=False, only_current_log=False):
        '''returns the list of logfiles to process'''
        self.filepath = self.ConfigData['IPv4']['Log']['all']
        self.filepath_accepted = self.ConfigData['IPv4']['Log']['accepted']
        self.filepath_blocked = self.ConfigData['IPv4']['Log']['blocked']
        self.filepath_list['all'] = []
        self.filepath_list['accepted'] = []
        self.filepath_list['blocked'] = []
        self.filepath_sizes = {}
        
        #-----get IPv4 log files-----
        filepath_mtime_list = {}
        current_log_entry = None
        dir_to_scan = self.ConfigData['Directory']['IPtablesLog']
        if self.test_mode:
            dir_to_scan = self.test_dir
        
        #-----minimum of 1 file is expected: ipv4.log-----
        for entry in os.scandir(dir_to_scan):
            #-----skip empty files-----
            if (not entry.is_file()) or (entry.stat().st_size==0):
                continue
            if entry.path.endswith('ipv4.log'):
                current_log_entry = entry
            # file name format: ipv4.log-0000000000
            if only_current_log or not self.regex_filename_date_pattern.search(entry.path):
                continue
            filepath_mtime_list[entry.path] = str(entry.stat().st_mtime)
            self.filepath_sizes[entry.path] = str(entry.stat().st_size)
            self.filepath_list['all'].append(entry.path)
        
        #-----put the latest log at the end of the sorted list-----
        if self.filepath_list:
            self.filepath_list['all'] = sorted(self.filepath_list['all'])
        if current_log_entry and include_current_log:
            filepath_mtime_list[current_log_entry.path] = str(current_log_entry.stat().st_mtime)
            self.filepath_sizes[current_log_entry.path] = str(current_log_entry.stat().st_size)
            self.filepath_list['all'].append(current_log_entry.path)
        #TEST
        self.IPtablesLogParserHTML['filepath_list'] = pprint.pformat(self.filepath_list)
    
    def get_ip_user_map(self):
        pass
    
    #--------------------------------------------------------------------------------
    
    def make_date_ip_key(self, log_date, ip):
        return f'{log_date}-{ip}'

    ##############################
    #TODO: fix memory issues
    #      when the cron has not been run in a while, this can make excessive arrays
    #      execute the insert/update query whenever there are 10,000 items in the array
    #      this should make the cron faster and less memory intense when it has been
    #        stopped for awhile and lots of unprocessed data is in the log directory
    ##############################
    #-----merge DB data with parsed data-----
    # assumes that all relevant log file(s) have already been parsed into self.ips_by_date
    #
    # DB data:
    #   db_ip_list[log_date][ip] = { DATA }
    # parsed data:
    #   ips_by_date[log_date][ip] = { DATA }
    #   if the log_date and ip match an entry in db_ip_list:
    #     merge DB DATA with parsed DATA
    #     flag the entry for updating
    #     update rows in DB
    #   else:
    #     run DB inserts on the entry
    def make_db_param(self, row, parsed_data_only=False):
        #-----this param should contain parsed logfile data-----
        param_insert = (row['num_accepted'], row['num_blocked'], row['is_ipv4'], row['is_cidr'], row['is_private'], row['log_date'], row['last_updated'], row['country_code'], row['ip'])
        
        if parsed_data_only:
            self.params_insert_list.append(param_insert)
            return
        
        #-----check the complete list of log_date-IP pairs for duplicates-----
        entry = self.make_date_ip_key(row['log_date'], row['ip'])
        found_entry = self.db_ip_list_gen_updates.get(entry, None)
        if not found_entry:
            #------use the insert param-----
            self.params_insert_list.append(param_insert)
            return
        
        #-----new parsed data matches the loaded DB date-IP pair, add numbers and make an UPDATE param-----
        # using db_ip_list for the DB row data source here, not db_ip_list_gen_updates
        db_entry = self.db_ip_list[row['log_date']][row['ip']]
        num_accepted = row['num_accepted'] + db_entry['num_accepted']
        num_blocked = row['num_blocked'] + db_entry['num_blocked']
        #-----choose the newer datetime from row or db_entry-----
        last_updated = row['last_updated']
        if db_entry['last_updated'] > row['last_updated']:
            last_updated = db_entry['last_updated']
        param_update = (num_accepted, num_blocked, row['is_ipv4'], row['is_cidr'], row['is_private'], last_updated, row['log_date'], row['ip'])
        self.params_update_list.append(param_update)
    
    #-----go through parsed data and a DB param from each entry-----
    def make_db_all_params(self, parsed_data_only=False):
        if parsed_data_only:
            #TEST
            print('no DB data to merge, making INSERT params only')
        else:
            #TEST
            print('merging DB data with parsed data, making INSERT and/or UPDATE params')
        for log_date in self.ips_by_date.keys():
            for ip in self.ips_by_date[log_date].keys():
                row = self.ips_by_date[log_date][ip]
                row['log_date'] = log_date
                row['ip'] = ip
                self.make_db_param(row, parsed_data_only)
    
    #-----merge DB data with parsed data-----
    # if updating the DB, indicate whether DB params are needed
    # handle all possibilities when making DB params:
    #   empty DB:
    #     only make INSERT params using parsed data
    #   data in the DB:
    #     merge overlapping data, make UPDATE params
    #     make INSERT params for the rest
    def parse_db_data_into_array(self, rows_with_colnames, should_make_db_params=False):
        self.db_ip_list = {}
        self.db_ip_list_by_last_updated = []
        self.db_ip_list_by_num_packets = []
        if should_make_db_params:
            #-----clear the params lists-----
            self.params_insert_list = []
            self.params_update_list = []
            if not rows_with_colnames:
                #-----no DB data, just make INSERT statements-----
                print('No DB data, just making INSERT statements')
                self.make_db_all_params(parsed_data_only=True)
                return
        
        #-----stuff all the DB data into an array-----
        #TODO: sort_by in ['last_updated', 'date_ip', 'num_packets']
        # 
        for row in rows_with_colnames:
            db_array_entry = {
                'num_accepted': row['num_accepted'],
                'num_blocked': row['num_blocked'],
                'is_ipv4': row['is_ipv4'],
                'is_cidr': row['is_cidr'],
                'is_private': row['is_private'],
                'last_updated': row['last_updated'],
                'country_code': row['country_code'],
            }
            if not db_array_entry['country_code']:
                db_array_entry['country_code'] = 'UNKNOWN'
            log_date = self.parse_date_from_hires_datetime(row['last_updated'])
            found_date = self.db_ip_list.get(log_date, None)
            if found_date:
                #-----already have at least one entry for this date (different IP's), so add another IP entry-----
                self.db_ip_list[log_date][row['ip']] = db_array_entry
            else:
                #-----this is the first entry for this date, so make a new date-IP sub-array-----
                self.db_ip_list[log_date] = {
                    row['ip']: db_array_entry,
                }
            
            #TODO: make this more efficient
            #-----make an array sorted by last_updated-----
            if self.sort_by=='last_updated':
                db_array_entry['ip'] = row['ip']
                db_array_entry['log_date'] = log_date
                self.db_ip_list_by_last_updated.append(db_array_entry)
            elif self.sort_by=='num_packets':
                db_array_entry['ip'] = row['ip']
                db_array_entry['log_date'] = log_date
                self.db_ip_list_by_num_packets.append(db_array_entry)
        
        #-----make insert/update params from all log entries-----
        if should_make_db_params:
            self.make_db_all_params()
    
    #-----get all the relevant IP's for a set of dates-----
    # prevents duplicate inserts later
    def get_all_ips(self, log_dates_list=None):
        if not log_dates_list:
            return
        log_dates_sql = "','".join(log_dates_list)
        sql = f"select distinct log_date, ip from ip_log_daily where log_date in ('{log_dates_sql}')"
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)

        #-----make a searchable index "log_date-IP"-----
        self.db_ip_list_gen_updates = {}
        for row in rows_with_colnames:
            entry = self.make_date_ip_key(row['log_date'], row['ip'])
            found_entry = self.db_ip_list_gen_updates.get(entry, None)
            if not found_entry:
                self.db_ip_list_gen_updates[entry] = 1

        self.util.force_garbage_collection()
    
    #-----get IP log DB data - everything or just certain dates-----
    # log_dates_list is used to restrict the date range
    # should_make_db_params is used if params are needed to perform insert/update
    # row_limit is used to limit the number of rows
    #TEST - @profile is used for memory profiling, disable before going live
    # @profile
    def get_ip_log_db(self, log_dates_list=None, should_make_db_params=False, row_limit=0):
        print('get_ip_log_db() - START')
        
        #-----get everything by default-----
        sql_start = 'select * from ip_log_daily '
        params = ()
        
        if self.sort_by=='num_packets':
            sql_start = 'select ip, num_accepted, num_blocked, is_ipv4, is_cidr, is_private, log_date, last_updated, country_code, (num_accepted+num_blocked) as num_packets from ip_log_daily '
        
        #NOTE: no max age for some queries? still need a proper WHERE clause
        sql_last_updated = ''
        if self.query_max_age:
            # generate datetime string - max
            datetime_now = datetime.datetime.now()
            timedelta = datetime.timedelta(minutes=self.query_max_age)
            datetime_earlier = datetime_now - timedelta
            # generate datetime string - min
            timedelta = datetime.timedelta(minutes=self.query_min_age)
            datetime_later = datetime_now - timedelta
            # append to query
            sql_last_updated = ' last_updated>? and last_updated<?'
            params = (self.date_to_str(datetime_earlier), self.date_to_str(datetime_later))
        
        #TODO: deal with lists of excessive length, they will break SQL due to query length limits
        #-----assumes the date is a safe string, always formatted YYYY-MM-DD-----
        sql_where_log_dates = ''
        if log_dates_list:
            log_dates_sql = "','".join(log_dates_list)
            sql_where_log_dates = f" log_date in ('{log_dates_sql}') "
            #-----need to get this with the list of dates for making update params later-----
            self.get_all_ips(log_dates_list)
        
        #-----need a WHERE if either param is set-----
        add_where = ''
        if sql_last_updated or sql_where_log_dates:
            add_where = ' where '
        #-----need an AND if both params are set-----
        add_and = ''
        if sql_last_updated and sql_where_log_dates:
            add_and = ' and '
        
        # sort by date and IP
        sql_sort_by = ' order by log_date desc, ip'
        if self.sort_by=='last_updated':
            sql_sort_by = ' order by last_updated desc'
        elif self.sort_by=='num_packets':
            sql_sort_by = ' order by num_packets desc'

        # do not allow more than 100,000 rows to be processed
        sql_limit = f' limit {self.max_rows}'
        if self.util.is_int(row_limit) and row_limit>0:
            if row_limit > self.max_rows:
                row_limit=self.max_rows
            sql_limit = f' limit {row_limit}'

        #-----assemble query-----
        sql = sql_start + add_where + sql_last_updated + add_and + sql_where_log_dates + sql_sort_by + sql_limit
        
        #TEST
        print('get_ip_log_db() SQL:')
        print('  ' + sql)

        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)
        rowcount = len(rows_with_colnames)
        print(f'rowcount={rowcount}')

        #TEST
        log_debug_data = {
            'colnames': colnames,
            'rows': rows,
            'rows_with_colnames': rows_with_colnames,
        }
        self.log_debug(f'DB query\n', log_debug_data)

        self.parse_db_data_into_array(rows_with_colnames, should_make_db_params)
        print('get_ip_log_db() - END')
    
    #--------------------------------------------------------------------------------

    #TODO: implement sqlite upsert instead of separate insert/update?
    #      do inserts/updates 1000 rows at a time
    #-----IP logs for today-----
    # if today's logs exist:
    #   add the current stats to what's in the DB
    # else:
    #   insert current stats in new rows
    # ip_log_daily:
    #     ip text not null,
    #     num_accepted integer not null,
    #     num_blocked integer not null,
    #     is_ipv4 boolean not null,
    #     is_cidr boolean not null,
    #     is_private boolean not null,
    #     log_date integer not null,
    #     last_updated text not null,
    #     country_code text
    # ips_by_date[date][ip]['num_accepted'] = count
    # ips_by_date[date][ip]['num_blocked'] = count
    # ips_by_date[date][ip]['is_ipv4'] = 0/1
    # ips_by_date[date][ip]['is_cidr'] = 0/1
    # ips_by_date[date][ip]['is_private'] = 0/1
    # ips_by_date[date][ip]['last_updated'] = DATETIME
    # ips_by_date[date][ip]['country_code'] = text
    def update_ip_log_db(self):
        #-----get today's IP's from the DB, to determine if we're doing updates or inserts on each parsed IP-----
        log_dates_list = sorted(self.ips_by_date.keys())
        if not log_dates_list:
            #-----no data to update-----
            return
        
        log_dates_sql = "','".join(log_dates_list)
        print('log_dates_sql: ' + log_dates_sql)
        print('update_ip_log_db()')
        
        #-----get whatever's in the DB for the dates covered by current data-----
        self.get_ip_log_db(log_dates_list, should_make_db_params=True)
        
        #TODO: sort params into update/insert?  does this happen elsewhere?
        
        #-----go through all the IP's we found in logs, update/insert as needed-----
        # Do a single large transaction for efficiency.
        # NOTE: no country_code updates here
        sql_update = "update ip_log_daily set num_accepted=?, num_blocked=?, is_ipv4=?, is_cidr=?, is_private=?, last_updated=? where log_date=date(?) and ip=?"
        #TEST - print queries and params
        # print('TEST-sql_update: ' + sql_update)
        # print('TEST-params_update_list:')
        # pprint.pprint(self.params_update_list)
        #ENDTEST
        self.db.query_exec_many(sql_update, self.params_update_list)
        
        sql_insert = "insert into ip_log_daily (num_accepted, num_blocked, is_ipv4, is_cidr, is_private, log_date, last_updated, country_code, ip) values (?, ?, ?, ?, ?, date(?), ?, ?, ?)"
        #TEST - print queries and params
        # print('TEST-sql_insert: ' + sql_insert)
        # print('TEST-params_insert_list:')
        # pprint.pprint(self.params_insert_list)
        #ENDTEST
        self.db.query_exec_many(sql_insert, self.params_insert_list)

    #-----turn self.upsert_ips_by_date entries into array entries that can be used by query_exec_many()-----
    # combine/rewrite make_db_all_params() and make_db_param()
    def upsert_make_db_all_params(self):
        if not self.upsert_ips_by_date:
            return []

        params_upsert = []
        for log_date in self.upsert_ips_by_date.keys():
            for ip in self.upsert_ips_by_date[log_date].keys():
                row = self.upsert_ips_by_date[log_date][ip]
                row['log_date'] = log_date
                row['ip'] = ip
                #-----this params tuple should contain parsed logfile data-----
                params = (row['num_accepted'], row['num_blocked'], row['is_ipv4'], row['is_cidr'], row['is_private'], row['log_date'], row['last_updated'], row['country_code'], row['ip'])
                params_upsert.append(params)

        return params_upsert

    #-----upsert the DB and clear the arrays-----
    #TEST - @profile is used for memory profiling, disable before going live
    # @profile
    def upsert_ip_log_db(self):
        print(f'upsert_ip_log_db() - rows_to_upsert={self.rows_to_upsert}')

        params_upsert = self.upsert_make_db_all_params()

        sql = '''
        INSERT INTO ip_log_daily (num_accepted, num_blocked, is_ipv4, is_cidr, is_private, log_date, last_updated, country_code, ip) VALUES (?, ?, ?, ?, ?, date(?), ?, ?, ?)
        ON CONFLICT(ip, log_date) DO UPDATE SET
            num_accepted=num_accepted+excluded.num_accepted, num_blocked=num_blocked+excluded.num_blocked, is_ipv4=excluded.is_ipv4, is_cidr=excluded.is_cidr, is_private=excluded.is_private, last_updated=excluded.last_updated
        '''
        # WHERE log_date=date(?) and ip=?

        #TODO: check the response from the DB call
        success = self.db.query_exec_many(sql, params_upsert)
        if not success:
            print('    ERROR updating DB')

        #-----reset the row count and clear the rows array-----
        self.rows_to_upsert = 0
        self.upsert_ips_by_date = {}
        params_upsert = []

        self.util.force_garbage_collection()

    #--------------------------------------------------------------------------------
    
    # ip_log_summary:
    #     ip text not null,
    #     num_accepted integer not null,
    #     num_blocked integer not null,
    #     is_ipv4 boolean not null,
    #     is_cidr boolean not null,
    #     is_private boolean not null,
    #     last_updated text not null,
    #     country_code text
    def update_ip_log_db_summary(self):
        sql = ''
        params = ()
    
    def get_ip_log_db_summary(self):
        sql = ''
        params = ()
    
    #--------------------------------------------------------------------------------
    
    #TODO: rebuild the summary table afterwards? make sure this doesn't conflict with the daily cron
    #-----delete entries from ip-log-----
    # self.delete_ip_log_db(delete_all=True)
    # self.delete_ip_log_db(entries_older_than=30)
    # self.delete_ip_log_db_summary()
    def delete_ip_log_db(self, delete_all=False, entries_older_than=30):
        if delete_all:
            sql = 'delete from ip_log_daily'
            params = ()
            self.db.query_exec(sql, params)
            return
        
        if not self.util.is_int(entries_older_than):
            return
        if entries_older_than<0:
            return
        sql = 'delete from ip_log_daily where (julianday() - julianday(log_date)) > ?'
        params = (entries_older_than,)
        self.db.query_exec(sql, params)
    
    def delete_ip_log_db_summary(self):
        sql = 'delete from ip_log_summary'
        params = ()
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    def init_db(self):
        #-----clear DB-----
        self.delete_ip_log_db(delete_all=True)
        self.delete_ip_log_db_summary()
        #-----reset the last time parsed-----
        self.last_time_parsed['all'] = '2020-01-01T00:00:00.000000'
        self.set_last_time_parsed()
        #TEST - cron can do this?
        #-----parse available logs-----
        # self.parse_latest_logs(update_db=True)
        # self.rebuild_summary_table()

    #--------------------------------------------------------------------------------

    def save_ip_logfile(self, filename: str) -> bool:
        print(f'save_ip_logfile(): filename={filename}')

        if not self.util.is_running_as_root():
            print(f'ERROR: save_ip_logfile() not running as root')
            return False

        if not self.util.standalone.is_valid_ip_log_filename(filename):
            print(f'''ERROR: save_ip_logfile() filename invalid: {filename}''')
            return False

        src_filepath = f'''{self.ConfigData['Directory']['IPtablesLog']}/{filename}'''
        dst_filepath = f'''{self.ConfigData['Directory']['IPtablesSavedLog']}/{filename}'''
        if not os.path.exists(src_filepath):
            print(f'ERROR: save_ip_logfile() logfile not found: {src_filepath}')
            return False

        try:
            shutil.copy2(src_filepath, dst_filepath)
        except Exception as e:
            print(f'ERROR: save_ip_logfile() failed copying file: {e}')
            return False

        return True

    #--------------------------------------------------------------------------------

    def delete_ip_logfile(self, filename: str) -> bool:
        print(f'delete_ip_logfile(): filename={filename}')

        if not self.util.is_running_as_root():
            print(f'ERROR: delete_ip_logfile() not running as root')
            return False
        if not self.util.standalone.is_valid_ip_log_filename(filename):
            print(f'''ERROR: delete_ip_logfile() filename invalid: {filename}''')
            return False

        filepath = f'''{self.ConfigData['Directory']['IPtablesSavedLog']}/{filename}'''
        if not os.path.exists(filepath):
            print(f'ERROR: delete_ip_logfile() logfile not found: {filepath}')
            return False
        try:
            os.remove(filepath)
        except Exception as e:
            print(f'ERROR: delete_ip_logfile() failed deleting file: {e}')
            return False

        return True

    #-----delete all files in the saved log directory-----
    def delete_all_ip_logfiles(self) -> bool:
        if not self.util.is_running_as_root():
            print(f'ERROR: save_ip_logfile() not running as root')
            return False

        self.ip_log_raw_data.get_saved_logfiles()
        files_deleted = 0
        files_failed = 0
        for filepath in self.ip_log_raw_data.saved_log_filepath_list:
            try:
                os.remove(filepath)
                files_deleted += 1
            except:
                files_failed += 1
        print(f'delete_all_ip_logfiles(): files_deleted={files_deleted}, files_failed={files_failed}')

        return True

    #--------------------------------------------------------------------------------

    # ip_log_last_time_parsed="2020-02-16T21:16:10.166070"
    # system table: zzz_system(version, json, last_updated, ip_log_last_time_parsed)
    def get_last_time_parsed(self):
        '''used to prevent double-counting of log entries, in case the same files are processed more than once'''
        if self.test_mode:
            self.last_time_parsed['all'] = self.test_last_time_parsed
            return
        sql = 'select ip_log_last_time_parsed from zzz_system'
        params = ()
        row = self.db.select(sql, params)
        self.last_time_parsed['all'] = ''
        if not row:
            return
        if row[0]:
            self.last_time_parsed['all'] = row[0]
    
    #-----save to system table-----
    def set_last_time_parsed(self):
        sql = 'update zzz_system set ip_log_last_time_parsed=?'
        params = (self.last_time_parsed['all'],)
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    def format_header_html(self):
        html = '''
<tr>
<th>Date</th>
<th>IP</th>
<th>Country</th>
<th class="do_not_wrap_text">Reverse DNS<br>
    <div id='rdns_load_all'><a class='clickable reverse_dns_load_batch'>(Load ALL)</a></div></th>
<th>Private?</th>
<th>Last Updated</th>
<th>Accepted</th>
<th>Blocked</th>
</tr>
        '''
        return html
    
    #--------------------------------------------------------------------------------
    
    #TODO: needs a binary search tree
    #TODO: cache data - IP links, Country, Private
    def format_row_html(self, date_str, ip, row_data):
        if not row_data:
            return ''
        
        class_rdns = ' rdns_' + ip.replace('.', '_')
        
        # 2020-07-28T05:39:48.769583 --> 2020-07-28 05:39:48
        show_last_updated = ''
        matches = self.date_regex_pattern.match(row_data['last_updated'])
        if matches:
            show_last_updated = f'{matches[1]}-{matches[2]}-{matches[3]} {matches[4]}:{matches[5]}:{matches[6]}'

        ip_data = None
        country_code = None
        cached_html_data = self.html_cache.get(ip, None)
        if cached_html_data:
            ip_data = cached_html_data['ip_data']
            country_code = cached_html_data['country_code']
        else:
            #TODO: needs a binary search tree
            ip_data = self.logparser.make_ip_analysis_links(ip, self.highlight_ips)
            # country_code = self.util.lookup_ip_country(ip)
            country_code = row_data['country_code']
            self.html_cache['ip'] = { 'ip_data': ip_data, 'country_code': country_code, }
        
        class_country = ' country_' + country_code
        
        #-----update the list of countries-----
        if not self.countries.get(country_code, None):
            self.countries[country_code] = 1
        
        show_private = ''
        private_ip = ''
        # show_country = self.ConfigData['OfficialCountries'].get(country_code, 'UNKNOWN')
        show_country = self.logparser.country_highlight(country_code)
        if self.util.is_special_ip(ip=ip):
            # show_private = 'PRIVATE'
            show_private = self.util.ip_util.lookup_reserved_subnet(ip)
            show_country = 'N/A'
            private_ip = ' private_ip'
        
        if self.rowcolor == '':
            self.rowcolor = ' gray-bg'
        else:
            self.rowcolor = ''
        self.lines_displayed += 1
        
        #-----accepted class is only applied if there are zero blocked entries-----
        accepted = ''
        if row_data['num_blocked']==0:
            accepted = ' accepted'

        # for running demos without exposing the real client IPs or other things that should be hidden
        if ip in self.ConfigData['HideIPs']:
            return ''

        #-----pack the TR with classes needed to show/hide different data types-----
        html_data = {
            'accepted': accepted,
            'class_country': class_country,
            'class_rdns': class_rdns,
            'country': show_country,
            'ctr': str(self.lines_displayed),
            'date': date_str,
            'highlight_ip': ip_data['highlight_ip'],
            'ip': ip,
            'ip_analysis_links': ip_data['ip_analysis_links'],
            'is_private': show_private,
            'last_updated': show_last_updated,
            'num_accepted': row_data['num_accepted'],
            'num_blocked': row_data['num_blocked'],
            'private_ip': private_ip,
            'rowcolor': self.rowcolor,
        }
        
        html = '''
<tr id='row_{ctr}' class='{rowcolor}{class_country}{private_ip}{accepted}'>
<td>{date}</td>
<td>{highlight_ip} {ip_analysis_links}</td>
<td>{country}</td>
<!--blank space to fill-in with reverse-DNS data-->
<td class='{class_rdns}'></td>
<td>{is_private}</td>
<td>{last_updated}</td>
<td>{num_accepted}</td>
<td>{num_blocked}</td>
</tr>
        '''
        return html.format(**html_data)
    
    #--------------------------------------------------------------------------------
    
    # allow 1 extra row for the table header
    def reached_row_limit(self, num_rows):
        if num_rows>self.ConfigData['LogParserRowLimit']:
            return True
        return False
    
    #TODO: needs a binary search tree (24hrs of data takes 8.5 sec to process)
    #-----process data arrays into HTML-formatted data-----
    # 'is_private': False,
    # 'last_updated': '2020-07-27T20:14:39.389575',
    # 'num_accepted': 4,
    # 'num_blocked': 0
    def process_parsed_data(self):
        table_rows = [self.format_header_html()]
        
        if self.sort_by=='date_ip' and self.ips_by_date:
            for date_str in sorted(self.ips_by_date, reverse=True):
                for ip in sorted(self.ips_by_date[date_str]):
                    # self.IPtablesLogParserHTML['full_table_html'] += self.format_row_html(date_str, ip, self.ips_by_date[date_str][ip])
                    table_rows.append(self.format_row_html(date_str, ip, self.ips_by_date[date_str][ip]))
                    if self.reached_row_limit(len(table_rows)):
                        break
                if self.reached_row_limit(len(table_rows)):
                    print(f'reached row limit')
                    break
            self.IPtablesLogParserHTML['full_table_html'] = ''.join(table_rows)
            return len(table_rows)
        
        if self.sort_by=='num_packets' and self.db_ip_list_by_num_packets:
            #-----no sorting here, assume it was sorted by the DB select query-----
            for date_str in self.db_ip_list_by_num_packets:
                # self.IPtablesLogParserHTML['full_table_html'] += self.format_row_html(date_str['log_date'], date_str['ip'], date_str)
                table_rows.append(self.format_row_html(date_str['log_date'], date_str['ip'], date_str))
                if self.reached_row_limit(len(table_rows)):
                    print(f'reached row limit')
                    break
            self.IPtablesLogParserHTML['full_table_html'] = ''.join(table_rows)
            return len(table_rows)
        
        if self.sort_by=='last_updated' and self.db_ip_list_by_last_updated:
            #-----no sorting here, assume it was sorted by the DB select query-----
            for date_str in self.db_ip_list_by_last_updated:
                table_rows.append(self.format_row_html(date_str['log_date'], date_str['ip'], date_str))
                if self.reached_row_limit(len(table_rows)):
                    print(f'reached row limit')
                    break
            self.IPtablesLogParserHTML['full_table_html'] = ''.join(table_rows)
            return len(table_rows)
        
        # default (never used?)
        if self.db_ip_list:
            for date_str in sorted(self.db_ip_list, reverse=True):
                for ip in sorted(self.db_ip_list[date_str]):
                    # self.IPtablesLogParserHTML['full_table_html'] += self.format_row_html(date_str, ip, self.db_ip_list[date_str][ip])
                    table_rows.append(self.format_row_html(date_str, ip, self.db_ip_list[date_str][ip]))
                    if self.reached_row_limit(len(table_rows)):
                        break
                if self.reached_row_limit(len(table_rows)):
                    print(f'reached row limit')
                    break
            self.IPtablesLogParserHTML['full_table_html'] = ''.join(table_rows)
            return len(table_rows)
        
        self.IPtablesLogParserHTML['full_table_html'] = '<tr><td>Empty log</td></tr>'
        return 0
    
    #--------------------------------------------------------------------------------
    
    #-----CRON-ONLY - rebuild data in the summary table after updating the daily table-----
    # CREATE TABLE ip_log_summary(
    #     ip text not null,
    #     num_accepted integer not null,
    #     num_blocked integer not null,
    #     is_ipv4 boolean not null,
    #     is_cidr boolean not null,
    #     is_private boolean not null,
    #     last_updated text not null
    # );
    # CREATE INDEX ip_log_summary_ip_idx on ip_log_summary(ip);
    # CREATE INDEX ip_log_summary_updated_idx on ip_log_summary(last_updated);
    # CREATE TABLE ip_log_daily(
    #     ip text not null,
    #     num_accepted integer not null,
    #     num_blocked integer not null,
    #     is_ipv4 boolean not null,
    #     is_cidr boolean not null,
    #     is_private boolean not null,
    #     log_date integer not null,
    #     last_updated text not null
    # );
    # CREATE INDEX ip_log_daily_ip_idx on ip_log_daily(ip);
    # CREATE INDEX ip_log_daily_log_date_idx on ip_log_daily(log_date);
    # CREATE INDEX ip_log_daily_updated_idx on ip_log_daily(last_updated);
    def rebuild_summary_table(self):
        #-----process all the days that we updated (usually one or two)-----
        # replace summary data with new data
        # no need to delete any rows, only add or update
        pass
    
    #--------------------------------------------------------------------------------
    
    #TODO: also update ip_log_summary when the table starts getting used
    #-----update missing country codes in log tables-----
    def update_country_codes(self):
        return self.logparser.update_country_codes('ip_log_daily')

    #--------------------------------------------------------------------------------
    
    # SAMPLE LOG DATA
    def sample_log_data(self, num_bytes=None):
        log_data = ''
        filepath = '/home/ubuntu/test/TEST-iptables.log'
        with open(filepath, 'r') as read_file:
            if num_bytes:
                log_data = read_file.read(num_bytes)
            else:
                log_data = read_file.read()
        return log_data
    
    #--------------------------------------------------------------------------------
