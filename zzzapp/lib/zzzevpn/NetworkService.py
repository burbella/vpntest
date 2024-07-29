#-----Network Services-----
# DNS, IPwhois, nslookup, Reverse DNS, Whois

#TODO: split this into NetworkService.py and NetworkServicePage.py ?

import datetime
import json
# import nslookup
import pprint
import re
import time

#-----package with all the Zzz modules-----
import zzzevpn
import zzzevpn.WhoisService

class NetworkService:
    'Network Services - DNS, IPwhois, nslookup, Reverse DNS, Whois'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    dns_service: zzzevpn.DNSservice = None
    ip_whois_obj = None
    iputil: zzzevpn.IPutil = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None
    whois_service: zzzevpn.WhoisService.WhoisService = None
    
    action: str = ''
    default_action = 'network_service'
    allowed_actions_get = ['network_service', 'nslookup', 'reverse_dns', 'whois', 'whois_cache', 'ipwhois_cache', 'ips_by_country']
    allowed_actions_post = ['nslookup', 'reverse_dns', 'whois', 'whois_cache', 'ipwhois_cache', 'ips_by_country']
    allowed_get_params = ['action', 'host', 'ip']
    allowed_post_params = ['action', 'host', 'ip', 'do_delete', 'nslookup_dns_blocked', 'whois_server_only']
    from_post: bool = False
    nslookup_dns_blocked: bool = False
    whois_server_only: bool = False
    db_domain_list = []
    last_whois_row = None
    NetworkServiceHTML = {}
    
    whois_date_fields = ['zzz_last_updated', 'creation_date', 'expiration_date', 'updated_date']
    service_name = 'network_service'
    whois_max_days = 30
    whois_max_seconds = whois_max_days*86400
    
    #TODO: check whois server domain
    #      check the domain's IP address
    #      check the IP-country against the blocked country list
    #      don't attempt the whois lookup if the whois server's IP is blocked
    #      report an error in that case
    # also check nameservers? (DNS-block, DNS-country, and IP-country)
    
    #TODO: finish updating these lists, load the lists from textfiles
    #-----whois data analysis-----
    privacy_services = []
    regex_privacy_services_patterns = [
        r'.*(whois protection|private|privacy|redacted).*',
        # r'whois protection.*',
        # r'.*privacy.*',
        # r'.*redacted.*',
        #TEST: maybe pattern-match "*privacy*" and "*redacted*" on org and/or name - could be a yellow flag
    ]
    regex_privacy_services = []
    
    registrars = []
    
    test_mode = False

    #TEST
    environ: dict = None

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None) -> None:
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
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
        if self.whois_service is None:
            self.whois_service = zzzevpn.WhoisService.WhoisService()
        self.dns_service = zzzevpn.DNSservice()
        self.data_validation = zzzevpn.DataValidation(self.ConfigData, enforce_rules=True, auto_clean=True)
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Network Service', self.settings)
        self.init_vars()

    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self) -> None:
        #TEST - remove this when it seems to be working
        # self.data_validation.should_print_test_results = True
        # self.test_mode = True

        self.action = self.default_action
        self.from_post = False
        self.nslookup_dns_blocked = False
        self.whois_server_only = False
        
        #-----prep the HTML values-----
        self.NetworkServiceHTML = {
            'domain': '""', # gets inserted into a javascript function call
            'show_header': 'true', # gets inserted into a javascript function call
            'TESTDATA': '',
        }
        self.regex_privacy_services = []
        for item in self.regex_privacy_services_patterns:
            self.regex_privacy_services.append(re.compile(item, re.IGNORECASE | re.DOTALL))
        self.get_registrars()
        self.get_registrar_privacy_services()

    #--------------------------------------------------------------------------------

    def print_test_results(self, data) -> None:
        if self.test_mode:
            pprint.pprint(data)

    #--------------------------------------------------------------------------------
    
    def get_registrars(self) -> None:
        self.registrars = []
        filepath = '/opt/zzz/data/registrars.txt'
        registrars_data = self.util.get_filedata(filepath)
        if not registrars_data:
            return
        for registrar in registrars_data.split('\n'):
            if not registrar:
                continue
            if len(registrar)<3:
                continue
            self.registrars.append(registrar)
    
    def get_registrar_privacy_services(self) -> None:
        self.privacy_services = []
        filepath = '/opt/zzz/data/registrar_privacy_services.txt'
        privacy_services_data = self.util.get_filedata(filepath)
        if not privacy_services_data:
            return
        for privacy_service in privacy_services_data.split('\n'):
            if not privacy_service:
                continue
            if len(privacy_service)<3:
                continue
            self.privacy_services.append(privacy_service)
    
    #--------------------------------------------------------------------------------
    
    # before downloading the URL contents, check some things:
    #     domain: rdap.verisign.com
    #     check if tld-blocked:
    #         tld: com
    #         blocked? no
    #     get IP: 199.7.54.30
    #         check if IP-blocked: no
    #     lookup IP-country: US
    #         check if country-blocked: no
    # if it passes all checks, do the standard RDAP lookup/parse
    # return: status(bool), err_msg(str)
    def check_rdap_server(self, domain: str):
        location, err_msg = self.whois_service.get_rdap_server(domain)
        if err_msg:
            #TODO: ERROR
            return False, err_msg
        
        rdap_host = self.util.get_host_from_url(location)
        if not rdap_host:
            #TODO: ERROR
            return False, 'ERROR: no host in URL'
        rdap_domain = self.util.get_domain_from_host(rdap_host)
        
        # check if tld-blocked
        tld_extract_result = self.util.get_tld_from_host(rdap_domain)
        if not tld_extract_result:
            return False, f'ERROR: failed to extract tld from RDAP domain "{rdap_domain}"'
        # rdap_tld, country_two_level_tld = tld_extract_result
        check_tld = tld_extract_result[0]
        if tld_extract_result[1]:
            check_tld = tld_extract_result[1]
        if self.util.is_country_tld(check_tld):
            if self.settings.is_blocked_country(check_tld):
                return False, 'ERROR: RDAP server country blocked'
            if self.settings.is_blocked_tld(check_tld):
                return False, 'ERROR: RDAP server TLD blocked'
        
        # maybe: check IP-blocks?
        
        return True, ''
    
    #--------------------------------------------------------------------------------
    
    def lookup_rdap(self, domain: str, rdap_server_only: bool=False):
        # self.check_rdap_server(domain)
        rdap_result_obj = self.whois_service.lookup_rdap(domain)
        #TODO: extract data from rdap_result_obj and process it
    
    #--------------------------------------------------------------------------------
    
    def handle_get(self, environ: dict):
        self.environ = environ
        self.init_vars()

        pagetitle = 'Network Service'
        # self.webpage.update_header(environ, pagetitle)
        
        #-----read the GET data-----
        data = self.webpage.load_data_from_get(environ, self.allowed_get_params)

        if not data['action']:
            data['action'] = self.default_action
        if not data['action'] in self.allowed_actions_get:
            self.webpage.error_log(environ, 'ERROR: invalid action')
            return self.make_error_webpage(environ, 'ERROR: invalid action')
        self.action = data['action']

        if data['ip']:
            pagetitle = f'''Whois {data['ip']}'''
            # self.webpage.update_header(environ, f'''Whois {data['ip']}''')
        if data['host']:
            data['host'] = data['host'].lower()
            if data['action'] == 'nslookup':
                pagetitle = f'''nslookup {data['host']}'''
                # self.webpage.update_header(environ, f'''nslookup {data['host']}''')
            else:
                pagetitle = f'''Whois {data['host']}'''
                # self.webpage.update_header(environ, f'''Whois {data['host']}''')

        self.print_test_results([f'handle_get() - action={self.action} - data:', data])

        #-----validate data-----
        if not self.data_validation.validate(environ, data):
            details = '<br>\n'.join(self.data_validation.validation_status_msgs)
            err_html = f'ERROR: data validation failed<br>\n{details}'
            return self.make_error_webpage(environ, err_html)

        #-----GET requests go to the new process flow-----
        # load the network service HTML template with the data filled-in
        # then jquery will fetch the data by AJAX
        # no more custom pages for most services
        if self.action == 'whois':
            return self.make_webpage(environ, 'Whois', data)
        elif self.action == 'nslookup':
            return self.make_webpage(environ, 'nslookup', data)
        elif self.action =='reverse_dns':
            return self.make_webpage(environ, 'reverse_dns', data)
        elif self.action=='ips_by_country':
            return self.show_ips_by_country(environ)

        #-----default page-----
        return self.make_webpage(environ, pagetitle, data)

    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    def handle_post(self, environ, request_body_size):
        self.environ = environ
        self.init_vars()
        self.from_post = True

        #-----return if missing data-----
        if request_body_size==0:
            return self.make_return_json('error', 'missing data', 'ERROR: missing data')

        self.webpage.update_header(environ, 'Network Service')
        
        #-----read the POST data-----
        data = self.webpage.load_data_from_post(environ, request_body_size, self.allowed_post_params)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        if not data['action']:
            data['action'] = self.default_action
        if not data['action'] in self.allowed_actions_post:
            return self.webpage.error_log(environ, 'ERROR: invalid action')
        self.action = data['action']

        if data['host']:
            data['host'] = data['host'].lower()
        
        # checkboxes 0/1
        if data['nslookup_dns_blocked'] is not None:
            self.nslookup_dns_blocked = True
        if data['whois_server_only'] is not None:
            self.whois_server_only = True

        data['nslookup_dns_blocked'] = self.nslookup_dns_blocked
        data['whois_server_only'] = self.whois_server_only

        self.print_test_results([f'handle_post() - action={self.action} - data:', data])

        #-----validate data-----
        if not self.data_validation.validate(environ, data):
            details = '<br>\n'.join(self.data_validation.validation_status_msgs)
            return self.make_return_json('error', 'data validation failed', f'ERROR: data validation failed<br>\n{details}')

        if self.action=='nslookup':
            return self.do_nslookup(data['host'])
        elif self.action=='reverse_dns':
            return self.lookup_reverse_dns(environ, data['ip'])
        elif self.action=='whois':
            if self.lookup_whois(data['host']):
                if self.iputil.ip or self.iputil.net:
                    return self.make_ipwhois_output_page(environ, self.last_whois_row)
                return self.make_whois_output_page(environ, self.last_whois_row)
            host = data['host']
            if not host:
                host = ''
            err = f'failed to lookup whois for host {host}'
            return self.make_return_json('error', err, f'ERROR: {err}')
        elif self.action=='whois_cache':
            if data['do_delete']:
                return self.delete_whois_cache(environ, data)
            # return self.show_whois_cache(environ)
        elif self.action=='ipwhois_cache':
            if data['do_delete']:
                return self.delete_ipwhois_cache(environ, data)
            # return self.show_ipwhois_cache(environ)
        elif self.action=='ips_by_country':
            return self.show_ips_by_country(environ)

        return self.make_return_json('error', 'invalid action', 'ERROR: invalid action')

    #--------------------------------------------------------------------------------

    #TODO: remove this
    # def check_action(self, environ):
    #     self.action = None
    #     if environ['PATH_INFO'] == '/network_service':
    #         self.action = 'network_service'

    #     if environ['PATH_INFO'] == '/nslookup':
    #         self.action = 'nslookup'
    #     elif environ['PATH_INFO'] == '/reverse_dns':
    #         self.action = 'reverse_dns'
    #     elif environ['PATH_INFO'] == '/whois':
    #         self.action = 'whois'
    #     elif environ['PATH_INFO'] == '/whois_cache':
    #         self.action = 'whois_cache'
    #     elif environ['PATH_INFO'] == '/ipwhois_cache':
    #         self.action = 'ipwhois_cache'
    #     #TEST
    #     self.print_test_results(f'check_action() - action: {self.action}')

    #--------------------------------------------------------------------------------

    # https://pypi.org/project/nslookup/
    # Returns an object containing two arrays:
    #     response_full: the full DNS response string(s)
    #     answer: the parsed DNS answer (list of IPs or SOA string)
    #
    # dns_query = Nslookup(dns_servers=["1.1.1.1"])
    #
    # ips_record = dns_query.dns_lookup(domain)
    # print(ips_record.response_full, ips_record.answer)
    #
    # soa_record = dns_query.soa_lookup(domain)
    # print(soa_record.response_full, soa_record.answer)
    def do_nslookup(self, host, raw_data=False):
        if not self.util.valid_domain(host):
            result = {
                'status': 'error',
                'details': 'invalid domain',
            }
            if raw_data:
                return result
            return json.dumps(result)
        
        # nslookup_service = nslookup.Nslookup(dns_servers=self.ConfigData['IPv4']['NameServers'])
        
        # ips_record = nslookup_service.dns_lookup(host)
        
        # soa_record = nslookup_service.soa_lookup(host)
        
        # nameserver = self.ConfigData['IPv4']['NameServers'][0]
        nameserver = '10.8.0.1'
        if self.nslookup_dns_blocked:
            nameserver = '10.6.0.1'
        
        #-----include a call to "dig" also-----
        dig_output = ''
        if self.util.run_script(['/usr/bin/dig', '@'+nameserver, host]):
            dig_output = self.util.subprocess_output.stdout
            if not dig_output:
                dig_output = ''
        
        if self.util.run_script(['/usr/bin/nslookup', host, nameserver]):
            output = self.util.subprocess_output.stdout
            if (not output) and self.util.script_output:
                output = self.util.script_output
            dashes = '-'*50
            result = {
                'status': 'success',
                'details': f'{output}\n{dashes}\n{dig_output}',
            }
            if raw_data:
                return result
            return json.dumps(result)
        
        result = {
            'status': 'error',
            'details': self.util.script_output,
        }
        if raw_data:
            return result
        return json.dumps(result)
    
    #--------------------------------------------------------------------------------
    
    #TEST: 74.125.195.189, 8.8.8.8
    # https://services.zzz.zzz/z/network_service?action=reverse_dns&ip=74.125.195.189
    # https://services.zzz.zzz/z/network_service?action=reverse_dns&ip=74.125.195.189,8.8.8.8
    #   return the RDNS lookups in a JSON {ip:rdns, ip2:rdns2, ...}
    def lookup_reverse_dns(self, environ, ip):
        if not ip:
            return '{}'

        #-----optional list of IP's instead of just one at a time-----
        ip_list = ip.split(',')
        if len(ip_list)==0:
            return '{}'

        result = {}
        for ip in ip_list:
            host = self.dns_service.lookup_reverse_dns(ip)
            if host:
                result[ip]=host.rstrip('.')
            # too many lookups too fast causes the DNS server to delay/refuse service, so sleep between lookups
            time.sleep(0.1)
        return json.dumps(result)
    
    #--------------------------------------------------------------------------------
    
    #TEST:
    # https://www.whois.com/whois/52.114.75.150
    #   CIDR:           52.96.0.0/12, 52.112.0.0/14
    #   Organization:   Microsoft Corporation (MSFT)
    # https://services.zzz.zzz/z/network_service?action=whois&host=52.114.75.150
    
    #-----lookup and IP/CIDR-----
    # ip text not null,
    # json text not null,
    # zzz_last_updated integer not null,
    # 
    # asn text not null,
    # asn_cidr text not null,
    # asn_country_code text,
    # asn_date text,
    # asn_date_int integer,
    # asn_description text not null,
    # 
    # network_cidr text not null,
    # network_country_code text,
    # ip_version text not null,
    # 
    # org text,
    # 
    # raw_whois text
    #
    # Registrar WHOIS Server: whois.markmonitor.com
    # Registrar URL: http://www.markmonitor.com
    def lookup_ipwhois(self, ip):
        #-----check the DB first-----
        # make sure integer date fields come back as integers
        sql = '''select ip, json, strftime('%s', zzz_last_updated) as 'zzz_last_updated',
            asn, asn_cidr, asn_country_code, asn_date, asn_date_int, asn_description,
            network_cidr, network_country_code, ip_version,
            org, raw_whois
            from ipwhois_cache where ip=?'''
        params = (ip,)
        (colnames, rows, data_with_colnames) = self.db.select_all(sql, params)
        
        if data_with_colnames:
            if not self.whois_expired(data_with_colnames[0]):
                self.last_whois_row = data_with_colnames[0]
                return True
        
        #-----no DB entry or old DB entry?  lookup online and save to DB-----
        run_result = None
        try:
            # result = self.whois_service.lookup_ipwhois(ip)
            # self.whois_service.cleanup_ipwhois_data(ip)

            #########################################
            #TODO: upgrade to using ipwhois-lookup.py
            # self.util.lookup_whois_domain_or_ip()
            #########################################

            # run_script success/fail gets reported in run_result['data']
            # ipwhois lookup success/fail gets reported in run_result['data']['data']
            run_result = self.util.lookup_ipwhois(ip)
        except Exception as e:
            # if self.whois_service.err:
            #     self.webpage.error_log(self.environ, 'WhoisService: {}'.format(self.whois_service.err))
            # self.webpage.error_log(self.environ, 'NetworkService.lookup_ipwhois() - ERROR: {}'.format(e))
            # #TODO: error handling
            # return False
            pass
        
        # self.last_whois_row = self.whois_service.ipwhois_processed_result
        if run_result['status'] == 'error':
            self.webpage.error_log(self.environ, f'''NetworkService.lookup_ipwhois() - ERROR: {run_result['error_msg']}''')
            return False

        if run_result['data']['status'] == 'error':
            self.webpage.error_log(self.environ, f'''ipwhois-lookup.py - ERROR: {run_result['data']['error_msg']}''')
            return False

        self.last_whois_row = run_result['data']['data']
        self.save_ipwhois_entry(self.last_whois_row)
        return True

    #--------------------------------------------------------------------------------
    
    #-----remove junk from a submitted string-----
    # \n, \r, \t, space, comma
    def cleanup_form_str(self, host):
        return host.replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '').replace(',', '')
    
    #-----host can be an IP or domain name-----
    def lookup_whois(self, host):
        if not host:
            return False
        
        host = self.cleanup_form_str(host)
        
        #-----check if we got an IP/CIDR, process separately-----
        self.iputil = zzzevpn.IPutil(host)
        if self.iputil.ip or self.iputil.net:
            return self.lookup_ipwhois(host)
        
        #-----reduce host to domain-----
        domain = self.util.get_domain_from_host(host)
        
        #-----check the DB first-----
        # make sure date fields come back as integers
        # sql = 'select * from whois_cache where domain=?'
        sql = "select domain, json, strftime('%s', zzz_last_updated) as 'zzz_last_updated', registrar, org, country_code, strftime('%s', creation_date) as 'creation_date', strftime('%s', expiration_date) as 'expiration_date', strftime('%s', updated_date) as 'updated_date', raw_whois from whois_cache where domain=?"
        params = (domain,)
        # row = self.db.select(sql, params)
        (colnames, rows, data_with_colnames) = self.db.select_all(sql, params)
        
        if data_with_colnames:
            if not self.whois_expired(data_with_colnames[0]):
                self.last_whois_row = data_with_colnames[0]
                return True
        
        #-----no DB entry or old DB entry?  lookup online and save to DB-----
        result = None
        try:
            result = self.whois_service.lookup_whois(domain)
            #TODO: user a new service when it is ready:
            # result = self.whois_service.lookup_whois_wizard(domain)
        except:
            #TODO: error handling
            return False

        #-----validate the domain-----
        if not self.util.valid_domain(domain):
            return False

        self.last_whois_row = self.whois_service.processed_result
        self.save_whois_entry()
        return True
    
    #--------------------------------------------------------------------------------
    
    #-----empty query or over 30 days old?  mark it expired-----
    def whois_expired(self, row):
        if not row:
            return True
        ts = time.time()
        if (ts - int(row['zzz_last_updated'])) > self.whois_max_seconds:
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    # "upsert" requires SQLite 3.24.0 or newer?  other alternatives?
    # table whois_cache:
    #     domain text not null
    #     json text not null - parsed whois fields in json format
    #     zzz_last_updated integer not null - date last updated in the zzz system
    #     registrar text
    #     org text
    #     country_code text
    #     creation_date integer
    #     expiration_date integer
    #     updated_date integer - date last updated in the whois server
    #     raw_whois text - all text from the whois server, including unparsed fields
    def save_whois_entry(self, processed_result=None):
        #-----allow passing-in of a processed_result value-----
        if processed_result is None:
            processed_result = self.whois_service.processed_result
        #-----take the processed_result from the whois_service object-----
        if not processed_result['domain']:
            # still no data after looking in the whois_service object?  just return
            return
        
        processed_result['zzz_last_updated'] = int(processed_result['zzz_last_updated'])
        if processed_result['creation_date']:
            processed_result['creation_date'] = int(processed_result['creation_date'])
        if processed_result['expiration_date']:
            processed_result['expiration_date'] = int(processed_result['expiration_date'])
        if processed_result['updated_date']:
            processed_result['updated_date'] = int(processed_result['updated_date'])
        if processed_result['country_code']:
            #-----deal with unneeded arrays-----
            if isinstance(processed_result['country_code'], list):
                processed_result['country_code'] = processed_result['country_code'][0]
            #-----country codes should be uppercase-----
            processed_result['country_code'] = processed_result['country_code'].upper()
        
        #TEST - log processed_result
        # self.webpage.error_log(self.environ, 'NetworkService: {}'.format(processed_result))
        
        sql = 'select * from whois_cache where domain=?'
        params = (processed_result['domain'],)
        row = self.db.select(sql, params)
        #TODO: finish param inserts
        if row:
            sql_update = "update whois_cache set json=?, zzz_last_updated=datetime('now'), registrar=?, org=?, country_code=?, creation_date=datetime(?, 'unixepoch'), expiration_date=datetime(?, 'unixepoch'), updated_date=datetime(?, 'unixepoch'), raw_whois=? where domain=?"
            params = (str(self.whois_service.whois_result), processed_result['registrar'], processed_result['org'], processed_result['country_code'], processed_result['creation_date'], processed_result['expiration_date'], processed_result['updated_date'], self.whois_service.whois_result.text, processed_result['domain'])
            self.db.query_exec(sql_update, params)
        else:
            # domain text not null,
            # json text not null,
            # zzz_last_updated integer not null,
            # registrar text,
            # org text,
            # country_code text,
            # creation_date integer,
            # expiration_date integer,
            # updated_date integer,
            # raw_whois text
            # datetime(FIELD, 'unixepoch')
            sql_insert = "insert into whois_cache (domain, json, zzz_last_updated, registrar, org, country_code, creation_date, expiration_date, updated_date, raw_whois) values (?, ?, datetime('now'), ?, ?, ?, datetime(?, 'unixepoch'), datetime(?, 'unixepoch'), datetime(?, 'unixepoch'), ?)"
            params = (processed_result['domain'], str(self.whois_service.whois_result), processed_result['registrar'], processed_result['org'], processed_result['country_code'], processed_result['creation_date'], processed_result['expiration_date'], processed_result['updated_date'], self.whois_service.whois_result.text)
            self.db.query_exec(sql_insert, params)
    
    #--------------------------------------------------------------------------------
    
    def save_ipwhois_entry(self, processed_result: dict=None):
        #-----check if data was provided-----
        if not processed_result:
            self.webpage.error_log(self.environ, '''NetworkService.save_ipwhois_entry() - ERROR: empty processed_result''')
            return
        ip = processed_result.get('ip', None)
        if not ip:
            self.webpage.error_log(self.environ, '''NetworkService.save_ipwhois_entry() - ERROR: processed_result does not contain an "ip" key''')
            return
        processed_result['zzz_last_updated'] = int(processed_result['zzz_last_updated'])
        raw_whois = processed_result.get('raw_whois', '')
        
        sql = 'select * from ipwhois_cache where ip=?'
        params = (ip,)
        row = self.db.select(sql, params)
        
        if row:
            sql_update = '''update ipwhois_cache set json=?, zzz_last_updated=datetime('now'),
                asn=?, asn_cidr=?, asn_country_code=?, asn_date=?, asn_date_int=?, asn_description=?,
                network_cidr=?, network_country_code=?, ip_version=?,
                org=?, raw_whois=?
                where ip=?'''
            params = (processed_result['json'],
                        processed_result['asn'], processed_result['asn_cidr'], processed_result['asn_country_code'],
                        processed_result['asn_date'], processed_result['asn_date_int'], processed_result['asn_description'],
                        processed_result['network_cidr'], processed_result['network_country_code'], processed_result['ip_version'],
                        processed_result['org'], raw_whois,
                        ip)
            self.db.query_exec(sql_update, params)
        else:
            sql_insert = '''insert into ipwhois_cache (ip, json, zzz_last_updated,
                asn, asn_cidr, asn_country_code, asn_date, asn_date_int, asn_description,
                network_cidr, network_country_code, ip_version,
                org, raw_whois)
                values (?, ?, datetime('now'),
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?)
            '''
            params = (ip, processed_result['json'],
                        processed_result['asn'], processed_result['asn_cidr'], processed_result['asn_country_code'],
                        processed_result['asn_date'], processed_result['asn_date_int'], processed_result['asn_description'],
                        processed_result['network_cidr'], processed_result['network_country_code'], processed_result['ip_version'],
                        processed_result['org'], raw_whois)
            self.db.query_exec(sql_insert, params)
    
    #--------------------------------------------------------------------------------
    
    def list_domains_cached(self):
        sql = 'select domain from whois_cache'
        params = ()
        (colnames, rows, self.db_domain_list) = self.db.select_all(sql, params)
    
    #--------------------------------------------------------------------------------

    def make_error_webpage(self, environ: dict, err_html: str) -> str:
        self.webpage.update_header(environ, 'ERROR')
        body = f'''
        <h2>ERROR</h2>{err_html}
        '''
        return self.webpage.make_webpage(environ, body)

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle, data: dict={}):
        #TEST - remove this when it seems to be working
        # self.test_mode = True

        # self.settings.get_settings()
        # self.webpage.settings = self.settings
        self.webpage.update_header(environ, pagetitle)
        if not self.action:
            self.action = self.default_action

        #TEST
        self.print_test_results([f'make_webpage() - action={self.action} - data:', data])

        if self.action in ['network_service', 'whois', 'nslookup', 'reverse_dns']:
            output = self.webpage.make_webpage(environ, self.make_NetworkServicePage_NEW(environ, pagetitle, data))
            return output

        if self.action=='whois_cache':
            return self.show_whois_cache(environ)
        
        if self.action=='ipwhois_cache':
            return self.show_ipwhois_cache(environ)

        #TODO: default error message for invalid actions
        #-----show the page where the user enters a domain-----
        body = self.make_NetworkServicePage_NEW(environ, pagetitle, data)
        self.webpage.update_header(environ, pagetitle)
        output = self.webpage.make_webpage(environ, body)
        return output

    #--------------------------------------------------------------------------------

    def make_NetworkServicePage_NEW(self, environ: dict, pagetitle: str='', data: dict={}) -> str:
        self.NetworkServiceHTML['CSP_NONCE'] = environ['CSP_NONCE']
        self.NetworkServiceHTML['domain'] = ''
        self.NetworkServiceHTML['action'] = ''

        if self.from_post:
            self.NetworkServiceHTML['show_header'] = "false"
        if self.action in ['whois', 'nslookup', 'reverse_dns']:
            host = data.get('host', '')
            if not host:
                host = data.get('ip', '')
            self.NetworkServiceHTML['domain'] = host
            self.NetworkServiceHTML['action'] = self.action

        self.print_test_results(f'make_NetworkServicePage_NEW() - data: {data}')

        self.webpage.update_header(environ, pagetitle)
        body = self.webpage.load_template('NetworkService')
        return body.format(**self.NetworkServiceHTML)

    #--------------------------------------------------------------------------------
    
    def apply_nonce_to_html(self, environ, html_data):
        html_vars = { 'CSP_NONCE': environ['CSP_NONCE'], }
        return html_data.format(**html_vars)
    
    #--------------------------------------------------------------------------------
    
    # def make_whois_form_page(self, environ):
    #     body = self.webpage.load_template('Whois')
    #     if self.from_post:
    #         # return body
    #         return self.make_return_json('success', '', body)
    #     return body
    
    #--------------------------------------------------------------------------------
    
    #-----add a google link to search for given data string, displayed next to the data-----
    def add_google_link(self, data, include_whois=False, include_location=False, include_reputation=False):
        if not data:
            return ''
        
        #-----CSP requires JS events to be in a <script> instead of in onclick() in a tag-----
        base64_data = self.util.encode_base64(data)
        added_links = f'''{data} <a class="clickable search_google" data-onclick="{base64_data}">Google</a>'''
        if include_whois:
            added_links += f''' <a class="clickable external_whois" data-onclick="{base64_data}">External Whois</a>'''
        if include_location:
            added_links += f''' <a class="clickable search_ipinfo" data-onclick="{base64_data}">IP Location</a>'''
        if include_reputation:
            added_links += f''' <a class="clickable search_ip_rep" data-onclick="{base64_data}">IP Reputation</a>'''
        return added_links
    
    #--------------------------------------------------------------------------------
    
    def make_nslookup_output_page(self, environ, data):
        #TODO: fill-in table when using the nslookup python module
        body = '''
<h2>nslookup for {title}</h2>
<pre>
{status}
{result}
</pre>

<table class="hide_item">
<tr><th>Field</th><th>Data</th></tr>
{table_data}
</table>
        '''
        result = self.do_nslookup(data['host'], True)
        status = result['status']
        if status=='success':
            status=''
        else:
            status='ERROR:'
        nslookupHTML = {
            'status': status,
            'table_data': '',
            'title': data['host'],
            'result': result['details'],
        }
        return self.webpage.make_webpage(environ, body.format(**nslookupHTML))
    
    #--------------------------------------------------------------------------------
    
    #TODO: each whois_data item could be a string or list, handle both possibilities
    def make_whois_output_page(self, environ, whois_data):
        # self.settings.get_settings()
        
        body = '''
<h2>Whois Lookup for {title}</h2>
<table>
<tr><th>Field</th><th>Data</th></tr>
{table_data}
</table>
        '''
        
        table_data = ''
        for item in whois_data.keys():
            if item in ['json', 'raw_whois']:
                continue
            show_fieldname = item
            show_data = whois_data[item]
            
            #-----take the first item if a list is returned-----
            if isinstance(show_data, list):
                show_data = show_data[0]
            
            if item in self.whois_date_fields:
                if show_data:
                    show_data = self.util.current_datetime(int(show_data))
            elif item=='domain':
                show_data = self.add_google_link(show_data, include_whois=True)
            elif item=='org':
                show_data = self.add_google_link(show_data)
            elif item=='country_code':
                country_code = show_data
                show_fieldname = 'country'
                show_data = ''
                if country_code:
                    show_data = self.ConfigData['OfficialCountriesWithExceptions'].get(country_code, 'UNKNOWN')
            red_flags = self.check_red_flags_whois(item, show_data)
            table_data += f'<tr><td>{show_fieldname}</td><td class="td_expanded_wide">{show_data} {red_flags}</td></tr>'
        
        #-----raw_whois data at the end-----
        table_data += f'''<tr><td class="top_align">raw_whois</td><td class="td_expanded_wide">{whois_data['raw_whois']}</td></tr>'''
        
        WhoisHTML = {
            'title': whois_data['domain'],
            'table_data': table_data,
        }
        
        pagetitle = 'Whois ' + whois_data['domain']
        self.webpage.update_header(environ, pagetitle)
        return self.json_or_webpage(environ, 'success', '', body.format(**WhoisHTML))

    #--------------------------------------------------------------------------------

    #-----posted data gets a JSON response, GET requests get a webpage-----
    def json_or_webpage(self, environ: dict, status: str, error_msg: str='', html_data: str='') -> str:
        if self.from_post:
            #TEST
            print('json_or_webpage() - from_post')
            #
            return self.make_return_json(status, error_msg, html_data)
        #TEST
        print('json_or_webpage() - GET')
        #
        return self.make_webpage(environ, html_data)

    #--------------------------------------------------------------------------------

    def make_return_json(self, status: str, error_msg: str='', html_data: str=''):
        return_data = {
            'status': status,
            'error_msg': error_msg,
            'html_data': html_data,
        }
        return_json = json.dumps(return_data)
        return return_json

    #--------------------------------------------------------------------------------
    
    def is_privacy_service(self, value):
        if not value:
            return False
        if value in self.privacy_services:
            return True
        for pattern in self.regex_privacy_services:
            if pattern.match(value):
                return True
        return False
    
    #--------------------------------------------------------------------------------
    
    def is_registrar(self, value):
        if not value:
            return False
        if value in self.registrars:
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    def is_created_recently(self, value):
        if not value:
            return False
        if self.timestamp_diff(value)<=30:
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    def is_expired(self, value):
        if not value:
            return False
        if self.timestamp_diff(value)>=0:
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    def make_span_red(self, data):
        return f'<span class="text_red">{data}</span>'
    
    #-----look for red flags in the whois data-----
    def check_red_flags_whois(self, name, value):
        if not value:
            return ''
        
        #-----privacy services-----
        if name=='org' and self.is_privacy_service(value):
            return self.make_span_red('(PRIVACY SERVICE)')
        
        #-----registrars-----
        if name=='registrar' and self.is_registrar(value):
            return self.make_span_red('(REGISTRAR)')
        
        #-----created recently-----
        if name=='creation_date' and self.is_created_recently(value):
            return self.make_span_red('(CREATED RECENTLY)')
        
        #-----expired-----
        if name=='expiration_date' and self.is_expired(value):
            return self.make_span_red('(EXPIRED)')
        
        #-----blocked country-----
        if name=='country_code' and self.settings.is_blocked_country(value):
            return self.make_span_red('(BLOCKED COUNTRY)')
        
        #-----blocked TLD-----
        if name=='domain' and value:
            split_domain = value.rsplit(sep='.', maxsplit=1)
            if len(split_domain)==2:
                if self.settings.is_blocked_tld(split_domain[1]):
                    return self.make_span_red('(BLOCKED TLD)')
        
        #-----default-----
        return ''
    
    #-----look for red flags in the IP-whois data-----
    def check_red_flags_ipwhois(self, name, value):
        if not value:
            return ''
        
        #-----blocked country-----
        if name=='asn_country_code' and self.settings.is_blocked_country(value):
            return self.make_span_red('(BLOCKED COUNTRY)')
        
        #-----default-----
        return ''
    
    #--------------------------------------------------------------------------------
    
    # INPUT: date/time string with timezone, timestamp string(all digits)
    # OUTPUT: datetime object
    def get_datetime_from_str(self, value):
        # samples to match:
        #   'Creation Date: 1997-09-15T07:00:00+0000'
        #   'Creation Date: 2018-07-23T12:26:02Z'
        # date_format_with_tz = '%Y-%m-%d %H:%M:%S %Z'
        date_format = '%Y-%m-%d %H:%M:%S'
        if value is None:
            return None
        value = str(value)
        value = value.strip()
        if self.util.is_int(value):
            #-----assume it's a timestamp if it's all digits-----
            return datetime.datetime.fromtimestamp(int(value))
        elif self.util.is_datetime(value, True):
            #-----process as a datetime if it passes the format check-----
            # drop the timezone to prevent errors
            date_parts = value.split(' ')
            value = date_parts[0] + ' ' + date_parts[1]
            # return datetime.datetime.strptime(value, date_format_with_tz)
            return datetime.datetime.strptime(value, date_format)
        return None
    
    #TODO: catch errors
    #-----calculate the date/time difference between 2 date strings (date2-date1)-----
    # accepted inputs: date/time string with timezone, timestamp string(all digits)
    # date2 is optional (assumes current date/time)
    def timestamp_diff(self, date1, date2=None):
        if date1 is None:
            return 0
        
        #-----handle a timestamp-----
        date1_obj = self.get_datetime_from_str(date1)
        date2_obj = None
        if date2 is None:
            #-----use the current date if only one date is given-----
            date2_obj = datetime.datetime.now()
        else:
            date2_obj = self.get_datetime_from_str(date2)
        
        if (date1_obj is None) or (date2_obj is None):
            return 0
        
        #-----report difference-----
        timedelta = date2_obj - date1_obj
        self.webpage.error_log(self.environ, 'timedelta.days: ' + str(timedelta.days))
        return timedelta.days
    
    #--------------------------------------------------------------------------------
    
    def delete_whois_cache(self, environ, data):
        sql = f'delete from whois_cache where domain=?'
        params = (data['host'],)
        self.db.query_exec(sql, params)
        return 'success'
    
    #--------------------------------------------------------------------------------
    
    def delete_ipwhois_cache(self, environ, data):
        sql = f'delete from ipwhois_cache where ip=?'
        params = (data['ip'],)
        self.db.query_exec(sql, params)
        return 'success'
    
    #--------------------------------------------------------------------------------

    def make_row_whois_cache(self, row: dict, row_count: int, org_name: str, registrar_name: str) -> str:
        row_id = f'tr_whois_delete_{row_count}'

        domain = row['domain']
        base64_domain = self.util.encode_base64(domain)
        domain_linked = f'''<a href="{self.ConfigData['URL']['Whois']}&host={domain}">{domain}</a>'''

        zzz_last_updated = self.util.current_datetime(int(row['zzz_last_updated']))
        if self.whois_expired(row):
            zzz_last_updated = self.make_span_red(zzz_last_updated)

        if self.is_registrar(registrar_name):
            registrar_name = self.make_span_red(registrar_name)
        if self.is_privacy_service(org_name):
            org_name = self.make_span_red(org_name)

        country_code = row['country_code']
        country = self.ConfigData['OfficialCountriesWithExceptions'].get(country_code, 'UNKNOWN')
        if self.settings.is_blocked_country(country_code):
            country = self.make_span_red(country)

        row_html = f'''
<tr id="{row_id}">
<!-- whois_delete('{row_id}', '{domain}') -->
<td><a class="clickable whois_delete" data-onclick-tr-id="{row_id}" data-onclick-domain="{base64_domain}">(D)</a> {domain_linked}</td>
<td>{zzz_last_updated}</td>
<td>{org_name}</td>
<td>{country}</td>
<td>{registrar_name}</td>
</tr>'''

        return row_html

    #--------------------------------------------------------------------------------

    def show_whois_cache(self, environ):
        sql = "select domain, strftime('%s', zzz_last_updated) as 'zzz_last_updated', registrar, org, country_code, strftime('%s', creation_date) as 'creation_date', strftime('%s', expiration_date) as 'expiration_date', strftime('%s', updated_date) as 'updated_date' from whois_cache order by domain"
        params = ()
        (colnames, rows, data_with_colnames) = self.db.select_all(sql, params)
        
        registrars_found = []
        orgs_found = []
        
        table_data = []
        row_count=0
        if data_with_colnames:
            for row in data_with_colnames:
                row_count += 1
                registrar_name = row['registrar']
                if registrar_name not in registrars_found:
                    registrars_found.append(registrar_name)
                org_name = row['org']
                if org_name not in orgs_found:
                    orgs_found.append(org_name)
                row_html = self.make_row_whois_cache(row, row_count, org_name, registrar_name)
                table_data.append(row_html)

        registrars_found = sorted(registrars_found)
        orgs_found = sorted(orgs_found)

        WhoisHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'table_data': ''.join(table_data),
            'timezone': self.util.format_timezone(),
            'registrars_found': '\n'.join(registrars_found),
            'orgs_found': '\n'.join(orgs_found),
        }
        self.webpage.update_header(environ, 'Whois Cache')
        body = self.webpage.load_template('NetworkService_WhoisCache')

        output = self.webpage.make_webpage(environ, body.format(**WhoisHTML))
        return output
    
    #--------------------------------------------------------------------------------

    def make_row_ipwhois_cache(self, row: dict, row_count: int, org_name: str) -> str:
        row_id = f'tr_ipwhois_delete_{row_count}'

        ip = row['ip']
        ip_linked = f'''<a href="{self.ConfigData['URL']['Whois']}&host={ip}">{ip}</a>'''

        zzz_last_updated = self.util.current_datetime(int(row['zzz_last_updated']))
        if self.whois_expired(row):
            zzz_last_updated = self.make_span_red(zzz_last_updated)
        if self.is_privacy_service(org_name):
            org_name = self.make_span_red(org_name)

        country_code = row['asn_country_code']
        country = self.ConfigData['OfficialCountriesWithExceptions'].get(country_code, 'UNKNOWN')
        if self.settings.is_blocked_country(country_code):
            country = self.make_span_red(country)

        row_html = f'''
<tr id="{row_id}">
<!-- ipwhois_delete('{row_id}', '{ip}') -->
<td><a class="clickable ipwhois_delete" data-onclick-tr-id="{row_id}" data-onclick-ip="{ip}">(D)</a> {ip_linked}</td>
<td>{zzz_last_updated}</td>
<td>{org_name}</td>
<td>{country}</td></tr>
        '''
        return row_html

    #--------------------------------------------------------------------------------

    def show_ipwhois_cache(self, environ):
        sql = '''select ip, strftime('%s', zzz_last_updated) as 'zzz_last_updated',
            asn, asn_cidr, asn_country_code, asn_date, asn_date_int, asn_description,
            network_cidr, network_country_code, ip_version,
            org
            from ipwhois_cache order by ip_version, ip'''
        params = ()
        (colnames, rows, data_with_colnames) = self.db.select_all(sql, params)
        
        orgs_found = []
        
        table_data = []
        row_count = 0
        if data_with_colnames:
            for row in data_with_colnames:
                row_count += 1
                org_name = row['org']
                if org_name not in orgs_found:
                    orgs_found.append(org_name)
                row_html = self.make_row_ipwhois_cache(row, row_count, org_name)
                table_data.append(row_html)
        
        orgs_found = sorted(orgs_found)

        IPWhoisHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'table_data': ''.join(table_data),
            'timezone': self.util.format_timezone(),
            'orgs_found': '\n'.join(orgs_found),
        }
        self.webpage.update_header(environ, 'IP-Whois Cache')
        body = self.webpage.load_template('NetworkService_IPWhoisCache')
        output = self.webpage.make_webpage(environ, body.format(**IPWhoisHTML))
        return output
    
    #--------------------------------------------------------------------------------
    
    def make_ipwhois_output_page(self, environ, whois_data):
        # self.settings.get_settings()
        
        body = '''
<h2>Whois for {title}</h2>
{maxmind_location}
<table>
<tr><th>Field</th><th>Data</th></tr>
{table_data}
</table>
        '''
        
        table_data = ''
        for item in whois_data.keys():
            if item in ['json', 'raw_whois']:
                continue
            show_fieldname = item
            show_data = whois_data[item]
            if item in self.whois_date_fields:
                if whois_data[item]:
                    show_data = self.util.current_datetime(int(whois_data[item]))
            elif item=='ip':
                show_data = self.add_google_link(show_data, include_whois=True, include_location=True)
            elif item=='org':
                show_data = self.add_google_link(show_data)
            elif item=='asn_country_code' or item=='network_country_code':
                country_code = whois_data[item]
                show_data = ''
                if item=='asn_country_code':
                    show_fieldname = 'asn_country'
                elif item=='network_country_code':
                    show_fieldname = 'network_country'
                if country_code:
                    show_data = self.ConfigData['OfficialCountriesWithExceptions'].get(country_code, 'UNKNOWN')
            red_flags = self.check_red_flags_ipwhois(item, whois_data[item])
            table_data += f'<tr><td>{show_fieldname}</td><td class="td_expanded_wide">{show_data} {red_flags}</td></tr>'
        #-----json data at the end-----
        json_str = ''
        json_value = whois_data.get('json', None)
        if json_value:
            json_str = json.loads(json_value)
        table_data += f'''<tr><td class="top_align">json</td><td class="td_expanded_wide">{pprint.pformat(json_str)}</td></tr>'''

        ip = whois_data.get('ip', '')
        maxmind_location = ''
        if self.ConfigData['EnableMaxMind']:
            country_code = self.util.lookup_ip_country(ip)
            if not country_code:
                country_code = 'UNKNOWN'
            maxmind_location = f'<p>Maxmind Location: {country_code}</p>'

        IPWhoisHTML = {
            'maxmind_location': maxmind_location,
            'title': ip,
            'table_data': table_data,
        }
        
        pagetitle = f'Whois {ip}'
        self.webpage.update_header(environ, pagetitle)
        return self.json_or_webpage(environ, 'success', '', body.format(**IPWhoisHTML))

    #--------------------------------------------------------------------------------

    def show_ips_by_country(self, environ: dict) -> str:
        ipdeny_country_codes = self.ConfigData['IPdeny']['countries']
        ipdeny_dir = self.ConfigData['IPdeny']['ipv4']['src_dir']
        country_data = {}
        not_found = []
        for country_code in ipdeny_country_codes:
            country_html = ''
            with open(f'{ipdeny_dir}/{country_code}.zone', 'r') as read_file:
                all_lines = read_file.readlines()
                country_html = '<br>\n'.join(all_lines)
            if not country_html:
                continue
            country_name = self.ConfigData['OfficialCountries'].get(country_code.upper(), None)
            if country_name:
                country_data[country_name] = f'<span class="font-large">{country_name} ({country_code.upper()})</span><br><br>\n{country_html}'
            else:
                not_found.append(country_code)

        #-----sort by country name-----
        country_sorted_list = []
        for country_name in sorted(country_data.keys()):
            country_sorted_list.append(country_data[country_name])
        country_output = '</p><hr>\n<p class="font-courier">'.join(country_sorted_list)

        body = f'''<h3>IPs by Country</h3>
<p>We use country IP data from <a href="https://www.ipdeny.com" target="_blank">IPDENY.COM</a></p>
<p class="font-courier">
{country_output}
</p>
'''
        country_data = None
        country_output = None
        self.util.force_garbage_collection()

        self.webpage.update_header(environ, 'IPs by Country')
        return self.webpage.make_webpage(environ, body)

    #--------------------------------------------------------------------------------
