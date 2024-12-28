#-----manages Zzz System Settings-----
import json

#TEST
import pprint

# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.Config
# import zzzevpn.DB
# import zzzevpn.Util
# import zzzevpn.ZzzTemplate
import zzzevpn

class Settings:
    'Settings data'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    db_ip_country: zzzevpn.DB = None
    util: zzzevpn.Util = None
    
    SquidNoBumpSites = [] # list of sites that squid should do peek-and-splice instead of peek-stare-bump
    SquidHideDomains = [] # don't show these domains in the squid log report
    HideIPs = [] # don't show these IP's in the IP log report
    AllowIPs = [] # overrides denylist IP's in iptables
    SettingsData = {}

    #-----separate settings for ICAP (not including the icap_settings table with regexes)-----
    ICAP = {}
    ICAP_default = {
        'icap_condensed': 'false',
    }
    #-----separate settings for the IP Log Raw Data page-----
    # keep separate from SettingsData so it can be loaded/saved separately
    # this allows the IP log raw data view page to save its own data without the risk of old data being saved when the Save button is pressed on the main Settings page
    IPLogRawDataView = {}
    IPLogRawDataView_default = {
        'auto_update_file_list': 'true',
        'extra_analysis': 'false',
        # IPs/ports
        'src_ip': '',
        'dst_ip': '',
        'src_ports': '',
        'dst_ports': '',
        'search_length': '',
        'ttl': '',
        'sort_by': 'ip',
        # connection type
        'connection_external': 'true',
        'connection_inbound': 'true',
        'connection_internal': 'false',
        'connection_outbound': 'true',
        # flags
        'flags_any': 'true',
        'flags_none': 'true',
        # highlights
        'flag_bps_above_value': 10000,
        'flag_pps_above_value': 8,
        # status
        'include_accepted_packets': 'true',
        'include_blocked_packets': 'true',
        # packet limits
        'min_displayed_packets': 1,
        # prec/tos
        'prec_tos_zero': 'true',
        'prec_tos_nonzero': 'true',
        # protocol
        'protocol_tcp': 'true',
        'protocol_udp': 'true',
        'protocol_icmp': 'true',
        'protocol_other': 'true',
        # bps display
        'show_max_bps_columns': 'true',
    }
    #-----separate settings for the iptables rules-----
    IPtablesRules = {}
    IPtablesRules_default = {
        'enable_auto_blocking': 'false',

        'allow_ips': '',
        'block_tcp': 'false',
        'block_udp': 'true',
        'block_low_ttl': 0,
        'block_nonzero_tos': 'false',
        'block_non_allowed_ips': 'false',
        'block_packet_length': 0,
        'bytes_burst': 50000,
        'bytes_per_sec': 10000,
        'dst_ports': '',
        'notes': '',
        'packets_burst': 50,
        'packets_per_sec': 10,
        'throttle_expire': 6*60, # minutes until rule expires
        'traffic_direction': 'inbound',
    }
    SettingTypeMain = 'main'
    SettingTypeIPLogRawDataView = 'ip_log_raw_data_view'
    SettingTypeIPtablesRules = 'iptables_rules'
    SettingTypeICAP = 'icap'
    setting_types = [SettingTypeMain, SettingTypeIPLogRawDataView, SettingTypeIPtablesRules, SettingTypeICAP]

    print_log: bool = True
    settings_last_loaded = 0
    
    body = ''
    service_name = 'settings'
    Countries = {} # country code: country name
    BlockedCountries = {} # country code: 1
    TLDs = {} # TLD
    BlockedTLDs = {} # TLD: 1
    SettingsHTML = {}
    checkboxes_available = ['autoplay', 'social', 'telemetry', 'duplicate_domain', 'links_by_function', 'icap_condensed', 'block_country_tld', 'block_country_tld_always', 'block_country_ip_always', 'block_custom_ip_always', 'block_tld_always', 'dark_mode', 'check_zzz_update', 'auto_install_zzz_update', 'show_dev_tools', 'restart_openvpn_weekly', 'test_server_dns_block', 'test_server_squid']
    
    #TEST
    TESTDATA = ''
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None):
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
        self.init_vars()
        #TODO: check this value before bothering with this DB
        #      self.ConfigData['EnableSqliteIPCountry']
        self.db_ip_country = zzzevpn.DB(self.ConfigData)
        self.db_ip_country.db_connect(self.ConfigData['DBFilePath']['IPCountry'])
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self) -> None:
        self.settings_last_loaded = 0
        self.SquidNoBumpSites = []
        self.SquidHideDomains = []
        self.HideIPs = []
        self.AllowIPs = []
        self.SettingsData = {}
        self.IPLogRawDataView = {}
        self.IPtablesRules = {}
        
        self.load_country_names()
        self.load_tld_names()
        
        #-----prep the HTML values-----
        self.SettingsHTML = {
            'URL_Services': self.ConfigData['URL']['Services'],
            
            'autoplay': '',
            'social': '',
            'telemetry': '',
            
            'autoplay_list': '(none)',
            'social_list': '(none)',
            'telemetry_list': '(none)',
            
            'duplicate_domain': '',
            'links_by_function': '',
            'icap_condensed': '',
            'block_country_tld': '',
            'block_country_tld_always': '',
            'block_country_ip_always': '',
            'block_custom_ip_always': '',
            'auto_blocking_status': '',
            
            'block_tld_always': '',
            
            'dark_mode': '',
            
            #-----System Updates-----
            'check_zzz_update': '',
            'auto_install_zzz_update': '',
            'show_dev_tools': '',
            'restart_openvpn_weekly': '',

            #-----controls test server settings-----
            'test_server_dns_block': '',
            'test_server_squid': '',
            
            'CountryMenu': '',
            'BlockedCountryMenu': '',
            'ProtectedCountries': '',
            
            'TLDmenu': '',
            'BlockedTLDmenu': '',
            'ProtectedTLDs': '',
            
            'AllowIPs': '',
            'SquidHideDomains': '',
            'HideIPs': '',
            'SquidNoBumpSites': '',
            
            'TESTDATA': '',
        }

    #--------------------------------------------------------------------------------
    
    def should_print_log(self, value=None):
        if (value is None):
            return self.print_log
        else:
            self.print_log = value
    
    #--------------------------------------------------------------------------------
    
    def load_country_names(self):
        sql = 'select * from countries order by country'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        self.Countries = {}
        self.BlockedCountries = {}
        for row in rows_with_colnames:
            self.Countries[row['country_code']] = row['country']
            if row['blocked']:
                self.BlockedCountries[row['country_code']] = 1
    
    def load_tld_names(self):
        sql = 'select * from tlds order by tld'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        self.TLDs = {}
        self.BlockedTLDs = {}
        for row in rows_with_colnames:
            self.TLDs[row['tld']] = 1
            if row['blocked']:
                self.BlockedTLDs[row['tld']] = 1
    
    #--------------------------------------------------------------------------------
    
    def got_settings_recently(self, ok_to_use_existing):
        if not ok_to_use_existing:
            return False
        
        # were the settings loaded recently?
        if (self.util.current_timestamp() - self.settings_last_loaded)<1:
            return True
        
        return False
    
    #--------------------------------------------------------------------------------

    def load_iptables_rules_into_dict(self, iptables_rules: str):
        if iptables_rules:
            try:
                self.IPtablesRules = json.loads(iptables_rules)
            except:
                # can't load settings? just start over
                if self.should_print_log():
                    print('get_settings(): json.loads(iptables_rules) failed, using default settings', flush=True)

        # in case new keys were added, load default values from above
        for key in self.IPtablesRules_default.keys():
            if key not in self.IPtablesRules:
                self.IPtablesRules[key] = self.IPtablesRules_default[key]

    #--------------------------------------------------------------------------------

    def load_raw_data_view_into_dict(self, ip_log_raw_data_view: str):
        if ip_log_raw_data_view:
            try:
                self.IPLogRawDataView = json.loads(ip_log_raw_data_view)
            except:
                # can't load settings? just start over
                if self.should_print_log():
                    print('get_settings(): json.loads(ip_log_raw_data_view) failed, using default settings', flush=True)

        # in case new keys were added, load default values from above
        for key in self.IPLogRawDataView_default.keys():
            if key not in self.IPLogRawDataView:
                self.IPLogRawDataView[key] = self.IPLogRawDataView_default[key]

    #--------------------------------------------------------------------------------

    # most apps do not need the SettingsHTML data, so do not populate it by default
    # currently only the SettingsPage module needs it
    def get_settings(self, ok_to_use_existing=False, need_html=False):
        """ lookup settings in DB """
        
        # just return existing settings if we updated less than a second ago
        if self.got_settings_recently(ok_to_use_existing):
            if self.should_print_log():
                print('get_settings(): use existing settings', flush=True)
            return
        
        self.init_vars()
        
        sql = 'select json, squid_nobumpsites, squid_hide_domains, hide_ips, allow_ips, ip_log_raw_data_view, iptables_rules, icap from settings'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)
        row = None
        if rows_with_colnames:
            row = rows_with_colnames[0]

        if row['json']:
            try:
                self.SettingsData = json.loads(row['json'])
            except:
                # can't load settings? just start over
                if self.should_print_log():
                    print('get_settings(): json.loads(json) failed, using default settings', flush=True)

        # separate json data for the IP log raw data view
        self.load_raw_data_view_into_dict(row['ip_log_raw_data_view'])
        self.load_iptables_rules_into_dict(row['iptables_rules'])

        if row['squid_nobumpsites']:
            self.SquidNoBumpSites = row['squid_nobumpsites'].split('\n')
            self.SettingsHTML['SquidNoBumpSites'] = row['squid_nobumpsites']
        else:
            self.SquidNoBumpSites = []
            self.SettingsHTML['SquidNoBumpSites'] = ''
        
        if row['squid_hide_domains']:
            self.SquidHideDomains = row['squid_hide_domains'].split('\n')
            self.SettingsHTML['SquidHideDomains'] = row['squid_hide_domains']
        else:
            self.SquidHideDomains = []
            self.SettingsHTML['SquidHideDomains'] = ''
        
        if row['hide_ips']:
            self.HideIPs = row['hide_ips'].split('\n')
            self.SettingsHTML['HideIPs'] = row['hide_ips']
        else:
            self.HideIPs = []
            self.SettingsHTML['HideIPs'] = ''
        
        if row['allow_ips']:
            self.AllowIPs = row['allow_ips'].split('\n')
            self.SettingsHTML['AllowIPs'] = row['allow_ips']
        else:
            self.AllowIPs = []
            self.SettingsHTML['AllowIPs'] = ''

        self.settings_last_loaded = self.util.current_timestamp()
        
        for checkbox in self.checkboxes_available:
            default_value = 'false'
            if self.is_setting_enabled(checkbox):
                #-----the checked attribute ends up in the HTML <input> tag-----
                self.SettingsHTML[checkbox] = 'checked'
            else:
                #-----newly-added checkboxes may not be in the DB yet, so set the default value in SettingsData-----
                self.SettingsData[checkbox] = default_value
        
        #TODO: move this to a function
        #-----populate lists of domains for checkboxes-----
        if need_html:
            # don't make an IPtablesRules object because it uses Settings() and would cause an import loop
            self.SettingsHTML['auto_blocking_status'] = ''
            if self.is_setting_enabled('enable_auto_blocking', self.SettingTypeIPtablesRules):
                self.SettingsHTML['auto_blocking_status'] = f''''''

            #TODO: remove these?
            for filename in ['autoplay', 'social', 'telemetry']:
                filepath = '{}/{}'.format(self.ConfigData['Directory']['Settings'], self.ConfigData['SettingFile'][filename])
                with open(filepath, 'r') as read_file:
                    self.SettingsHTML[filename + '_list'] = read_file.read()

            #-----sorted list of country names from countries table-----
            # for country_code in self.ConfigData['IPdeny']['countries']:
            country_list = self.util.sort_array_by_values(self.Countries)
            #-----ProtectedCountries-----
            ProtectedCountries_names = []
            if self.ConfigData['ProtectedCountries']:
                for country_code in self.ConfigData['ProtectedCountries']:
                    ProtectedCountries_names.append('(' + country_code + ')' + self.ConfigData['OfficialCountries'][country_code])
            self.SettingsHTML['ProtectedCountries'] = ', '.join(ProtectedCountries_names)
            #-----entries in country menus-----
            for country_row in country_list:
                (country_code, country_name) = country_row
                #-----skip ipdeny countries not in maxmind DB (or vice versa)-----
                check_country = self.Countries.get(country_code)
                if not country_code.lower() in self.ConfigData['IPdeny']['countries']:
                    continue
                if check_country is None:
                    continue
                option_class = ''
                if country_code in self.ConfigData['ProtectedCountries']:
                    option_class = 'class="protected_option"'
                option = f'<option value="{country_code}" {option_class}>{country_code}-{country_name}</option>'
                self.SettingsHTML['CountryMenu'] += option
                check_blocked = self.BlockedCountries.get(country_code)
                if check_blocked != None:
                    self.SettingsHTML['BlockedCountryMenu'] += option
            #-----ProtectedTLDs-----
            self.SettingsHTML['ProtectedTLDs'] = ', '.join(self.ConfigData['ProtectedTLDs'])
            for tld in self.ConfigData['TLDs']:
                option_class = ''
                if tld in self.ConfigData['ProtectedTLDs']:
                    option_class = 'class="protected_option"'
                option = f'<option value="{tld}" {option_class}>{tld}</option>'
                self.SettingsHTML['TLDmenu'] += option
                check_blocked = self.BlockedTLDs.get(tld)
                if check_blocked != None:
                    self.SettingsHTML['BlockedTLDmenu'] += option
        
        if self.should_print_log():
            print('get_settings()', flush=True)
    
    #--------------------------------------------------------------------------------
    
    #-----looks up Settings checkbox values-----
    # example of the type of test performed:
    #   if self.SettingsData['show_dev_tools'] == 'true'
    def is_setting_enabled(self, setting_name: str, setting_type: str=None) -> bool:
        if not setting_name:
            return False
        if not setting_type in self.setting_types:
            # default to main settings
            setting_type = self.SettingTypeMain
        if not self.SettingsData:
            if self.should_print_log():
                print('is_setting_enabled() - ERROR: no SettingsData loaded', flush=True)
            return False

        if setting_type == self.SettingTypeMain:
            setting_value = self.SettingsData.get(setting_name, None)
        elif setting_type == self.SettingTypeIPtablesRules:
            setting_value = self.IPtablesRules.get(setting_name, None)
        elif setting_type == self.SettingTypeICAP:
            setting_value = self.ICAP.get(setting_name, None)
        else:
            setting_value = self.IPLogRawDataView.get(setting_name, None)

        if setting_value is None:
            #-----probably called with a non-existent key-----
            return False
        if setting_value == 'true':
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    def is_blocked_country(self, value):
        if not value:
            return False
        if value in self.SettingsData['blocked_country']:
            return True
        return False
    
    # non-country TLD's
    def is_blocked_tld(self, value):
        if not value:
            return False
        if value in self.SettingsData['blocked_tld']:
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    #-----separate the squid_nobumpsites data from the rest of the settings-----
    def process_nobumpsites(self):
        self.SquidNoBumpSites = []
        squid_nobumpsites = self.SettingsData['squid_nobumpsites']
        del self.SettingsData['squid_nobumpsites']
        if not squid_nobumpsites:
            return
        self.SquidNoBumpSites = self.cleanup_domain_list(squid_nobumpsites.split("\n"), True)
    
    #--------------------------------------------------------------------------------
    
    #-----separate the squid_hide_domains data from the rest of the settings-----
    def process_hide_domains(self):
        self.SquidHideDomains = []
        squid_hide_domains = self.SettingsData['squid_hide_domains']
        del self.SettingsData['squid_hide_domains']
        if not squid_hide_domains:
            return
        self.SquidHideDomains = self.cleanup_domain_list(squid_hide_domains.split("\n"), True)
    
    #--------------------------------------------------------------------------------
    
    #-----separate the hide_ips data from the rest of the settings-----
    def process_hide_ips(self):
        self.HideIPs = []
        hide_ips = self.SettingsData['hide_ips']
        del self.SettingsData['hide_ips']
        if not hide_ips:
            return
        self.HideIPs = self.cleanup_ip_list(hide_ips.split("\n"))
    
    #--------------------------------------------------------------------------------
    
    #-----separate the allow_ips data from the rest of the settings-----
    def process_allow_ips(self):
        self.AllowIPs = []
        allow_ips = self.SettingsData['allow_ips']
        del self.SettingsData['allow_ips']
        if not allow_ips:
            return
        self.AllowIPs = self.cleanup_ip_list(allow_ips.split("\n"))
    
    #--------------------------------------------------------------------------------
    
    #TODO: move this to Util.py
    def cleanup_ip_list(self, ip_list):
        clean_list = []
        if not ip_list:
            return []
        for item in ip_list:
            if not item:
                continue
            ip_result = self.util.ip_util.is_ip(item)
            if ip_result:
                clean_list.append(item)
                continue
            cidr_result = self.util.ip_util.is_cidr(item)
            if cidr_result:
                clean_list.append(item)
        
        # de-duplicate and sort
        clean_list = self.util.unique_sort(clean_list)
        
        return clean_list
    
    #--------------------------------------------------------------------------------
    
    #TODO: move this to Util.py
    #-----reduce subdomains to domains only, remove duplicates-----
    def cleanup_domain_list(self, domain_list, remove_subdomains=False):
        clean_list = []
        if not domain_list:
            return []
        for host in domain_list:
            if not host:
                continue
            item = host
            if remove_subdomains:
                #-----reduce the list to domains-----
                item = self.util.get_domain_from_host(host)
            clean_list.append(item)
        
        # lowercase, de-duplicate, sort
        clean_list = self.util.unique_sort(clean_list, make_lowercase=True)
        
        return clean_list
    
    #--------------------------------------------------------------------------------
    
    def save_settings(self):
        #-----save to settings table-----
        sql = "update settings set json=?, squid_nobumpsites=?, squid_hide_domains=?, hide_ips=?, allow_ips=?, last_updated=datetime('now')"
        params = (json.dumps(self.SettingsData), '\n'.join(self.SquidNoBumpSites), '\n'.join(self.SquidHideDomains), '\n'.join(self.HideIPs), '\n'.join(self.AllowIPs))
        self.db.query_exec(sql, params)
        
        #-----clear old country blocks first-----
        sql = "update countries set blocked=0"
        params = ()
        self.db.query_exec(sql, params)
        
        #-----apply country blocks to country table-----
        sql_countries = "','".join(self.SettingsData['blocked_country'])
        sql = "update countries set blocked=1 where country_code in ('" + sql_countries + "')"
        self.db.query_exec(sql, params)
        
        #-----clear old TLD blocks first-----
        sql = "update tlds set blocked=0"
        params = ()
        self.db.query_exec(sql, params)
        
        #-----apply TLD blocks to TLD table-----
        sql_tlds = "','".join(self.SettingsData['blocked_tld'])
        sql = "update tlds set blocked=1 where tld in ('" + sql_tlds + "')"
        self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    # separate function to save just the ip_log_raw_data_view column
    def save_ip_log_view_settings(self):
        if not self.IPLogRawDataView:
            return
        #-----save to settings table-----
        sql = "update settings set ip_log_raw_data_view=?, raw_data_view_last_updated=datetime('now')"
        params = (json.dumps(self.IPLogRawDataView),)
        self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    # separate function to save just the iptables_rules column
    def save_iptables_rules_settings(self):
        if not self.IPtablesRules:
            return
        #-----save to settings table-----
        sql = "update settings set iptables_rules=?, iptables_rules_last_updated=datetime('now')"
        params = (json.dumps(self.IPtablesRules),)
        self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    # separate function to save just the icap column
    def save_icap_settings(self):
        if not self.ICAP:
            return
        #-----save to settings table-----
        sql = "update settings set icap=?, icap_last_updated=datetime('now')"
        params = (json.dumps(self.ICAP),)
        self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    #-----make sure invalid Settings don't get saved-----
    # Returns a list of ProtectedCountries not blocked
    # SettingsData JSON Example:
    # {
    #  "blocked_country": ["XX", "YY", "ZZ"],
    #  "blocked_tld": ["XXX", "YYY"],
    #  'squid_nobumpsites': '',
    #  'squid_hide_domains': '',
    #  'hide_ips': '',
    # }
    def validate_settings(self):
        self.process_nobumpsites()
        self.process_hide_domains()
        self.process_hide_ips()
        self.process_allow_ips()
        
        #-----prevent ProtectedTLDs from being blocked-----
        tlds_not_blocked = []
        if self.SettingsData['blocked_tld']:
            allowed_tld_blocks = []
            for tld in self.SettingsData['blocked_tld']:
                if tld in self.ConfigData['ProtectedTLDs']:
                    #-----this will never be called from WSGI if front-end javascript protections are working-----
                    tlds_not_blocked.append(tld)
                else:
                    allowed_tld_blocks.append(tld)
            self.SettingsData['blocked_tld'] = allowed_tld_blocks
        
        #-----prevent ProtectedCountries from getting blocked-----
        countries_not_blocked = []
        if self.SettingsData['blocked_country']:
            allowed_country_blocks = []
            for country in self.SettingsData['blocked_country']:
                if country in self.ConfigData['ProtectedCountries']:
                    #-----this will never be called from WSGI if front-end javascript protections are working-----
                    countries_not_blocked.append(country)
                else:
                    allowed_country_blocks.append(country)
            self.SettingsData['blocked_country'] = allowed_country_blocks
        return countries_not_blocked
    
    #--------------------------------------------------------------------------------
    
    def init_webserver_domain(self):
        sql_update = 'update zzz_system set webserver_domain=?'
        params = (self.ConfigData['AppInfo']['Domain'],)
        self.db.query_exec(sql_update, params)
    
    #--------------------------------------------------------------------------------
    
    def init_settings_db(self):
        """initialize settings - needed during install"""
        
        self.SettingsData = {
            'autoplay': 'false',
            'social': 'false',
            'telemetry': 'false',
            'duplicate_domain': 'false',
            'links_by_function': 'false',
            'icap_condensed': 'false',
            'block_country_tld': 'false',
            'block_country_tld_always': 'false',
            'block_country_ip_always': 'false',
            'block_custom_ip_always': 'false',
            'block_tld_always': 'false',
            'dark_mode': 'true', # dark mode on by default
            'check_zzz_update': 'true',
            'auto_install_zzz_update': 'false',
            'show_dev_tools': 'false',
            'restart_openvpn_weekly': 'true',

            'test_server_dns_block': 'false',
            'test_server_squid': 'true',

            'blocked_country': [],
            'blocked_tld': [],
        }
        
        #-----use the default squid nobumpsites file to initialize the DB-----
        self.SquidNoBumpSites = []
        filepath = self.ConfigData['UpdateFile']['squid']['nobumpsites']
        with open(filepath, 'r') as read_file:
            for line in read_file:
                self.SquidNoBumpSites.append(line.lstrip('.').strip())
        
        self.SquidHideDomains = []
        self.HideIPs = []
        self.AllowIPs = []
        
        sql_delete = "delete from settings"
        params_delete = ()
        
        sql = "insert into settings (json, squid_nobumpsites, squid_hide_domains, hide_ips, allow_ips, last_updated) values (?, ?, ?, ?, ?, datetime('now'))"
        params = (json.dumps(self.SettingsData), '\n'.join(self.SquidNoBumpSites), '\n'.join(self.SquidHideDomains), '\n'.join(self.HideIPs), '\n'.join(self.AllowIPs))
        
        self.db.query_exec(sql_delete, params_delete)
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    def init_country_db(self):
        """initialize country list DB"""
        self.clear_countries_db()
        
        #-----insert the data into the countries table-----
        sql = 'insert into countries (country_code, country, blocked) values (?, ?, ?)'
        params_list = []
        for country_code in self.ConfigData['OfficialCountries'].keys():
            params_list.append((country_code, self.ConfigData['OfficialCountries'][country_code], 0))
        self.db.query_exec_many(sql, params_list)
    
    def clear_countries_db(self):
        sql = "delete from countries"
        params = ()
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    def init_tld_db(self):
        """initialize tld list DB"""
        self.clear_tlds_db()
        
        #-----insert the data into the TLDs table-----
        sql = 'insert into tlds (tld, blocked) values (?, ?)'
        params_list = []
        for tld in self.ConfigData['TLDs']:
            params_list.append((tld, 0))
        self.db.query_exec_many(sql, params_list)
    
    def clear_tlds_db(self):
        sql = "delete from tlds"
        params = ()
        self.db.query_exec(sql, params)
    
    #-----add/remove entries in the tld table after a new TLD-list file is installed-----
    # check if the file differs from the DB, update the DB
    # ConfigData['TLDFile'] = '/opt/zzz/data/TLD-list.txt'
    def update_tld_db(self):
        # Config list is an array
        params_list_add_tlds = []
        for tld in self.ConfigData['TLDs']:
            found_tld = self.TLDs.get(tld, None)
            if not found_tld:
                # DB is missing a TLD from the file, add it
                params_list_add_tlds.append((tld, 0))
        sql = 'insert into tlds (tld, blocked) values (?, ?)'
        self.db.query_exec_many(sql, params_list_add_tlds)
        
        # Settings list is an associative array
        remove_tlds = []
        for tld in self.TLDs.keys():
            if tld not in self.ConfigData['TLDs']:
                # DB has a TLD that is not in the file, remove it
                remove_tlds.append(tld)
        sql_tlds = "','".join(remove_tlds)
        sql = "delete from tlds where tld in ('" + sql_tlds + "')"
        params = ()
        self.db.query_exec(sql, params)
        
        # rebuild bind configs
        self.get_settings()
        should_block_tld_always = self.is_setting_enabled('block_tld_always')
        should_block_country_tlds_always = self.is_setting_enabled('block_country_tld_always')
        enable_test_server_dns_block = self.is_setting_enabled('test_server_dns_block')
        zzz_template = zzzevpn.ZzzTemplate(self.ConfigData, self.db, self.util)
        zzz_template.make_bind_configs(should_block_tld_always, should_block_country_tlds_always, enable_test_server_dns_block)
        
        # insert restart requests for all python apps so they pick up the new settings
        self.db.request_reload('bind')
        # self.db.request_restart('apache')
        self.util.apache_config_reload()
        self.db.request_reload('zzz_icap')
        self.db.request_restart('zzz')
        self.util.work_available(1)
    
    #--------------------------------------------------------------------------------
    
    def init_ip_country_db(self):
        self.clear_ip_country_db()
        
        #-----insert the data into the countries table-----
        sql = 'insert into countries (country_code, country) values (?, ?)'
        params_list = []
        for country_code in self.ConfigData['OfficialCountries'].keys():
            params_list.append((country_code, self.ConfigData['OfficialCountries'][country_code]))
        self.db_ip_country.query_exec_many(sql, params_list)
    
    def clear_ip_country_db(self):
        sql = "delete from countries"
        params = ()
        self.db_ip_country.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    #-----insert a service request to update the settings-----
    def queue_settings_update(self):
        self.db.insert_service_request('settings', 'settings')
        self.util.work_available(1)
    
    #--------------------------------------------------------------------------------
    
    #-----use settings to generate a nobumpsites ACL for squid-----
    def generate_squid_nobumpsites(self):
        nobumpsites_output = ''
        for domain in self.SquidNoBumpSites:
            nobumpsites_output += '.{}\n'.format(domain)
        filepath = self.ConfigData['UpdateFile']['squid']['nobumpsites']
        with open(filepath, 'w') as write_file:
            write_file.write(nobumpsites_output)
    
    #--------------------------------------------------------------------------------
    
    def get_allowlist(self):
        #-----start with internal IP's-----
        allow_ips = self.util.ip_util.ipv4_private_subnets
        
        #-----add protected IP's from Config-----
        if self.ConfigData['ProtectedIPs']:
            allow_ips.extend(self.ConfigData['ProtectedIPs'])
        
        #-----add allowlist IP's from Settings-----
        if self.AllowIPs:
            allow_ips.extend(self.AllowIPs)
        
        # de-duplicate the list
        return self.util.unique_sort(allow_ips)
    
    #-----use settings to generate an allowlist-----
    def generate_iptables_allowlist(self):
        unique_ips = self.get_allowlist()
        allowlist_output = '\n'.join(unique_ips)
        
        #-----write to dir accessible to apache-----
        filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath_allow']
        with open(filepath, 'w') as write_file:
            write_file.write(allowlist_output)
    
    #--------------------------------------------------------------------------------

