#-----view raw IP log data-----

import copy
import json
import os.path
import pprint

#-----package with all the Zzz modules-----
import zzzevpn

class IpLogRawDataPage:
    'view raw IP log data'

    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    ip_log_raw_data: zzzevpn.IpLogRawData = None
    logparser: zzzevpn.LogParser = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None

    IpLogRawDataHTML = {}
    service_name = 'iptables'
    common_field_values = {
        'PREC': '0x00',
        'TOS': '0x00',
        'RES': '0x00',
        'URGP': '0',
    }

    return_page_header = True
    limit_fields = {
        'hide_internal_connections': False,
        'src_ip': set(),
        'dst_ip': set(),
        'src_ports': set(),
        'dst_ports': set(),
    }
    count_test_prints = 0

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
        #-----get Config-----
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
        #-----use the given DB connection or get a new one-----
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
        self.ip_log_raw_data = zzzevpn.IpLogRawData(self.ConfigData, self.db, self.util, self.settings)
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)
        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        self.count_test_prints = 0
        self.return_page_header = True
        self.limit_fields = {
            'hide_internal_connections': False,
            'src_ip': set(),
            'dst_ip': set(),
            'src_ports': set(),
            'dst_ports': set(),
        }

        #-----prep the HTML values-----
        self.IpLogRawDataHTML = {
            # 'logdata': '',
            'logfile_menu': '',
            'show_rowcount': '',
        }

    #--------------------------------------------------------------------------------

    #-----process POST data-----
    # always return JSON
    def handle_post(self, environ, request_body_size):
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')

        self.init_vars()

        #-----get post data-----
        allowed_post_params = {'action', 'filename', 'hide_internal_connections', 'src_ip', 'dst_ip', 'src_ports', 'dst_ports'}
        data = self.webpage.load_data_from_post(environ, request_body_size, allowed_post_params)

        #-----return if missing data-----
        if data['action'] is None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        if data['filename'] is None:
            return self.webpage.error_log(environ, 'ERROR: missing filename')
        self.limit_fields['hide_internal_connections'] = self.util.js_string_to_python_bool(data['hide_internal_connections'])
        if data['src_ip']:
            self.limit_fields['src_ip'] = set(data['src_ip'].split(','))
        if data['dst_ip']:
            self.limit_fields['dst_ip'] = set(data['dst_ip'].split(','))
        if data['src_ports']:
            self.limit_fields['src_ports'] = set(data['src_ports'].split(','))
            # self.limit_fields['src_ports'] = {}
            # for num in data['src_ports'].split(','):
            #     self.limit_fields['src_ports'].add(self.util.get_int_safe(num))
        if data['dst_ports']:
            self.limit_fields['dst_ports'] = set(data['dst_ports'].split(','))

        #TODO: validate filename
        #-----validate data-----
        if self.data_validation is None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData, enforce_rules=True, auto_clean=True)
        if not self.data_validation.validate(environ, data):
            err_msg = f'''data validation failed<br>{self.data_validation.show_detailed_errors()}'''
            return self.make_return_json_error(self.webpage.error_log(environ, err_msg))

        #TEST
        # print('-'*40)
        # print('data:')
        # pprint.pprint(data)
        # print('limit_fields:')
        # pprint.pprint(self.limit_fields)
        # print('-'*40)

        if data['action']=='view_log':
            # return only the table rows, not the entire HTML page
            self.return_page_header = False
            return self.make_IpLogRawData(environ, data['filename'])

        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle):
        # if self.webpage is None:
        #     self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        self.webpage.update_header(environ, pagetitle)
        # self.webpage.settings.get_settings()
    
        output = self.webpage.make_webpage(environ, self.make_IpLogRawData(environ))
    
        return output

    #--------------------------------------------------------------------------------
    
    def make_IpLogRawData(self, environ, filename=None):
        #-----CSP nonce required for JS to run in browser-----
        self.IpLogRawDataHTML['CSP_NONCE'] = environ['CSP_NONCE']
        self.IpLogRawDataHTML['logfile_menu'] = self.make_logfile_menu()

        #-----initial page load, just return the page header-----
        if self.return_page_header:
            body = self.webpage.load_template('IpLogRawData')
            return body.format(**self.IpLogRawDataHTML)

        #-----send a JSON back to the AJAX function-----
        logdata_rows, entries = self.make_logdata_rows(filename)
        rowcount = len(logdata_rows)
        analysis = self.ip_log_raw_data.analyze_log_data(entries)
        all_analysis_rows = self.make_all_analysis_rows(analysis)

        #TEST
        TESTDATA = ''
        # analysis_print = pprint.pformat(analysis)
        # analysis_keys = ' '.join(analysis.keys())
        # TESTDATA = f'''<p class="font-courier gray-bg">TESTDATA:<br>
        # analysis keys: {analysis_keys}<br>
        # analysis: {analysis_print}<br>
        # </p>'''

        bps_limit_displayed = ''
        if analysis['duration'] > self.ip_log_raw_data.bps_time_limit:
            bps_limit_displayed = f'({self.ip_log_raw_data.bps_increment_size}-second bps columns shown, up to {self.ip_log_raw_data.bps_time_limit} seconds)'
        data_to_send = {
            'status': 'success',
            'error_msg': '',

            'logdata': '\n'.join(logdata_rows),
            'src_ip_analysis': '\n'.join(all_analysis_rows['src_analysis_rows']),
            'dst_ip_analysis': '\n'.join(all_analysis_rows['dst_analysis_rows']),
            'rowcount': rowcount,
            'start_timestamp': analysis['start_timestamp'],
            'end_timestamp': analysis['end_timestamp'],
            'duration': analysis['duration'],
            'bps_limit_displayed': bps_limit_displayed,
            'TESTDATA': TESTDATA,
        }
        json_data_to_send = json.dumps(data_to_send)

        return json_data_to_send

    #--------------------------------------------------------------------------------

    def make_return_json_error(self, error_msg: str='') -> str:
        data_to_send = {
            'status': 'error',
            'error_msg': error_msg,

            'logdata': '',
        }
        
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    #--------------------------------------------------------------------------------

    def make_analysis_ip_segment(self, analysis: dict, key, ip, bps_max_seconds: int) -> str:
        bps_by_segment = analysis[key][ip].get('bps_by_segment', None)
        bps_cols_list = []
        if not bps_by_segment:
            return ''

        # segment is labeled by it's end value, so data from the 5-10 second range is labeled as 10
        for segment in range(5, bps_max_seconds+1, 5):
            bps = 0
            flags = 0
            segment_info = analysis[key][ip]['bps_by_segment'].get(segment, None)
            if segment_info:
                if segment_info['bps']<10:
                    # give it one decimal place if it's a small number
                    bps = round(segment_info['bps'], 1)
                else:
                    bps = round(segment_info['bps'])
                flags = segment_info['flags']
            highlight_class = ''
            if flags:
                highlight_class = 'warning_text'
            bps_cols_list.append(f'<td class="{highlight_class}">{bps}</td>')

        return ''.join(bps_cols_list)

    #--------------------------------------------------------------------------------

    # key: 'analysis_by_src_ip' or 'analysis_by_dst_ip'
    # colname: 'Source IP' or 'Destination IP'
    def make_analysis_rows(self, analysis: dict, key: str, colname: str) -> list:
        if not analysis[key]:
            return ['']

        # ok_to_display_src_ip = self.check_limit_field('src_ip', entry['src'])
        # ok_to_display_dst_ip = self.check_limit_field('dst_ip', entry['dst'])

        bps_max_seconds = int(analysis['duration']/5)*5
        if bps_max_seconds > self.ip_log_raw_data.bps_time_limit:
            # over 60 seconds of data results in too many columns, so limit it to 60 seconds
            bps_max_seconds = self.ip_log_raw_data.bps_time_limit
        bps_header = ''
        for segment in range(0, bps_max_seconds-4, 5):
            bps_header += f'<th>bps({segment}-{segment+5})</th>'

        analysis_rows = [f'''<tr>
<th>{colname}</th>
<th>Packets</th>
<th>Total Bytes</th>
<th>bytes/sec</th>
{bps_header}
</tr>''']
        for ip in sorted(analysis[key].keys()):
            if ip in self.ConfigData['HideIPs']:
                # for running demos without exposing the real client IPs or other things that should be hidden
                continue
            if self.has_limits():
                if key=='analysis_by_src_ip' and not self.check_limit_field('src_ip', ip):
                    continue
                if key=='analysis_by_dst_ip' and not self.check_limit_field('dst_ip', ip):
                    continue
            ip_data = self.logparser.make_ip_analysis_links(ip, highlight_ips=False, include_blocking_links=False)
            total_bytes = analysis[key][ip]['length']
            if analysis['duration']:
                bytes_per_sec = int(total_bytes / analysis['duration'])
            else:
                bytes_per_sec = 0
            bps_cols = self.make_analysis_ip_segment(analysis, key, ip, bps_max_seconds)
            row = f'''<tr>
<td><span class="cursor_copy">{ip}</span>&nbsp;{ip_data['ip_analysis_links']}</td>
<td>{analysis[key][ip]['packets']}</td>
<td>{total_bytes}</td>
<td>{bytes_per_sec}</td>
{bps_cols}
</tr>'''
            analysis_rows.append(row)
        return analysis_rows

    #--------------------------------------------------------------------------------

    #-----make the analysis rows from the output of ip_log_raw_data.analyze_log_data()-----
    def make_all_analysis_rows(self, analysis: dict) -> list:
        if not analysis['analysis_by_src_ip'] and not analysis['analysis_by_dst_ip']:
            return {
                'src_analysis_rows': [''],
                'dst_analysis_rows': [''],
            }
        src_analysis_rows = self.make_analysis_rows(analysis, 'analysis_by_src_ip', 'Source IP')
        dst_analysis_rows = self.make_analysis_rows(analysis, 'analysis_by_dst_ip', 'Destination IP')

        all_analysis_rows = {
            'src_analysis_rows': src_analysis_rows,
            'dst_analysis_rows': dst_analysis_rows,
        }
        return all_analysis_rows

    #--------------------------------------------------------------------------------

    def make_logfile_menu(self) -> str:
        '''returns the HTML for the logfile menu'''
        self.ip_log_raw_data.get_logfiles()
        if not self.ip_log_raw_data.filepath_list:
            return '<option>No logfiles found</option>'

        output = ['<option value="ipv4.log">latest</option>']
        for filepath in self.ip_log_raw_data.filepath_list:
            #-----get the timestamp from the filename-----
            match = self.ip_log_raw_data.regex_filename_date.search(filepath)
            if match:
                timestamp = int(match.group(1))
                readable_timestamp = self.util.current_datetime(timestamp)
                output.append(f'<option value="ipv4.log-{timestamp}">{readable_timestamp}</option>')
        return '\n'.join(output)

    #--------------------------------------------------------------------------------

    def highlight_uncommon_values(self, name, value) -> str:
        '''returns the HTML for the logfile menu'''
        found_value = self.common_field_values.get(name, None)
        if found_value is None:
            # this name is not in the common_field_values dict
            return value
        if found_value==value:
            # this value is common, do not highlight it
            return value
        return f'<span class="warning_text">{value}</span>'

    #--------------------------------------------------------------------------------

    def make_logdata_header(self) -> str:      
        header = '''<tr>
<th>DateTime</th>
<th>Type</th>
<th>In</th>
<th>Out</th>
<th>Src IP</th>
<th>Src Port</th>
<th>Dst IP</th>
<th>Dst Port</th>
<th>Length</th>
<th>TTL</th>
<th>Proto</th>
<th>PREC</th>
<th>TOS</th>
<th>Window</th>
<th>RES</th>
<th>URGP</th>
<th>ID</th>
<th>Flags</th>
</tr>'''
        return header

    #--------------------------------------------------------------------------------

    def has_limits(self) -> bool:
        if self.limit_fields['hide_internal_connections'] or self.limit_fields['src_ip'] or self.limit_fields['dst_ip'] or self.limit_fields['src_ports'] or self.limit_fields['dst_ports']:
            return True
        return False

    #--------------------------------------------------------------------------------

    def check_limit_field(self, field: str, value: str) -> bool:
        if not value:
            # empty values are always allowed
            return True
        if not self.limit_fields[field]:
            # no limit field set, so allow all values
            return True
        # assume the value is being tested against a set
        if value in self.limit_fields[field]:
            return True
        return False

    #--------------------------------------------------------------------------------

    def make_row(self, entry: dict):
        if self.limit_fields['hide_internal_connections'] and (not entry['in'] or not entry['out']):
            #-----skip internal connections-----
            return None

        #TEST
        # if self.count_test_prints < 3:
        #     self.count_test_prints += 1
        #     print('ENTRY:')
        #     pprint.pprint(entry)

        #-----skip rows not matching limit fields-----
        ok_to_display = False
        ok_to_display_src_ip = self.check_limit_field('src_ip', entry['src'])
        ok_to_display_dst_ip = self.check_limit_field('dst_ip', entry['dst'])
        ok_to_display_src_ports = self.check_limit_field('src_ports', str(entry['SPT']))
        ok_to_display_dst_ports = self.check_limit_field('dst_ports', str(entry['DPT']))
        if not (self.limit_fields['src_ip'] or self.limit_fields['dst_ip'] or self.limit_fields['src_ports'] or self.limit_fields['dst_ports']):
            #-----no limit fields, so display all rows-----
            ok_to_display = True
        if not ((ok_to_display_src_ip and ok_to_display_src_ports ) or (ok_to_display_dst_ip and ok_to_display_dst_ports)):
            #TEST: print the entry that was skipped
            # self.count_test_prints += 1
            # if self.count_test_prints < 10:
            #     show_entry_info = f'''src={entry['src']}, dst={entry['dst']}, SPT={entry['SPT']} DPT={entry['DPT']}'''
            #     print(f'''entry skipped: {show_entry_info}\ntest flags: ok_to_display_src_ip={ok_to_display_src_ip} ok_to_display_dst_ip={ok_to_display_dst_ip} ok_to_display_src_ports={ok_to_display_src_ports} ok_to_display_dst_ports={ok_to_display_dst_ports}''')
            return None

        display_entry = copy.deepcopy(entry)
        for field in entry:
            if not entry[field]:
                continue
            display_entry[field] = self.highlight_uncommon_values(field, entry[field])

        # currently not used: pid, mac
        logdata_row = f'''
<tr>
<td>{display_entry['datetime']}</td>
<td>{display_entry['type']}</td>
<td>{display_entry['in']}</td>
<td>{display_entry['out']}</td>
<td class="cursor_copy">{display_entry['src']}</td>
<td>{display_entry['SPT']}</td>
<td class="cursor_copy">{display_entry['dst']}</td>
<td>{display_entry['DPT']}</td>
<td>{display_entry['LEN']}</td>
<td>{display_entry['TTL']}</td>
<td>{display_entry['PROTO']}</td>
<td>{display_entry['PREC']}</td>
<td>{display_entry['TOS']}</td>

<td>{display_entry['WINDOW']}</td>
<td>{display_entry['RES']}</td>
<td>{display_entry['URGP']}</td>

<td>{display_entry['ID']}</td>
<td>{entry['msg']}</td>
</tr>'''
        return logdata_row

    #--------------------------------------------------------------------------------

    def make_logdata_rows(self, filename: str):
        '''returns the log data table rows'''
        # table_cols = 12
        filepath = f'{self.ConfigData["Directory"]["IPtablesLog"]}/{filename}'
        if not os.path.isfile(filepath):
            logdata_rows = [f'<tr><td>ERROR: logfile not found "{filename}"<br>Try refreshing the page to get the latest list of logs</td></tr>']
            return logdata_rows, None

        logdata_rows = [self.make_logdata_header()]
        entries = self.ip_log_raw_data.parse_ip_log(filepath, extended_parsing=True)
        rowcount = 0
        for entry in entries:
            logdata_row = self.make_row(entry)
            if not logdata_row:
                continue
            logdata_rows.append(logdata_row)
            rowcount += 1
            if rowcount > 25:
                logdata_rows.append(self.make_logdata_header())
                rowcount = 0

        return logdata_rows, entries
