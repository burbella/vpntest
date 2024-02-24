#!/opt/zzz/venv/bin/python3

# OLD: !/usr/bin/env python3

#-----download and install list of country codes-----

import argparse
from datapackage import Package
import json
import site
import os
import sys
import urllib.request

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

util = zzzevpn.Util(ConfigData)

#--------------------------------------------------------------------------------

def get_json_data(url):
    page_data = None
    try:
        page_request = urllib.request.urlopen(url)
        page_data = page_request.read().decode('utf-8')
    except:
        print(f'ERROR downloading JSON page data for {url}')
        return None
    
    json_data = None
    try:
        json_data = json.loads(page_data)
    except:
        print(f'ERROR parsing JSON page data for {url}')
        return None
    
    return json_data

#--------------------------------------------------------------------------------

def get_json_datapackage(datahub_io_url):
    country_codes = None
    try:
        package = Package(datahub_io_url)
        resource_data_json = package.get_resource('data_json')
        country_codes_url = resource_data_json.descriptor['path']
        country_codes = get_json_data(country_codes_url)
    except:
        country_codes = None
    
    return country_codes

#--------------------------------------------------------------------------------

#TODO: remove "TEST-" from filenames before going live
# downloaded file(UTF8): country-codes-utf8.json
# file converted to ASCII: country-codes.json
read_filepath = '/opt/zzz/data/country-codes-utf8.json'
utf8_filepath = '/opt/zzz/data/TEST-country-codes-utf8.json'
ascii_filepath = '/opt/zzz/data/TEST-country-codes.json'

#TEST - conversion of the existing UTF-8 file to ASCII
print('reading file...')
country_codes = ''
# with open(utf8_filepath, mode='r') as read_file:
with open(read_filepath, mode='r') as read_file:
    country_codes = read_file.read()
if country_codes:
    print('converting to ASCII...')
    country_codes_json_parsed = json.loads(country_codes)
    # handle each string separately
    ascii_data = []
    for item in country_codes_json_parsed:
        ascii_item = { 'Code': item['Code'], 'Name':util.convert_utf8_to_ascii(item['Name']) }
        ascii_data.append(ascii_item)
    if ascii_data:
        print('writing file...')
        with open(ascii_filepath, 'w') as write_file:
            write_file.write(json.dumps(ascii_data))
print('DONE')
sys.exit()
#ENDTEST

##################################################

datahub_io_url = 'https://datahub.io/core/country-list/datapackage.json'

print('downloading country codes')
country_codes = get_json_datapackage(datahub_io_url)
if not country_codes:
    print(f'ERROR getting country codes from {datahub_io_url}')
    sys.exit(1)

#-----save downloaded country codes to a file-----
print('saving country codes')
with open(utf8_filepath, 'w') as write_file:
    write_file.write(country_codes)

#-----convert from UTF-8 to to ASCII-----
ascii_data = util.convert_utf8_to_ascii(country_codes)
if not ascii_data:
    print(f'ERROR converting country codes to ASCII')
    sys.exit(1)

#-----save to a separate file-----
with open(ascii_filepath, 'w') as write_file:
    write_file.write(ascii_data)

