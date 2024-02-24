#!/opt/zzz/venv/bin/python3

import base64
import datetime
import decimal
import dns.rdatatype
import dns.resolver
import dns.reversename
import glob
import ifcfg
import ipaddress
import json
import maxminddb
import nslookup
import os
import pathlib
import pprint
import psutil
import pytz
from pytz import timezone
import random
import re
import requests
# from string import Template
import shlex
import site
import socket
import string
import sys
import time
import uuid

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')
import zzzevpn
import zzzevpn.NetworkService

print("TEST\n")

def get_domain_from_host(host):
    TEST_TLD_list = ['com', 'net', 'org', 'gov', 'co.jp', 'co.uk', 'info', 'io', 'ru', 'tv']
    
    for TLD in TEST_TLD_list:
        match = re.search(r'\.(\w+)\.' + TLD + '$', host)
        if match:
            domain = match.group(1) + '.' + TLD
            return domain
    return host

#--------------------------------------------------------------------------------

def get_net_interface():
    default_interface = ifcfg.default_interface()
    print('default network device: ' + default_interface['device'])

#--------------------------------------------------------------------------------

def remove_ansi_codes(data):
    regex_pattern = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]', re.IGNORECASE)
    return regex_pattern.sub('', data)

#--------------------------------------------------------------------------------

def current_datetime():
    my_tz = 'America/Los_Angeles'
    datetime_now = datetime.datetime.now(timezone(my_tz))
    date_format = '%Y-%m-%d %H:%M:%S'
    formatted_date = datetime_now.strftime(date_format)
    return formatted_date

#--------------------------------------------------------------------------------

#-----find subdomains in a list that match domains in the list-----
# return a list without the matching subdomains
def remove_subdomains_with_matching_domains(assembled_list):
    clean_list = []
    for host in assembled_list:
        domain = get_domain_from_host(host)
        if domain == host or not domain in assembled_list:
            clean_list.append(host)
    return clean_list

def unique_sort(mylist):
    mylist.sort()
    return list(dict.fromkeys(mylist))

#--------------------------------------------------------------------------------

def rand_str():
    test_uuid = str(uuid.uuid4())
    return test_uuid

#--------------------------------------------------------------------------------

def show_time_diff(datetime_early, datetime_now=None):
    if not datetime_now:
        datetime_now = datetime.datetime.now()
    print(datetime_early.strftime('%X.%f'))
    print(datetime_now.strftime('%X.%f'))
    timedelta = datetime_now - datetime_early
    seconds = timedelta.total_seconds()
    print('seconds elapsed: ' + str(seconds))

#--------------------------------------------------------------------------------

regex_int_select_pattern = r'(\d+)'
regex_int_select = re.compile(regex_int_select_pattern, re.DOTALL | re.MULTILINE)

def str_to_int_or_str(data_str):
    if data_str.isdigit():
        return int(data_str)
    return data_str

def mixed_sort(data_str):
    return [ str_to_int_or_str(item) for item in regex_int_select.split(data_str) ]

def sleep_until_file_updated(seconds, filepath):
    time_start = time.time()
    while (time.time() - time_start)<seconds:
        if os.path.exists(filepath):
            timestamp_now = time.time()
            print('timestamp_now: ' + str(timestamp_now))
            path_obj = pathlib.Path(filepath)
            if path_obj:
                file_mtime = path_obj.stat().st_mtime
                print('  file_mtime: ' + str(file_mtime))
                seconds_ago = timestamp_now - file_mtime
                print(f'  modified {seconds_ago} seconds ago')
                # modification time should be in the past 2 seconds
                if seconds_ago<2:
                    print('EXIT')
                    return
        time.sleep(1)
    timestamp_now = time.time()
    print('timestamp_now: ' + str(timestamp_now))

def recursive_split(str_to_split):
    items = str_to_split.split('/', maxsplit=1)
    print(str_to_split + ' --> ' + pprint.pformat(items))
    if len(items)>1:
        recursive_split(items[1])

def print_int_or_not(util, testvar):
    if util.is_int(testvar):
        print(f'testvar="{testvar}" is an int')
    else:
        print(f'testvar="{testvar}" NOT an int')

def test_regex(pattern, test_str, flags):
    regex = re.compile(pattern, flags)
    if regex.match(test_str):
        print(f'match {test_str}')
    else:
        print(f'NO match {test_str}')

def test_function_crash_assignment(data, new_data):
    return data + new_data

def get_dict_values(data):
    values = []
    for key, value in data.items():
        new_values = []
        if isinstance(value, dict):
            new_values = get_dict_values(value)
        else:
            new_values = [value]
        values.extend(new_values)
    return values

def old_timestamp_to_date_hires(unix_timestamp):
    date_format_hi_res = '%Y-%m-%dT%H:%M:%S.%f'
    unix_timestamp = float(unix_timestamp)
    datetime_obj = datetime.datetime.fromtimestamp(unix_timestamp)
    return datetime_obj.strftime(date_format_hi_res)

def timestamp_to_date_hires(unix_timestamp, tz=datetime.timezone.utc):
    date_format_hi_res = '%Y-%m-%dT%H:%M:%S.%f'
    unix_timestamp = float(unix_timestamp)
    datetime_obj = datetime.datetime.fromtimestamp(unix_timestamp, tz)
    return datetime_obj.strftime(date_format_hi_res)

#--------------------------------------------------------------------------------

#####################################
#-----CALL FUNCTIONS BELOW HERE-----#
#####################################

config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()

country_filename_regex = re.compile(r'\/([^\/]+)\.zone$')
country_files = glob.glob(os.path.join(ConfigData['IPdeny']['ipv4']['src_dir'], '*.zone'))
for filepath in sorted(country_files):
    match = country_filename_regex.search(filepath)
    if match:
        country_code = match.group(1)
        ConfigData['IPdeny']['countries'].append(country_code)

pprint.pprint(ConfigData['IPdeny']['countries'])

quit()

#--------------------------------------------------------------------------------

