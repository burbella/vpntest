#-----provides Whois services-----
# no Config or DB modules loaded here, only whois services
# NetworkService will do whois DB-related cache stuff

import rdap
import requests
import time
import whois
#TODO: this will replace "import whois" when the new code is all written
# import wizard_whois

#TEST
import pprint

#-----import modules from the lib directory-----
# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.IPutil
import zzzevpn

class WhoisService:
    'Whois services'
    
    iputil = None
    
    whois_result = None
    whois_wizard_result = None
    rdap_result_obj = None
    processed_result = None

    err = ''
    
    def __init__(self):
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    def init_vars(self):
        self.err = ''
        self.whois_result = None
        self.whois_wizard_result = None
        self.rdap_result_obj = None
        self.processed_result = {
            'country_code': '',
            'creation_date': None,
            'domain': '',
            'expiration_date': None,
            'org': '',
            'registrar': '',
            'updated_date': None,
            'whois_server': '',
            'zzz_last_updated': None,
            'raw_whois': None
        }

    #--------------------------------------------------------------------------------
    
    #TODO: finish this
    #-----host can be an IP or domain name?-----
    # https://pypi.org/project/python-whois/
    # not "whois", but rather "python-whois"
    # NOTE: both projects are loaded with "import whois", so they cannot both be installed
    def lookup_whois(self, domain):
        self.init_vars()
        
        #-----do a whois domain lookup-----
        try:
            self.whois_result = whois.whois(domain)
        except Exception as e:
            #TODO: error handling, separate for each exception
            self.err += 'lookup_whois - whois.whois() - other error for {}\n     {}\n'.format(domain, str(e))
            return 'ERROR: ' + str(e)
        
        #-----cleanup-----
        self.cleanup_whois_data(domain)
        return ''
    
    #-----sample whois data structure-----
    # {'address': None,
    #  'city': None,
    #  'country': 'US',
    #  'creation_date': [datetime.datetime(1997, 9, 15, 4, 0),
    #                    datetime.datetime(1997, 9, 15, 0, 0)],
    #  'dnssec': 'unsigned',
    #  'domain_name': ['GOOGLE.COM', 'google.com'],
    #  'emails': ['abusecomplaints@markmonitor.com', 'whoisrequest@markmonitor.com'],
    #  'expiration_date': [datetime.datetime(2020, 9, 14, 4, 0),
    #                      datetime.datetime(2020, 9, 13, 21, 0)],
    #  'name': None,
    #  'name_servers': ['NS1.GOOGLE.COM',
    #                   'NS2.GOOGLE.COM',
    #                   'NS3.GOOGLE.COM',
    #                   'NS4.GOOGLE.COM',
    #                   'ns2.google.com',
    #                   'ns4.google.com',
    #                   'ns3.google.com',
    #                   'ns1.google.com'],
    #  'org': 'Google LLC',
    #  'referral_url': None,
    #  'registrar': 'MarkMonitor, Inc.',
    #  'state': 'CA',
    #  'status': ['clientDeleteProhibited '
    #             'https://icann.org/epp#clientDeleteProhibited',
    #             'clientTransferProhibited '
    #             'https://icann.org/epp#clientTransferProhibited',
    #             'clientUpdateProhibited '
    #             'https://icann.org/epp#clientUpdateProhibited',
    #             'serverDeleteProhibited '
    #             'https://icann.org/epp#serverDeleteProhibited',
    #             'serverTransferProhibited '
    #             'https://icann.org/epp#serverTransferProhibited',
    #             'serverUpdateProhibited '
    #             'https://icann.org/epp#serverUpdateProhibited',
    #             'clientUpdateProhibited '
    #             '(https://www.icann.org/epp#clientUpdateProhibited)',
    #             'clientTransferProhibited '
    #             '(https://www.icann.org/epp#clientTransferProhibited)',
    #             'clientDeleteProhibited '
    #             '(https://www.icann.org/epp#clientDeleteProhibited)',
    #             'serverUpdateProhibited '
    #             '(https://www.icann.org/epp#serverUpdateProhibited)',
    #             'serverTransferProhibited '
    #             '(https://www.icann.org/epp#serverTransferProhibited)',
    #             'serverDeleteProhibited '
    #             '(https://www.icann.org/epp#serverDeleteProhibited)'],
    #  'updated_date': [datetime.datetime(2018, 2, 21, 18, 36, 40),
    #                   datetime.datetime(2018, 2, 21, 10, 45, 7)],
    #  'whois_server': 'whois.markmonitor.com',
    #  'zipcode': None}
    
    #--------------------------------------------------------------------------------
    
    #-----make the whois output easier to work with-----
    def cleanup_whois_data(self, domain):
        if self.whois_result is None:
            return
        self.processed_result['domain'] = domain
        self.processed_result['zzz_last_updated'] = int(time.time())
        self.processed_result['raw_whois'] = self.whois_result.text
        
        if self.whois_result.country:
            self.processed_result['country_code'] = self.whois_result.country
        if self.whois_result.creation_date:
            self.processed_result['creation_date'] = self.process_date(self.whois_result.creation_date)
        if self.whois_result.expiration_date:
            self.processed_result['expiration_date'] = self.process_date(self.whois_result.expiration_date)
        
        if self.whois_result.org:
            self.processed_result['org'] = self.whois_result.org
        elif self.whois_result.name:
            self.processed_result['org'] = self.whois_result.name
        
        if self.whois_result.registrar:
            self.processed_result['registrar'] = self.whois_result.registrar
        if self.whois_result.updated_date:
            self.processed_result['updated_date'] = self.process_date(self.whois_result.updated_date)
        if self.whois_result.whois_server:
            self.processed_result['whois_server'] = self.whois_result.whois_server
    
    #--------------------------------------------------------------------------------
    
    #-----deal with random list/scalar issues in whois date fields-----
    def process_date(self, date_obj):
        if not date_obj:
            return None
        data = date_obj
        #-----deal with random list/scalar issues-----
        if isinstance(date_obj, list):
            data = date_obj[0]
        return int(data.timestamp())
    
    #--------------------------------------------------------------------------------
    
    # replace "python-whois" pypi package with "whois_wizard"
    def lookup_whois_wizard(self, domain: str):
        self.init_vars()
        
        #-----do a whois domain lookup-----
        try:
            #TODO: turn this back on when ready to test
            # self.whois_wizard_result = wizard_whois.get_whois(domain)
            pass
        except Exception as e:
            #TODO: error handling, separate for each exception
            self.err += 'lookup_whois_wizard() - ERROR for domain="{}"\n     {}\n'.format(domain, str(e))
            return 'ERROR: ' + str(e)
        
        #-----cleanup-----
        self.cleanup_whois_wizard_data(domain)
        return ''
    
    #--------------------------------------------------------------------------------
    
    # NOTE: the "raw" field is an array of strings
    #whois_wizard_result:
    # {'contacts': {'admin': None, 'billing': None, 'registrant': None, 'tech': None},
    #  'creation_date': [datetime.datetime(1997, 9, 15, 4, 0)],
    #  'expiration_date': [datetime.datetime(2028, 9, 14, 4, 0)],
    #  'id': ['2138514_DOMAIN_COM-VRSN'],
    #  'nameservers': ['NS1.GOOGLE.COM',
    #                  'NS2.GOOGLE.COM',
    #                  'NS3.GOOGLE.COM',
    #                  'NS4.GOOGLE.COM'],
    # 'raw': ['   Domain Name: GOOGLE.COM\n', '\n, '\n'],
    # 'registrar': ['MarkMonitor Inc.'],
    # 'updated_date': [datetime.datetime(2019, 9, 9, 15, 39, 4)],
    # 'whois_server': ['whois.markmonitor.com']}
    def cleanup_whois_wizard_data(self, domain: str):
        if self.whois_wizard_result is None:
            return
        self.processed_result['domain'] = domain
        self.processed_result['zzz_last_updated'] = int(time.time())
        self.processed_result['raw_whois'] = ''.join(self.whois_wizard_result['raw'])
        
        # if self.whois_result.country:
        #     self.processed_result['country_code'] = self.whois_result.country
        if self.whois_wizard_result['creation_date']:
            self.processed_result['creation_date'] = self.process_date(self.whois_wizard_result['creation_date'])
        if self.whois_wizard_result['expiration_date']:
            self.processed_result['expiration_date'] = self.process_date(self.whois_wizard_result['expiration_date'])
        
        # if self.whois_result.org:
        #     self.processed_result['org'] = self.whois_result.org
        # elif self.whois_result.name:
        #     self.processed_result['org'] = self.whois_result.name
        
        if self.whois_wizard_result['registrar']:
            self.processed_result['registrar'] = self.whois_wizard_result['registrar']
            # take the first item in the list
            if isinstance(self.processed_result['registrar'], list):
                self.processed_result['registrar'] = self.processed_result['registrar'][0]
        if self.whois_wizard_result['updated_date']:
            self.processed_result['updated_date'] = self.process_date(self.whois_wizard_result['updated_date'])
        if self.whois_wizard_result['whois_server']:
            self.processed_result['whois_server'] = self.whois_wizard_result['whois_server']
            # take the first item in the list
            if isinstance(self.processed_result['whois_server'], list):
                self.processed_result['whois_server'] = self.processed_result['whois_server'][0]
    
    #--------------------------------------------------------------------------------
    
    # rdap.org limit 600 requests per 300 seconds
    # returns: location, err_msg
    def get_rdap_server(self, domain: str):
        download_url = f'https://rdap.org/domain/{domain}'
        response_obj = requests.get(download_url, allow_redirects=False)
        
        # print('status code: ' + str(response_obj.status_code))
        # print('url: ' + response_obj.url)
        # print('location: ' + response_obj.headers['Location'])
        # print('headers: ')
        # pprint.pprint(response_obj.headers)
        #TEST
        # pprint.pprint(response_obj.text)
        
        if response_obj.status_code == 404:
            status_code = str(response_obj.status_code)
            return '', f'ERROR: RDAP not available for domain {domain}'
        
        if response_obj.status_code != 302:
            status_code = str(response_obj.status_code)
            return '', f'ERROR: HTTP {status_code} status code returned, was expecting 302'
        return response_obj.headers['Location'], ''
    
    #--------------------------------------------------------------------------------
    
    # Registration Data Access Protocol(RDAP) is the new Whois
    # /opt/zzz/venv/bin/rdap --output-format json google.com
    def lookup_rdap(self, domain: str):
        rdap_client = rdap.RdapClient()
        self.rdap_result_obj = rdap_client.get(domain)
        # self.rdap_result_obj.parsed()
        # self.rdap_result_obj.data
    
    #--------------------------------------------------------------------------------
    
    # rdap_result --> processed_result
    def cleanup_rdap_data(self, domain: str):
        # self.rdap_result_obj.data
        
        pass
    
    #--------------------------------------------------------------------------------
