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
    MEGABYTE = 1024 * 1024
    GIGABYTE = 1024 * MEGABYTE

    #-----regexes-----
    # EX: ipv4.log-1724555701
    regex_valid_ip_log_filename_pattern = r'^ipv4\.log\-(\d+)$'
    regex_valid_ip_log_filename = None

    #--------------------------------------------------------------------------------

    def __init__(self):
        self.init_vars()

    def init_vars(self):
        self.regex_valid_ip_log_filename = re.compile(self.regex_valid_ip_log_filename_pattern, re.DOTALL | re.MULTILINE | re.IGNORECASE)

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

