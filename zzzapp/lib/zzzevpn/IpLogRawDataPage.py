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

    return_page_header = True
    sort_by = 'ip' # ip, packets, bytes
    allowed_sort_by = ['ip', 'packets', 'bytes']

    limit_fields = {
        'auto_update_file_list': False,
        'hide_internal_connections': False,
        # text boxes
        'src_ip': set(),
        'dst_ip': set(),
        'src_ports': set(),
        'dst_ports': set(),
        # flags
        'flags_any': False,
        'flags_none': False,
        # status
        'include_accepted_packets': False,
        'include_blocked_packets': False,
        # prec/tos
        'prec_tos_zero': False,
        'prec_tos_nonzero': False,
        # protocol
        'protocol_tcp': False,
        'protocol_udp': False,
        'protocol_icmp': False,
        'protocol_other': False,
        # bps display
        'show_max_bps_columns': False,
    }

    checkbox_fields = ['auto_update_file_list', 'flags_any', 'flags_none', 'hide_internal_connections', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_tcp', 'protocol_udp', 'protocol_icmp', 'protocol_other', 'show_max_bps_columns']
    allowed_post_params = ['action', 'auto_update_file_list', 'dst_ip', 'dst_ports', 'filename', 'flag_bps_above_value', 'flag_pps_above_value', 'flags_any', 'flags_none', 'hide_internal_connections', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_icmp', 'protocol_other', 'protocol_tcp', 'protocol_udp', 'show_max_bps_columns', 'sort_by', 'src_ip', 'src_ports']

    # used to make sure only IPs in the displayed raw data are also displayed in the bps analysis tables
    displayed_raw_data_src_ips = set()
    displayed_raw_data_dst_ips = set()

    displayed_raw_data_src_ports = set()
    displayed_raw_data_dst_ports = set()

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
            'src_ip': set(),
            'dst_ip': set(),
            'src_ports': set(),
            'dst_ports': set(),
        }
        for checkbox_field in self.checkbox_fields:
            self.limit_fields[checkbox_field] = False

        self.displayed_raw_data_src_ips = set()
        self.displayed_raw_data_dst_ips = set()
        self.displayed_raw_data_src_ports = set()
        self.displayed_raw_data_dst_ports = set()

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
        # include all limit_fields
        data = self.webpage.load_data_from_post(environ, request_body_size, self.allowed_post_params)

        #TODO: validate filename
        #-----validate data-----
        if self.data_validation is None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData, enforce_rules=True, auto_clean=True)
        if not self.data_validation.validate(environ, data):
            err_msg = f'''data validation failed<br>{self.data_validation.show_detailed_errors()}'''
            return self.make_return_json_error(self.webpage.error_log(environ, err_msg))

        #-----return if missing data in required fields (action, filename)-----
        if data['action'] is None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        if (data['action']=='view_log') and (data['filename'] is None):
            # filename only applies to view_log
            return self.webpage.error_log(environ, 'ERROR: missing filename')

        if data['dst_ip']:
            self.limit_fields['dst_ip'] = set(data['dst_ip'].split(','))
        if data['dst_ports']:
            self.limit_fields['dst_ports'] = set(data['dst_ports'].split(','))
        if data['sort_by'] and data['sort_by'] in self.allowed_sort_by:
            self.sort_by = data['sort_by']
        else:
            self.sort_by = 'ip'
        if data['src_ip']:
            self.limit_fields['src_ip'] = set(data['src_ip'].split(','))
        if data['src_ports']:
            self.limit_fields['src_ports'] = set(data['src_ports'].split(','))
        self.load_js_checkbox_data(data)

        #TEST
        # print('-'*40)
        # print('data:')
        # pprint.pprint(data)
        # print('limit_fields:')
        # pprint.pprint(self.limit_fields)
        # print('-'*40)

        if data['action']=='view_log':
            # save the latest settings
            #TODO: make this save the current checkbox settings, not just the default values
            #      make sure self.settings.IPLogRawDataView contains the current settings
            self.store_data_in_settings(data)
            self.settings.save_ip_log_view_settings()
            # return only the table rows, not the entire HTML page
            self.return_page_header = False
            return self.make_IpLogRawData(environ, data['filename'])
        elif data['action']=='get_logfile_menu':
            return self.get_logfile_menu()

        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')

    #--------------------------------------------------------------------------------

    #-----store the data from the POST into the settings var IPLogRawDataView-----
    def store_data_in_settings(self, data: dict):
        # allow zero here
        self.settings.IPLogRawDataView['flag_bps_above_value'] = self.util.get_int_safe(data['flag_bps_above_value'])
        self.settings.IPLogRawDataView['flag_pps_above_value'] = self.util.get_int_safe(data['flag_pps_above_value'])

        if data['dst_ip']:
            self.settings.IPLogRawDataView['dst_ip'] = data['dst_ip']
        if data['dst_ports']:
            self.settings.IPLogRawDataView['dst_ports'] = data['dst_ports']
        if data['sort_by'] in self.allowed_sort_by:
            self.settings.IPLogRawDataView['sort_by'] = data['sort_by']
        else:
            self.settings.IPLogRawDataView['sort_by'] = 'ip'
        if data['src_ip']:
            self.settings.IPLogRawDataView['src_ip'] = data['src_ip']
        if data['src_ports']:
            self.settings.IPLogRawDataView['src_ports'] = data['src_ports']

        for checkbox_field in self.checkbox_fields:
            self.settings.IPLogRawDataView[checkbox_field] = data[checkbox_field]

    #--------------------------------------------------------------------------------

    def get_logfile_menu(self):
        logfile_menu = self.make_logfile_menu()
        data_to_send = {
            'status': 'success',
            'error_msg': '',
            'logfile_menu': logfile_menu,
        }
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    #--------------------------------------------------------------------------------

    def load_js_checkbox_data(self, data: dict):
        for checkbox_field in self.checkbox_fields:
            self.limit_fields[checkbox_field] = self.util.js_string_to_python_bool(data[checkbox_field])

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle):
        # if self.webpage is None:
        #     self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        self.webpage.update_header(environ, pagetitle)
        # self.webpage.settings.get_settings()
    
        output = self.webpage.make_webpage(environ, self.make_IpLogRawData(environ))
    
        return output

    #--------------------------------------------------------------------------------

    # settings from the settings.IPLogRawDataView need to be put in self.IpLogRawDataHTML
    def load_settings_into_html(self):
        # settings = self.settings.get_settings()
        # self.IpLogRawDataHTML['hide_internal_connections'] = self.settings.is_setting_enabled('hide_internal_connections', self.settings.SettingTypeIPLogRawDataView)

        self.IpLogRawDataHTML['dst_ip'] = self.settings.IPLogRawDataView['dst_ip']
        self.IpLogRawDataHTML['dst_ports'] = self.settings.IPLogRawDataView['dst_ports']
        self.IpLogRawDataHTML['flag_bps_above_value'] = self.settings.IPLogRawDataView['flag_bps_above_value']
        self.IpLogRawDataHTML['flag_pps_above_value'] = self.settings.IPLogRawDataView['flag_pps_above_value']
        self.IpLogRawDataHTML['sort_by'] = self.settings.IPLogRawDataView['sort_by']
        self.IpLogRawDataHTML['src_ip'] = self.settings.IPLogRawDataView['src_ip']
        self.IpLogRawDataHTML['src_ports'] = self.settings.IPLogRawDataView['src_ports']

        for checkbox in self.checkbox_fields:
            self.IpLogRawDataHTML[checkbox] = self.limit_fields[checkbox]
            default_value = 'true'
            if self.settings.is_setting_enabled(checkbox, self.settings.SettingTypeIPLogRawDataView):
                #-----the checked attribute ends up in the HTML <input> tag-----
                self.IpLogRawDataHTML[checkbox] = 'checked'
            else:
                #-----newly-added checkboxes may not be in the DB yet, so set the default value in settings.IPLogRawDataView-----
                self.settings.IPLogRawDataView[checkbox] = default_value

    #--------------------------------------------------------------------------------

    def make_IpLogRawData(self, environ, filename=None):
        #-----CSP nonce required for JS to run in browser-----
        self.IpLogRawDataHTML['CSP_NONCE'] = environ['CSP_NONCE']
        self.IpLogRawDataHTML['logfile_menu'] = self.make_logfile_menu()
        self.load_settings_into_html()

        #-----initial page load, just return the page header-----
        if self.return_page_header:
            body = self.webpage.load_template('IpLogRawData')
            return body.format(**self.IpLogRawDataHTML)

        if self.limit_fields['show_max_bps_columns']:
            self.ip_log_raw_data.adjust_bps_columns(100, 5)
        else:
            self.ip_log_raw_data.adjust_bps_columns(12, 5)

        #-----send a JSON back to the AJAX function-----
        logdata_rows, entries = self.make_logdata_rows(filename)
        rowcount = len(logdata_rows)
        analysis = self.ip_log_raw_data.analyze_log_data(entries)
        all_analysis_rows = self.make_all_analysis_rows(analysis)

        #TEST
        TESTDATA = ''
        # analysis_print = pprint.pformat(analysis)
        # analysis_keys = ' '.join(analysis.keys())
        #
        # TESTDATA = f'''<p class="font-courier gray-bg">TESTDATA:<br>
        # analysis keys: {analysis_keys}<br>
        # analysis: {analysis_print}<br>
        # </p>'''
        #
        #TEST: make sure checkboxes work
        # testdata_rows = []
        # testdata_rows.append(f'''<p class="font-courier gray-bg">TESTDATA:<br>''')
        # for checkbox_field in self.checkbox_fields:
        #     testdata_rows.append(f'''{checkbox_field}: {self.limit_fields[checkbox_field]}<br>''')
        # testdata_rows.append('''</p>''')
        # TESTDATA = '\n'.join(testdata_rows)

        bps_limit_displayed = ''
        if analysis['duration'] > self.ip_log_raw_data.bps_time_limit:
            bps_limit_displayed = f'({self.ip_log_raw_data.bps_increment_size}-second bps columns shown, up to {self.ip_log_raw_data.bps_time_limit} seconds)'

        displayed_src_ports = ''
        if self.displayed_raw_data_src_ports:
            displayed_src_ports = '\n'.join(str(port) for port in sorted(self.displayed_raw_data_src_ports))
        displayed_dst_ports = ''
        if self.displayed_raw_data_dst_ports:
            displayed_dst_ports = '\n'.join(str(port) for port in sorted(self.displayed_raw_data_dst_ports))

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

            'displayed_src_ports': displayed_src_ports,
            'displayed_dst_ports': displayed_dst_ports,

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

    # round floats to ints if they are large, or to one decimal place if they are small
    def round_large_or_small(self, num: float):
        if num<10:
            # give it one decimal place if it's a small number
            return round(num, 1)
        return round(num)

    def make_analysis_ip_segment(self, analysis: dict, key, ip, bps_max_seconds: int) -> str:
        bps_by_segment = analysis[key][ip].get('bps_by_segment', None)
        bps_cols_list = []
        if not bps_by_segment:
            return ''

        # segment is labeled by its end value, so data from the 5-10 second range is labeled as 10
        for segment in range(5, bps_max_seconds+1, 5):
            bps = 0
            pps = 0
            flags = 0
            segment_info = analysis[key][ip]['bps_by_segment'].get(segment, None)
            if segment_info:
                bps = self.round_large_or_small(segment_info['bps'])
                pps = self.round_large_or_small(segment_info['pps'])
                flags = segment_info['flags']
            highlight_class = ''
            if flags:
                highlight_class = 'warning_text'
            bps_cols_list.append(f'<td class="{highlight_class} right_align">{bps}<br>{pps}</td>')

        return ''.join(bps_cols_list)

    #--------------------------------------------------------------------------------

    # this function assumes that make_logdata_rows() has been called first, to populate the displayed_raw_data_src_ips and displayed_raw_data_dst_ips sets
    # key: 'analysis_by_src_ip' or 'analysis_by_dst_ip'
    # colname: 'Source IP' or 'Destination IP'
    def make_analysis_rows(self, analysis: dict, key: str, colname: str) -> list:
        if not analysis[key]:
            return ['']

        bps_max_seconds = int(analysis['duration']/5)*5
        if bps_max_seconds > self.ip_log_raw_data.bps_time_limit:
            # over 60 seconds of data results in too many columns, so limit it to 60 seconds
            bps_max_seconds = self.ip_log_raw_data.bps_time_limit
        bps_header = ''
        for segment in range(0, bps_max_seconds-4, 5):
            bps_header += f'<th>bps({segment}-{segment+5})<br>pps</th>'

        analysis_rows = [f'''<tr>
<th>{colname}</th>
<th>Packets</th>
<th>pkts/sec</th>
<th>Total Bytes</th>
<th>bytes/sec</th>
{bps_header}
</tr>''']
        view_has_limits = self.has_limits()

        #TODO: apply the sort_by menu to sort the rows by IPs, packets, or bytes
        # sort packets/bytes descending, IPs ascending
        # analysis_dict[ip]
        # analysis_dict[packets-ip]
        # analysis_dict[bytes-ip]
        analysis_dict = {}
        for ip in sorted(analysis[key].keys()):
            if ip in self.ConfigData['HideIPs']:
                # for running demos without exposing the real client IPs or other things that should be hidden
                continue

            # limit the displayed IPs to only those that are in the raw data
            if key=='analysis_by_src_ip' and not ip in self.displayed_raw_data_src_ips:
                continue
            if key=='analysis_by_dst_ip' and not ip in self.displayed_raw_data_dst_ips:
                continue

            if view_has_limits:
                if not self.check_all_limits(key, ip):
                    continue

            ip_data = self.logparser.make_ip_analysis_links(ip, highlight_ips=False, include_blocking_links=False, rdns_popup=True)
            total_bytes = analysis[key][ip]['length']
            total_packets = analysis[key][ip]['packets']
            bytes_per_sec = 0
            packets_per_sec = 0
            if analysis['duration']:
                bytes_per_sec = int(total_bytes / analysis['duration'])
                packets_per_sec = int(total_packets / analysis['duration'])
            bps_cols = self.make_analysis_ip_segment(analysis, key, ip, bps_max_seconds)
            row = f'''<tr>
<td><span class="cursor_copy">{ip}</span>&nbsp;{ip_data['ip_analysis_links']}</td>
<td class="right_align">{total_packets}</td>
<td class="right_align">{packets_per_sec}</td>
<td class="right_align">{total_bytes}</td>
<td class="right_align">{bytes_per_sec}</td>
{bps_cols}
</tr>'''
            #OLD:
            # analysis_rows.append(row)

            sort_by_key = ip
            if self.sort_by=='packets':
                # multiple entries may have the same packet count, so sort by IP if packets are equal
                # pad with a lot of zeros to help sorting
                sort_by_key = f'{total_packets:012}-{ip}'
            elif self.sort_by=='bytes':
                # multiple entries may have the same bytes count, so sort by IP if bytes are equal
                # pad with a lot of zeros to help sorting
                sort_by_key = f'{total_bytes:012}-{ip}'
            analysis_dict[sort_by_key] = row

        # sort the rows as needed
        for sort_by_key in sorted(analysis_dict.keys(), reverse=True):
            analysis_rows.append(analysis_dict[sort_by_key])

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
                readable_timestamp_utc = self.util.current_datetime(timestamp, localize_timezone=False)
                output.append(f'<option value="ipv4.log-{timestamp}">{readable_timestamp} ({readable_timestamp_utc}UTC)</option>')
        return '\n'.join(output)

    #--------------------------------------------------------------------------------

    def highlight_uncommon_values(self, name, value) -> str:
        '''returns the HTML for the logfile menu'''
        found_value = self.ip_log_raw_data.common_field_values.get(name, None)
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
        # if self.limit_fields['hide_internal_connections'] or self.limit_fields['src_ip'] or self.limit_fields['dst_ip'] or self.limit_fields['src_ports'] or self.limit_fields['dst_ports']:
        #     return True
        for limit_field in self.limit_fields.keys():
            if self.limit_fields[limit_field]:
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

    # return value of False means that key failed a test, so the row should be skipped
    def check_all_limits(self, key, ip) -> bool:
        if key=='analysis_by_src_ip' and not self.check_limit_field('src_ip', ip):
            return False
        elif key=='analysis_by_dst_ip' and not self.check_limit_field('dst_ip', ip):
            return False
        return True

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

        #-----skip rows not matching limit field text boxes-----
        if self.limit_fields['src_ip'] or self.limit_fields['dst_ip'] or self.limit_fields['src_ports'] or self.limit_fields['dst_ports']:
            #-----limit field text boxes have data, so check those limits-----
            ok_to_display_src_ip = self.check_limit_field('src_ip', entry['src'])
            ok_to_display_dst_ip = self.check_limit_field('dst_ip', entry['dst'])
            ok_to_display_src_ports = self.check_limit_field('src_ports', str(entry['SPT']))
            ok_to_display_dst_ports = self.check_limit_field('dst_ports', str(entry['DPT']))
            if not ((ok_to_display_src_ip and ok_to_display_src_ports ) or (ok_to_display_dst_ip and ok_to_display_dst_ports)):
                #TEST: print the entry that was skipped
                # self.count_test_prints += 1
                # if self.count_test_prints < 10:
                #     show_entry_info = f'''src={entry['src']}, dst={entry['dst']}, SPT={entry['SPT']} DPT={entry['DPT']}'''
                #     print(f'''entry skipped: {show_entry_info}\ntest flags: ok_to_display_src_ip={ok_to_display_src_ip} ok_to_display_dst_ip={ok_to_display_dst_ip} ok_to_display_src_ports={ok_to_display_src_ports} ok_to_display_dst_ports={ok_to_display_dst_ports}''')
                return None

        #-----apply the checkboxes-----
        # default to allowing the row to display
        # 'flags_any', 'flags_none', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_tcp', 'protocol_udp', 'protocol_icmp', 'protocol_other'
        ok_to_display = True

        # type: accepted, blocked
        if entry['type']=='accepted':
            if not self.limit_fields['include_accepted_packets']:
                ok_to_display = False
        else:
            # type=blocked is the only other option
            if not self.limit_fields['include_blocked_packets']:
                ok_to_display = False

        # FLAGS
        if entry['msg']:
            if not self.limit_fields['flags_any']:
                ok_to_display = False
        else:
            if not self.limit_fields['flags_none']:
                ok_to_display = False

        # PREC/TOS
        if entry['PREC']=='0x00' and entry['TOS']=='0x00':
            if not self.limit_fields['prec_tos_zero']:
                ok_to_display = False
        else:
            if not self.limit_fields['prec_tos_nonzero']:
                ok_to_display = False

        # protocol: TCP, UDP, ICMP, other
        if entry['PROTO']=='TCP':
            if not self.limit_fields['protocol_tcp']:
                ok_to_display = False
        elif entry['PROTO']=='UDP':
            if not self.limit_fields['protocol_udp']:
                ok_to_display = False
        elif entry['PROTO']=='ICMP':
            if not self.limit_fields['protocol_icmp']:
                ok_to_display = False
        else:
            if not self.limit_fields['protocol_other']:
                ok_to_display = False

        if not ok_to_display:
            # don't display this row
            return None

        # note the IP addresses that are displayed in the raw data
        if entry['src']:
            self.displayed_raw_data_src_ips.add(entry['src'])
        if entry['dst']:
            self.displayed_raw_data_dst_ips.add(entry['dst'])
        # note the ports that are displayed in the raw data
        if entry['SPT']:
            self.displayed_raw_data_src_ports.add(entry['SPT'])
        if entry['DPT']:
            self.displayed_raw_data_dst_ports.add(entry['DPT'])

        # display_entry will look different than entry, so make a complete copy of the dictionary
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
<td class="wrap_text">{entry['msg']}</td>
</tr>'''
        return logdata_row

    #--------------------------------------------------------------------------------

    #-----display table of raw packet metadata for each packet-----
    def make_logdata_rows(self, filename: str):
        '''returns the log data table rows'''
        # table_cols = 12
        filepath = f'{self.ConfigData["Directory"]["IPtablesLog"]}/{filename}'
        if not os.path.isfile(filepath):
            logdata_rows = [f'<tr><td>ERROR: logfile not found "{filename}"<br>Try refreshing the page to get the latest list of logs<br>Check the box "Auto-update file list" to keep the list current</td></tr>']
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
