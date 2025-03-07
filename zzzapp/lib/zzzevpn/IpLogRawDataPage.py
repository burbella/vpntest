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
    iptables_rules: zzzevpn.IPtablesRules = None
    logparser: zzzevpn.LogParser = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None

    IpLogRawDataHTML = {}
    service_name = 'iptables'

    sort_by = 'ip' # ip, packets, bytes
    allowed_sort_by = ['ip', 'packets', 'bytes']

    # store ipaddress objects here
    net_objects = {
        'src_ip': {},
        'dst_ip': {},
    }
    # store data from the POST in these fields
    limit_fields = {
        'auto_update_file_list': False,
        'extra_analysis': False,
        'min_displayed_packets': 1,
        # text boxes
        'src_ip': set(),
        'dst_ip': set(),
        'src_ports': set(),
        'dst_ports': set(),
        'search_length': set(),
        'ttl': set(),
        # connection type
        'connection_external': False,
        'connection_inbound': True,
        'connection_internal': False,
        'connection_outbound': True,
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

    text_fields = ['dst_ip', 'dst_ports', 'search_length', 'src_ip', 'src_ports', 'ttl']
    range_allowed_fields = ['dst_ports', 'src_ports', 'search_length', 'ttl']
    checkbox_fields = ['auto_update_file_list', 'connection_external', 'connection_inbound', 'connection_internal', 'connection_outbound', 'extra_analysis', 'flags_any', 'flags_none', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_tcp', 'protocol_udp', 'protocol_icmp', 'protocol_other', 'show_max_bps_columns']
    allowed_post_params = ['action', 'auto_update_file_list', 'connection_external', 'connection_inbound', 'connection_internal', 'connection_outbound', 'dst_ip', 'dst_ports', 'extra_analysis', 'filename', 'flag_bps_above_value', 'flag_pps_above_value', 'flags_any', 'flags_none', 'include_accepted_packets', 'include_blocked_packets', 'min_displayed_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_icmp', 'protocol_other', 'protocol_tcp', 'protocol_udp', 'search_length', 'show_max_bps_columns', 'sort_by', 'src_ip', 'src_ports', 'ttl']
    actions_requiring_filenames = {'delete_logfile', 'save_logfile', 'view_log', 'view_saved_log', 'view_raw_text', 'saved_view_raw_text'}

    # used to make sure only IPs in the displayed raw data are also displayed in the bps analysis tables
    displayed_raw_data_src_ips = set()
    displayed_raw_data_dst_ips = set()

    displayed_raw_data_src_ports = set()
    displayed_raw_data_dst_ports = set()
    displayed_packet_lengths = set()
    displayed_packet_header_lengths = set()
    displayed_packet_payload_lengths = set()
    displayed_packet_ttls = set()

    count_test_prints = 0
    errors = []

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
        self.iptables_rules = zzzevpn.IPtablesRules(self.ConfigData, self.db, self.util, self.settings)
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)
        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        self.count_test_prints = 0
        self.errors = []

        self.limit_fields = {
            'src_ip': set(),
            'dst_ip': set(),
            'src_ports': set(),
            'dst_ports': set(),
            'search_length': set(),
            'ttl': set(),
        }
        for checkbox_field in self.checkbox_fields:
            self.limit_fields[checkbox_field] = False

        self.displayed_raw_data_src_ips = set()
        self.displayed_raw_data_dst_ips = set()
        self.displayed_raw_data_src_ports = set()
        self.displayed_raw_data_dst_ports = set()
        self.displayed_packet_lengths = set()
        self.displayed_packet_header_lengths = set()
        self.displayed_packet_payload_lengths = set()
        self.displayed_packet_ttls = set()

        #-----prep the HTML values-----
        self.IpLogRawDataHTML = {
            'flag_bps_default': self.settings.IPLogRawDataView_default['flag_bps_above_value'],
            'flag_pps_default': self.settings.IPLogRawDataView_default['flag_pps_above_value'],
            'logfile_menu': '',
            'logrotate_numfiles': self.ConfigData['LogRotate']['NumFiles'],
            'min_displayed_packets_default': self.settings.IPLogRawDataView_default['min_displayed_packets'],
            'hide_view_raw_text': '',
            'saved_logfile_menu': '',
            'hide_saved_view_raw_text': '',
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
        if (data['action'] in self.actions_requiring_filenames) and (data['filename'] is None):
            # filename only applies to view/save log actions
            return self.webpage.error_log(environ, 'ERROR: missing filename')

        self.process_range_params(data)

        if data['dst_ip']:
            self.limit_fields['dst_ip'], self.net_objects['dst_ip'] = self.parse_cidr_list(data['dst_ip'])
        if data['sort_by'] and data['sort_by'] in self.allowed_sort_by:
            self.sort_by = data['sort_by']
        else:
            self.sort_by = 'ip'
        if data['src_ip']:
            self.limit_fields['src_ip'], self.net_objects['src_ip'] = self.parse_cidr_list(data['src_ip'])

        if data['min_displayed_packets']:
            self.limit_fields['min_displayed_packets'] = self.util.standalone.get_int_safe(data['min_displayed_packets'])

        self.load_js_checkbox_data(data)

        if data['action']=='get_logfile_menu':
            return self.get_logfile_menu()
        elif data['action'] in {'view_log', 'view_saved_log'}:
            # save the latest settings
            self.store_data_in_settings(data)
            self.settings.save_ip_log_view_settings()
            return self.view_log_analysis(data['filename'], data['action'])
        elif data['action']=='save_logfile':
            return self.save_logfile(data['filename'])
        elif data['action']=='delete_logfile':
            return self.delete_logfile(data['filename'])
        elif data['action']=='delete_all_logfiles':
            return self.delete_all_logfiles()
        elif data['action'] in ['view_raw_text', 'saved_view_raw_text']:
            return self.view_raw_text(data['filename'], data['action'])

        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')

    #--------------------------------------------------------------------------------

    def process_range_params(self, data: dict):
        for range_param in self.range_allowed_fields:
            if not data[range_param]:
                continue

            valid_max = 65535
            if range_param=='ttl':
                valid_max = 255

            self.limit_fields[range_param] = set()
            translation_result = self.iptables_rules.translate_ranges_str_to_set(data[range_param], valid_max, field_name=range_param)

            if translation_result['error_msg']:
                self.errors.extend(translation_result['error_msg'])

            # return the valid numbers as strings for searching
            if translation_result['numbers']:
                for number in translation_result['numbers']:
                    self.limit_fields[range_param].add(str(number))

    #--------------------------------------------------------------------------------

    #TODO: limit the number of saves to avoid filling up the disk
    def save_logfile(self, filename: str):
        #-----save the logfile to the saved logs directory-----
        if not filename:
            return self.make_return_json_error('ERROR: missing filename')

        #-----queue the request for the daemon to process-----
        did_insert = self.db.insert_unique_service_request(self.service_name, 'save_logfile', filename)
        if did_insert:
            # signal the daemon that there is work to do
            self.util.work_available(1)

        filepath = f'''{self.ConfigData['Directory']['IPtablesSavedLog']}/{filename}'''
        data_to_send = {
            'status': 'success',
            'error_msg': '',
            'saved_logfile_menu_entry': self.logfile_menu_entry(filepath),
        }
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    #--------------------------------------------------------------------------------

    def delete_logfile(self, filename: str):
        #-----delete the logfile from the saved logs directory-----
        if not filename:
            return self.make_return_json_error('ERROR: missing filename')

        #-----queue the request for the daemon to process-----
        did_insert = self.db.insert_unique_service_request(self.service_name, 'delete_logfile', filename)
        if did_insert:
            # signal the daemon that there is work to do
            self.util.work_available(1)

        data_to_send = {
            'status': 'success',
            'error_msg': '',
        }
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    def delete_all_logfiles(self):
        #-----delete all logfiles from the saved logs directory-----
        #-----queue the request for the daemon to process-----
        did_insert = self.db.insert_unique_service_request(self.service_name, 'delete_all_logfiles', '')
        if did_insert:
            # signal the daemon that there is work to do
            self.util.work_available(1)

        data_to_send = {
            'status': 'success',
            'error_msg': '',
        }
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    #--------------------------------------------------------------------------------

    #-----store the data from the POST into the settings var IPLogRawDataView-----
    def store_data_in_settings(self, data: dict):
        # allow zero here
        self.settings.IPLogRawDataView['flag_bps_above_value'] = self.util.standalone.get_int_safe(data['flag_bps_above_value'])
        self.settings.IPLogRawDataView['flag_pps_above_value'] = self.util.standalone.get_int_safe(data['flag_pps_above_value'])
        self.settings.IPLogRawDataView['min_displayed_packets'] = self.util.standalone.get_int_safe(data['min_displayed_packets'])

        for textbox in self.text_fields:
            if data[textbox] is None:
                self.settings.IPLogRawDataView[textbox] = ''
            else:
                # store the raw data in the settings, even with mistypes
                self.settings.IPLogRawDataView[textbox] = data[textbox]

        if data['sort_by'] in self.allowed_sort_by:
            self.settings.IPLogRawDataView['sort_by'] = data['sort_by']
        else:
            self.settings.IPLogRawDataView['sort_by'] = 'ip'

        for checkbox_field in self.checkbox_fields:
            self.settings.IPLogRawDataView[checkbox_field] = data[checkbox_field]

    #--------------------------------------------------------------------------------

    # list items can be either IP's or CIDR: 1.2.3.0/24,2.3.4.5
    def parse_cidr_list(self, cidr_list: str):
        if not cidr_list:
            return set()

        cidr_list = self.util.standalone.whitespace_to_commas(cidr_list)
        net_objects = {}
        raw_data_set = set()
        for item in cidr_list.split(','):
            #-----verify that the item is a valid IP or CIDR before adding to the set-----
            if '/' in item:
                #-----CIDR-----
                cidr = self.util.ip_util.is_cidr(item)
                if cidr:
                    # add the string
                    raw_data_set.add(item)
                    # add the IPNetwork object since it will be needed later for many calculations
                    net_objects[item] = cidr
            else:
                #-----IP-----
                ip = self.util.ip_util.is_ip(item)
                if ip:
                    # add the string
                    raw_data_set.add(item)

        return raw_data_set, net_objects

    #--------------------------------------------------------------------------------

    def get_logfile_menu(self):
        # load the saved logfiles first, so the logfiles menu can be highlighted with matches
        saved_logfile_menu = self.make_saved_logfile_menu()
        logfile_menu = self.make_logfile_menu()
        data_to_send = {
            'status': 'success',
            'error_msg': '',
            'logfile_menu': logfile_menu,
            'saved_logfile_menu': saved_logfile_menu,
        }
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    #--------------------------------------------------------------------------------

    def load_js_checkbox_data(self, data: dict):
        for checkbox_field in self.checkbox_fields:
            self.limit_fields[checkbox_field] = self.util.js_string_to_python_bool(data[checkbox_field])

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle):
        self.webpage.update_header(environ, pagetitle)
    
        output = self.webpage.make_webpage(environ, self.make_IpLogRawData(environ))
    
        return output

    #--------------------------------------------------------------------------------

    def raw_text_buttons(self):
        # only show the raw text buttons if the dev checkbox is checked
        if self.settings.is_setting_enabled('show_dev_tools'):
            return
        self.IpLogRawDataHTML['hide_view_raw_text'] = 'hide_item'
        self.IpLogRawDataHTML['hide_saved_view_raw_text'] = 'hide_item'

    #--------------------------------------------------------------------------------

    # settings from the settings.IPLogRawDataView need to be put in self.IpLogRawDataHTML
    def load_settings_into_html(self):
        self.IpLogRawDataHTML['saved_logfile_menu'] = self.make_saved_logfile_menu()
        self.IpLogRawDataHTML['logfile_menu'] = self.make_logfile_menu()

        # load the raw data in the HTML, even with saved user mistypes
        self.IpLogRawDataHTML['dst_ip'] = self.settings.IPLogRawDataView['dst_ip']
        self.IpLogRawDataHTML['dst_ports'] = self.settings.IPLogRawDataView['dst_ports']
        self.IpLogRawDataHTML['flag_bps_above_value'] = self.settings.IPLogRawDataView['flag_bps_above_value']
        self.IpLogRawDataHTML['flag_pps_above_value'] = self.settings.IPLogRawDataView['flag_pps_above_value']
        self.IpLogRawDataHTML['min_displayed_packets'] = self.settings.IPLogRawDataView['min_displayed_packets']
        self.IpLogRawDataHTML['search_length'] = self.settings.IPLogRawDataView['search_length']
        self.IpLogRawDataHTML['sort_by'] = self.settings.IPLogRawDataView['sort_by']
        self.IpLogRawDataHTML['src_ip'] = self.settings.IPLogRawDataView['src_ip']
        self.IpLogRawDataHTML['src_ports'] = self.settings.IPLogRawDataView['src_ports']
        self.IpLogRawDataHTML['ttl'] = self.settings.IPLogRawDataView['ttl']

        self.raw_text_buttons()

        # Format:
        # self.IpLogRawDataHTML['CHECKBOX_ID'] = self.settings.is_setting_enabled('CHECKBOX_ID', self.settings.SettingTypeIPLogRawDataView)
        default_value = 'true'
        for checkbox in self.checkbox_fields:
            self.IpLogRawDataHTML[checkbox] = self.limit_fields[checkbox]
            if self.settings.is_setting_enabled(checkbox, self.settings.SettingTypeIPLogRawDataView):
                #-----the checked attribute ends up in the HTML <input> tag-----
                self.IpLogRawDataHTML[checkbox] = 'checked'
            else:
                #-----newly-added checkboxes may not be in the DB yet, so set the default value in settings.IPLogRawDataView-----
                self.settings.IPLogRawDataView[checkbox] = default_value

    #--------------------------------------------------------------------------------

    def numbers_to_printable_str(self, numbers: list) -> str:
        if not numbers:
            return ''
        return '\n'.join(str(number) for number in sorted(numbers))

    #--------------------------------------------------------------------------------

    def is_logfile_saved(self, filename: str) -> bool:
        filepath = f'''{self.ConfigData['Directory']['IPtablesSavedLog']}/{filename}'''
        return os.path.exists(filepath)

    #--------------------------------------------------------------------------------

    def view_logfile(self, filename: str, action: str=None) -> str:
        return

    #--------------------------------------------------------------------------------

    def view_raw_text(self, filename: str, action: str=None) -> str:
        filepath = f'''{self.ConfigData['Directory']['IPtablesLog']}/{filename}'''
        if action=='saved_view_raw_text':
            filepath = f'''{self.ConfigData['Directory']['IPtablesSavedLog']}/{filename}'''

        filedata = self.util.get_filedata(filepath)
        if not filedata:
            return self.make_return_json_error('logfile not found')
        logdata_html = self.util.make_html_display_safe(filedata)
        logdata_html = f'''<tr><td class="whitespace_pre no_border">{logdata_html}</td></tr>'''

        data_to_send = {
            'status': 'success',
            'error_msg': '',
            'logdata': logdata_html,
        }
        json_data_to_send = json.dumps(data_to_send)

        return json_data_to_send

    #--------------------------------------------------------------------------------

    def view_log_analysis(self, filename: str, action: str) -> str:
        if self.limit_fields['show_max_bps_columns']:
            self.ip_log_raw_data.adjust_bps_columns(100, 5)
        else:
            self.ip_log_raw_data.adjust_bps_columns(12, 5)

        #-----send a JSON back to the AJAX function-----
        logdata_rows, entries = self.make_logdata_rows(filename, action)
        rowcount = len(logdata_rows)
        analysis = self.ip_log_raw_data.analyze_log_data(entries, extra_analysis=self.limit_fields['extra_analysis'])
        all_analysis_rows = self.make_all_analysis_rows(analysis)

        bps_limit_displayed = ''
        if analysis['duration'] > self.ip_log_raw_data.bps_time_limit:
            bps_limit_displayed = f'({self.ip_log_raw_data.bps_increment_size}-second bps columns shown, up to {self.ip_log_raw_data.bps_time_limit} seconds)'

        # note the source IPs that are not in the destination IPs
        displayed_src_not_in_dst = self.displayed_raw_data_src_ips - self.displayed_raw_data_dst_ips
        displayed_dst_not_in_src = self.displayed_raw_data_dst_ips - self.displayed_raw_data_src_ips
        limit_field_errors = ''
        if self.errors:
            limit_field_errors = self.util.ascii_to_html_with_line_breaks('\n'.join(self.errors))

        data_to_send = {
            'status': 'success',
            'error_msg': '',

            'limit_field_errors': limit_field_errors,
            'logdata': '\n'.join(logdata_rows),

            'src_ip_analysis': '\n'.join(all_analysis_rows['src_analysis_rows']),
            'dst_ip_analysis': '\n'.join(all_analysis_rows['dst_analysis_rows']),

            'src_length_analysis': '\n'.join(all_analysis_rows['src_length_analysis_rows']),
            'dst_length_analysis': '\n'.join(all_analysis_rows['dst_length_analysis_rows']),
            'summary_src_length_analysis': '\n'.join(all_analysis_rows['summary_src_length_analysis_rows']),

            'rowcount': rowcount,
            'start_timestamp': analysis['datetime_start'].strftime(self.util.date_format_seconds),
            'end_timestamp': analysis['datetime_end'].strftime(self.util.date_format_seconds),
            'duration': analysis['duration'],
            'bps_limit_displayed': bps_limit_displayed,

            'displayed_src_ports': self.numbers_to_printable_str(self.displayed_raw_data_src_ports),
            'displayed_dst_ports': self.numbers_to_printable_str(self.displayed_raw_data_dst_ports),
            'displayed_packet_lengths': self.numbers_to_printable_str(self.displayed_packet_lengths),
            'displayed_packet_header_lengths': self.numbers_to_printable_str(self.displayed_packet_header_lengths),
            'displayed_packet_payload_lengths': self.numbers_to_printable_str(self.displayed_packet_payload_lengths),
            'displayed_packet_ttls': self.numbers_to_printable_str(self.displayed_packet_ttls),
            'displayed_src_not_in_dst': '\n'.join(sorted(displayed_src_not_in_dst)),
            'displayed_dst_not_in_src': '\n'.join(sorted(displayed_dst_not_in_src)),

            'calculation_time': analysis['calculation_time'],
            'filename': filename,
            'is_logfile_saved': self.is_logfile_saved(filename),

            'TESTDATA': '',
        }
        json_data_to_send = json.dumps(data_to_send)

        return json_data_to_send

    #--------------------------------------------------------------------------------

    def make_IpLogRawData(self, environ: dict) -> str:
        #-----CSP nonce required for JS to run in browser-----
        self.IpLogRawDataHTML['CSP_NONCE'] = environ['CSP_NONCE']
        self.load_settings_into_html()
        body = self.webpage.load_template('IpLogRawData')
        return body.format(**self.IpLogRawDataHTML)

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

    #--------------------------------------------------------------------------------

    def make_analysis_ip_segment(self, analysis: dict, key, ip, bps_max_seconds: int, rowcolor: str='') -> str:
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
            if flags>4:
                # major flags value
                highlight_class = 'warning_text_red_dark'
                # if rowcolor=='':
                #     highlight_class = 'warning_text_red_dark'
                # else:
                #     highlight_class = 'warning_text_red'
            elif flags>0:
                # minor flags value
                highlight_class = 'warning_text_dark'
                # if rowcolor=='':
                #     highlight_class = 'warning_text_dark'
                # else:
                #     highlight_class = 'warning_text'
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
            bps_header += f'<th>{segment}-{segment+5}<br>bps<br>pps</th>'

        analysis_rows = [f'''<tr>
<th>{colname}</th>
<th>Country</th>
<th>Packets</th>
<th>pkts<br>/sec</th>
<th>Total<br>Bytes</th>
<th>bytes<br>/sec</th>
{bps_header}
</tr>''']
        view_has_limits = self.has_limits()

        #TODO: apply the sort_by menu to sort the rows by IPs, packets, or bytes
        # sort packets/bytes descending, IPs ascending
        # analysis_sortable[ip]
        # analysis_sortable[packets-ip]
        # analysis_sortable[bytes-ip]
        analysis_sortable = {}
        rowcolor = ''
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
                if not self.check_all_limits(key, ip, analysis[key][ip]['packets']):
                    continue

            ip_data = self.logparser.make_ip_analysis_links(ip, highlight_ips=False, include_blocking_links=True, rdns_popup=True)
            total_bytes = analysis[key][ip]['length']
            total_packets = analysis[key][ip]['packets']
            bytes_per_sec = 0
            packets_per_sec = 0
            if analysis['duration']:
                bytes_per_sec = int(total_bytes / analysis['duration'])
                packets_per_sec = int(total_packets / analysis['duration'])
            bps_cols = self.make_analysis_ip_segment(analysis, key, ip, bps_max_seconds, rowcolor)
            country_code = self.util.lookup_ip_country(ip)
            country = self.ConfigData['OfficialCountries'].get(country_code, 'UNKNOWN')
            row = f'''<tr class="{rowcolor}">
<td><span class="cursor_copy">{ip}</span>&nbsp;{ip_data['ip_analysis_links']}</td>
<td class="wrap_text">{country}</td>
<td class="right_align">{total_packets}</td>
<td class="right_align">{packets_per_sec}</td>
<td class="right_align">{total_bytes}</td>
<td class="right_align">{bytes_per_sec}</td>
{bps_cols}
</tr>'''
            rowcolor = self.util.swap_rowcolor(rowcolor)

            sort_by_key = ip
            if self.sort_by=='packets':
                # multiple entries may have the same packet count, so sort by IP if packets are equal
                # pad with a lot of zeros to help sorting
                sort_by_key = f'{total_packets:012}-{ip}'
            elif self.sort_by=='bytes':
                # multiple entries may have the same bytes count, so sort by IP if bytes are equal
                # pad with a lot of zeros to help sorting
                sort_by_key = f'{total_bytes:012}-{ip}'
            analysis_sortable[sort_by_key] = row

        # sort the rows as needed
        for sort_by_key in sorted(analysis_sortable.keys(), reverse=True):
            analysis_rows.append(analysis_sortable[sort_by_key])

        return analysis_rows

    #--------------------------------------------------------------------------------

    #TODO: some IPs may only be in the dst_ip analysis, so they won't show up in the src_ip analysis
    #
    # length_analysis_rows['src_ip']['summary'] = []
    def make_length_summary_rows(self, analysis: dict, length_analysis_rows: dict):
        # don't let the html table get too big
        max_rows = 5000
        row_count = 0
        length_keys = analysis['length_analysis']['src_ip']['summary'].keys()
        for length in sorted(length_keys):
            row_count += 1
            if row_count > max_rows:
                break
            info_by_length = analysis['length_analysis']['src_ip']['summary'][length]
            packets = info_by_length['packets']
            percent = info_by_length['percent']
            if packets<self.settings.IPLogRawDataView['min_displayed_packets']:
                # only show rows with at least 10 packets
                continue
            row = f'''<tr>
            <td class="right_align">{length}</td>
            <td class="right_align">{packets}</td>
            <td class="right_align">{percent}</td>
            </tr>'''
            length_analysis_rows['src_ip']['summary'].append(row)

    def make_length_details_rows(self, analysis: dict, src_or_dst: str, length_analysis_rows: dict):
        # don't let the html table get too big
        max_rows = 5000
        row_count = 0
        view_has_limits = self.has_limits()
        ip_keys = analysis['length_analysis'][src_or_dst]['details'].keys()
        for ip in sorted(ip_keys):
            length_keys = analysis['length_analysis'][src_or_dst]['details'][ip].keys()
            # make all keys str() so they sort correctly
            length_keys = [str(key) for key in length_keys]
            for length_str in sorted(length_keys):
                # if length_str=='total':
                #     # don't show the total row
                #     continue
                if (not ip in self.displayed_raw_data_src_ips) and (not ip in self.displayed_raw_data_dst_ips):
                    # apply the same IP limits to the length analysis
                    continue
                if view_has_limits:
                    if not self.check_limit_field(src_or_dst, ip):
                        continue

                # back to int
                length = int(length_str)

                row_count += 1
                if row_count > max_rows:
                    break
                packets = analysis['length_analysis'][src_or_dst]['details'][ip][length]['packets']
                if packets<self.settings.IPLogRawDataView['min_displayed_packets']:
                    # only show rows with at least 10 packets
                    continue
                show_ip = ip
                if ip in self.ConfigData['HideIPs']:
                    # for running demos without exposing the real client IPs or other things that should be hidden
                    show_ip = 'hidden'
                percent = analysis['length_analysis'][src_or_dst]['details'][ip][length]['percent']
                row = f'''<tr>
                <td>{show_ip}</td>
                <td class="right_align">{length}</td>
                <td class="right_align">{packets}</td>
                <td class="right_align">{percent}</td>
                </tr>'''
                length_analysis_rows[src_or_dst]['details'].append(row)

    # make HTML table rows to show extra analysis: packet length distribution
    # analysis['length_analysis']['src_ip']['summary'][length] = packets
    # analysis['length_analysis']['src_ip']['details'][ip][length] = packets
    # analysis['length_analysis']['dst_ip']['details'][ip][length] = packets
    def make_extra_analysis_rows(self, analysis: dict) -> dict:
        # html table header rows
        length_analysis_rows = {
            'src_ip': {
                'summary': [
                    '''<tr><th>Length</th><th>Packets</th><th>Percent</th></tr>'''
                ],
                'details': [
                    '''<tr><th>Source IP</th><th>Length</th><th>Packets</th><th>Percent</th></tr>'''
                ],
            },
            'dst_ip': {
                'details': [
                    '''<tr><th>Destination IP</th><th>Length</th><th>Packets</th><th>Percent</th></tr>'''
                ],
            },
        }
        if (not analysis['length_analysis']) or (not self.limit_fields['extra_analysis']):
            return length_analysis_rows

        self.make_length_summary_rows(analysis, length_analysis_rows)
        for src_or_dst in ['src_ip', 'dst_ip']:
            self.make_length_details_rows(analysis, src_or_dst, length_analysis_rows)

        return length_analysis_rows

    #--------------------------------------------------------------------------------

    #-----make the analysis rows from the output of ip_log_raw_data.analyze_log_data()-----
    def make_all_analysis_rows(self, analysis: dict) -> dict:
        if not analysis['analysis_by_src_ip'] and not analysis['analysis_by_dst_ip']:
            return {
                'src_analysis_rows': [''],
                'dst_analysis_rows': [''],
                'src_length_analysis_rows': [''],
                'dst_length_analysis_rows': [''],
                'summary_src_length_analysis_rows': [''],
            }
        src_analysis_rows = self.make_analysis_rows(analysis, 'analysis_by_src_ip', 'Source IP')
        dst_analysis_rows = self.make_analysis_rows(analysis, 'analysis_by_dst_ip', 'Destination IP')
        length_analysis_rows = self.make_extra_analysis_rows(analysis)

        all_analysis_rows = {
            'src_analysis_rows': src_analysis_rows,
            'dst_analysis_rows': dst_analysis_rows,
            'src_length_analysis_rows': length_analysis_rows['src_ip']['details'],
            'dst_length_analysis_rows': length_analysis_rows['dst_ip']['details'],
            'summary_src_length_analysis_rows': length_analysis_rows['src_ip']['summary'],
        }
        return all_analysis_rows

    #--------------------------------------------------------------------------------

    def logfile_menu_entry(self, filepath: str, highlight_class: str='') -> str:
        #-----get the timestamp from the filename-----
        match = self.ip_log_raw_data.regex_filename_date.search(filepath)
        if not match:
            return ''
        timestamp = int(match.group(1))
        readable_timestamp = self.util.current_datetime(timestamp)
        readable_timestamp_utc = self.util.current_datetime(timestamp, localize_timezone=False)
        return f'<option value="ipv4.log-{timestamp}" class="{highlight_class}">{readable_timestamp} ({readable_timestamp_utc}UTC)</option>'

    def make_logfile_menu(self) -> str:
        '''returns the HTML for the logfile menu'''
        self.ip_log_raw_data.get_logfiles()
        if not self.ip_log_raw_data.filepath_list:
            return '<option>No logfiles found</option>'

        output = ['<option value="ipv4.log">latest</option>']
        for filepath in self.ip_log_raw_data.filepath_list:
            # split on '/' to get the filename
            filename = filepath.split('/')[-1]
            saved_filepath = f'''{self.ConfigData['Directory']['IPtablesSavedLog']}/{filename}'''
            # highlight any logs that are already saved, assumes make_saved_logfile_menu() was called first
            highlight_class = ''
            if saved_filepath in self.ip_log_raw_data.saved_log_filepath_list:
                highlight_class = 'text_green'
            entry = self.logfile_menu_entry(filepath, highlight_class=highlight_class)
            output.append(entry)

        return '\n'.join(output)

    def make_saved_logfile_menu(self) -> str:
        self.ip_log_raw_data.get_saved_logfiles()
        if not self.ip_log_raw_data.saved_log_filepath_list:
            return ''
        output = []
        for filepath in sorted(self.ip_log_raw_data.saved_log_filepath_list, reverse=True):
            entry = self.logfile_menu_entry(filepath)
            output.append(entry)

        return '\n'.join(output)

    #--------------------------------------------------------------------------------

    def highlight_uncommon_values(self, name, value, rowcolor: str='') -> str:
        '''returns the HTML for the logfile menu'''
        found_value = self.ip_log_raw_data.common_field_values.get(name, None)
        if found_value is None:
            # this name is not in the common_field_values dict
            return value
        if found_value==value:
            # this value is common, do not highlight it
            return value
        warning_class = 'warning_text_dark'
        # if rowcolor:
        #     warning_class = 'warning_text'
        return f'<span class="{warning_class}">{value}</span>'

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
<th>IP<br>Length</th>
<th>IP<br>Header</th>
<th>Payload<br>Length</th>
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

        # src_ip and dst_ip may contain cidr, so run extra tests to calculate if the value is in any CIDR's in the set
        if not field in ['src_ip', 'dst_ip']:
            return False
        for limit_item in self.limit_fields[field]:
            # limit_item is an IP or CIDR string, only CIDR strings will get a match
            ip_network_obj = self.net_objects[field].get(limit_item, None)
            if ip_network_obj:
                if self.util.ip_cidr_check(value, ip_network_obj=ip_network_obj):
                    return True

        return False

    #--------------------------------------------------------------------------------

    # return value of False means that key failed a test, so the row should be skipped
    def check_all_limits(self, key: str, ip: str, packets: int) -> bool:
        if key=='analysis_by_src_ip' and not self.check_limit_field('src_ip', ip):
            return False
        elif key=='analysis_by_dst_ip' and not self.check_limit_field('dst_ip', ip):
            return False
        if self.limit_fields['min_displayed_packets'] > packets:
            return False
        return True

    #--------------------------------------------------------------------------------

    def make_row(self, entry: dict, rowcolor: str='') -> str:
        #-----apply the connection checkboxes-----
        # 'connection_external', 'connection_inbound', 'connection_internal', 'connection_outbound'
        if entry['internal']:
            #-----skip internal connections-----
            if not self.limit_fields['connection_internal']:
                return None
        else:
            if not self.limit_fields['connection_external']:
                #-----skip external connections-----
                return None

        if entry['inbound']:
            #-----skip inbound connections-----
            if not self.limit_fields['connection_inbound']:
                return None
        else:
            if not self.limit_fields['connection_outbound']:
                #-----skip outbound connections-----
                return None

        #-----skip rows not matching limit field text boxes-----
        if self.limit_fields['src_ip'] or self.limit_fields['dst_ip'] or self.limit_fields['src_ports'] or self.limit_fields['dst_ports'] or self.limit_fields['search_length'] or self.limit_fields['ttl']:
            #-----limit field text boxes have data, so check those limits-----
            ok_to_display_src_ip = self.check_limit_field('src_ip', entry['src'])
            ok_to_display_dst_ip = self.check_limit_field('dst_ip', entry['dst'])
            ok_to_display_src_ports = self.check_limit_field('src_ports', str(entry['SPT']))
            ok_to_display_dst_ports = self.check_limit_field('dst_ports', str(entry['DPT']))
            ok_to_display_search_length = self.check_limit_field('search_length', str(entry['LEN']))
            ok_to_display_ttl = self.check_limit_field('ttl', str(entry['TTL']))
            if not ((ok_to_display_src_ip and ok_to_display_src_ports ) or (ok_to_display_dst_ip and ok_to_display_dst_ports)):
                #TEST: print the entry that was skipped
                # self.count_test_prints += 1
                # if self.count_test_prints < 10:
                #     show_entry_info = f'''src={entry['src']}, dst={entry['dst']}, SPT={entry['SPT']} DPT={entry['DPT']}'''
                #     print(f'''entry skipped: {show_entry_info}\ntest flags: ok_to_display_src_ip={ok_to_display_src_ip} ok_to_display_dst_ip={ok_to_display_dst_ip} ok_to_display_src_ports={ok_to_display_src_ports} ok_to_display_dst_ports={ok_to_display_dst_ports}''')
                return None
            if not ok_to_display_search_length:
                return None
            if not ok_to_display_ttl:
                return None

        #-----apply the remaining checkboxes-----
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
        # note the packet lengths that are displayed in the raw data
        if entry['LEN']:
            self.displayed_packet_lengths.add(entry['LEN'])
        # note the packet header lengths that are displayed in the raw data
        header_length = entry.get('header_length', None)
        if header_length is None:
            header_length = 0
        else:
            self.displayed_packet_header_lengths.add(header_length)
        # note the packet payload lengths that are displayed in the raw data
        payload_length = entry.get('payload_length', None)
        if payload_length is None:
            payload_length = 0
        else:
            self.displayed_packet_payload_lengths.add(payload_length)
        # note the packet TTLs that are displayed in the raw data
        if entry['TTL']:
            self.displayed_packet_ttls.add(entry['TTL'])

        # display_entry will look different than entry, so make a complete copy of the dictionary
        display_entry = copy.deepcopy(entry)
        for field in entry:
            if not entry[field]:
                continue
            display_entry[field] = self.highlight_uncommon_values(field, entry[field], rowcolor)

        # currently not used: pid, mac
        logdata_row = f'''
<tr class="{rowcolor}">
<td>{display_entry['datetime']}</td>
<td>{display_entry['type']}</td>
<td>{display_entry['in']}</td>
<td>{display_entry['out']}</td>
<td class="cursor_copy">{display_entry['src']}</td>
<td>{display_entry['SPT']}</td>
<td class="cursor_copy">{display_entry['dst']}</td>
<td>{display_entry['DPT']}</td>
<td class="right_align">{display_entry['LEN']}</td>
<td class="right_align">{display_entry['header_length']}</td>
<td class="right_align">{display_entry['payload_length']}</td>
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

    # when the given file is too small, get the previous file by modification date
    def get_previous_file(self, filename:str):
        filepath = f'{self.ConfigData["Directory"]["IPtablesLog"]}/{filename}'
        if not os.path.isfile(filepath):
            return None
        file_size = os.path.getsize(filepath)
        bytes_per_line = self.ConfigData['DiskSpace']['IPtablesBytesPerLine']
        # 2000 lines is enough data to analyze
        if file_size > (bytes_per_line*2000):
            # file is large enough
            return None

        # list files in the directory by modification date, choose the one before the given file
        file_list = self.util.get_file_list(self.ConfigData['Directory']['IPtablesLog'])
        previous_file = None
        for file in file_list:
            if file==filename:
                break
            previous_file = file

    #-----display table of raw packet metadata for each packet-----
    def make_logdata_rows(self, filename: str, action: str) -> tuple:
        '''returns the log data table rows'''
        # don't let the html table get too big
        max_rows = 10000
        filepath = f'{self.ConfigData["Directory"]["IPtablesLog"]}/{filename}'
        if action=='view_saved_log':
            filepath = f'{self.ConfigData["Directory"]["IPtablesSavedLog"]}/{filename}'
        if not os.path.isfile(filepath):
            logdata_rows = [f'<tr><td>ERROR: logfile not found "{filename}"<br>Try refreshing the page to get the latest list of logs<br>Check the box "Auto-update file list" to keep the list current</td></tr>']
            return logdata_rows, None

        logdata_rows = [self.make_logdata_header()]
        entries = self.ip_log_raw_data.parse_ip_log(filepath, extended_parsing=True)
        rowcount = 0
        total_rows = 0
        rowcolor = ''
        for entry in entries:
            logdata_row = self.make_row(entry, rowcolor)
            if not logdata_row:
                continue
            logdata_rows.append(logdata_row)
            rowcolor = self.util.swap_rowcolor(rowcolor)
            rowcount += 1
            if rowcount > 25:
                logdata_rows.append(self.make_logdata_header())
                rowcount = 0
            total_rows += 1
            if total_rows > max_rows:
                break

        return logdata_rows, entries

    #--------------------------------------------------------------------------------
