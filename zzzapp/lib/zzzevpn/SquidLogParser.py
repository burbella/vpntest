#-----Squid Log Parser-----

import datetime
import file_read_backwards
import os
import pytz
import re
import socket

#TEST
import pprint

#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.LogParser

class SquidLogParser:
    'Squid Log Parser'
    
    #-----objects-----
    ConfigData: dict = None
    db: zzzevpn.DB = None
    dns_service: zzzevpn.DNSservice = None
    logparser: zzzevpn.LogParser = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    
    #-----vars-----
    client_ips = []
    countries = {}
    date_format = '%Y-%m-%d %H:%M:%S'
    db_ip_list = {} # data downloaded from the DB
    environ = { 'CSP_NONCE': '', }
    filepath = ''
    filepath_list = []
    filepath_sizes = {}
    filesize_limit = 10*1024*1024 # 10 MB max file size to parse?
    ip_country_map = []
    ip_user_map = []
    last_setting_name = ''
    last_time_parsed = ''
    lines_displayed = 0
    lines_in_logfile = 0
    lines_to_analyze = 1000
    rowcolor = ''
    js_ip_list = '[]'
    server_ip_list = []
    squid_data = []
    unique_domains = []
    
    #-----regex patterns pre-compiled-----
    server_ip_regex_pattern = r'^([\d\.]+)(|\:80|\:443)$'
    server_ip_regex = re.compile(server_ip_regex_pattern, re.IGNORECASE)
    microseconds_regex_pattern = r'^(.+?\.\d{3})\d{3}$'
    microseconds_regex = re.compile(microseconds_regex_pattern)
    
    # Native log format squid %ts.%03tu %6tr %>a %Ss/%03>Hs %<st %rm %ru %un %Sh/%<A %mt
    native_format_regex1_pattern = r'^(\d+\.\d{3})\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)'
    ssl_custom_format_regex_pattern = r'^(\d+\.\d{3})\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)'
    ssl_custom_format_regex = re.compile(ssl_custom_format_regex_pattern, re.IGNORECASE)
    
    all_parsed_data = []
    cached_rdns = False
    skip_rdns = False
    service_name = 'squid'
    return_page_header = True
    
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
        self.logparser = zzzevpn.LogParser(self.ConfigData, self.db, self.util, self.settings)
        self.dns_service = zzzevpn.DNSservice()
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        self.return_page_header = True
        
        #-----clear internal vars for a fresh list processing-----
        self.client_ips = []
        self.countries = {}
        self.filepath = self.ConfigData['Directory']['SquidAccess'] + '/access.log'
        self.filepath_list = []
        self.filepath_sizes = {}
        self.ip_country_map = []
        self.js_ip_list = '[]'
        self.last_setting_name = ''
        self.lines_displayed = 0
        self.lines_in_logfile = 0
        self.rowcolor = ''
        self.server_ip_list = []
        self.squid_data = []
        self.unique_domains = []
        
        self.all_parsed_data = []
    
    #--------------------------------------------------------------------------------

    def use_cached_rdns(self, value: bool=None):
        if (value is None):
            return self.cached_rdns
        else:
            self.cached_rdns = value
    
    def should_skip_rdns(self, value: bool=None):
        if (value is None):
            return self.skip_rdns
        else:
            self.skip_rdns = value

    #--------------------------------------------------------------------------------

    #-----make sure a string is a valid int-----
    def process_lines_to_analyze(self, value):
        if value is None:
            return
        
        #-----more than 999,999 lines will probably crash any browser (so will over 50,000 for that matter)-----
        match = re.match(r'^\d{1,6}$', value, re.DOTALL | re.MULTILINE)
        if not match:
            #-----no match, use default value-----
            self.lines_to_analyze = 1000
        
        #-----keep it within configured limits or reset to default value-----
        self.lines_to_analyze = int(value)
        if self.lines_to_analyze==0:
            self.lines_to_analyze = 1000
        if self.lines_to_analyze>self.ConfigData['LogParserRowLimit']:
            self.lines_to_analyze = self.ConfigData['LogParserRowLimit']
    
    #--------------------------------------------------------------------------------
    
    def parse_line(self, line):
        match = self.ssl_custom_format_regex.match(line)
        if not match:
            return
        
        parsed_data = []
        
        ##############################
        # Fields:
        # time elapsed remotehost code/status bytes method URL rfc931 peerstatus/peerhost type ssl_domain
        #
        # non-SSL examples:
        # 1652874338.265    291 10.7.0.4 TCP_MISS/200 8610 GET http://www.squid-cache.org/ - ORIGINAL_DST/67.215.9.148 text/html -
        # 1652753787.275     66 10.7.0.4 TCP_MISS/304 344 GET http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab? - ORIGINAL_DST/23.44.205.219 application/vnd.ms-cab-compressed -
        #
        # SSL example:
        # 1652746492.787  72855 10.7.0.4 TCP_TUNNEL/200 4919 CONNECT 142.251.33.110:443 - ORIGINAL_DST/142.251.33.110 - apis.google.com
        #
        # type is often "-" for SSL
        # rfc931 is often "-"
        # ssl_domain is "-" for non-SSL
        ##############################
        code_status = match[4].split('/')
        peer_status_host = match[9].split('/')
        server_ip = peer_status_host[1]
        url = match[7]
        
        #-----get the server IP from the URL param if peerhost is empty-----
        # 191.232.80.53:443
        if server_ip == '-' or server_ip == '- ':
            #TODO: fix this, it may not parse properly all the time
            host = self.util.get_host_from_url(url)
            match_url = self.server_ip_regex.search(url)
            if match_url:
                # URL param is just an IP
                server_ip = match_url[1]
            elif len(host)>2:
                # server ip: -
                # code: TCP_MEM_HIT
                # extract IP from domain in URL:
                try:
                    server_ip = socket.gethostbyname(host)
                except socket.gaierror as e:
                    server_ip = ''
                    print('ERROR: socket.gethostbyname({})'.format(host))
                    print('  code {}: {}'.format(e.args[0], e.args[1]), flush=True)
        
        pos = server_ip.find('-')
        if pos == -1:
            # do nothing
            pass
        else:
            #TEST - debug non-existent IP's in logs, usually due to a terminated connection
            # error_log('Server IP: ' . $server_ip);
            # error_log($line);
            pass
        
        parsed_data = {
            'time': match[1],
            'elapsed': abs(int(match[2])),
            'client_ip': match[3],
            #'code_status': match[4],
            'code': code_status[0],
            'status': code_status[1],
            'bytes': match[5],
            'method': match[6],
            'URL': url,
            'rfc931': match[8],
            #'peerstatus_peerhost': match[9],
            'peerstatus': peer_status_host[0],
            'peerhost': server_ip, #server ip
            'type': match[10],
            'ssl_domain': match[11],
        }
        
        #-----update the list of users-----
        if not parsed_data['client_ip'] in self.client_ips:
            self.client_ips.append(parsed_data['client_ip'])
        
        return parsed_data
    
    #--------------------------------------------------------------------------------
    
    def parse_squid_log(self, filepath, update_db=False):
        print('parse_squid_log(): ' + filepath)
        
        #-----check if file exists, is readable-----
        if not self.util.file_is_accessible(filepath):
            print(f'  File: {filepath}')
            print('  ERROR: file not accessible')
            return ''
        
        #TEST
        print(f'filepath={filepath}')
        #ENDTEST
        
        #-----read in the file from the bottom, pass to line parser-----
        stopped_parsing_early = False
        file_reader = file_read_backwards.FileReadBackwards(filepath, encoding="ascii")
        with file_reader as frb:
            parsed_data = None
            for line in frb:
                #-----stop when we get to the requested limit-----
                # ignore this limit for DB updates, it is only for browser live parsing
                if not update_db:
                    if self.lines_in_logfile >= self.lines_to_analyze:
                        stopped_parsing_early = True
                        break

                #-----stop when the DB latest log_date is reached-----
                # with the current test, this may skip multiple entries that occur in the same millisecond if they are not parsed in the same parsing session (very uncommon?)
                parsed_data = self.parse_line(line)
                if not parsed_data:
                    continue
                date_str = self.util.timestamp_to_date_hires(parsed_data['time'])
                if self.last_time_parsed>=date_str:
                    stopped_parsing_early = True
                    break

                #-----store the parsed data in a list-----
                # put this after the date_str test to prevent duplication of the last log file line
                self.all_parsed_data.append(parsed_data)
                self.lines_in_logfile += 1
        return stopped_parsing_early
    
    #--------------------------------------------------------------------------------
    
    #-----scan the log directory for logs-----
    # a minimum of 2 files are expected: access.log, access-icap.log
    # /var/log/squid_access/
    # file name format: access.log.1, access-icap.log.1
    def get_logfiles(self):
        #-----scan for the next oldest log-----
        filepath_mtime_list = {}
        for entry in os.scandir(self.ConfigData['Directory']['SquidAccess']):
            #-----skip empty files-----
            if entry.is_file() and entry.stat().st_size>0:
                filepath_mtime_list[entry.path] = str(entry.stat().st_mtime)
                self.filepath_sizes[entry.path] = str(entry.stat().st_size)
        
        if not filepath_mtime_list:
            # print('ERROR: no logfiles found')
            return
        
        filepath_mtime_tuples = self.util.sort_array_by_values(filepath_mtime_list, reverse_sort=True)
        for entry in filepath_mtime_tuples:
            self.filepath_list.append(entry[0])
    
    #TODO: finish this
    #  maintain a map with changes over time?
    #  client IP's may be re-allocated by openvpn?
    def get_ip_user_map(self):
        self.ip_user_map = []
    
    #--------------------------------------------------------------------------------
    
    def microseconds_to_milliseconds(self, datetime_str):
        match = self.microseconds_regex.match(datetime_str)
        if match:
            return match.group(1)
        return datetime_str
    
    #-----convert the unix timestamp to something readable-----
    def format_time(self, time, use_hires=False):
        time_obj = datetime.datetime.fromtimestamp(float(time), pytz.timezone(self.ConfigData['TimeZoneDisplay']))
        if use_hires:
            date_str = time_obj.strftime(self.util.date_format_hi_res)
            return self.microseconds_to_milliseconds(date_str)
        return time_obj.strftime(self.date_format)
    
    # INPUT: unix timestamp, duration in milliseconds
    # OUTPUT: readable date/time with the duration subtracted from the timestamp
    def calc_request_start_time(self, time, duration, use_hires=False):
        try:
            time = float(time)
        except:
            return ''
        try:
            duration = int(duration)
        except:
            #TODO: log error? return nothing?
            #-----bad data in duration? just run the calculation without duration-----
            duration = 0
        # return self.format_time(time - duration/1000, use_hires)
        return self.util.timestamp_to_date_hires(time - duration/1000)
    
    #--------------------------------------------------------------------------------
    
    def should_skip_domain(self, domain):
        #-----check if we have seen this domain once already-----
        if not self.settings.is_setting_enabled('duplicate_domain'):
            return False
        if domain in self.unique_domains:
            # we have a duplicate domain
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    #-----report if a given host is blocked-----
    # check for matching subdomain-domain
    # EXAMPLE: dns denylist has "example.com" on it
    #          is_dns_blocked("example.com") should report as blocked
    #          is_dns_blocked("www.example.com") should report as blocked
    # EXAMPLE 2: dns denylist has "www.example.com" on it
    #            is_dns_blocked("example.com") should report as NOT blocked
    #            is_dns_blocked("other.example.com") should report as NOT blocked
    #            is_dns_blocked("www.example.com") should report as blocked
    # Also check Settings lists:
    #   /etc/bind/settings --> should be pre-loaded in ConfigData
    def is_dns_blocked(self, host):
        self.last_setting_name = ''
        
        # check the host against the DNS denylist instead
        if self.ConfigData['DNSDenylist'].get(host, None):
            return True
        
        for setting_name in self.ConfigData['SettingFile'].keys():
            if self.ConfigData['Settings'][setting_name].get(host, None):
                self.last_setting_name = setting_name
                return True
        
        return False
    
    #--------------------------------------------------------------------------------
    
    #-----DB-storage/loading functions below-----
    
    #-----Using data from parsed_data returned by parse_line()-----
    #NOTE: SquidLogPage also depends on the field names here to be consistent
    def make_db_all_params(self):
        params_insert_list = []
        if not self.all_parsed_data:
            return params_insert_list
        for parsed_data in self.all_parsed_data:
            country_code = self.util.lookup_ip_country(parsed_data['peerhost'])
            
            #TODO: convert from float to datetime_hires str
            log_date = self.util.timestamp_to_date_hires(parsed_data['time'])
            # log_date = self.format_time(parsed_data['time'], use_hires=True)
            log_start_date = self.calc_request_start_time(parsed_data['time'], parsed_data['elapsed'], use_hires=True)
            
            #-----similar to processing in SquidLogPage.format_row_html()-----
            url = parsed_data['URL'] or ''
            domain = ''
            host = self.util.get_host_from_url(parsed_data['URL'])
            if len(host)>2:
                if not self.util.ip_util.is_ip(host):
                    domain = self.util.get_domain_from_host(host)
            if len(parsed_data['ssl_domain'])>2:
                host = parsed_data['ssl_domain']
                if not self.util.ip_util.is_ip(host):
                    domain = self.util.get_domain_from_host(parsed_data['ssl_domain'])
            reverse_dns = ''
            if self.should_skip_rdns():
                reverse_dns = ''
            elif self.use_cached_rdns():
                reverse_dns = self.dns_service.lookup_reverse_dns_cached(parsed_data['peerhost'])
            else:
                reverse_dns = self.dns_service.lookup_reverse_dns(parsed_data['peerhost'])
            if reverse_dns:
                reverse_dns = reverse_dns.rstrip('.')
            else:
                reverse_dns = ''

            # param_insert_dict = {
            #     'ip': parsed_data['peerhost'],
            #     'log_date': log_date,
            #     'time_elapsed': parsed_data['elapsed'], # int, milliseconds
            #     'log_start_date': log_start_date,
            #     'host': host, # optional
            #     'domain': domain, # calculate from host, if host exists
            #     'reverse_dns': reverse_dns, # lookup from IP, may be empty
            #     'url_str': url, # only exists for HTTP connections
            #     'country_code': country_code, # lookup from IP, may be UNKNOWN
            #     'client_ip': parsed_data['client_ip'],
            #     'http_code': parsed_data['code'],
            #     'http_status': parsed_data['status'],
            #     'xfer_bytes': parsed_data['bytes'],
            #     'method': parsed_data['method'],
            # }
            param_insert = (parsed_data['peerhost'],
                log_date,
                parsed_data['elapsed'], # int, milliseconds
                log_start_date,
                host, # optional
                domain, # calculate from host, if host exists
                reverse_dns, # lookup from IP, may be empty
                url, # only exists for HTTP connections
                country_code, # lookup from IP, may be UNKNOWN
                parsed_data['client_ip'],
                parsed_data['code'],
                parsed_data['status'],
                parsed_data['bytes'],
                parsed_data['method']
            )
            params_insert_list.append(param_insert)
        return params_insert_list

    #-----get rows 5000 at a time, until the necessary number are processed for display-----
    # limit 0,5000
    # limit 5000,5000
    # limit 10000,5000
    # etc.
    def get_squid_log_db(self, start_row: int=0, row_limit: int=0, order_by: str='log_date'):
        #TODO: program the checkbox on the squid_log page to handle this
        if order_by!='log_start_date':
            order_by = 'log_date'
        if not self.util.is_int(start_row):
            start_row=0
        sql = f'''select * from squid_log
            order by {order_by} desc
            limit {start_row},5000
        '''
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)
        return rows_with_colnames
    
    def get_last_time_parsed(self):
        sql = 'select max(log_date) from squid_log'
        params = ()
        row = self.db.select(sql, params)
        self.last_time_parsed = ''
        if not row:
            return
        if row[0]:
            self.last_time_parsed = row[0]
    
    #--------------------------------------------------------------------------------

    #-----insert new squid log entries-----
    def update_squid_log_db(self):
        #TODO: replace IP references with squid/domain/host references
        print('update_squid_log_db()')
        print(f'  last_time_parsed: {self.last_time_parsed}')
        
        #-----get the latest DB entry to check the timestamp-----
        params_insert_list = self.make_db_all_params()
        row_count = len(params_insert_list)
        
        sql_insert = "insert into squid_log (ip, log_date, time_elapsed, log_start_date, host, domain, reverse_dns, url_str, country_code, client_ip, http_code, http_status, xfer_bytes, method) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.db.query_exec_many(sql_insert, params_insert_list)
        print(f'  rows inserted: {row_count}')

    #-----delete entries from ip-log-----
    # self.delete_squid_log_db(delete_all=True)
    # self.delete_squid_log_db(entries_older_than=30)
    def delete_squid_log_db(self, delete_all=False, entries_older_than=30):
        if delete_all:
            sql = 'delete from squid_log'
            params = ()
            self.db.query_exec(sql, params)
            return
        
        if not self.util.is_int(entries_older_than):
            return
        if entries_older_than<0:
            return
        sql = 'delete from squid_log where (julianday() - julianday(log_date)) > ?'
        params = (entries_older_than,)
        self.db.query_exec(sql, params)

    # params:
    #   update_db - True if we want to write to the DB after parsing
    # limit to 10,000 rows at a time to reduce memory usage
    def parse_latest_logs(self, update_db=False, parse_all=False):
        self.get_logfiles()
        self.get_ip_user_map()
        self.get_last_time_parsed()
        num_stopped_early = 0
        for filepath in self.filepath_list:
            stopped_parsing_early = self.parse_squid_log(filepath, update_db=update_db)
            if stopped_parsing_early:
                num_stopped_early += 1
            rows_parsed=len(self.all_parsed_data)
            if update_db and rows_parsed>9999:
                print(f'intermediate insert of {rows_parsed} rows')
                self.update_squid_log_db()
                self.all_parsed_data = []
            #-----skipped 4 files? probably all additional files are old data already in the DB also-----
            # this allows for 2 files (access.log, access-icap.log) that may be rotated between log parser runs,
            #   leaving 1 new file and 1 unfinished old file for each log
            #   total of 4 files that require parsing in that case:
            #       access.log, access-icap.log, access.log.1, access-icap.log.1
            # parse everything if the parse_all flag is set
            if num_stopped_early>3 and not parse_all:
                break
        if update_db and self.all_parsed_data:
            print(f'final insert of {rows_parsed} rows')
            self.update_squid_log_db()

    #--------------------------------------------------------------------------------

    def update_country_codes(self):
        return self.logparser.update_country_codes('squid_log')

    #--------------------------------------------------------------------------------
