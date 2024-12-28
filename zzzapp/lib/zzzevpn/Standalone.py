#-----standalone util class for storing constants and any common functions that do not require other zzzevpn modules-----
# util imports config and db
# this prevents config and db from using any functions in util
# functions not needing config or db should be moved to here

import re

#-----package with all the Zzz modules-----
# do not import zzzevpn here because all modules import this module
# import zzzevpn

class Standalone:
    'standalone util class for storing constants and any common functions that do not require other zzzevpn modules'

    # boolean values
    BOOLEAN_STR_VALUES: list = ['TRUE', 'FALSE']

    # number constants
    KILOBYTE = 1024
    MEGABYTE = 1024 * KILOBYTE
    GIGABYTE = 1024 * MEGABYTE

    MILLISECONDS_PER_SECOND = 1000
    SECONDS_PER_MINUTE = 60
    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    DAYS_PER_YEAR = 365

    SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR
    SECONDS_PER_DAY = SECONDS_PER_HOUR * HOURS_PER_DAY
    SECONDS_PER_YEAR = SECONDS_PER_DAY * DAYS_PER_YEAR

    MILLISECONDS_PER_MINUTE = MILLISECONDS_PER_SECOND * SECONDS_PER_MINUTE
    MILLISECONDS_PER_HOUR = MILLISECONDS_PER_SECOND * SECONDS_PER_HOUR

    #-----regexes-----
    # EX: ipv4.log-1724555701
    regex_valid_ip_log_filename_pattern = r'^ipv4\.log\-(\d+)$'
    regex_valid_ip_log_filename = None
    regex_tunnel_interface_pattern = r'^tun(\d)$'
    regex_tunnel_interface = None

    #--------------------------------------------------------------------------------

    def __init__(self):
        self.init_vars()

    def init_vars(self):
        self.regex_valid_ip_log_filename = re.compile(self.regex_valid_ip_log_filename_pattern, re.DOTALL)
        self.regex_tunnel_interface = re.compile(self.regex_tunnel_interface_pattern, re.IGNORECASE)

    #--------------------------------------------------------------------------------

    def calc_iptables_logrotate_numfiles(self, bytes_per_line: int, lines_per_file: int, max_diskspace: int) -> dict:
        if not bytes_per_line or not lines_per_file or not max_diskspace:
            return {
                'numfiles': 100,
                'err': 'Invalid input. The number of log files has been set to the minimum value of 100.',
            }
        err = ''
        numfiles = int(max_diskspace / (bytes_per_line * lines_per_file))

        # keep it in the range of 100-10000
        if numfiles<100:
            numfiles = 100
            err = 'The IPtablesLogFiles and LogPacketsPerMinute settings only allow for {numfiles} log files. The number of log files has been set to the minimum value of 100.'
        if numfiles>10000:
            numfiles = 10000
            err = 'The IPtablesLogFiles and LogPacketsPerMinute settings allow for {numfiles} log files. The number of log files has been set to the maximum value of 10000.'

        result = {
            'numfiles': numfiles,
            'err': err,
        }
        return result

    #--------------------------------------------------------------------------------

    def is_valid_ip_log_filename(self, filename: str='') -> bool:
        if not filename:
            return False
        match = self.regex_valid_ip_log_filename.match(filename)
        if match:
            return True
        return False

    #--------------------------------------------------------------------------------

    # some versions do not sort well as strings, so convert them to integers, padded with zeros
    def version_to_int(self, version) -> int:
        if not version:
            return 0

        version_str = str(version)
        version_int = 0

        # "4.10" --> "004010000" --> 4010000
        # "4_10" --> "004010000" --> 4010000
        regex_pattern = r'^(\d+)(\.|\_)(\d+)$'
        regex = re.compile(regex_pattern, re.DOTALL | re.IGNORECASE)
        match = regex.match(version_str)
        if match:
            version_major = str(match.group(1)).zfill(3)
            version_minor = str(match.group(3)).zfill(3)
            version_int = f'{version_major}{version_minor}'
            return int(version_int)

        # "2.6.12" --> "002006012" --> 2006012
        # "5.0.1" --> "005000001" --> 5000001
        regex_pattern = r'^(\d+)(\.|\_)(\d+)(\.|\_)(\d+)$'
        regex = re.compile(regex_pattern, re.DOTALL | re.IGNORECASE)
        match = regex.match(version_str)
        if match:
            version_major = str(match.group(1)).zfill(3)
            version_minor = str(match.group(3)).zfill(3)
            version_patch = str(match.group(5)).zfill(3)
            version_int = f'{version_major}{version_minor}{version_patch}'

        return int(version_int)

    #--------------------------------------------------------------------------------

    def get_int_safe(self, value: str, none_on_error: bool=False) -> int:
        try:
            return int(value)
        except:
            if none_on_error:
                return None
            return 0

    def whitespace_to_commas(self, data: str) -> str:
        return data.replace(' ', ',').replace('\n', ',').replace('\r', ',').replace('\t', ',')

    def value_between_range(self, value: int, min_value: int, max_value: int) -> bool:
        if min_value <= value <= max_value:
            return True
        return False

    #--------------------------------------------------------------------------------

    #-----processes a range string-----
    # process_range('1-5,6,77777', 1, 5)
    # returns: { 'values': {1,2,3,4,5}, 'dropped_values': {6,77777}, 'error_msg': '' }
    def process_range(self, range_str: str, valid_min: int, valid_max: int, invalid_values: set=set()) -> dict:
        result = { 'values': set(), 'dropped_values': set(), 'error_msg': '' }
        start, end = range_str.split('-')
        start = self.get_int_safe(start.strip(), none_on_error=True)
        end = self.get_int_safe(end.strip(), none_on_error=True)
        if start is None or end is None:
            result['error_msg'] = f'ERROR: invalid range: {range_str} (requires 2 integers)'
            return result
        if start>=end:
            result['error_msg'] = f'ERROR: range start must be less than end: {range_str}'
            return result
        if not self.value_between_range(start, valid_min, valid_max) or not self.value_between_range(end, valid_min, valid_max):
            result['error_msg'] = f'ERROR: invalid range: {range_str} (valid values are {valid_min}-{valid_max})'
            return result

        for num in range(start, end+1):
            if num in invalid_values:
                result['dropped_values'].add(num)
                result['error_msg'] = f'ERROR: invalid value: {num} (on the invalid list)'
            else:
                result['values'].add(num)

        return result

    #--------------------------------------------------------------------------------

    def process_number(self, num_str: int, valid_min: int, valid_max: int, invalid_values: set=set()) -> dict:
        result = { 'values': set(), 'dropped_values': set(), 'error_msg': '' }
        num = self.get_int_safe(num_str.strip(), none_on_error=True)

        if num is None:
            result['error_msg'] = f'ERROR: invalid value: {num_str} (not an integer)'
            return result
        if not self.value_between_range(num, valid_min, valid_max):
            result['dropped_values'].add(num)
            result['error_msg'] = f'ERROR: invalid value: {num} (outside the valid range)'
            return result
        
        if num in invalid_values:
            result['dropped_values'].add(num)
            result['error_msg'] = f'ERROR: invalid value: {num} (on the invalid list)'
        else:
            result['values'].add(num)

        return result

    #--------------------------------------------------------------------------------

    #-----converts a string of ranges to a set of numbers, with validation applied-----
    # allow_range_with_invalid_values: if True, the range will be processed and invalid values will be dropped
    # example with ports: '1-5,22,32-35' --> {1,2,3,4,5,22,32,33,34,35}
    # example with validation:
    #   translate_ranges_to_set('1-5,22,32-35', 0, 65535, invalid_values={22})
    #   result: {1,2,3,4,5,32,33,34,35}
    #   note that 22 is dropped because it is on the invalid list
    # steps:
    #   1. split the string by commas
    #   2. determine if each item is a range or a single number
    #   3. process each range or number
    #   4. return the set of valid numbers, the set of dropped numbers, and error message(s)
    def translate_ranges_to_set(self, ranges: list, valid_min: int, valid_max: int, invalid_values: set=set(), allow_range_with_invalid_values: bool=False) -> dict:
        '''Converts a string of ranges to a set of numbers, with validation applied.
        Example with ports: '1-5,22,32-35' --> {1,2,3,4,5,22,32,33,34,35}
        Returns a dictionary with the following keys
        values: set of valid numbers
        dropped_values: set of invalid numbers
        approved_ranges: string of valid ranges
        error_msg: string of error messages
        '''
        combined_result = { 'values': set(), 'dropped_values': set(), 'approved_ranges': '', 'error_msg': '' }

        if not ranges:
            return combined_result
        #-----must have min/max, they can be equal-----
        if (not valid_min) or (not valid_max):
            return combined_result
        if valid_min > valid_max:
            return combined_result

        for range_str in ranges:
            if not range_str:
                continue

            result = None
            if '-' in range_str:
                result = self.process_range(range_str, valid_min, valid_max, invalid_values=invalid_values)
            else:
                result = self.process_number(range_str, valid_min, valid_max, invalid_values=invalid_values)

            if result['values']:
                combined_result['values'].update(result['values'])
            if result['dropped_values']:
                combined_result['dropped_values'].update(result['dropped_values'])
            if result['error_msg']:
                combined_result['error_msg'] += f'{result["error_msg"]}\n'

        return combined_result

    #--------------------------------------------------------------------------------

    #-----validate a list of ports-----
    # assumes: ports_to_check is a list of ints
    # returns: { 'valid_ports': {12345,23456}, 'invalid_ports': {22, 443}, 'error_msg': '' }
    def validate_ports(self, ports_to_check: list, invalid_ports: set={}) -> dict:
        result = { 'valid_ports': set(), 'invalid_ports': set(), 'approved_ranges': '', 'error_msg': [] }
        #-----check for non-integers or numbers outside the range-----
        for port in ports_to_check:
            if not (1024 <= port <= 65535):
                result['error_msg'].append(f'ERROR: invalid port number: {port} (valid range is 1024-65535)')
                result['invalid_ports'].add(port)
                continue
            if port in invalid_ports:
                result['error_msg'].append(f'ERROR: invalid port number: {port} (on the invalid list)')
                result['invalid_ports'].add(port)
                continue
            result['valid_ports'].add(port)

        return result

    #--------------------------------------------------------------------------------

    # range is a string in the format: '1-10'
    # invalid_values is a set of integers
    # reject if the range is not valid or if any value in the range is in the invalid list
    def validate_range(self, range: str, invalid_values: set=set()) -> bool:
        if not range:
            return False
        # result = self.process_range(range, 1, 65535, invalid_values=invalid_values)
        # if result['error_msg']:
        #     return False
        # if result['values']:
        #     return True
        return False
