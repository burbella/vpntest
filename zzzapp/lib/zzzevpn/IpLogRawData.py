#-----parse raw IP log data-----

import datetime
import os
import re

#-----package with all the Zzz modules-----
import zzzevpn

class IpLogRawData:
    'parse raw IP log data'

    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None

    date_regex_pattern = None
    ip_log_regex = None
    regex_complete_pattern = None
    regex_filename_date = None

    filepath_list = []
    no_match_lines = []

    #TODO: make this a config var
    flag_bps_above_value = 20000

    # data is processed in increments of 5 seconds
    bps_increment_size = 5
    # max 12 segments(60 seconds of data), so the html table doesn't get too wide
    max_segments = 12
    bps_time_limit = bps_increment_size * max_segments

    # IPs/CIDRs that are exempt from the bps_above_value check
    # private IPs and the VPN server IP are exempt, or get might higher limits
    exempted_ips = set()

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
        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        self.filepath_list = []
        self.no_match_lines = []
        self.exempted_ips = set(self.ConfigData['ProtectedIPs'])

        #-----assemble IP log regex-----
        # 2020-02-16T00:16:01.844723 [93216.767428] zzz accepted IN=eth0 OUT= MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=172.30.0.2 DST=172.30.0.164 LEN=174 TOS=0x00 PREC=0x00 TTL=255 ID=10659 PROTO=UDP SPT=53 DPT=35500 LEN=154
        regex_date = r'(\d{4}\-\d{2}\-\d{2}T\d{2}\:\d{2}\:\d{2}\.\d{6})' # 2020-02-16T00:16:01.844723

        #TODO: rename this to PID?
        regex_timestamp = r'\[(\s*\d+\.\d+)\]' # [ 3216.767428]

        regex_app_prefix = r'zzz (accepted|blocked)'

        #-----assemble msg regex (end part of the IP log line)-----
        # regex_interface_pattern = r'(|eth\d|lo|tun\d|{})'.format(self.ConfigData['PhysicalNetworkInterfaces']['internal'])
        regex_interface_pattern = r'(|\w+)'
        regex_ip_pattern = r'([\d.]+)'
        regex_mac_pattern = r'(| MAC=| MAC=[\da-f:]+)'
        regex_rest_of_line = r'(.+?)'

        # after "OUT", there may be nothing, or an empty MAC address, or a MAC address, so no space after OUT
        self.regex_complete_pattern = r'^{} {} {} IN={} OUT={}{} SRC={} DST={} {}$'.format(regex_date, regex_timestamp, regex_app_prefix, regex_interface_pattern, regex_interface_pattern, regex_mac_pattern, regex_ip_pattern, regex_ip_pattern, regex_rest_of_line)
        self.ip_log_regex = re.compile(self.regex_complete_pattern, re.DOTALL | re.IGNORECASE | re.MULTILINE)

        #-----break the date into pieces-----
        regex_date_pieces = r'^(\d{4})\-(\d{2})\-(\d{2})T(\d{2})\:(\d{2})\:(\d{2})\.(\d{6})$'
        self.date_regex_pattern = re.compile(regex_date_pieces, re.DOTALL)

        #-----get the timestamp from the filename-----
        regex_filename_date_pattern = r'/ipv4.log\-(\d+)'
        self.regex_filename_date = re.compile(regex_filename_date_pattern, re.DOTALL)

    #--------------------------------------------------------------------------------

    # returns an entry dict created from parsed line data
    # combines some fields into a single field since IPtablesLogParser.py does not need them separated
    def parse_line_upsert(self, line: str) -> dict:
        match = self.ip_log_regex.match(line)
        if not match:
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
            # regex_timestamp group(2) is not used
            'type': match.group(3),
            'in': match.group(4),
            'out': match.group(5),
            'mac': match.group(6),
            'src': match.group(7),
            'dst': match.group(8),
            'msg': match.group(9),
        }
        return entry

    #--------------------------------------------------------------------------------

    # returns an entry dict created from parsed line data
    def parse_line_complete(self, line: str, extended_parsing: bool=False) -> dict:
        match = self.ip_log_regex.match(line)
        if not match:
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
            'pid': match.group(2),
            'type': match.group(3),
            'in': match.group(4),
            'out': match.group(5),
            'mac': match.group(6),
            'src': match.group(7),
            'dst': match.group(8),
            'msg': match.group(9),
        }

        if extended_parsing:
            # mac = ''
            # if entry['mac']:
            #     mac = entry['mac'].split('=')[1]
            entry['timestamp'] = self.timestamp_str_to_decimal(entry['datetime'])
            entry = self.parse_msg(entry)

        return entry

    #--------------------------------------------------------------------------------

    def parse_msg(self, entry:dict) -> dict:
        msg = ''
        unparsed_msgs = []
        field_names = { 'DPT', 'ID', 'LEN', 'PREC', 'PROTO', 'RES', 'SPT', 'TOS', 'TTL', 'URGP', 'WINDOW', }

        # leaving out WINDOW and URGP because they are optional
        int_fields = { 'DPT', 'ID', 'LEN', 'SPT', 'TTL', }

        common_values = {
            'PREC': '0x00',
            'TOS': '0x00',
            'RES': '0x00',
            'URGP': '0',
        }

        # make sure all fields are present, even if they need to be blank
        for field in field_names:
            entry[field] = ''

        if not entry['msg']:
            # no further processing if msg is empty
            return entry

        msg_fields = entry['msg'].strip().split(' ')
        for field in msg_fields:
            if not field:
                continue
            param = field.split('=')
            if param[0] in field_names:
                if param[0] in int_fields:
                    # cast string to int for number fields
                    entry[param[0]] = self.util.get_int_safe(param[1])
                else:
                    entry[param[0]] = param[1]
            else:
                unparsed_msgs.append(field)

        #-----dump the unparsed fields into the msg field-----
        entry['msg'] = ' '.join(unparsed_msgs)

        return entry

    #--------------------------------------------------------------------------------

    #-----parse a given iptables logfile-----
    # use parse_line_complete() on each line of the file
    # return the parsed data in a list of dicts
    # skip lines that do not match the regex
    def parse_ip_log(self, filepath: str, extended_parsing: bool=False) -> list:
        print('parse_ip_log(): ' + filepath)
        current_file_lines_parsed = 0
        entries = []
        with open(filepath, 'r') as read_file:
            for line in read_file:
                current_file_lines_parsed += 1
                line = line.strip()
                entry = self.parse_line_complete(line, extended_parsing=extended_parsing)
                if entry:
                    entries.append(entry)

        self.util.force_garbage_collection()

        return entries

    #--------------------------------------------------------------------------------

    #-----scan the log directory for logs-----
    # current log: /var/log/iptables/ipv4.log
    # rotated logs: /var/log/iptables/ipv4.log-1704121561
    # the number in the filename is the unix timestamp of the file creation date
    def get_logfiles(self, include_current_log=False, only_current_log=False):
        '''returns the list of logfiles to process'''
        self.filepath_list = []
        current_log_entry = None
        dir_to_scan = self.ConfigData['Directory']['IPtablesLog']

        #-----minimum of 1 file is expected: ipv4.log-----
        for entry in os.scandir(dir_to_scan):
            try:
                #-----skip empty files-----
                if (not entry.is_file()) or (entry.stat().st_size==0):
                    continue
                if entry.path.endswith('ipv4.log'):
                    current_log_entry = entry
                if only_current_log or not self.regex_filename_date.search(entry.path):
                    continue
                self.filepath_list.append(entry.path)
            except:
                #-----skip files that cannot be read-----
                # logrotate may be in the process of rotating the log
                continue

        #-----put the latest log at the end of the sorted list-----
        if self.filepath_list:
            self.filepath_list = sorted(self.filepath_list, reverse=True)
        if current_log_entry and include_current_log:
            self.filepath_list.append(current_log_entry.path)

    #--------------------------------------------------------------------------------

    # count packets and bytes per IP
    # convert timestamps to: decimal, datetime objects 
    def sum_data_by_ip(self, analysis_by_ip: dict, unique_ips: set, ip: str, length: int) -> dict:
        ip_initialized = analysis_by_ip.get(ip, None)
        if ip_initialized:
            analysis_by_ip[ip]['length'] += length
            analysis_by_ip[ip]['packets'] += 1
        else:
            analysis_by_ip[ip] = {
                'length': length,
                'packets': 1,
            }
            unique_ips.add(ip)
        return analysis_by_ip, unique_ips

    #--------------------------------------------------------------------------------

    #TODO: apply limits from UI fields: src_ports, dst_ports, hide_internal_connections
    # do various types of analysis on the raw log data
    # list unique IPs
    # count packets per IP (each row is one packet)
    # count amount of data per IP (sum the length field)
    def analyze_log_data(self, entries: list) -> dict:
        if not entries:
            return {
                'analysis_by_src_ip': {},
                'analysis_by_dst_ip': {},
                'unique_ips': set(),
            }

        analysis_by_src_ip = {}
        analysis_by_dst_ip = {}
        unique_ips = set()
        incremental_bps = {}

        #-----process each line-----
        for entry in entries:
            length = entry.get('LEN', 0)
            # data by src_ip
            analysis_by_src_ip, unique_ips = self.sum_data_by_ip(analysis_by_src_ip, unique_ips, entry['src'], length)
            # data by dst_ip
            analysis_by_dst_ip, unique_ips = self.sum_data_by_ip(analysis_by_dst_ip, unique_ips, entry['dst'], length)

        #-----sort by amount of data-----
        # sorted_data_per_ip = sorted(data_per_ip.items(), key=lambda kv: kv[1], reverse=True)
        # for ip, data in sorted_data_per_ip:
        #     print(f'{ip}: {data}')

        #-----sort by number of packets-----
        # sorted_packets_per_ip = sorted(packets_per_ip.items(), key=lambda kv: kv[1], reverse=True)
        # for ip, packets in sorted_packets_per_ip:
        #     print(f'{ip}: {packets}')

        #-----log entries are in order by timestamp-----
        start_timestamp = entries[0]['datetime']
        end_timestamp = entries[-1]['datetime']
        datetime_start, datetime_end, duration = self.calc_duration(start_timestamp, end_timestamp)

        analysis = {
            'analysis_by_src_ip': analysis_by_src_ip,
            'analysis_by_dst_ip': analysis_by_dst_ip,
            'incremental_bps': incremental_bps,
            'unique_ips': unique_ips,

            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,

            'datetime_start': datetime_start,
            'datetime_end': datetime_end,
            'duration': duration,
        }

        # incremental bps
        analysis = self.calc_incremental_bps(analysis, entries)
        # flag bad data
        analysis = self.flag_bad_data(analysis)

        return analysis

    #--------------------------------------------------------------------------------

    # convert a timestamp string in the format "2024-01-07T11:11:02.021770" to a datetime object
    # then get the difference in seconds
    def calc_duration(self, start_timestamp: str, end_timestamp: str) -> int:
        datetime_start = datetime.datetime.strptime(start_timestamp, self.util.date_format_hi_res)
        datetime_end = datetime.datetime.strptime(end_timestamp, self.util.date_format_hi_res)
        duration = datetime_end - datetime_start
        return datetime_start, datetime_end, duration.seconds

    #--------------------------------------------------------------------------------

    def timestamp_str_to_decimal(self, timestamp: str) -> float:
        '''convert a timestamp string in the format "2024-01-07T11:11:02.021770" to a decimal'''
        datetime_obj = datetime.datetime.strptime(timestamp, self.util.date_format_hi_res)
        return datetime_obj.timestamp()

    #--------------------------------------------------------------------------------

    # src or dst entries only
    # ips: src_ips or dst_ips
    # direction_key: 'analysis_by_src_ip' or 'analysis_by_dst_ip'
    # entry_key: 'src' or 'dst'
    def calc_incremental_bps_by_direction(self, analysis: dict, entries: dict, ips: set, direction_key: str, entry_key: str) -> dict:
        if not ips:
            return analysis

        start_segment = analysis['datetime_start'].timestamp()
        # start_segment_id = 0
        end_segment = start_segment + self.bps_increment_size
        end_segment_id = self.bps_increment_size

        # entries should be in order by timestamp because they are appended to the array as they are read from the file
        for entry in entries:
            ip = entry[entry_key]
            if ip not in ips:
                # some IP's will be DST only, so don't process them here
                continue

            timestamp = entry['timestamp']

            # does this entry belong in the current increment?
            if not(start_segment <= timestamp <= end_segment):
                # transition to the next increment
                start_segment += self.bps_increment_size
                # start_segment_id += self.bps_increment_size
                end_segment += self.bps_increment_size
                end_segment_id += self.bps_increment_size

            if end_segment_id > analysis['duration'] and end_segment_id > self.bps_increment_size:
                # the last increment may be less than 5 seconds, so don't process it
                break

            # too many segments will make the html table too wide, so exit early
            if end_segment_id > (self.max_segments * self.bps_increment_size):
                break

            if analysis[direction_key][ip].get('bps_by_segment', None) is None:
                analysis[direction_key][ip]['bps_by_segment'] = {}
            # label the entry with the timestamp of the increment it belongs to
            # add the length of the packet to the bps for the current increment
            segment_info = analysis[direction_key][ip]['bps_by_segment'].get(end_segment_id, None)
            if segment_info:
                # flags will be checked/updated elsewhere
                analysis[direction_key][ip]['bps_by_segment'][end_segment_id]['bps'] += entry['LEN'] / self.bps_increment_size
            else:
                analysis[direction_key][ip]['bps_by_segment'][end_segment_id] = {
                    'bps': entry['LEN'] / self.bps_increment_size,
                    'flags': 0,
                }

        return analysis

    #--------------------------------------------------------------------------------

    #-----if there is at least 10 seconds of data, calculate the bytes/sec in 5-second increments-----
    def calc_incremental_bps(self, analysis: dict, entries: dict) -> dict:
        if not entries:
            return analysis

        if analysis['duration'] < self.bps_increment_size:
            # need a full increment to calculate bps
            return analysis
        src_ips = set(analysis['analysis_by_src_ip'].keys())
        dst_ips = set(analysis['analysis_by_dst_ip'].keys())

        analysis = self.calc_incremental_bps_by_direction(analysis, entries, src_ips, 'analysis_by_src_ip', 'src')
        analysis = self.calc_incremental_bps_by_direction(analysis, entries, dst_ips, 'analysis_by_dst_ip', 'dst')

        return analysis

    #--------------------------------------------------------------------------------

    #-----flag IPs that have suspicous data patterns-----
    # more than 20kbps for two 5-second increments in a row
    def flag_bad_data(self, analysis: dict) -> dict:
        if not analysis:
            return analysis
        #TEST
        # return analysis

        # direction_key: 'analysis_by_src_ip' or 'analysis_by_dst_ip'
        # assume some sections of the dictionary may have no data
        for direction_key in ['analysis_by_src_ip', 'analysis_by_dst_ip']:
            if not analysis[direction_key]:
                continue
            for ip in analysis[direction_key].keys():
                if ip in self.exempted_ips:
                    continue
                bps_by_segment = analysis[direction_key][ip].get('bps_by_segment', None)
                if not bps_by_segment:
                    continue
                for end_segment_id, segment_info in bps_by_segment.items():
                    if segment_info['bps'] > self.flag_bps_above_value:
                        analysis[direction_key][ip]['bps_by_segment'][end_segment_id]['flags'] += 1

        return analysis

    #--------------------------------------------------------------------------------
