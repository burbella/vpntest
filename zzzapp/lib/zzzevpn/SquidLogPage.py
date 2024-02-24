#-----Squid Log Page-----
#TODO: move functions from LogParser to SquidLogParser and SquidLogPage
#      integrate the 3 modules

from xml import dom
import json
import re
import urllib.parse

#TEST
import pprint

#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.SquidLogParser

class SquidLogPage:
    'Squid Log Page'
    
    #-----objects-----
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    squid_log_parser: zzzevpn.SquidLogParser = None
    webpage: zzzevpn.Webpage = None
    
    #-----vars-----
    client_ips = []
    countries = {}
    environ = { 'CSP_NONCE': '', }
    filepath = ''
    # filepath_list = []
    # filepath_sizes = {}
    # filesize_limit = 10*1024*1024
    html_table_rows = []
    ip_country_map = []
    ip_user_map = []
    last_displayable_time_parsed = ''
    lines_displayed = 0
    lines_in_logfile = 0
    lines_to_analyze = 1000
    rowcolor = ''
    js_ip_list = '[]'
    server_ip_list = []
    squid_data = []
    unique_domains = []
    
    #-----regex patterns pre-compiled-----
    server_ip_regex_pattern = None
    ssl_custom_format_regex_pattern = None
    
    #-----POST actions-----
    allowed_actions = ['squid_delete_old', 'squid_delete_all', 'squid_log_view']

    LogParserHTML = {}
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
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Squid Log', self.settings)
        self.squid_log_parser = zzzevpn.SquidLogParser(self.ConfigData, self.db, self.util, self.settings)
        self.squid_log_parser.should_skip_rdns(True)
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        self.return_page_header = True
        
        #-----prep the HTML values-----
        self.LogParserHTML = {
            'CSP_NONCE': '',
            
            'full_table_html': '',
            
            'ip_user_map': '',
            'js_ip_list': self.js_ip_list,
            
            'lines_displayed': str(self.lines_displayed),
            'lines_in_logfile': str(self.lines_in_logfile),
            'lines_to_analyze': str(self.lines_to_analyze),
            'lines_analyzed': str(self.lines_to_analyze),
            
            'list_of_countries': '',
            'list_of_users': '',
            
            'rows_in_db': '',
            'oldest_entry': '',
            'newest_entry': '',
            
            'server_ip': self.ConfigData['AppInfo']['IP'],
            'URL_Services': self.ConfigData['URL']['Services'],
            
            'TESTDATA': '',
        }
        
        # Native log format squid %ts.%03tu %6tr %>a %Ss/%03>Hs %<st %rm %ru %un %Sh/%<A %mt
        native_format_regex1 = r'^(\d+\.\d{3})\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)'
        ssl_custom_format_regex = r'^(\d+\.\d{3})\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)'
        self.ssl_custom_format_regex_pattern = re.compile(ssl_custom_format_regex, re.IGNORECASE)
        
        server_ip_regex = r'^([\d\.]+)(|\:80|\:443)$'
        self.server_ip_regex_pattern = re.compile(server_ip_regex, re.IGNORECASE)
        
        #-----clear internal vars for a fresh list processing-----
        self.client_ips = []
        self.countries = {}
        self.filepath = self.ConfigData['Directory']['SquidAccess'] + '/access.log'
        # self.filepath_list = []
        # self.filepath_sizes = {}
        self.html_table_rows = []
        self.ip_country_map = []
        self.js_ip_list = '[]'
        self.lines_displayed = 0
        self.lines_in_logfile = 0
        self.rowcolor = ''
        self.server_ip_list = []
        self.squid_data = []
        self.unique_domains = []
        
        self.get_ip_user_map()
    
    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    # WSGI entry point for POST requests
    def handle_post(self, environ, request_body_size):
        return_data = {
            'error': 'ERROR: missing data',
            'full_table_html': '<tr><td>ERROR: missing data</td></tr>',
        }
        
        #-----return if missing data-----
        if request_body_size==0:
            self.webpage.error_log(environ, 'ERROR: missing data')
            return return_data
        
        self.environ = environ
        
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Squid Log', self.settings)
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        action = raw_data.get('action', None)
        
        # action=squid_delete_old
        # action=squid_delete_all
        #-----return if missing data-----
        if action is None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        else:
            action = action[0]

        lines_to_analyze = raw_data.get('lines_to_analyze', None)
        if lines_to_analyze is None:
            lines_to_analyze = '1000'
        else:
            lines_to_analyze = lines_to_analyze[0]
        
        #-----validate data-----
        if self.data_validation is None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
            'lines_to_analyze': lines_to_analyze,
        }
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')
        
        if not (action in self.allowed_actions):
            self.webpage.error_log(environ, 'allowed_actions: ' + ','.join(self.allowed_actions))
            return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')

        self.process_lines_to_analyze(lines_to_analyze)

        if action=='squid_log_view':
            self.init_vars()
            self.return_page_header = False;
            # self.process_lines_to_analyze(lines_to_analyze[0])
            # return only the body, not the entire HTML page
            return self.make_LogParserPage(environ)
        elif action=='squid_delete_old':
            #-----queue the request-----
            status = self.db.insert_unique_service_request(self.service_name, 'delete_log_old')
            result_str = 'ERROR: pending request in queue, not adding another request to delete old squid logs'
            if status:
                result_str = 'Request to delete old squid logs has been queued'
                self.util.work_available(1)
            return self.util.make_html_display_safe(result_str)
        elif action=='squid_delete_all':
            #-----queue the request-----
            status = self.db.insert_unique_service_request(self.service_name, 'delete_log_all')
            result_str = 'ERROR: pending request in queue, not adding another request to delete ALL squid logs'
            if status:
                result_str = 'Request to delete ALL squid logs has been queued'
                self.util.work_available(1)
            return self.util.make_html_display_safe(result_str)

        self.init_vars()
        self.return_page_header = False;
        return self.make_LogParserPage(environ)
    
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
        
        # set the limit in the parser module
        self.squid_log_parser.lines_to_analyze = self.lines_to_analyze
    
    #--------------------------------------------------------------------------------
    
    #-----WSGI default entry point for GET requests without data (initial page load)-----
    def make_webpage(self, environ, pagetitle):
        self.environ = environ
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        
        self.init_vars()
        rows_in_db, oldest_entry, newest_entry = self.db.get_table_date_info('squid_log', 'log_date')
        #TEST
        # print(f'rows_in_db={rows_in_db}, oldest_entry={oldest_entry}, newest_entry={newest_entry}')
        # result = self.util.make_datetime_readable(newest_entry)
        # print(f'make_datetime_readable(newest_entry)={result}')
        #ENDTEST
        self.LogParserHTML['rows_in_db'] = self.util.add_commas(rows_in_db)
        self.LogParserHTML['oldest_entry'] = self.util.make_datetime_readable(oldest_entry)
        self.LogParserHTML['newest_entry'] = self.util.make_datetime_readable(newest_entry)

        output = self.webpage.make_webpage(self.environ, self.make_LogParserPage(environ))
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def make_LogParserPage(self, environ):
        #-----CSP nonce required for JS to run in browser-----
        self.LogParserHTML['CSP_NONCE'] = environ['CSP_NONCE']
        
        #-----initial page load, just return the page header-----
        if self.return_page_header:
            body = self.webpage.load_template('LogParser')
            return body.format(**self.LogParserHTML)
        
        self.parse_all_squid_logs()
        
        #-----get user list-----
        self.LogParserHTML['list_of_users'] = ''
        if self.squid_log_parser.client_ips:
            for client_ip in self.squid_log_parser.client_ips:
                safe_css_classname = 'client_' + client_ip.replace('.', '_')
                self.LogParserHTML['list_of_users'] += "<input type='radio' name='limit_by_user' value='{}'>{}<br>".format(safe_css_classname, client_ip)
                #TEST - enable this when static client IP's work
                # self.LogParserHTML['list_of_users'] += "<input type='radio' name='limit_by_user' value='{}'>{} ({})<br>".format(safe_css_classname, client_ip, self.ip_user_map[client_ip])
        
        #-----get country list-----
        self.LogParserHTML['list_of_countries'] = self.squid_log_parser.logparser.make_country_input_tags(self.countries)
        self.LogParserHTML['list_of_countries'] += '<input type="radio" name="limit_by_country" value="all" checked>All Countries'
        
        self.LogParserHTML['lines_displayed'] = str(self.lines_displayed)
        self.LogParserHTML['lines_in_logfile'] = str(self.lines_in_logfile)
        self.LogParserHTML['lines_analyzed'] = str(self.lines_to_analyze)
        self.LogParserHTML['lines_to_analyze'] = str(self.lines_to_analyze)
        self.LogParserHTML['js_ip_list'] = self.js_ip_list

        rows_in_db, oldest_entry, newest_entry = self.db.get_table_date_info('squid_log', 'log_date')
        self.LogParserHTML['rows_in_db'] = self.util.add_commas(rows_in_db)
        self.LogParserHTML['oldest_entry'] = self.util.make_datetime_readable(oldest_entry)
        # self.LogParserHTML['newest_entry'] = self.util.make_datetime_readable(newest_entry)
        self.LogParserHTML['newest_entry'] = self.last_displayable_time_parsed or self.util.make_datetime_readable(newest_entry)
        if self.html_table_rows:
            self.LogParserHTML['full_table_html'] += ''.join(self.html_table_rows)

        data_to_send = {
            'logdata': self.LogParserHTML['full_table_html'],
            # 'last_time_parsed': self.LogParserHTML['show_last_time_parsed'],
            # 'last_time_parsed_seconds': self.LogParserHTML['last_time_parsed_seconds'],
            # 'ip_list': ip_list,
            'lines_displayed': self.LogParserHTML['lines_displayed'],
            'lines_in_logfile': self.LogParserHTML['lines_in_logfile'],
            'lines_analyzed': self.LogParserHTML['lines_analyzed'],
            'lines_to_analyze': self.LogParserHTML['lines_to_analyze'],
            'js_ip_list': self.LogParserHTML['js_ip_list'],
            'list_of_users': self.LogParserHTML['list_of_users'],
            'list_of_countries': self.LogParserHTML['list_of_countries'],

            'rows_in_db': self.LogParserHTML['rows_in_db'],
            'oldest_entry': self.LogParserHTML['oldest_entry'],
            'newest_entry': self.LogParserHTML['newest_entry'],

            #TODO: option to report errors to the client?
            'status': 'success',
        }

        #TEST
        # print('data_to_send:')
        # pprint.pprint(data_to_send)
        #ENDTEST

        return json.dumps(data_to_send)
    
    #--------------------------------------------------------------------------------
    
    def process_parsed_data(self, parsed_data, using_db_data: bool=False) -> bool:
        if not parsed_data:
            return False
        #-----method NONE is useless so we skip those-----
        if parsed_data['method']=='NONE':
            return False
        if parsed_data['status'] in ['0', '400']:
            return False
        
        row_html = self.format_row_html(parsed_data, using_db_data)
        if row_html == '':
            return False
        
        #-----latest DISPLAYABLE entry log_date in the DB (some DB entries may have been skipped above)-----
        # parser object var: last_time_parsed
        if using_db_data and not self.last_displayable_time_parsed:
            if parsed_data['time']:
                self.last_displayable_time_parsed = parsed_data['time']

        self.lines_displayed += 1
        self.html_table_rows.append(row_html)
        self.server_ip_list.append(parsed_data['peerhost'])
        
        #-----alternate row colors with each row-----
        if self.rowcolor == '':
            self.rowcolor = ' gray-bg'
        else:
            self.rowcolor = ''
        return True
    
    #--------------------------------------------------------------------------------
    
    def translate_db_data_to_parsed_data(self, db_data):
        # UTC to localtime
        # EX: 2022-05-21T02:35:17.196000 --> 2022-05-20 19:35:17.196

        log_date = self.util.format_time_from_str(db_data['log_date'], use_hires=True)
        log_start_date = self.util.format_time_from_str(db_data['log_start_date'], use_hires=True)
        parsed_data = {
            'peerhost': db_data['ip'],
            'time': self.util.make_datetime_readable(log_date),
            'elapsed': str(db_data['time_elapsed']),
            'log_start_date': self.util.make_datetime_readable(log_start_date),
            
            # processing issues with ssl_domain require it to be the full subdomain, not the top domain
            'host': db_data['host'],
            'db_domain': db_data['domain'],
            'ssl_domain': db_data['host'],

            'reverse_dns': db_data['reverse_dns'],
            'URL': db_data['url_str'],
            'country_code': db_data['country_code'],
            'client_ip': db_data['client_ip'],
            'code': db_data['http_code'],
            'status': str(db_data['http_status']),
            'bytes': str(db_data['xfer_bytes']),
            'method': db_data['method']
        }

        return parsed_data

    def parse_all_squid_logs(self):
        self.LogParserHTML['full_table_html'] = self.format_header_html()
        
        # if not self.filepath_list:
        #     self.webpage.error_log(self.environ, 'parse_squid_log(): Log file(s) not specified')
        #     return
        
        # for filepath in self.filepath_list:
        #     self.squid_log_parser.parse_squid_log(filepath)

        # self.squid_log_parser.parse_latest_logs()
        
        # if self.squid_log_parser.all_parsed_data:
        #     for parsed_data in self.squid_log_parser.all_parsed_data:
        #         self.process_parsed_data(parsed_data)
        
        #TODO: first parse the latest data from logfiles, up to the last_time_parsed in the DB
        #   then get rows from the DB, up to lines_to_analyze
        #   check 4 files, since ICAP is logged separately and logs may have rotated recently
        self.squid_log_parser.parse_latest_logs()
        latest_parsed_data = self.squid_log_parser.all_parsed_data
        lines_processed = 0
        if latest_parsed_data:
            for parsed_data in latest_parsed_data:
                # not using DB data with live-parsed logs, so extra processing is needed to generate the data that is calculated by cron and stored in the DB
                if self.process_parsed_data(parsed_data, using_db_data=False):
                    lines_processed += 1
                if lines_processed >= self.lines_to_analyze:
                    break
        else:
            latest_parsed_data = []

        #-----start with the first DB row-----
        start_row = 0
        while lines_processed < self.lines_to_analyze:
            rows_with_colnames = self.squid_log_parser.get_squid_log_db(start_row=start_row)
            if not rows_with_colnames:
                break
            for db_data in rows_with_colnames:
                parsed_data = self.translate_db_data_to_parsed_data(db_data)
                self.process_parsed_data(parsed_data, using_db_data=True)
                lines_processed += 1
                if lines_processed >= self.lines_to_analyze:
                    break
            #-----get the next 5000 DB rows-----
            start_row += 5000
        
        if (self.squid_log_parser.lines_in_logfile == 0) and (lines_processed==0):
            self.LogParserHTML['full_table_html'] = '<tr><td>Empty log</td></tr>'
        
        #-----get a list of unique IP's-----
        self.server_ip_list = self.util.unique_sort(self.server_ip_list)
        #-----encode the array to a JSON array so the JS can work with it-----
        self.js_ip_list = json.dumps(self.server_ip_list)
    
    #--------------------------------------------------------------------------------

    #TODO: finish this
    def get_ip_user_map(self):
        self.ip_user_map = []
    
    #--------------------------------------------------------------------------------
    
    def format_header_html(self):
        html = '''
<tr>
<th>Time ({})</th>
<th class='extra_column'>Elapsed<br>(msec)</th>
<th class='more_column'>Client IP</th>
<th>Server IP</th>
<th>Country</th>
<th class="do_not_wrap_text">Reverse DNS<br>
    <div id='rdns_load_all'><a class='clickable reverse_dns_load_batch'>(Load ALL)</a></div></th>
<th class='extra_column'>Code</th>
<th class='more_column'>Status</th>
<th class='extra_column'>Bytes</th>
<th class='extra_column'>Method</th>
<th>URL/SSL Domain</th>
</tr>
        '''
        
        #-----available columns not used-----
        # <th>URL</th>
        # <th class='extra_column'>RFC931</th>
        # <th class='extra_column'>PeerStatus</th>
        # <th class='extra_column'>MIME Type</th>
        
        return html.format(self.util.format_timezone())
    
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
    
    #TODO: apply DB data differently than live-parsed data
    def format_row_html(self, parsed_data, using_db_data: bool=False):
        class_status = ' status_' + parsed_data['status']
        class_client = ' client_' + parsed_data['client_ip'].replace('.', '_')
        class_rdns = ' rdns_' + parsed_data['peerhost'].replace('.', '_')
        class_dup = ''
        dns_blocked = ''
        
        #-----identify actual URL's, link them and make analysis links-----
        full_url = parsed_data['URL']
        domain_found = full_url
        host = ''
        if parsed_data['URL']:
            host = self.util.get_host_from_url(parsed_data['URL'])
        if len(host)>2:
            #-----HTTP-----
            domain_found = host
            if self.should_skip_domain(domain_found):
                return ''
            
            #-----skip domains that have been flagged for hiding-----
            skip_check = self.util.get_domain_from_host(host)
            if skip_check in self.settings.SquidHideDomains:
                return ''
            
            #-----no DNS searches for IP's-----
            url_analysis_links = ''
            if not self.util.ip_util.is_ip(host):
                base64_host = self.util.encode_base64(host)
                url_analysis_links = f'''<a class="clickable search_google" data-onclick="{base64_host}">(G)</a><a class="clickable do_nslookup" data-onclick="{base64_host}">(N)</a><a class="clickable search_whois" data-onclick="{base64_host}">(W)</a>'''
            
            # Don't show blocking links for links that are already blocked
            blocking_links = self.get_blocking_links(parsed_data['peerhost'], host)
            if not blocking_links:
                dns_blocked = ' dns_blocked'
            
            #-----link the URL and shorten it so the table doesn't get too wide-----
            short_url = full_url;
            if (len(parsed_data['URL']) > self.ConfigData['MaxUrlDisplayLength']):
                short_url = parsed_data['URL'][0:self.ConfigData['MaxUrlDisplayLength']]
            
            full_url = '<a href=\'{}\'>{}</a><br> {} {}'.format(parsed_data['URL'], short_url, url_analysis_links, blocking_links)
        
        #-----don't process "-" entries from SSL Domain-----
        # if we're on SSL and got a domain in the log, process the SSL Domain instead of the HTTP URL (which will be blank)
        show_domain_or_url = full_url
        ssl_domain_analysis_links = ''
        if len(parsed_data['ssl_domain'])>2 and not parsed_data['URL'].startswith('http:'):
            #-----HTTPS-----
            domain_found = parsed_data['ssl_domain']
            
            if self.should_skip_domain(domain_found):
                return ''
            
            #-----skip domains that have been flagged for hiding-----
            skip_check = ''
            if using_db_data:
                skip_check = parsed_data['db_domain']
            else:
                skip_check = self.util.get_domain_from_host(parsed_data['ssl_domain'])
            if skip_check in self.settings.SquidHideDomains:
                return ''
            
            blocking_links = self.get_blocking_links(parsed_data['peerhost'], parsed_data['ssl_domain'])
            if not blocking_links:
                dns_blocked = ' dns_blocked'
            
            base64_ssl_domain = self.util.encode_base64(parsed_data['ssl_domain'])
            ssl_domain_analysis_links += f'<br><a class="clickable search_google" data-onclick="{base64_ssl_domain}">(G)</a>'
            ssl_domain_analysis_links += f'<a class="clickable do_nslookup" data-onclick="{base64_ssl_domain}">(N)</a>'
            ssl_domain_analysis_links += f'<a class="clickable search_whois" data-onclick="{base64_ssl_domain}">(W)</a>'
            
            highlight_class = 'cursor_copy'
            settings_indicator = ''
            if self.squid_log_parser.is_dns_blocked(parsed_data['ssl_domain']) or self.squid_log_parser.is_dns_blocked(self.util.get_domain_from_host(parsed_data['ssl_domain'])):
                highlight_class += ' text_red'
                if self.squid_log_parser.last_setting_name:
                    settings_indicator = ' (Settings: {})'.format(self.squid_log_parser.last_setting_name)
                    
                    #-----turn it red if the Setting is checked-----
                    if self.settings.is_setting_enabled(self.squid_log_parser.last_setting_name):
                        settings_indicator = '<span class="text_red">{}</span>'.format(settings_indicator)
            
            show_domain_or_url = '''<span class="{}">{}</span>{} {} {}'''.format(highlight_class, parsed_data['ssl_domain'], settings_indicator, ssl_domain_analysis_links, blocking_links)
        
        #-----check if we have seen this domain once already-----
        if domain_found in self.unique_domains:
            class_dup = ' dup_domain'
            #-----return empty HTML string if the Settings says to hide duplicates-----
            if self.settings.is_setting_enabled('duplicate_domain'):
                return ''
        else:
            self.unique_domains.append(domain_found)
        
        country_code = ''
        if using_db_data:
            country_code = parsed_data['country_code']
        else:
            country_code = self.util.lookup_ip_country(parsed_data['peerhost'])
        class_country = ' country_' + country_code
        
        #-----update the list of countries-----
        if not self.countries.get(country_code, None):
            self.countries[country_code] = 1
        
        #-----make analysis links for public IP's only-----
        # "peerhost" is the server IP
        ip_data = self.squid_log_parser.logparser.make_ip_analysis_links(parsed_data['peerhost'])
        
        #----start and end times for the request-----
        logged_time = ''
        if using_db_data:
            logged_time = parsed_data['time']
        else:
            logged_time = self.util.timestamp_to_date_hires(parsed_data['time'])
            if self.squid_log_parser.last_time_parsed>=logged_time:
                return ''
            logged_time = self.util.format_time_from_str(logged_time, use_hires=True)
            logged_time = self.util.make_datetime_readable(logged_time)
        #-----don't bother processing differences under 1 second-----
        # effective_elapsed = int(parsed_data['elapsed'])
        # if effective_elapsed<1000:
        #     effective_elapsed = 0
        start_time = ''
        if using_db_data:
            start_time = parsed_data['log_start_date']
        else:
            start_time = self.squid_log_parser.calc_request_start_time(parsed_data['time'], parsed_data['elapsed'], use_hires=True)
            start_time = self.util.format_time_from_str(start_time, use_hires=True)
            start_time = self.util.make_datetime_readable(start_time)
        show_start_time = ''
        if start_time != logged_time:
            show_start_time = '<br>' + start_time
        
        #-----pack the TR with classes needed to show/hide different data types-----
        html_data = {
            'ctr': str(self.lines_displayed),
            'rowcolor': self.rowcolor,
            'class_status': class_status,
            'class_client': class_client,
            'class_country': class_country,
            'class_dup': class_dup,
            'dns_blocked': dns_blocked,
            
            'logged_time': logged_time,
            'show_start_time': show_start_time,
            'elapsed': parsed_data['elapsed'],
            'client_ip': parsed_data['client_ip'],
            'highlight_ip': ip_data['highlight_ip'],
            'server_ip_analysis_links': ip_data['ip_analysis_links'],
            'country': self.ConfigData['OfficialCountries'].get(country_code, 'UNKNOWN'),
            'class_rdns': class_rdns,
            'code': parsed_data['code'],
            'status': parsed_data['status'],
            'bytes': parsed_data['bytes'],
            'method': parsed_data['method'],
            'show_domain_or_url': show_domain_or_url,
        }
        html = '''
<tr id='row_{ctr}' class='{rowcolor}{class_status}{class_client}{class_country}{class_dup}{dns_blocked}'>
<td>{logged_time}{show_start_time}</td>
<td class='extra_column'>{elapsed}</td>
<td class='more_column'>{client_ip}</td>
<td>{highlight_ip} {server_ip_analysis_links}</td>
<td>{country}</td>
<!--blank space to fill-in with reverse-DNS data-->
<td class='{class_rdns}'></td>
<td class='extra_column'>{code}</td>
<td class='more_column'>{status}</td>
<td class='extra_column'>{bytes}</td>
<td class='extra_column'>{method}</td>
<td>{show_domain_or_url}</td>
</tr>
        '''
        
        return html.format(**html_data)
    
    #--------------------------------------------------------------------------------
    
    #TODO: links to unblock DNS/squid
    #-----generates the links that are used to block an individual domain or host-----
    def get_blocking_links(self, server_ip, host):
        blocking_links = '';
        domain = self.util.get_domain_from_host(host)
        
        #-----no DNS-blocks for IP's-----
        if self.util.ip_util.is_ip(host):
            return ''
        
        if not (self.squid_log_parser.is_dns_blocked(host) or self.squid_log_parser.is_dns_blocked(domain)):
            blocking_links = f'<a class="clickable_red block_dns" data-onclick="{domain}">(D)</a><a class="clickable_red block_dns" data-onclick="{host}">(S)</a>'
        
        return blocking_links
    
    #--------------------------------------------------------------------------------
