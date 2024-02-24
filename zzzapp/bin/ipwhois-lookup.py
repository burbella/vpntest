#!/opt/zzz/venv_alt/bin/python3
# ^^^ DIFFERENT VENV: "venv_alt" has the old ipwhois package

#-----lookup ipwhois with an alternate venv-----
# returns JSON data
# moved ipwhois-related code into here from WhoisService.py
# this allows old packages to run in a separate venv, while the main venv can be upgraded with the latest packages
# dnspython cannot upgrade beyond 2.0.0 because ipwhois requires dnspython==2.0.0
#   ipwhois 1.2.0 is the latest version, released 9/17/2020

import argparse
# import ipaddress
from ipwhois import IPWhois
# import ipwhois.utils
import json
# import pprint
import site
import sys
import time

#-----run at minimum priority-----
# os.nice(19)

#-----make sure we're running as root or exit-----
# if os.geteuid()==0:
#     print('Zzz memory check', flush=True)
# else:
#     sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
# config = zzzevpn.Config(skip_autoload=True)
# ConfigData = config.get_config_data()
# if not config.is_valid():
#     sys.exit('ERROR: invalid zzz config file')

#--------------------------------------------------------------------------------

#-----save asn data-----
def ipwhois_process_asn(ipwhois_result: dict, ipwhois_processed_result: dict) -> dict:
    ipwhois_processed_result['asn'] = ipwhois_result.get('asn', '')
    ipwhois_processed_result['asn_cidr'] = ipwhois_result.get('asn_cidr', '')
    ipwhois_processed_result['asn_country_code'] = ipwhois_result.get('asn_country_code', '')
    ipwhois_processed_result['asn_date'] = ipwhois_result.get('asn_date', '')
    ipwhois_processed_result['asn_date_int'] = ipwhois_result.get('asn_date_int', None)
    ipwhois_processed_result['asn_description'] = ipwhois_result.get('asn_description', '')
    # if ipwhois_result['asn']:
    #     ipwhois_processed_result['asn'] = ipwhois_result['asn']
    # if ipwhois_result['asn_cidr']:
    #     ipwhois_processed_result['asn_cidr'] = ipwhois_result['asn_cidr']
    # if ipwhois_result['asn_country_code']:
    #     ipwhois_processed_result['asn_country_code'] = ipwhois_result['asn_country_code']
    # if ipwhois_result['asn_date']:
    #     ipwhois_processed_result['asn_date'] = ipwhois_result['asn_date']
    # if ipwhois_result['asn_description']:
    #     ipwhois_processed_result['asn_description'] = ipwhois_result['asn_description']

    #TODO: convert the date to an int that the DB can handle
    # ??? 'asn_date_int': None,

    return ipwhois_processed_result

#-----save network data-----
def ipwhois_process_network(ipwhois_result: dict, ipwhois_processed_result: dict) -> dict:
    result_network = ipwhois_result.get('network', None)
    if result_network:
        ipwhois_processed_result['network_cidr'] = result_network.get('cidr', '')
        ipwhois_processed_result['network_country_code'] = result_network.get('cidr', 'country')
        ipwhois_processed_result['ip_version'] = result_network.get('ip_version', '')
    # if ipwhois_result['network']['cidr']:
    #     ipwhois_processed_result['network_cidr'] = ipwhois_result['network']['cidr']
    # if ipwhois_result['network']['country']:
    #     ipwhois_processed_result['network_country_code'] = ipwhois_result['network']['country']
    # if ipwhois_result['network']['ip_version']:
    #     ipwhois_processed_result['ip_version'] = ipwhois_result['network']['ip_version']
    return ipwhois_processed_result

def ipwhois_process_org(ipwhois_result: dict, ipwhois_processed_result: dict) -> dict:
    #-----find the org name-----
    entities = ipwhois_result.get('entities', None)
    objects = ipwhois_result.get('objects', None)
    if (not entities) or (not objects):
        return ipwhois_processed_result

    first_entity = entities[0]
    contact = objects[first_entity].get('contact', None)
    if not contact:
        return ipwhois_processed_result

    contact_name = contact.get('name', None)
    if contact_name:
        ipwhois_processed_result['org'] = contact_name
    return ipwhois_processed_result

#-----make the ipwhois output easier to work with-----
def cleanup_ipwhois_data(ip: str, ipwhois_result: dict) -> dict:
    if (not ip) or (not ipwhois_result):
        return {}

    #-----initialize the processed_result dictionary-----
    ipwhois_processed_result = {
        'ip': ip,
        'zzz_last_updated': int(time.time()),
        'json': '',
        'raw_whois': '',

        'asn': '',
        'asn_cidr': '',
        'asn_country_code': '',
        'asn_date': '',
        # what is asn_date_int and why was it never included in previous code?
        'asn_date_int': 0,
        'asn_description': '',

        'network_cidr': '',
        'network_country_code': '',
        'ip_version': '',

        'org': '',
    }

    #-----move the raw data to a separate field-----
    # ipwhois_processed_result['raw_whois'] = ipwhois_result['raw']
    # ipwhois_result['raw'] = None
    #NOTE: raw_whois was only needed for initial testing/debugging, it clutters the display otherwise
    try:
        ipwhois_processed_result['json'] = json.dumps(ipwhois_result)
    except:
        pass

    #-----process result data fields-----
    ipwhois_processed_result = ipwhois_process_asn(ipwhois_result, ipwhois_processed_result)
    ipwhois_processed_result = ipwhois_process_network(ipwhois_result, ipwhois_processed_result)
    ipwhois_processed_result = ipwhois_process_org(ipwhois_result, ipwhois_processed_result)

    return ipwhois_processed_result

#--------------------------------------------------------------------------------

##################################################
#TODO: migrate OLD code from WhoisService.py:
# self.lookup_ipwhois(domain_or_ip)
# self.cleanup_ipwhois_data(domain_or_ip)
##################################################

def print_json(result: dict):
    output = ''
    try:
        output = json.dumps(result)
    except:
        err_result = {
            'data': '',
            'status': 'error',
            'error_msg': 'ERROR generating JSON',
        }
        print(json.dumps(err_result))
    print(output)

#--------------------------------------------------------------------------------

def run_ipwhois_test(ip: str) -> dict:
    #TEST
    # print(f'IP: {ip}')

    result = {
        'data': '',
        # 'status': 'success',
        'status': 'error',
        'error_msg': 'ERROR',
    }

    #-----validate IP-----
    ip_util = zzzevpn.IPutil(ip)
    if not (ip_util.ip or ip_util.net):
        result['error_msg'] = 'ERROR: not an IP or CIDR'
        return result

    ipwhois_obj = None
    try:
        ipwhois_obj = IPWhois(ip)
    except Exception as e:
        result['error_msg'] = "IPWhois() ERROR: {}".format(e)
        return result

    if not ipwhois_obj:
        result['error_msg'] = 'ERROR: IPWhois() not defined'
        return result

    #TEST
    # print('TEST ipwhois_obj:')
    # pprint.pprint(ipwhois_obj)

    ipwhois_result = None
    try:
        #TEST - to include raw data from the RDAP lookup:
        # ipwhois_result = ipwhois_obj.lookup_rdap(depth=1, inc_raw=True)
        #LIVE: no raw data
        ipwhois_result = ipwhois_obj.lookup_rdap(depth=1)
    except Exception as e:
        result['error_msg'] = "ipwhois lookup ERROR: {}".format(e)
        return result

    #TEST
    # print('TEST ipwhois_result:')
    # pprint.pprint(ipwhois_result)

    ipwhois_processed_result = cleanup_ipwhois_data(ip, ipwhois_result)

    result = {
        'data': ipwhois_processed_result,
        'status': 'success',
        'error_msg': '',
    }
    return result

#--------------------------------------------------------------------------------

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='')
arg_parser.add_argument('--ip', dest='ip', action='store', help='IP address to run ipwhois on')
args = arg_parser.parse_args()

ip = ''

count_args = 0

if args.ip:
    count_args += 1
    ip = args.ip

#--------------------------------------------------------------------------------

if count_args==0:
    arg_parser.print_help()
    sys.exit()

if ip:
    result = run_ipwhois_test(ip)
    print_json(result)
