#-----Utility functions-----

from ansi2html import Ansi2HTMLConverter
import base64
import datetime
import gc
import ipaddress
import json
import maxminddb
import os
import pathlib
import pprint
import psutil
# from pytz import timezone
import pytz
import re
import subprocess
import sys
import time
import tldextract
import traceback
import unidecode

#-----import modules from the lib directory-----
# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.Config
# import zzzevpn.DB
# import zzzevpn.IPutil
# import zzzevpn.ZzzRedis
import zzzevpn

class Util:
    'Utility functions'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    db_ip_country: zzzevpn.DB = None
    ip_util: zzzevpn.IPutil = None
    maxmind_reader: maxminddb.Reader = None
    standalone: zzzevpn.Standalone = None
    tldextract_obj: tldextract.TLDExtract = None
    zzz_redis: zzzevpn.ZzzRedis = None
    
    private_subnet_cidr_list = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']
    #-----fill this in init() with ip_network objects-----
    private_subnet_list = []
    
    regex_cidr = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2})$'
    regex_cidr_pattern = re.compile(regex_cidr, re.DOTALL)
    regex_class_c = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}$'
    regex_class_c_pattern = re.compile(regex_class_c, re.DOTALL)
    regex_ipv4_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    regex_ipv4 = re.compile(regex_ipv4_pattern, re.DOTALL)
    regex_ansi_codes_pattern = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]', re.IGNORECASE)
    
    regex_datetime = r'^\d{4}\-\d{2}\-\d{2} \d{2}\:\d{2}\:\d{2}$'
    regex_datetime_pattern = re.compile(regex_datetime, re.DOTALL | re.IGNORECASE)
    regex_datetime_tz = r'^\d{4}\-\d{2}\-\d{2} \d{2}\:\d{2}\:\d{2} [a-z]{3}$'
    regex_datetime_tz_pattern = re.compile(regex_datetime_tz, re.DOTALL | re.IGNORECASE)
    regex_git_output_pattern = r'\n(diff \-\-git .+?)\n'
    regex_git_output = re.compile(regex_git_output_pattern, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    regex_int_select_pattern = r'(\d+)'
    regex_int_select = re.compile(regex_int_select_pattern, re.DOTALL | re.MULTILINE)
    regex_linefeed = re.compile(r'\r*\n', re.DOTALL | re.IGNORECASE | re.MULTILINE)
    regex_microseconds_pattern = r'^(.+?\.\d{3})\d{3}$'
    regex_microseconds = re.compile(regex_microseconds_pattern)
    regex_zzz_domain_without_tld_pattern = r'^services\.([a-zA-Z0-9\-]+)\.zzz$'
    
    #TODO: add this as a zzz.conf entry so users can customize their own most popular TLD's
    #      this accelerates the subdomain-->domain calculation
    # common_TLD_list = ['com', 'net', 'org', 'gov', 'info', 'io', 'tv', 'cn', 'ru', 'co.uk', 'co.jp']
    regex_common_TLD_pattern = r'\.(com|net|org|gov|info|io|tv|cn|ru|co\.uk|co\.jp)$'
    regex_common_TLD = re.compile(regex_common_TLD_pattern, re.DOTALL | re.IGNORECASE)
    
    #-----full TLD list-----
    # compile as needed
    # TLD: {
    #     'domain': regex_TLD_domain,
    #     'subdomain': regex_TLD_subdomain,
    # }
    regex_full_cache = {}
    
    # allow up to 10 levels of subdomains
    regex_valid_domain_pattern = r'^((?!-))((xn--)?[a-z0-9][a-z0-9\-_]{0,61}[a-z0-9]{0,1}\.){0,10}(xn--)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30}\.[a-z]{2,})$'
    regex_valid_domain = re.compile(regex_valid_domain_pattern, re.DOTALL | re.IGNORECASE)
    
    host_url_regex_pattern = r'^http(|s)\:\/\/(.+?)\/'
    host_url_regex = re.compile(host_url_regex_pattern, re.DOTALL | re.IGNORECASE)

    date_format_filename = '%Y-%m-%d-%H-%M-%S'
    date_format_hi_res = '%Y-%m-%dT%H:%M:%S.%f'
    date_format_seconds = '%Y-%m-%d %H:%M:%S'
    date_format_seconds_timezone = '%Y-%m-%d %H:%M:%S %Z'

    display_script_error_output = True
    script_output = ''
    script_err = ''
    subprocess_output = None
    decode_status = ''
    decode_error_msg = ''
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, should_use_db: bool=True) -> None:
        self.standalone = zzzevpn.Standalone()
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
        self.db = db
        if should_use_db and db is None:
            self.db = zzzevpn.DB(self.ConfigData)
            self.db.db_connect(self.ConfigData['DBFilePath']['Services'])
        self.ip_util = zzzevpn.IPutil()
        for cidr in self.private_subnet_cidr_list:
            self.private_subnet_list.append(ipaddress.ip_network(cidr, strict=False))
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    def init_vars(self) -> None:
        pass
    
    #--------------------------------------------------------------------------------
    
    def is_using_venv(self) -> bool:
        return sys.prefix!=sys.base_prefix

    #--------------------------------------------------------------------------------

    def force_garbage_collection(self) -> None:
        gc.collect()

    #--------------------------------------------------------------------------------

    #-----creates a datetime string that can be appended to a filename-----
    def filename_datetime(self) -> str:
        datetime_now = datetime.datetime.now()
        return datetime_now.strftime(self.date_format_filename)
    
    def current_timestamp(self):
        return time.time()
    
    #-----printable datetime string-----
    def current_datetime(self, timestamp=None, localize_timezone=True):
        datetime_now = None
        timezone_info = None
        if localize_timezone:
            timezone_info = pytz.timezone(self.ConfigData['TimeZoneDisplay'])
        if timestamp is None:
            datetime_now = datetime.datetime.now(timezone_info)
        else:
            datetime_now = datetime.datetime.fromtimestamp(timestamp, timezone_info)
        return datetime_now.strftime(self.date_format_seconds_timezone)
    
    #-----ANSI terminal color codes look like a mess in a webpage, remove them-----
    def remove_ansi_codes(self, data):
        return self.regex_ansi_codes_pattern.sub('', data)
    
    def convert_ansi_to_html(self, text_data):
        ansi2html_converter = Ansi2HTMLConverter()
        return ansi2html_converter.convert(text_data)
    
    #-----"<" and ">" in source diff can mess up a webpage, so HTML-encode them-----
    # alternate spaces and nbsp so space-indents look right, but text still wraps OK
    def make_html_display_safe(self, data):
        return data.replace('<', '&lt;').replace('>', '&gt;').replace('  ', ' &nbsp;')
    
    # ASCII --> HTML line breaks
    def add_html_line_breaks(self, data, highlight_diff=False, include_spans=True):
        processed_data = data
        if highlight_diff:
            processed_data = self.regex_git_output.sub(r'<br>\n<span class="text_green">\g<1></span><br>\n', processed_data)
        if include_spans:
            processed_data = self.regex_linefeed.sub('</span><br>\n<span class="font-courier">', processed_data)
            return f'<span class="font-courier">{processed_data}</span>'
        else:
            processed_data = self.regex_linefeed.sub('<br>\n', processed_data)
            return processed_data
    
    def ascii_to_html_with_line_breaks(self, data, highlight_diff=False):
        html_safe_data = self.make_html_display_safe(data)
        return self.add_html_line_breaks(html_safe_data, highlight_diff=highlight_diff)
    
    #TODO: handle DST time changes without getting errors
    #-----get the 3-letter timezone-----
    # date_format = '%Z'
    # datetime_now = datetime.datetime.now(pytz.timezone(self.ConfigData['TimeZoneDisplay']))
    # timezone_name = datetime_now.strftime(date_format)
    def format_timezone(self):
        timezone_name = ''
        try:
            datetime_now = datetime.datetime.now()
            tz = pytz.timezone(self.ConfigData['TimeZoneDisplay'])
            timezone_name = tz.tzname(datetime_now)
        except:
            # temporary handler for DST time change errors
            timezone_name = 'PT'
        return timezone_name
    
    #-----convert the unix timestamp to something readable-----
    # similar to format_time() from LogParser.py, but this one takes a DB string
    def format_time_from_str(self, date_str, use_hires=False):
        date_format = self.date_format_seconds
        if use_hires:
            date_format = self.date_format_hi_res
        datetime_obj = datetime.datetime.strptime(date_str, date_format)
        tz_obj = pytz.timezone(self.ConfigData['TimeZoneDisplay'])
        localized_datetime = datetime_obj.astimezone(tz_obj)
        return localized_datetime.strftime(date_format)
    
    def microseconds_to_milliseconds(self, datetime_str):
        match = self.regex_microseconds.match(datetime_str)
        if match:
            return match.group(1)
        return datetime_str

    def make_datetime_readable(self, date_str):
        return self.microseconds_to_milliseconds(date_str.replace('T', ' '))

    # convert unix timestamp to hi-res datetime
    #   1598497201.123 --> 2020-08-27T03:00:01.123000
    def timestamp_to_date_hires(self, unix_timestamp, tz=datetime.timezone.utc):
        if not self.is_float(unix_timestamp):
            return ''
        unix_timestamp = float(unix_timestamp)
        datetime_obj = datetime.datetime.fromtimestamp(unix_timestamp, tz)
        return datetime_obj.strftime(self.date_format_hi_res)
    
    # pass in 2 datetimes, get the difference in seconds
    def datetime_diff_seconds(self, start_time: datetime.datetime, end_time: datetime.datetime=None):
        if not start_time:
            return 0
        if not end_time:
            end_time = datetime.datetime.now()
        timedelta = end_time - start_time
        return timedelta.total_seconds()
    
    def timestamp_diff_seconds(self):
        pass
    
    def convert_utf8_to_ascii(self, utf8_data):
        ascii_data = None
        try:
            # ascii_data = utf8_data.decode('iso-8859-1', 'ignore')
            ascii_data = unidecode.unidecode(utf8_data)
        except:
            ascii_data = None
        return ascii_data
    
    def convert_utf8_to_html(self, utf8_data):
        html_data = None
        try:
            html_data = utf8_data.encode('ascii', 'xmlcharrefreplace')
        except:
            html_data = None
        return html_data

    def decode_bytes_to_text(self, data: bytes) -> str:
        if data is None:
            return

        decoded_data = ''
        status = 'success'
        error_msg = ''

        if data.isascii():
            try:
                decoded_data = data.decode('iso-8859-1')
            except:
                decoded_data = None
                status = 'error'
                error_msg = 'ERROR decoding ASCII'
        else:
            try:
                decoded_data = data.decode('utf-8')
            except:
                decoded_data = None
                status = 'error'
                error_msg = 'ERROR decoding UTF-8'

        return decoded_data, status, error_msg

    def js_string_to_python_bool(self, js_string: str) -> bool:
        if js_string=='true':
            return True
        return False

    #--------------------------------------------------------------------------------

    def add_commas(self, num: int):
        return '{:,}'.format(num)

    #-----remove junk from a submitted string-----
    def cleanup_str(self, data):
        # \n, \r, \t, space, comma
        return data.strip('\n\r\t ')

    def str_to_int_or_str(self, data_str):
        if self.is_int(data_str):
            return int(data_str)
        return data_str
    
    #-----numeric sort of arrays with mixed numbers/strings in values-----
    # Example:
    #   versions = [
    #       '20',
    #       '21',
    #       '20a2',
    #       '20a1',
    #       '20a10',
    #       '19',
    #       '101',
    #       '3',
    #   ]
    #   versions.sort(key=self.util.mixed_sort)
    #   for version in versions:
    #       pass
    def mixed_sort(self, data_str):
        return [ self.str_to_int_or_str(item) for item in self.regex_int_select.split(data_str) ]
    
    def unique_sort(self, item_list, make_lowercase=False):
        #return sorted(set(item_list))
        if not item_list:
            return item_list
        if make_lowercase:
            item_list = map(lambda item:item.lower(), item_list)
        item_list = list(dict.fromkeys(item_list))
        item_list.sort()
        return item_list

    #-----return the difference of 2 lists-----
    def diff_list(self, list1, list2):
        return sorted(list(set(list1) - set(list2)))

    def sort_array_by_values(self, associative_array, reverse_sort=False):
        if not associative_array:
            return None
        return sorted(associative_array.items(), key=lambda item: item[1], reverse=reverse_sort)
    
    #-----limit the array rows by a given list of keys, then sort the resulting array by value-----
    # EX: given a list of 3 country codes "subset_keys"
    #     pull the 3 code-name pairs from the full countries list "associative_array"
    #     sort the 3 countries by name
    def sort_array_subset_by_values(self, subset_keys, associative_array, reverse_sort=False):
        if not associative_array or not subset_keys:
            return None
        subset_array = {}
        for key in subset_keys:
            item = associative_array.get(key, None)
            if item:
                subset_array[key] = associative_array[key]
        return self.sort_array_by_values(subset_array, reverse_sort)
    
    #--------------------------------------------------------------------------------
    
    def print_error_subprocess(self, e):
        err = f"command '{e.cmd}' returned with error (code {e.returncode}): {e.output}"
        print(err, flush=True)
        return err
    
    #--------------------------------------------------------------------------------
    
    #-----do not wait for the process to return-----
    # used for restarting zzz or rebooting the server
    # proc = Popen([cmd_str], shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
    def run_without_wait(self, subprocess_commands):
        try:
            p = subprocess.Popen(subprocess_commands, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            # self.print_error_subprocess(e)
            print('ERROR running ' + ' '.join(subprocess_commands))
            print(traceback.format_exc())
            return False
        return True
    
    def restart_zzz(self):
        return self.run_without_wait(['systemctl', 'restart', 'zzz'])
    
    def restart_os(self):
        return self.run_without_wait(['systemctl', 'reboot'])
    
    #--------------------------------------------------------------------------------
    
    # True/False - controls printing in run_script()
    def set_script_error_output(self, value=True):
        if value==False:
            self.display_script_error_output = value
        self.display_script_error_output = True
    
    #--------------------------------------------------------------------------------
    
    #TODO: more thorough handling of binary data
    #-----runs a given script, reports errors-----
    # decode_data is only relevant in binary_mode
    def run_script(self, subprocess_commands, binary_mode: bool=False, decode_data: bool=False) -> bool:
        #TODO: check if file exists and is runnable by the current user
        self.subprocess_output = None
        self.script_output = ''
        self.script_err = ''
        if not isinstance(subprocess_commands, list):
            subprocess_commands = [subprocess_commands]
        try:
            # can't use capture_output=True here because that is python 3.7+
            # self.subprocess_output = subprocess.run(subprocess_commands, stdout=subprocess.PIPE, check=True, universal_newlines=True)
            #-----python 3.6-----
            # self.subprocess_output = subprocess.run(subprocess_commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, universal_newlines=True)
            #-----python 3.8 supports "capture_output" and "text"-----
            # TODO: add UTF-8 support with "encoding" param
            if binary_mode:
                # handles UTF-8
                self.subprocess_output = subprocess.run(subprocess_commands, capture_output=True, check=True)
                if decode_data:
                    stdout, self.decode_status, self.decode_error_msg = self.decode_bytes_to_text(self.subprocess_output.stdout)
                    if not stdout:
                        stdout = ''
                    stderr, decode_status, decode_error_msg = self.decode_bytes_to_text(self.subprocess_output.stderr)
                    if not stderr:
                        stderr = ''
                    self.script_output = f'{stdout}\n{stderr}'
            else:
                self.subprocess_output = subprocess.run(subprocess_commands, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            if self.display_script_error_output:
                print('CalledProcessError running ' + ' '.join(subprocess_commands))
                self.print_error_subprocess(e)
            stdout = e.stdout
            if binary_mode:
                stdout, status, error_msg = self.decode_bytes_to_text(e.stdout)
            if stdout is None:
                stdout = ''
            stderr = e.stderr
            if binary_mode:
                stderr, status, error_msg = self.decode_bytes_to_text(e.stderr)
            if stderr is None:
                stderr = ''
            if self.display_script_error_output:
                print('stdout: ' + stdout)
                print('stderr: ' + stderr)
            self.script_output = stdout + '\n' + stderr + '\n' + ''.join(traceback.format_exc())
            return False
        except OSError as e:
            self.script_output = 'OS ERROR running ' + ' '.join(subprocess_commands)
            self.script_output += ''.join(traceback.format_exc())
            print(self.script_output)
            return False
        except Exception as e:
            self.script_output = 'ERROR running ' + ' '.join(subprocess_commands)
            self.script_output += ''.join(traceback.format_exc())
            print(self.script_output)
            return False
        return True
    
    #--------------------------------------------------------------------------------
    
    #-----download all data from the given list of settings files-----
    def get_settings_file_data(self, file_list):
        file_data = []
        for filename in file_list:
            settings_filepath = f'''{self.ConfigData['Directory']['Settings']}/{filename}'''
            with open(settings_filepath, 'r') as settings_file:
                for item in settings_file:
                    #TODO: check if it is a domain or IP, only keep the domains
                    item = item.strip("\n").lower()
                    file_data.append(item)
        return file_data
    
    #--------------------------------------------------------------------------------
    
    #-----these domains are needed to filter them out of the main list-----
    # BIND will fail to start if there are conflicts between the settings and main lists
    def get_settings_domains(self):
        settings_domains = []
        #-----open all settings files-----
        settings_file_data = self.get_settings_file_data(self.ConfigData['SettingFile'].values())
        
        #-----extract domains from each entry and save to list-----
        for item in settings_file_data:
            #TODO: separate IP's from hosts here
            domain = self.get_domain_from_host(item)
            if domain == '':
                continue
            if not domain in settings_domains:
                settings_domains.append(domain)
        
        #TODO: cache settings domains in ConfigData? or in another textfile?
        return settings_domains
    
    # "services.test.zzz" --> "test"
    def get_zzz_domain_without_tld(self) -> str:
        match = re.match(self.regex_zzz_domain_without_tld_pattern, self.ConfigData['AppInfo']['Domain'])
        if not match:
            # ERROR: failed to extract domain_without_tld from config Domain
            return ''
        return match.group(1)

    #--------------------------------------------------------------------------------

    def is_running_as_root(self):
        if os.geteuid()==0:
            return True
        return False

    #-----IPC should get through faster than a DB flag-----
    def send_signal_checkwork(self):
        if self.is_running_as_root():
            #-----signals can only be sent by root, due to linux safety restrictions-----
            self.run_script([self.ConfigData['Subprocess']['checkwork']])
        else:
            #-----set a flag in the redis server for non-root users-----
            if not self.zzz_redis:
                self.zzz_redis=zzzevpn.ZzzRedis(self.ConfigData)
            self.zzz_redis.redis_init()
            self.zzz_redis.zzz_checkwork_set()

    #-----used for setting the work_available flag after uploading work to the DB-----
    def work_available(self, value=None):
        if value is None:
            sql = 'SELECT check_requests_table FROM work_available'
            params = ()
            row = self.db.select(sql, params)
            if row:
                return row[0]
            else:
                if not self.db.last_query_status:
                    # query error? sleep, then return False
                    print('sleeping due to query error')
                    time.sleep(5)
                return False
        else:
            sql = 'UPDATE work_available set check_requests_table=?'
            params = (value,)
            self.db.query_exec(sql, params)
            if value:
                # True or 1 means also send a signal to the app
                self.send_signal_checkwork()
    
    #--------------------------------------------------------------------------------

    #-----tell apache to reload its config-----
    # curl --resolve services.zzz.zzz:443:10.7.0.1 https://services.zzz.zzz/z/config_reload
    def apache_config_reload(self):
        domain = self.ConfigData['AppInfo']['Domain']
        script_commands = [
            'curl',
            '--resolve',
            # hardcode the DNS here because command-line apps have issues interacting with bind for the apache server
            f'{domain}:443:10.7.0.1',
            f'https://{domain}/z/config_reload'
        ]
        # in case apache is not running or not responding, don't bother waiting for curl to return
        self.run_without_wait(script_commands)

    #--------------------------------------------------------------------------------
    
    # for www.google.com, return google.com
    # for google.com, return google.com
    # otherwise, return ''
    def regex_match_domain(self, TLD, host):
        TLD = TLD.upper()
        #-----get regex from cache or compile and cache it first-----
        regex_TLD = self.regex_full_cache.get(TLD, None)
        if not regex_TLD:
            regex_TLD_subdomain_pattern = r'\.([^\.]+)\.' + TLD + '$'
            regex_TLD_subdomain = re.compile(regex_TLD_subdomain_pattern, re.DOTALL | re.IGNORECASE)
            regex_TLD_domain_pattern = r'^([^\.]+)\.' + TLD + '$'
            regex_TLD_domain = re.compile(regex_TLD_domain_pattern, re.DOTALL | re.IGNORECASE)
            regex_TLD = {
                'domain': regex_TLD_domain,
                'subdomain': regex_TLD_subdomain,
            }
            self.regex_full_cache[TLD] = regex_TLD
        
        #-----get domain from subdomain matching TLD-----
        # match = re.search(r'\.([^\.]+)\.' + TLD + '$', host)
        match = regex_TLD['subdomain'].search(host)
        if match:
            domain = match.group(1) + '.' + TLD.lower()
            return domain
        
        #-----get domain from domain matching TLD-----
        # match = re.search(r'^([^\.]+)\.' + TLD + '$', host)
        match = regex_TLD['domain'].search(host)
        if match:
            domain = match.group(1) + '.' + TLD.lower()
            return domain
        
        #FAIL
        return ''
    
    #--------------------------------------------------------------------------------
    
    def is_country_tld(self, tld):
        if not tld:
            return False
        if self.ConfigData['OfficialCountriesWithExceptions'].get(tld.upper(), None):
            return True
        return False
    
    def is_public_tld(self, tld):
        if self.ConfigData['TLDdict'].get(tld.upper(), None):
            return True
        return False

    #TODO: put the TLD list update command in a monthly cron
    # bash: tldextract --update
    # python: self.tldextract_obj.update(True)
    def get_tld_from_host(self, host: str=None):
        if not host:
            return None, None
        if not self.tldextract_obj:
            try:
                self.tldextract_obj = tldextract.TLDExtract(cache_dir=self.ConfigData['Directory']['TLDextractCache'])
            except:
                return None, None

        extract_result = None
        try:
            # extract_result = tldextract.extract(host)
            extract_result = self.tldextract_obj(host)
        except:
            return None, None

        host_tld = extract_result.suffix
        if not host_tld:
            return None, None

        #-----handle 2-level TLD's, like .co.uk-----
        country_two_level_tld = None
        split_tld = host_tld.split('.')
        if len(split_tld)>1:
            country_two_level_tld = split_tld[1]
        return host_tld, country_two_level_tld

    #--------------------------------------------------------------------------------
    
    #TODO: rewrite this to use self.get_tld_from_host()
    #-----parse a host to extract the domain-----
    def get_domain_from_host(self, host, strict_match: bool=False) -> str:
        #-----try the most common TLD's first-----
        if not host:
            return None
        host = host.lower()
        match = self.regex_common_TLD.search(host)
        if match:
            return self.regex_match_domain(match.group(1), host)
        
        #-----try the list of all country codes-----
        split_host = host.rsplit(sep='.', maxsplit=1)
        if len(split_host)<2:
            # no "." in the hostname, just return
            return None
        host_tld = split_host[1]
        found_country_tld = self.ConfigData['OfficialCountriesWithExceptions'].get(host_tld.upper(), None)
        if found_country_tld:
            return self.regex_match_domain(host_tld, host)
        
        #-----try the massive list of all TLD's-----
        found_tld = self.ConfigData['TLDdict'].get(host_tld.upper(), None)
        if found_tld:
            return self.regex_match_domain(host_tld, host)
        
        #-----either the entire host is a domain or it's not in a valid format-----
        if strict_match:
            return None
        return host
    
    #-----find subdomains in a list that match domains in the list-----
    # return a list without the matching subdomains
    def remove_subdomains_with_matching_domains(self, assembled_list, settings_list):
        clean_list = []
        
        if self.ConfigData['Debug']:
            print('remove_subdomains_with_matching_domains - START', flush=True)
        
        #-----lowercase list items, remove duplicates, sort items-----
        assembled_list = self.unique_sort(assembled_list, make_lowercase=True)
        
        if self.ConfigData['Debug']:
            print('remove_subdomains_with_matching_domains - sorted list', flush=True)
        
        total = 0
        accepted = 0
        for host in assembled_list:
            total += 1
            domain = self.get_domain_from_host(host)
            if domain == '' or domain in settings_list:
                #-----skip blank domains and anything that might overlap with Settings-----
                continue
            if domain == host or not domain in assembled_list:
                accepted += 1
                clean_list.append(host)
        
        print("remove_subdomains_with_matching_domains - total hosts: " + str(total), flush=True)
        print("remove_subdomains_with_matching_domains - accepted hosts: " + str(accepted), flush=True)
        
        if self.ConfigData['Debug']:
            print('remove_subdomains_with_matching_domains - END', flush=True)
        
        return clean_list
    
    # domain = example.com, sub.example.com, sub.sub.example.com, etc.
    def valid_domain(self, domain):
        if not domain:
            return False
        match = self.regex_valid_domain.match(domain)
        if match:
            # domain pattern is good, but do we have a valid TLD also?
            if self.get_domain_from_host(domain, strict_match=True):
                return True
        return False

    def validate_domain_list(self, domain_list: list, list_rejected_domains: bool=False) -> dict:
        validation_result = {
            'accepted_domains': [],
            'rejected_domains': [],
            'list_length': 0,
            'status': 'empty list',
        }
        if not domain_list:
            return validation_result

        #-----remove duplicates-----
        domain_list = self.unique_sort(domain_list, make_lowercase=True)

        validation_result['status'] = 'OK'
        for domain in domain_list:
            if not domain:
                continue
            if self.valid_domain(domain):
                validation_result['accepted_domains'].append(domain)
            else:
                validation_result['rejected_domains'].append(domain)
        validation_result['list_length'] = len(validation_result['accepted_domains'])

        return validation_result

    #--------------------------------------------------------------------------------
    
    def is_int(self, value):
        if value is None:
            return False
        str_value = str(value)
        return str_value.isdigit()
    
    def is_float(self, value):
        try:
            result = float(value)
        except:
            return False
        return True
    
    #-----determine if the given string looks like a datetime string-----
    def is_datetime(self, value, include_tz=False):
        if not value:
            return False
        if not isinstance(value, str):
            return False
        if include_tz:
            match = self.regex_datetime_tz_pattern.search(value)
            if match:
                return True
        else:
            match = self.regex_datetime_pattern.search(value)
            if match:
                return True
        return False

    def get_int_safe(self, value: str) -> int:
        try:
            return int(value)
        except:
            return 0

    #--------------------------------------------------------------------------------

    # options = {
    #   ***makes a column have click-to-collapse/expand***
    #     'collapsable_html': {
    #         'column': 'html_attr_name',
    #     },
    #   ***makes a table header row with the given list of colnames***
    #     'generate_headers': colnames,
    #   ***makes JSON data more readable for given columns***
    #     'pprint_json': ['json'],
    #   ***assigns classes to all TD's***
    #     'td_class': 'wrap_text valign_top',
    #   ***overrides TD class default for the given columns***
    #     'td_class_custom': {
    #         # 'column': 'class_data',
    #     },
    # }
    #TODO: function calls to fix collapsability:
    # BIND.py:333:        custom_html_table = self.util.custom_html_table(self.dns_requests_data)
    # TaskHistory.py:87:        table_html = self.util.custom_html_table(rows_with_colnames, {'custom_timezone': True})
    # IPset.py:392:        custom_html_table = self.util.custom_html_table(self.ip_requests_data)
    def custom_html_table_row(self, row, row_id, options=None):
        #-----check options-----
        collapsable_html = None
        custom_timezone = None
        max_table_cell_data = 1024*1024
        pprint_json = None
        td_class_default = ''
        td_class_custom = None
        if options:
            collapsable_html = options.get('collapsable_html', None)
            custom_timezone = options.get('custom_timezone', False)
            max_table_cell_data = options.get('max_table_cell_data', 1024*1024)
            pprint_json = options.get('pprint_json', None)
            td_class_default = options.get('td_class', '')
            td_class_custom = options.get('td_class_custom', None)

        #-----process each column-----
        coldata = []
        for key in row.keys():
            value = row[key]
            if (key.lower()=='ip') and (value in self.ConfigData['HideIPs']):
                # for running demos without exposing the real client IPs or other things that should be hidden
                return []
            collapsable_row_id_attr_name = ''
            if collapsable_html:
                collapsable_row_id_attr_name = collapsable_html.get(key, '')

            if value is None:
                value = ''
            if len(str(value)) > max_table_cell_data:
                value = value[0:max_table_cell_data]
                value = f'''{value}\n(truncated at {max_table_cell_data} bytes)'''

            #-----check options-----
            if custom_timezone and self.is_datetime(value):
                #-----apply custom timezone from config-----
                value = self.format_time_from_str(value)
            if pprint_json:
                if key in pprint_json:
                    try:
                        json_parsed = json.loads(value)
                        value = json.dumps(json_parsed, indent=4)
                    except:
                        value = 'INVALID JSON'
            td_class = td_class_default
            if td_class_custom:
                td_class_custom_data = td_class_custom.get(key, None)
                if td_class_custom_data is not None:
                    td_class = td_class_custom_data

            #-----apply collapsable at the end, to avoid data damage-----
            if collapsable_row_id_attr_name:
                value = self.make_collapsable_html(value.rstrip("\n"), row_id, id_attr_name=collapsable_row_id_attr_name)

            coldata.append(f'<td class="{td_class}">{value}</td>')
        return coldata

    #-----customize the look of an HTML table-----
    # result: DB output array of rows from fetchAll
    # options: dictionary, controls table appearance
    def custom_html_table(self, db_result, options=None):
        if not db_result:
            return ''
        if len(db_result)==0:
            return ''

        html_cols = []
        generate_headers = None
        if options:
            generate_headers = options.get('generate_headers', None)
        if generate_headers:
            header_data = self.db.result_header(generate_headers)
            html_cols = [header_data]

        ctr = 0
        for row in db_result:
            ctr += 1
            #-----alternate row colors-----
            rowcolor = ''
            if (ctr % 2) == 0:
                rowcolor = 'class="gray-bg"'
            coldata = self.custom_html_table_row(row, ctr, options)
            if not coldata:
                # didn't process the row, skip it
                continue
            html_cols.append(f'<tr {rowcolor}>')
            html_cols.extend(coldata)
            html_cols.append('</tr>\n')
        return ''.join(html_cols)
    
    #--------------------------------------------------------------------------------

    # width must be a class that exists in main.css
    def make_collapsable_html(self, html_str, row_id, id_attr_name='row_', width='width_300'):
        row_id = str(row_id)
        wrapped_html = f'''<div class='expandable_container'><div class='content_collapsed {width}' id='{id_attr_name}{row_id}'>{html_str}</div><div class='expandable_spacer'></div><span>&nbsp;</span></div>'''
        return wrapped_html

    #--------------------------------------------------------------------------------

    def swap_rowcolor(self, current_color: str, color_options: list=['', 'gray-bg']) -> str:
        if current_color==color_options[0]:
            return color_options[1]
        return color_options[0]

    #--------------------------------------------------------------------------------

    def file_is_accessible(self, filepath):
        if not os.path.exists(filepath):
            return False
        return os.access(filepath, os.R_OK)
    
    #--------------------------------------------------------------------------------
    
    def get_filesize(self, filepath):
        if not os.path.exists(filepath):
            return 0
        statinfo = os.stat(filepath)
        return statinfo.st_size

    #--------------------------------------------------------------------------------

    def get_directory_list(self, dir: str, options: dict) -> list:
        if not self.file_is_accessible(dir):
            return {}
        if not os.path.isdir(dir):
            return {}

        previous_file = ''
        if (options['find_previous_file']):
            current_file = options['find_previous_file']
            all_files = {}
            for entry in os.scandir(dir):
                try:
                    file_stats = entry.stat()
                    #-----skip empty files-----
                    if (not entry.is_file()) or (file_stats.st_size==0):
                        continue
                except:
                    continue
            all_files[file_stats.st_mtime] = entry.name
            if all_files:
                sorted_files = sorted(all_files.items(), key=lambda x: x[0], reverse=True)
                for file in sorted_files:
                    if file[1]==current_file:
                        break
                    previous_file = file[1]
            return previous_file

        return os.listdir(dir)

    #--------------------------------------------------------------------------------

    def get_filedata_binary(self, filepath):
        if not self.file_is_accessible(filepath):
            #TODO: log an error? let it crash? force try-except at each function call?
            return b''
        
        if self.get_filesize(filepath) == 0:
            return b''
        
        data = b''
        opened_ok = True
        try:
            with open(filepath, 'rb') as read_file:
                data = read_file.read()
        except:
            #TODO: handle other file opening errors
            opened_ok = False
            return b''
        return data

    #-----return the contents of a text file-----
    # sends back ASCII text by default, unicode gets reduced to ASCII in this case
    # file_encoding: None, utf-8
    # return_format: ASCII, utf-8
    def get_filedata(self, filepath, file_encoding=None, return_format='ascii'):
        if not self.file_is_accessible(filepath):
            #TODO: log an error? let it crash? force try-except at each function call?
            return ''
        
        if self.get_filesize(filepath) == 0:
            return ''
        
        data = ''
        opened_ok = True
        try:
            with open(filepath, 'r', encoding=file_encoding) as read_file:
                data = read_file.read()
        except UnicodeDecodeError as e:
            # opening a unicode file with the default ASCII encoding may throw an exception
            # try to auto-recover from this
            opened_ok = False
        except:
            #TODO: handle other file opening errors
            opened_ok = False
            return ''
        
        if not opened_ok:
            try:
                file_encoding='utf-8'
                with open(filepath, 'r', encoding=file_encoding) as read_file:
                    data = read_file.read()
                opened_ok = True
            except:
                #TODO: handle other file opening errors
                opened_ok = False
                return ''
        
        if return_format=='ascii' and file_encoding=='utf-8':
            data = self.convert_utf8_to_ascii(data)
        
        return data

    #--------------------------------------------------------------------------------

    def log_stderr(self, err_msg):
        data_str = err_msg
        try:
            data_str = str(err_msg)
        except Exception:
            # what to do when it fails to decode bytes to str?
            sys.stderr.write('zzz_log_message() - Exception converting data to str()\n')
        try:
            sys.stderr.write(f'{data_str}\n')
        except Exception:
            pass
        sys.stderr.flush()

    #--------------------------------------------------------------------------------

    def get_delete_users_list(self) -> list:
        filepath_users_to_delete = self.ConfigData['UpdateFile']['openvpn']['users_to_delete']
        if not os.path.exists(filepath_users_to_delete):
            return []
        users_to_delete = []
        with open(filepath_users_to_delete, mode='r') as read_file:
            for line in read_file:
                if not line:
                    continue
                line = line.rstrip('\n')
                if line:
                    users_to_delete.append(line)
        return users_to_delete
    
    #--------------------------------------------------------------------------------
    
    def is_public_cidr(self, cidr):
        cidr_obj = self.is_cidr(cidr)
        if cidr_obj:
            return not (cidr_obj.is_private or self.net_contains_private_subnet(cidr))
        return False
    
    #-----check if a given IP/CIDR is public-----
    def is_public(self, ip):
        if self.match_cidr(ip):
            return self.is_public_cidr(ip)
        else:
            return self.ip_util.is_public_ip(ip)
    
    #-----check if an IP is in a CIDR-----
    # ip_network_obj should be the output from is_cidr()
    def ip_cidr_check(self, ip: str, cidr: str='', ip_network_obj=None):
        if ip_network_obj:
            return ipaddress.ip_address(ip) in ip_network_obj
        net = self.is_cidr(cidr)
        if not net:
            return False
        return ipaddress.ip_address(ip) in net
    
    #-----check if a CIDR entry overlaps a private network-----
    def net_contains_subnet(self, net_cidr, subnet_cidr):
        net = self.is_cidr(net_cidr)
        subnet = self.is_cidr(subnet_cidr)
        if net and subnet:
            return subnet in net
        return False
    
    def net_contains_private_subnet(self, net_cidr):
        #-----don't process individual IP's-----
        net = self.is_cidr(net_cidr)
        if net:
            for subnet in self.private_subnet_list:
                if subnet.overlaps(net):
                    return True
        #-----no matches-----
        return False
    
    #--------------------------------------------------------------------------------
    
    #-----check if it's a CIDR-----
    def match_cidr(self, cidr):
        match = self.regex_cidr_pattern.search(cidr)
        if match:
            return match
        else:
            return None

    #-----match IP address pattern-----
    # not strict about the IP address, just check if it looks like an IP
    def match_ip(self, ip):
        match = self.regex_ipv4.search(ip)
        if match:
            return match
        else:
            return None

    #TODO: change references to this in code to use IPutil instead
    #-----check if it's an IP address-----
    def is_ip(self, host):
        return self.ip_util.is_ip(host)
    
    #TODO: change references to this in code to use IPutil instead
    def is_cidr(self, cidr):
        return self.ip_util.is_cidr(cidr)

    def valid_port(self, port: str) -> bool:
        if not port:
            return False
        if not port.isdigit():
            return False
        if len(port)>5:
            return False
        port_num = int(port)
        if not (0<port_num<65536):
            return False
        return True

    #--------------------------------------------------------------------------------
    
    #-----check if a given IP is on the protected list-----
    def is_protected_ip(self, ip):
        found_ip = self.ConfigData['ProtectedIPdict'].get(ip, None)
        if found_ip:
            return True
        return False
    
    def cidr_includes_protected_ip(self, cidr):
        #-----don't process individual IP's-----
        match = self.match_cidr(cidr)
        if not match:
            return False
        
        for protected_ip in self.ConfigData['ProtectedIPs']:
            #-----calculate if the given IP is covered by the blacklist CIDR entry-----
            if self.ip_cidr_check(protected_ip, cidr):
                return True
        #-----no matches-----
        return False
    
    #-----check if a given IP/CIDR is on the ProtectedIPs list in the config-----
    def is_protected(self, ip):
        if self.match_cidr(ip):
            return self.cidr_includes_protected_ip(ip)
        else:
            return self.is_protected_ip(ip)
    
    #--------------------------------------------------------------------------------
    
    #-----private/reserved/etc. all go into a general "special" group-----
    # pass in an IP string or a python ipaddress object
    def is_special_ip(self, ip=None, ip_obj=None):
        if ip:
            ip_obj = self.ip_util.is_ip(ip)
        if not ip_obj:
            return False
        if ip_obj.is_private or ip_obj.is_reserved or ip_obj.is_link_local or ip_obj.is_unspecified or ip_obj.is_loopback or self.ip_util.is_cg_nat(ip_obj=ip_obj):
            return True
        return False
    
    #--------------------------------------------------------------------------------
    #-----report if a given IP address is blocked-----
    # match against exact IP's or CIDR blocks containing the submitted IP
    def is_ip_blocked(self, server_ip):
        #-----check the iptables list that was pre-scanned into Config at startup-----
        if self.ConfigData['IPBlacklist'].get(server_ip, None):
            return True
        
        #-----check CIDR-----
        for item in self.ConfigData['IPBlacklist'].keys():
            match = self.match_cidr(item)
            if match:
                #-----calculate if the given IP is covered by the blacklist CIDR entry-----
                if self.ip_cidr_check(server_ip, item):
                    return True
        
        return False
    
    #--------------------------------------------------------------------------------
    
    def generate_class_c(self, ip):
        if not self.ip_util.is_ip(ip):
            return ''
        
        class_c = ''
        match = self.regex_class_c_pattern.match(ip)
        if match:
            class_c = match[1] + '0/24'
        
        return class_c
    
    #--------------------------------------------------------------------------------
    
    def get_host_from_url(self, url):
        if not url:
            return ''
        
        host = ''
        match = self.host_url_regex.search(url)
        if match:
            host = match[2]
        
        return host
    
    #--------------------------------------------------------------------------------
    
    def lookup_sqlite_ip_country(self, ip):
        if not self.db_ip_country:
            self.db_ip_country = zzzevpn.DB(self.ConfigData)
            self.db_ip_country.db_connect(self.ConfigData['DBFilePath']['IPCountry'])
        
        ip_int = int(ipaddress.ip_address(ip))
        sql = 'select country_code from ip_country_map where ip_min<=? and ip_max>=?'
        params = (ip_int, ip_int)
        row = self.db_ip_country.select(sql, params)
        if row:
            if row[0]:
                return row[0]
        
        return 'UNKNOWN'
    
    #--------------------------------------------------------------------------------
    
    #-----lookup country name and country code in maxmind DB for a given IP-----
    #TODO: find out what to do when country does not match registered_country
    # Data Available:
    # 1.0.0.1, 1.0.0.0/24
    # {'continent': {'code': 'OC',
    #                'geoname_id': 6255151,
    #                'names': {
    #                          'en': 'Oceania',
    #                         },
    #  'country': {'geoname_id': 2077456,
    #              'iso_code': 'AU',
    #              'names': {
    #                        'en': 'Australia',
    #                       }
    #  'registered_country': {'geoname_id': 2077456,
    #                         'iso_code': 'AU',
    #                         'names': {
    #                                   'en': 'Australia',
    #                                  }
    #                        }
    # }
    def lookup_ip_country(self, ip):
        country = 'UNKNOWN'
        if not self.ip_util.is_ip(ip):
            return country
        if not self.ip_util.is_public_ip(ip):
            return country
        if not self.ConfigData['EnableMaxMind']:
            if self.ConfigData['EnableSqliteIPCountry']:
                country = self.lookup_sqlite_ip_country(ip)
            return country
        
        if self.maxmind_reader is None:
            # self.maxmind_reader = maxminddb.open_database(self.ConfigData['DBFilePath']['GeoIP'])
            self.maxmind_reader = maxminddb.open_database(self.ConfigData['DBFilePath']['GeoIP'], mode=maxminddb.MODE_MEMORY)
        
        data = self.maxmind_reader.get(ip)
        
        if data is None:
            pass
            #-----report errors-----
            #TODO: how to handle IP's not in the DB?
        elif 'country' in data.keys():
            #-----where maxmind believes the user is located-----
            #TODO: report mismatches?
            # check_registered_country(data)
            country = data['country']['iso_code']
        elif 'registered_country' in data.keys():
            #-----where the ISP has registered the IP-----
            country = data['registered_country']['iso_code']
        elif 'continent' in data.keys():
            #-----no country, just use the continent value-----
            pass
        elif 'traits' in data.keys():
            # anonymous proxies and satellites have no country or continent
            # these may only exist in the paid maxmind DB
            self.check_traits(data)
        else:
            #-----report errors-----
            # this should never happen
            print(f'ERROR: get_country({ip})')
        
        #-----check the other DB for a country (slower)-----
        if country=='UNKNOWN' and self.ConfigData['EnableSqliteIPCountry']:
            country = self.lookup_sqlite_ip_country(ip)
        
        return country
    
    def check_traits(self, data, ip):
        if 'is_anonymous_proxy' in data['traits'].keys():
            print('ANONYMOUS PROXY: ' + ip)
        elif 'is_satellite_provider' in data['traits'].keys():
            print('SATELLITE' + ip)
    
    #--------------------------------------------------------------------------------
    
    #-----append data to a file-----
    def append_output(self, filepath, output, add_separator_line=False):
        with open(filepath, 'a') as write_file:
            if add_separator_line:
                write_file.write('-' * 80)
                write_file.write('\n')
            write_file.write(output)
    
    #-----save data to a file-----
    def save_output(self, filepath: str, output):
        with open(filepath, 'w') as write_file:
            write_file.write(output)
    
    #--------------------------------------------------------------------------------
    
    #-----lookup the Zzz System table data-----
    # the boot script looks for a flag file so it doesn't need the DB
    def reboot_needed(self, activate=False):
        reboot_needed_filepath = '/opt/zzz/apache/reboot_needed'
        if activate:
            if os.path.exists(reboot_needed_filepath):
                return True
            with open(reboot_needed_filepath, 'w'):
                pass
        if os.path.exists(reboot_needed_filepath):
            return True
        return False
    
    #-----lookup the Zzz System installed version in the DB-----
    def zzz_version(self):
        zzz_system_info_parsed = self.db.get_zzz_system_info()
        zzz_system_info = zzz_system_info_parsed['zzz_system_info']
        version = 0
        if zzz_system_info['version']:
            version = zzz_system_info['version']
        available_version = 0
        if zzz_system_info['available_version']:
            available_version = zzz_system_info['available_version']
        db_version = {
            'version': int(version),
            'available_version': int(available_version),
            'dev_version': zzz_system_info['dev_version'],
        }
        return db_version
    
    #--------------------------------------------------------------------------------
    
    # NOTE: this only counts running processes accurately if all instances are run with the full path
    # OS default: 'python3'
    # venv: '/opt/zzz/venv/bin/python3'
    def count_running_processes(self, name: str='python3', cmdline: list=[]) -> int:
        if not name:
            return 0
        
        # name - abbreviated to 15 chars by psutil
        if len(name)>15:
            name = name[0:15]
        
        found = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            proc_info_name = proc.info.get('name', '')
            if proc_info_name != name:
                continue
            #-----no extra command-line items? count the process-----
            if not cmdline:
                found += 1
                continue
            #-----got a list of command-line items? only count the process if ALL items are found-----
            found_all_cmdline = True
            for item in cmdline:
                proc_info_cmdline = proc.info.get('cmdline', [])
                if not proc_info_cmdline:
                    found_all_cmdline = False
                elif item not in proc_info_cmdline:
                    found_all_cmdline = False
            if found_all_cmdline:
                found += 1
        
        #-----got thru the whole process list without a match? return False-----
        return found
    
    #--------------------------------------------------------------------------------
    
    def sleep_until_file_updated(self, seconds, filepath):
        time_start = time.time()
        while (time.time() - time_start)<seconds:
            if os.path.exists(filepath):
                path_obj = pathlib.Path(filepath)
                if path_obj:
                    file_mtime = path_obj.stat().st_mtime
                    seconds_ago = time.time() - file_mtime
                    # modification time should be in the past 2 seconds
                    if seconds_ago<2:
                        return
            time.sleep(1)
    
    #--------------------------------------------------------------------------------
    
    #TODO: move this somewhere more appropriate?
    # json='{"EnableMaxMind": "false"}'
    def detect_maxmind_config_change(self):
        zzz_system_info_parsed = self.db.get_zzz_system_info()
        json_parsed = zzz_system_info_parsed['json_parsed']
        
        #-----empty json field? reset it-----
        if not json_parsed:
            json_parsed = {}
        EnableMaxMind = json_parsed.get('EnableMaxMind', None)
        if not EnableMaxMind:
            EnableMaxMind = 'false'
            json_parsed = { 'EnableMaxMind': EnableMaxMind, }
        
        should_update_maxmind_in_db = False
        if EnableMaxMind=='true' and not self.ConfigData['EnableMaxMind']:
            # maxmind was enabled in config, update the DB
            json_parsed['EnableMaxMind'] = 'false'
            should_update_maxmind_in_db = True
        elif EnableMaxMind=='false' and self.ConfigData['EnableMaxMind']:
            json_parsed['EnableMaxMind'] = 'true'
            should_update_maxmind_in_db = True
        if not should_update_maxmind_in_db:
            return
        
        self.db.update_zzz_system_info_json(json_parsed)
    
    #--------------------------------------------------------------------------------

    # safely encode data that might be ascii or utf-8
    def safe_encode(self, data):
        if not data:
            return ''
        # if isinstance(data, bytes):
        # do utf8 first?
        try:
            data = data.encode('ascii')
        except:
            # failed to encode ascii, try utf-8
            try:
                data = data.encode('utf-8')
            except:
                # failed to encode utf-8 also
                pass
        return data

    def safe_decode(self, data):
        if not data:
            return ''
        try:
            data = data.decode('utf-8')
        except:
            # failed to decode utf-8, try ascii
            try:
                data = data.decode('ascii')
            except:
                # failed to decode ascii also
                pass
        return data

    def encode_base64(self, data):
        if not data:
            return ''
        # base64 comes out in a binary format
        base64_binary = base64.b64encode(self.safe_encode(data))
        # need base64 in text format for JSON
        base64_ascii = base64_binary.decode('ascii')
        return base64_ascii
    
    #TODO: base64.b64decode(base64_text, validate=True)
    def decode_base64(self, base64_text):
        if not base64_text:
            return ''
        decoded_binary = base64.b64decode(self.safe_encode(base64_text))
        # decoded_ascii = decoded_binary.decode('ascii')
        decoded_ascii = self.safe_decode(decoded_binary)
        return decoded_ascii

    #--------------------------------------------------------------------------------

    def count_multiple_running_processes(self, process_filenames: list) -> int:
        count_processes = 0
        for process_filename in process_filenames:
            process_filepath = f'/opt/zzz/python/bin/{process_filename}'
            count_processes += self.count_running_processes(name=process_filename, cmdline=[process_filepath])
        return count_processes

    # assumes all processes are zzz python apps running from the zzz bin directory
    def wait_for_process_to_stop(self, process_filenames: list, max_wait: int=0, sleep_time: int=10, print_updates=False) -> bool:
        if not process_filenames:
            return False
        if max_wait > 3600:
            max_wait = 3600 # 1 hour
        if sleep_time > 60:
            sleep_time = 60 # 1 minute

        wait_time = 0
        while self.count_multiple_running_processes(process_filenames):
            wait_time += sleep_time
            time.sleep(sleep_time)
            # don't run this app forever, quit if too much time passes without the processes stopping
            if wait_time>max_wait:
                return False
        return True

    #--------------------------------------------------------------------------------

    #TODO: use redis for the flag instead of a file
    def check_db_maintenance_flag(self) -> bool:
        return os.path.exists(self.ConfigData['UpdateFile']['db_maintenance'])

    def get_db_maintenance_note(self) -> str:
        return self.get_filedata(self.ConfigData['UpdateFile']['db_maintenance'])

    def wait_for_no_db_maintenance(self, max_wait: int=0, sleep_time: int=10, print_updates=False) -> bool:
        if max_wait > 3600:
            max_wait = 3600 # 1 hour
        if sleep_time > 60:
            sleep_time = 60 # 1 minute
        if sleep_time < 1:
            sleep_time = 1

        wait_time = 0
        while self.check_db_maintenance_flag() and wait_time<max_wait:
            if print_updates:
                filedata = self.get_db_maintenance_note()
                print(f'DB maintenance flag is set({filedata}), waiting ({wait_time})...')
            wait_time += sleep_time
            time.sleep(sleep_time)
        return self.check_db_maintenance_flag()

    #-----tell the log parsers not to run until maintenance is done-----
    def set_db_maintenance_flag(self, data_to_write: str='db_maintenance'):
        self.save_output(self.ConfigData['UpdateFile']['db_maintenance'], data_to_write)

    def clear_db_maintenance_flag(self):
        if self.check_db_maintenance_flag():
            os.remove(self.ConfigData['UpdateFile']['db_maintenance'])

    #--------------------------------------------------------------------------------

    #-----return a python dictionary created from the called script's JSON output-----
    def lookup_ipwhois(self, ip: str) -> dict:
        commands = ['/opt/zzz/python/bin/ipwhois-lookup.py', '--ip', ip]
        # expect JSON data to be returned
        if not self.run_script(commands, binary_mode=True, decode_data=True):
            #-----error running ipwhois script-----
            run_result = {
                'data': self.script_output,
                'status': 'error',
                'error_msg': 'ipwhois script failed',
            }
            return run_result

        # script ran OK, now parse the output from JSON back into a python dictionary
        json_parsed = None
        try:
            json_parsed = json.loads(self.script_output)
        except:
            # error parsing JSON
            run_result = {
                'data': self.script_output,
                'status': 'error',
                'error_msg': f'invalid json from ipwhois script\n{self.script_output}',
            }
            return run_result

        # success
        run_result = {
            'data': json_parsed,
            'status': 'success',
            'error_msg': '',
        }
        return run_result

    #--------------------------------------------------------------------------------

    #-----decide if we have a domain or an IP, then call the appropriate function for lookup-----
    # 
    def lookup_whois_domain_or_ip(self, domain_or_ip: str):
        #-----IP's get looked-up with a separate function-----
        # using a local var, not the package var for iputil
        local_iputil = zzzevpn.IPutil(domain_or_ip)
        if local_iputil.ip or local_iputil.net:
            return self.lookup_ipwhois(domain_or_ip)

        #-----do a domain lookup-----
        import zzzevpn.WhoisService
        whois_service = zzzevpn.WhoisService.WhoisService()
        last_whois_row = whois_service.lookup_whois(domain_or_ip)
        return last_whois_row

    #--------------------------------------------------------------------------------
