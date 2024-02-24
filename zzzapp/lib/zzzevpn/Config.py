#-----python Config-----
# Loads custom settings from /etc/zzz.conf
# Items with a #CONFIG comment should be customized in zzz.conf

import copy
import glob
import ifcfg
import json
import os
import pathlib
import re
import shutil
import yaml

#-----import modules from the lib directory-----
import zzzevpn

class Config:
    'Config constants'
    
    conf_data_loaded: dict = None
    dns_service: zzzevpn.DNSservice = None
    ip_util: zzzevpn.IPutil = None
    
    #TODO: rename this to "zzzevpn" after moving the codebase to the new repos
    # should match ZZZ_REPOS_NAME in util.sh
    repos_name: str = 'vpntest'
    repos_dir: str = f'/home/ubuntu/repos/{repos_name}'
    
    ConfigFile: str = '/etc/zzz.conf'
    TLDFile: str = '/opt/zzz/data/TLD-list.txt'

    # boolean values
    boolean_values: list = ['TRUE', 'FALSE']

    # squid/ICAP/redis ports are not allowed to be used for openvpn
    invalid_ports: list = [3127, 3128, 3129, 29999]

    # regex_VPNusers_pattern = r'^[A-Za-z0-9][A-Za-z0-9\-]{1,48}[A-Za-z0-9](\,[A-Za-z0-9][A-Za-z0-9\-]{1,48}[A-Za-z0-9])*$'
    regex_VPNusers_pattern = r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9](\,[a-z0-9][a-z0-9\-]{1,48}[a-z0-9])*$'
    regex_VPNusers = re.compile(regex_VPNusers_pattern, re.DOTALL | re.IGNORECASE)
    regex_tld_pattern = r'^([a-z]{2,32}|XN\-\-[a-z0-9\-]{2,40})$'
    regex_tld = re.compile(regex_tld_pattern, re.DOTALL | re.IGNORECASE)
    regex_favicon_pattern = r'^[a-z0-9]{1,6}$'
    regex_favicon = re.compile(regex_favicon_pattern, re.DOTALL | re.IGNORECASE)

    # set to True to enable extra log output
    test_mode = False

    #TODO: make this readonly after loading YAML config data below
    default_ConfigData: dict = {
        'ApacheTempFiles': '/opt/zzz/apache',
        
        'AppInfo': {
            'BlockedIPRange': '10.4.0.0/14', #CONFIG - client IP's in this range will have IP blocks applied
            # 'BlockedIPRangeICAP': '10.5.0.0/16', #CONFIG - client IP's in this range will have IP blocks applied
            'CA': {
                'Default': '', # root CA, long expiration
                'OpenVPN': '', # intermediate CA, long expiration
                'Squid': '', # intermediate CA, 1-year expiration
                'Squid-Top': '', # intermediate CA, long expiration
            },
            'ConfigJSupdated': '1650675000', # update timestamp for /var/www/html/js/zzz_config.js
            'Domain': 'services.zzz.zzz', #CONFIG
            'Hostname': 'localhost', # load from /etc/hostname
            'IP': '10.7.0.1',
            'RedisDBnumber': 0, # valid numbers are 0-15, 0 is production, 15 is pytest
            'RedisHostname': 'localhost',
            'VpnIPRange': '10.0.0.0/12', #TODO: move to 10.0.0.0/13 or 10.8.0.0/13 when possible
            'VpnServerName': 'vpn.zzz.zzz',
        },

        #TODO: add support for dns-allow
        # list_type: list_name
        'CombinedLists': {
            'dns-deny': 'combined-DNS-deny',
            'ip-deny': 'combined-IP-deny',
            'ip-allow': 'combined-IP-allow',
        },

        'DataFile': {
            'CountryList': '/opt/zzz/data/country-codes.json',
            'CountryListUTF8': '/opt/zzz/data/country-codes-utf8.json',
            'motd': '/run/motd.dynamic',
        },
        
        # indicates if the config file data has already been loaded
        'DataLoaded': False,
        
        # indicates if the config file data has passed validation
        'DataValid': False,
        
        'DBFilePath': {
            'CountryIP': '/opt/zzz/sqlite/country-IP.sqlite3', # get a list of IP's for a given country
            'IPCountry': '/opt/zzz/sqlite/ip-country.sqlite3', # lookup the country for a given IP
            'GeoIP': '/usr/share/GeoIP/GeoLite2-Country.mmdb', # auto-backup? /var/lib/GeoIP/GeoLite2-Country.mmdb
            'Services': '/opt/zzz/sqlite/services.sqlite3',
        },
        
        #-----default is False, set to True for extra log output-----
        'Debug': False,
        
        'Directory': {
            'Apache': '/etc/apache2',
            'ApacheSites': '/etc/apache2/sites-available',
            'BIND': '/etc/bind',
            'BINDallowedCustomDirs': [
                '/opt/zzz/named', # used for production to test the config before install
                '/opt/zzz/python/test/named', # used by pytest
            ],
            'Config': '/opt/zzz/config',
            'Coverage': '/var/www/html/coverage',
            'EasyRSA': '/home/ubuntu/easyrsa3',
            'EasyRSAvars': '/home/ubuntu/easyrsa3/zzz_vars',
            'IPtablesLog': '/var/log/iptables',
            'LinuxUser': '/home/ubuntu',
            'OpenVPNclient': '/home/ubuntu/openvpn',
            'OpenVPNserver': '/etc/openvpn',
            'PKI': {
                'Default': '/home/ubuntu/easyrsa3/pki',
                'OpenVPN': '/home/ubuntu/easyrsa3/pki-openvpn-int',
                'Squid': '/home/ubuntu/easyrsa3/pki-squid',
                'Squid-Top': '/home/ubuntu/easyrsa3/pki-squid-top',
            },
            'Repos': repos_dir,
            'Settings': '/etc/bind/settings',
            'SquidAccess': '/var/log/squid_access',
            'Templates': '/opt/zzz/python/templates',
            # users in the www-data group can write to TLDextractCache:
            'TLDextractCache': '/opt/zzz/data/tldextract_cache',
            # upgrades need to be run out of the repos directory for now
            'UpgradeScript': f'{repos_dir}/upgrade/zzz',
        },

        'DiskSpace': {
            'Database': 1024, # default to 1024 MB database file size limit
            'IPtablesLogFiles': 1024, # default to 1024 MB database file size limit
        },

        'DNSDenylist': {}, # load this below
        
        'EffectiveTLDs': [],
        
        'EnableMaxMind': False,
        
        'EnableSqliteIPCountry': False,

        'Favicon': {
            'use_custom': False,
            'line1': 'ZZZ',
            'line2': 'VPN',
            'line3': '',
            'error': '',
            'sizes': {
                #TODO: make an svg image file so only one file is needed?
                'android': [196],
                'apple': [120, 152, 167, 180],
                'browser': [16, 32, 57, 76, 96, 128, 192, 228],
                # serve the 48x48 file in a 32x32 image tag on high-density displays
                'high_density': [48],
                'max': 512,
            },
        },

        # for running demos without exposing the real client IPs or other things that should be hidden
        # manually create a file with the IP's to hide: /opt/zzz/data/hide_ips.txt
        'HideIPs': set(), # load this below

        'IPBlacklist': {}, # load this below
        
        'IPdeny': {
            'countries': [], # populate this below
            'ipv4': {
                'src_dir': '/opt/zzz/data/ipdeny-ipv4',
                'dst_dir': '/etc/iptables/countries',
                'conf_file': '/etc/iptables/ipset-update-countries.conf',
            },
            'ipv6': {
                'src_dir': '/opt/zzz/data/ipdeny-ipv6',
                'dst_dir': '/etc/iptables/countries-ipv6',
                'conf_file': '/etc/iptables/ipset-update-countries-ipv6.conf',
            },
        },
        
        'IPv4': {
            'Internal': '',
            'IPCountry': { # database SQL scripts to update the IP-country data
                'new': '/opt/zzz/upgrade/ip_country_new.sql',
                'swap': '/opt/zzz/upgrade/ip_country_table_swap.sql',
            },
            'iptables': {
                'class-b': {
                    'dns-icap': '10.5.0.0',
                    'dns': '10.6.0.0',
                    'dns-squid': '10.7.0.0',
                    'open': '10.8.0.0',
                    'open-squid': '10.9.0.0',
                },
            },
            'Log': {
                'all': '/var/log/iptables/ipv4.log',
                'accepted': '/var/log/iptables/ipv4-accepted.log',
                'blocked': '/var/log/iptables/ipv4-blocked.log',
            },
            'NameServers': [
                '8.8.8.8', # Google DNS
                '8.8.4.4', # Google DNS
            ],
            'VPNserver': '',
        },
        
        # set Activate to True in zzz.conf to use IPv6, must be done on install
        # VPNserver can be auto-detected from ifconfig output
        'IPv6': {
            'Activate': False,
            'BlockedIPRange': 'IP64:10:6:0:0/95', #substitute 'IP64' for the first /64 on loading
            'IP64': '', # initialize below to our assigned /64
            'Log': {
                'all': '/var/log/iptables/ipv6.log',
                'accepted': '/var/log/iptables/ipv6-accepted.log',
                'blocked': '/var/log/iptables/ipv6-blocked.log',
            },
            'NameServers': [
                '2001:4860:4860::8888', # Google DNS
                '2001:4860:4860::8844', # Google DNS
            ],
            'ProtectedIPs': [
                '2001:4860:4860::8888', # Google DNS
                '2001:4860:4860::8844', # Google DNS
            ],
            'VPNserver': '',
        },
        
        'LogFile': {
            'ICAPdata': '/var/log/zzz/icap/zzz-icap-data',
        },

        'LogPacketsPerMinute': '1000',

        # too many HTML table rows makes the squid/IP log pages load too slowly or run out of memory
        'LogParserRowLimit': 10000,
        
        # prevent the squid log URL column from getting too wide, only affects HTTP URLs, not HTTPS
        'MaxUrlDisplayLength': 60,

        'MemoryUsage': {
            'bind': {
                # BIND memory usage tested with: ubuntu 20.04.4, bind 9.16.1-0ubuntu2.11
                'base_mem': 60,
                'mb_per_domain': 18.2/1024,
                'excess_allowed': 100,
            },
            'squid': {
                'base_mem': 40,
                'excess_allowed': 50,
            },
        },

        'OfficialCountries': {},
        
        # https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Exceptional_reservations
        'OfficialCountriesWithExceptions': {},
        
        'OpenVPN': {
            'MaxClients': 50,
        },
        
        # list of physical network interfaces, required for proper routing
        'PhysicalNetworkInterfaces': {
            'internal': 'AUTODETECT',
            # limited to one physical network interface for now
            # 'external': '',
        },

        'PKI': {
            'apache_all_certs': '/etc/ssl/certs/zzz-apache-all-certs.crt',
            'openvpn-ca-cert': '/opt/zzz/data/ssl-public/openvpn-ca.crt',
            'root-ca-cert': '/opt/zzz/data/ssl-public/root-ca.crt',
            'squid-ca-cert': '/opt/zzz/data/ssl-public/squid-ca.crt',
            'squid-top-ca-cert': '/opt/zzz/data/ssl-public/squid-top-ca.crt',
        },
        
        'Ports': {
            'ICAP': 29999,
            'OpenVPN': {
                # 'dns': 39101,
                'dns-icap': 39102,
                # 'dns-squid': 39103,
                # 'open': 39104,
                # 'open-squid': 39105,
                
                #TODO: switch to new ports and remove this
                'dns': 39077,
                'dns-squid': 39094,
                'open': 39066,
                'open-squid': 39055,
            },
            'pytest': { # ports reserved for testing the Zzz apps
                'ICAP': 29981,
                'WSGI': 29982,
            },
            'redis': 29998,
            'Squid': {
                'non-intercept': '3127', # 3127 --> 29901 non-intercept traffic
                'http': '3128', # 3128 --> 29902 HTTP intercept
                'https': '3129', # 3129 --> 29903 HTTPS intercept
            },
            'SquidICAP': {
                'non-intercept': '29911', # non-intercept traffic
                'http': '29912', # HTTP intercept
                'https': '29913', # HTTPS intercept
            },
        },
        
        #-----load this below, will be blocked from selecting in Settings-----
        'ProtectedCountries': [],
        
        # there are too many useful domains with these TLD's to allow blocking of the entire TLD
        # load a customized list below
        'ProtectedTLDs': [ 'COM', 'NET', 'ORG', 'GOV', ],
        
        #TODO: load this list from a textfile?
        'ProtectedIPs': [
            '8.8.8.8', # Google DNS
            '8.8.4.4', # Google DNS
        ],
        'ProtectedIPdict': {},
        
        'ReverseIPBatchSize': 10, # can lookup more reverse IP's at once if the lookup server is fast
        
        'ServiceStatus': {
            'Requested': 'Requested',
            'Working':   'Working',
            'Done':      'Done',
            'Error':     'Error',
        },
        
        #-----load below from /etc/bind/settings files-----
        'Settings': {
            'autoplay': {},
            'social': {},
            'telemetry': {},
        },
        
        #-----map setting names to files-----
        'SettingFile': {
            'autoplay': 'autoplay.txt',
            'social': 'social.txt',
            'telemetry': 'telemetry.txt',
        },

        'SqliteUtilsFormats': {
            'ascii_formats': [
                'asciidoc',
                'github',
                'grid',
                'jira',
                'latex',
                'latex_booktabs',
                'latex_longtable',
                'latex_raw',
                'mediawiki',
                'moinmoin',
                'orgtbl',
                'outline',
                'pipe',
                'plain',
                'presto',
                'pretty',
                'psql',
                'rst',
                'simple',
                'textile',
                'tsv',
                'youtrack',
            ],
            'html_formats': [
                'html',
                'unsafehtml',
            ],
            'unicode_formats': [
                'double_grid',
                'double_outline',
                'fancy_grid',
                'fancy_outline',
                'heavy_grid',
                'heavy_outline',
                'mixed_grid',
                'mixed_outline',
                'rounded_grid',
                'rounded_outline',
                'simple_grid',
                'simple_outline',
            ],
        },

        #-----scripts designed to be called by python subprocess.run-----
        # may have minimal output vs. normal command-line scripts
        'Subprocess': {
            # CheckLatestVersion, ServiceRequest, UpdateZzz
            'git-branch': '/home/ubuntu/bin/git-branch',
            'git-checkout': '/home/ubuntu/bin/git-checkout',
            'git-diff': '/home/ubuntu/bin/git-diff',
            'git-pull': '/home/ubuntu/bin/git-pull',
            'git-reset': '/home/ubuntu/bin/git-reset',
            'openvpn-latest-stable-version': '/opt/zzz/python/bin/subprocess/openvpn-latest-stable-version.sh',
            'squid-latest-stable-version': '/opt/zzz/python/bin/subprocess/squid-latest-stable-version.sh',
            'zzz-latest-stable-version': '/opt/zzz/python/bin/subprocess/zzz-latest-stable-version.sh',
            'zzz-list-versions': '/opt/zzz/python/bin/subprocess/zzz-list-versions.sh',
            
            # ServiceRequest
            'checkwork': '/opt/zzz/python/bin/subprocess/checkwork.sh',
            'diff_code': '/opt/zzz/python/bin/diff_code.py',
            'openvpn-restart': '/opt/zzz/python/bin/subprocess/openvpn-restart.sh',
            'os-list-updates': '/opt/zzz/python/bin/subprocess/os-list-updates.sh',
            'os-install-updates': '/opt/zzz/python/bin/subprocess/os-install-updates.sh',
            'update-ip-log': '/opt/zzz/python/bin/update-ip-log.py',
            'zzz-app-update': '/opt/zzz/python/bin/subprocess/zzz-app-update.sh',
            
            # SystemStatus
            'list-installed-software': '/opt/zzz/python/bin/subprocess/list-installed-software.sh',
            'os-list-installed-packages': '/opt/zzz/python/bin/subprocess/os-list-installed-packages.sh',
            
            # UpdateZzz
            'pip-check': '/opt/zzz/python/bin/subprocess/pip-check.sh',
            'sqlite-utils': '/opt/zzz/venv/bin/sqlite-utils',
        },
        
        'TimeZoneDisplay': 'America/Los_Angeles', #CONFIG
        
        #-----load the PublicSuffix.org TLD's from a config file in __init__()-----
        # There are about 1536 TLD's as of 11/7/2018
        # There are even more effective TLD's (.uk, .co.uk, etc.)
        'TLDs': [],
        'TLDdict': {},
        
        'UpdateFile': {
            'bind': {
                'src_filepath': '/opt/zzz/apache/dns-blacklist.txt',
                'src_filepath_add': '/opt/zzz/apache/dns_add_domains.txt',
                'src_filepath_replace': '/opt/zzz/apache/dns_replace_domains.txt',
                'tmp_filepath': '/opt/zzz/python/dns-blacklist', # for converting the domain list to a zone file list
                'dst_filepath': '/etc/bind/dns-blacklist',
                'named_settings': '/etc/bind/named-settings.conf',
                'named_options_template_filepath': '/opt/zzz/config/named/named.conf.options.template',
                'named_options_dst_filepath': '/etc/bind/named.conf.options',
            },
            'bind_ipv6': {
                'template_filepath': '/opt/zzz/config/named/named.conf.options.template',
                'dst_filepath': '/etc/bind/named.conf.options',
            },
            'db_maintenance': '/opt/zzz/db_maintenance',
            #-----co-ordinate these values with ZzzTemplate.easyrsa_cert_config-----
            # also used in pki_utils.sh-->zzz_make_cert_pass_file()
            'easyrsa': {
                'ca-pass-openvpn': '/opt/zzz/data/ssl-private/ca-openvpn.pass',
                'ca-pass-root': '/opt/zzz/data/ssl-private/ca-root.pass',
                'ca-pass-squid': '/opt/zzz/data/ssl-private/ca-squid.pass',
                'ca-pass-squid-top': '/opt/zzz/data/ssl-private/ca-squid-top.pass',
                'server-pass-apache': '/opt/zzz/data/ssl-private/apache-server.pass',
                'server-pass-openvpn': '/etc/openvpn/vpn.zzz.zzz_pem_pass.txt',
            },
            'ipset': {
                'allowlist_filepath': '/etc/iptables/ipset-update-allow-ip.conf',
                'blacklist_filepath': '/etc/iptables/ipset-update-blacklist.conf',
                'country_filepath': '/etc/iptables/ipset-update-countries.conf',
            },
            'ipset_ipv6': {
                'allowlist_filepath': '/etc/iptables/ipset-ipv6-update-allowlist.conf',
                'blacklist_filepath': '/etc/iptables/ipset-ipv6-update-blacklist.conf',
                'country_filepath': '/etc/iptables/ipset-ipv6-update-countries.conf',
            },
            'iptables': {
                'src_filepath_allow': '/opt/zzz/apache/iptables-allowlist.txt', # Settings list of allowed IP's
                'src_filepath': '/opt/zzz/apache/iptables-blacklist.txt',
                'src_filepath_add': '/opt/zzz/apache/iptables_add_ips.txt',
                'src_filepath_replace': '/opt/zzz/apache/iptables_replace_ips.txt',
                
                # not used anymore?
                'tmp_filepath': '/opt/zzz/python/ip-blacklist.conf', # iptables config file
                
                'dst_allowlist_filepath': '/etc/iptables/ip-allowlist.conf',
                'dst_filepath': '/etc/iptables/ip-blacklist.conf',
                'dst_countries_filepath': '/etc/iptables/ip-countries.conf',
                'dst_log_accepted_filepath': '/etc/iptables/ip-log-accepted.conf',
                
                'router_config_template': '/opt/zzz/config/iptables/iptables-zzz.conf.template',
                'router_config_dst': '/etc/iptables/iptables-zzz.conf',
                
                'update-ip-log': '/var/log/zzz/cron/update-ip-log.log',
            },
            'ip6tables': {
                'src_filepath': '/opt/zzz/apache/ip6tables-blacklist.txt',
                'src_filepath_add': '/opt/zzz/apache/ip6tables_add_ips.txt',
                'src_filepath_replace': '/opt/zzz/apache/ip6tables_replace_ips.txt',
                'tmp_filepath': '/opt/zzz/python/ip6-blacklist.conf', # iptables config file
                'dst_filepath': '/etc/iptables/ip6-blacklist.conf',
            },
            'linux': {
                'list_os_updates': '/opt/zzz/apache/OS_Updates.txt',
                'os_update_output': '/opt/zzz/apache/os_update_output.txt',
            },
            'openvpn': {
                'users_to_add': '/opt/zzz/data/openvpn_users_to_add.txt',
                'users_to_delete': '/opt/zzz/data/openvpn_users_to_delete.txt',
            },
            'redis': {
                'config_dst': '/etc/redis/redis.conf',
                'config_template': '/opt/zzz/config/redis.conf.template',
            },
            #TODO: remove this
            # 'pid': '/var/run/zzz.pid',
            'squid': {
                'config_dst': '/etc/squid/squid.conf',
                #TODO: remove "TEST-" from filename when going live
                'config_squid_dst': '/etc/squid/squid.conf', # should end up the same as squid.conf
                'config_squid_icap_dst': '/etc/squid/squid-icap.conf',
                'config_template': '/opt/zzz/config/squid/squid.conf.template',
                'nobumpsites': '/etc/squid/nobumpsites.acl',
                'src_filepath_ip': '/opt/zzz/apache/blocked-ips.txt',
                'dst_filepath_ip': '/etc/squid/blocked-ips.txt',
                'src_filepath_subdomain': '/opt/zzz/apache/blocked-sites.txt',
                'dst_filepath_subdomain': '/etc/squid/blocked-sites.txt',
            },
            'zzz': {
                'config_js': '/var/www/html/js/zzz_config.js',
                'run_code_diff': '/opt/zzz/apache/dev/zzz-code-diff.txt',
                'run_pytest': '/opt/zzz/apache/dev/zzz-pytest.txt',
                'installer_output': '/opt/zzz/apache/dev/zzz-installer-output.txt',
                'git_branches': '/opt/zzz/apache/dev/zzz-git-branches.txt',
                'git_branch_current': '/opt/zzz/apache/dev/zzz-git-branch-current.txt',
                'git_output': '/opt/zzz/apache/dev/zzz-git-output.txt',
                'upgrade_log': '/opt/zzz/apache/dev/zzz-upgrade.log',
                'dev_upgrade_log': '/opt/zzz/apache/dev/zzz-dev-upgrade.log',
            },
        },
        
        'URL': {
            'Services': '/z/index', # WSGI index page
            'UpdateOS': '/z/update_os',
            'UpdateZzz': '/z/update_zzz',
            'Whois': '/z/network_service?action=whois',
        },
        
        'VersionFiles': {
            'openvpn': '/opt/zzz/apache/openvpn_version_check.txt',
            'squid': '/opt/zzz/apache/squid_version_check.txt',
            'zzz': '/opt/zzz/apache/zzz_version_check.txt',
        },
        
        'VPNusers': [],
        
        #-----load from zzz.conf-----
        'WireGuard': {
            'Enable': False,
        },
    }

    #-----copying ConfigData here allows access to the original unaltered default ConfigData if needed-----
    # ConfigData will be altered by __init__() to make it more useful to apps
    ConfigData: dict = default_ConfigData

    #--------------------------------------------------------------------------------
    
    #TODO: change methods of calling Config()
    #   OLD:
    #     config = zzzevpn.Config.Config()
    #     self.ConfigData = getattr(config, 'ConfigData')
    #   NEW:
    #     config = zzzevpn.Config(skip_autoload=True)
    #     self.ConfigData = config.get_config_data()
    #
    # AFTER all upgrades are done in the entire codebase:
    #   remove the call to self.get_config_data()
    #   remove all params (except self and custom_ConfigData)
    def __init__(self, print_log: bool=False, config_file: str=None, force_reload: bool=False, custom_ConfigData: dict=None, skip_autoload: bool=False) -> None:
        self.dns_service = zzzevpn.DNSservice()
        self.ip_util = zzzevpn.IPutil()
        self.init_vars(custom_ConfigData)
        if not skip_autoload:
            self.get_config_data(print_log, config_file, force_reload, custom_ConfigData)
    
    #--------------------------------------------------------------------------------
    
    def init_vars(self, custom_ConfigData: dict=None) -> None:
        if custom_ConfigData:
            # pytest --> test_zzz.py --> uses custom_ConfigData to override constants above
            self.ConfigData = custom_ConfigData
        else:
            # self.ConfigData = self.default_ConfigData
            #-----use deepcopy to avoid changing the default_ConfigData-----
            self.ConfigData = copy.deepcopy(self.default_ConfigData)
        self.ConfigData['DataValid'] = False
        self.ConfigData['DataLoaded'] = False
        self.test_mode = False
        
        # list all non-OpenVPN assigned ports
        self.invalid_ports = [
            self.ConfigData['Ports']['ICAP'],
            self.ConfigData['Ports']['pytest']['ICAP'],
            self.ConfigData['Ports']['pytest']['WSGI'],
            self.ConfigData['Ports']['redis'],
            self.ConfigData['Ports']['Squid']['non-intercept'],
            self.ConfigData['Ports']['Squid']['http'],
            self.ConfigData['Ports']['Squid']['https'],
            self.ConfigData['Ports']['SquidICAP']['non-intercept'],
            self.ConfigData['Ports']['SquidICAP']['http'],
            self.ConfigData['Ports']['SquidICAP']['https'],
        ]
    
    #--------------------------------------------------------------------------------
    
    #TODO: move most of the __init__() code into here - requires re-writing about 85 calls to Config.Config()
    #-----returns the ConfigData dictionary-----
    def get_config_data(self, print_log: bool=False, config_file: str=None, force_reload: bool=False, custom_ConfigData: dict=None):
        if config_file:
            if os.path.exists(config_file):
                self.ConfigFile = config_file
        #-----skip this if we have already loaded data once-----
        if force_reload or not self.ConfigData['DataLoaded']:
            # reset vars in case of a forced reload
            self.init_vars(custom_ConfigData)
            
            if not self.configtest():
                return
            self.ConfigData['DataValid'] = True
            
            if not self.load_config_data():
                return
            self.ConfigData['DataLoaded'] = True
            
            if print_log:
                print('Config loaded')
        return self.ConfigData
    
    #--------------------------------------------------------------------------------
    
    #-----load constants from a YAML config file-----
    # validate_entries() is also loading zzz.conf data into the ConfigData dictionary after it passes tests
    def load_config_data(self) -> bool:
        """ Load config file data into internal ConfigData variable
            Assumes that configtest() has already loaded the file into the config_data_loaded variable
        """
        if self.conf_data_loaded is None:
            return False
        self.load_official_country_list()
        # IPdeny countries
        self.load_country_list()
        # official TLD's
        self.load_TLD_list(self.TLDFile)
        
        #-----load the hostname-----
        with open('/etc/hostname', 'r') as hostname_file:
            self.ConfigData['AppInfo']['Hostname'] = hostname_file.read().strip()
        #-----update ConfigData with the values from the config file-----
        self.ConfigData['AppInfo']['Domain'] = self.conf_data_loaded['Domain']
        self.ConfigData['AppInfo']['CA']['Default'] = self.conf_data_loaded['CA']['Default']
        self.ConfigData['AppInfo']['CA']['OpenVPN'] = self.conf_data_loaded['CA']['Default'] + ' OpenVPN'
        self.ConfigData['AppInfo']['CA']['Squid'] = self.conf_data_loaded['CA']['Default'] + ' Squid'
        self.ConfigData['AppInfo']['CA']['Squid-Top'] = self.conf_data_loaded['CA']['Default'] + ' Squid Top'
        #-----optional maxmind param-----
        enable_maxmind = self.conf_data_loaded.get('EnableMaxMind', 'False')
        if enable_maxmind.upper()=='TRUE':
            self.ConfigData['EnableMaxMind'] = True
        #-----optional sqlite ip-country param-----
        # dev testing only
        enable_sqlite_ip_country = self.conf_data_loaded.get('EnableSqliteIPCountry', 'False')
        if enable_sqlite_ip_country.upper()=='TRUE':
            self.ConfigData['EnableSqliteIPCountry'] = True
        #-----IPv4-----
        self.ConfigData['IPv4']['VPNserver'] = self.conf_data_loaded['IPv4']['VPNserver']
        #-----IPv6-----
        self.load_IPv6()
        #-----load other info-----
        self.load_js_config_time()
        self.load_physical_network_interfaces()
        self.load_protected_ips()
        self.load_protected_country_list()
        self.load_protected_tld_list()
        self.load_dns_denylist()
        self.load_ip_denylist()
        self.load_vpn_users()
        self.load_hide_ip_list()

        return True
    
    #--------------------------------------------------------------------------------
    
    # get the linux timestamp for /var/www/html/js/zzz_config.js
    def load_js_config_time(self) -> None:
        filepath = self.ConfigData['UpdateFile']['zzz']['config_js']
        if os.path.exists(filepath):
            path_obj = pathlib.Path(filepath)
            if path_obj:
                self.ConfigData['AppInfo']['ConfigJSupdated'] = path_obj.stat().st_mtime
    
    #--------------------------------------------------------------------------------
    
    def load_physical_network_interfaces(self) -> None:
        physical_network_interfaces = self.conf_data_loaded.get('PhysicalNetworkInterfaces', None)
        interface_internal = 'AUTODETECT'
        if physical_network_interfaces:
            interface_internal = physical_network_interfaces.get('internal', 'AUTODETECT')
        if interface_internal=='AUTODETECT':
            default_interface = ifcfg.default_interface()
            self.ConfigData['PhysicalNetworkInterfaces']['internal'] = default_interface['device']
        else:
            self.ConfigData['PhysicalNetworkInterfaces']['internal'] = interface_internal
    
    #--------------------------------------------------------------------------------
    
    def load_IPv6(self) -> None:
        #TODO: turn this back on when IPv6 is ready
        conf_data_IPv6 = None
        # conf_data_IPv6 = self.conf_data_loaded.get('IPv6', None)
        
        if conf_data_IPv6:
            conf_data_IPv6_Activate = self.conf_data_loaded['IPv6'].get('Activate', None)
            if conf_data_IPv6_Activate:
                if conf_data_IPv6_Activate.upper()=='TRUE':
                    self.ConfigData['IPv6']['Activate'] = True
            conf_data_IPv6_VPNserver = self.conf_data_loaded['IPv6'].get('VPNserver', None)
            if conf_data_IPv6_VPNserver:
                self.ConfigData['IPv6']['VPNserver'] = conf_data_IPv6_VPNserver
    
    #--------------------------------------------------------------------------------
    
    #-----add important IP's to the protected list, so they cannot be blocked in iptables-----
    # DNS servers (saved above)
    # our external IP - lookup
    #
    def load_protected_ips(self) -> None:
        #-----lookup our internal IPv4-----
        self.ConfigData['IPv4']['Internal'] = self.dns_service.lookup_ipv4_by_socket(self.ConfigData['AppInfo']['Hostname'])
        #-----lookup our external IPv4-----
        server_ipv4 = self.dns_service.lookup_my_external_ipv4()
        if self.ConfigData['IPv4']['VPNserver'].upper() == 'AUTODETECT':
            self.ConfigData['IPv4']['VPNserver'] = server_ipv4
        self.ConfigData['ProtectedIPs'].append(server_ipv4)
        
        #-----optional IPv4 NameServers in config file-----
        config_data_IPv4_NameServers = self.conf_data_loaded['IPv4'].get('NameServers', None)
        if config_data_IPv4_NameServers:
            new_nameservers = []
            for ip in self.conf_data_loaded['IPv4']['NameServers']:
                #-----de-duplicate-----
                if ip in self.ConfigData['IPv4']['NameServers']:
                    continue
                #-----make sure the IP's are valid-----
                if self.ip_util.is_ip(ip):
                    new_nameservers.append(ip)
            # no nameservers? default will be Google DNS
            if new_nameservers:
                self.ConfigData['IPv4']['NameServers'] = new_nameservers
        
        #-----optional IPv4 ProtectedIPs in config file-----
        # nameservers get on the protected list
        self.ConfigData['ProtectedIPs'] = self.ConfigData['IPv4']['NameServers']
        if self.conf_data_loaded['ProtectedIPs']:
            for ip in self.conf_data_loaded['ProtectedIPs']:
                #-----de-duplicate-----
                if ip in self.ConfigData['ProtectedIPs']:
                    continue
                #-----make sure the IP's are valid-----
                if self.ip_util.is_cidr(ip):
                    self.ConfigData['ProtectedIPs'].append(ip)
                elif self.ip_util.is_ip(ip):
                    self.ConfigData['ProtectedIPs'].append(ip)
        
        for ip in self.ConfigData['ProtectedIPs']:
            self.ConfigData['ProtectedIPdict'][ip] = 1
        
        #-----IPv6-----
        if self.ConfigData['IPv6']['Activate']:
            #TODO: after an OS reboot, IPv6 DNS lookup might crash due to the IPv6 networking being asleep
            #      maybe wake it up with a ping6 to google DNS?
            server_ipv6 = self.dns_service.lookup_my_external_ipv6()
            if self.ConfigData['IPv6']['VPNserver'].upper() == 'AUTODETECT':
                self.ConfigData['IPv6']['VPNserver'] = server_ipv6
            self.ConfigData['IPv6']['IP64'] = self.dns_service.ip_util.calc_ipv6_64(server_ipv6)
            #TODO: finish adding ipv6 handling before activating this or it will crash things
            #self.ConfigData['IPv6']['ProtectedIPs'].append(server_ipv6)
    
    #--------------------------------------------------------------------------------
    
    #-----load TLD's from file-----
    def load_TLD_list(self, filepath: str) -> None:
        """ Load TLD list from a given config file
        """
        self.ConfigData['TLDs'] = []
        self.ConfigData['TLDdict'] = {}
        with open(filepath, 'r') as tld_file:
            for tld in tld_file:
                #-----skip comment lines-----
                if tld.startswith('#'):
                    continue
                tld = tld.strip("\n")
                #-----skip empty lines-----
                if len(tld)==0:
                    continue
                #-----pattern match for safety-----
                if not self.regex_tld.match(tld):
                    continue
                #-----skip country codes, those go in a separate array-----
                found_country_tld = self.ConfigData['OfficialCountriesWithExceptions'].get(tld, None)
                if not found_country_tld:
                    self.ConfigData['TLDs'].append(tld)
                    self.ConfigData['TLDdict'][tld] = 1
    
    #--------------------------------------------------------------------------------
    
    #-----load DNS denylist from file-----
    def load_dns_denylist(self) -> None:
        dns_filepath = self.ConfigData['UpdateFile']['bind']['src_filepath']
        if not os.path.exists(dns_filepath):
            return
        if os.path.getsize(dns_filepath)==0:
            return
        with open(dns_filepath, 'r') as read_file:
            for host in read_file:
                self.ConfigData['DNSDenylist'][host.rstrip()] = 1
    
    #--------------------------------------------------------------------------------
    
    #-----load IP denylist from file-----
    def load_ip_denylist(self) -> None:
        ip_filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath']
        if not os.path.exists(ip_filepath):
            return
        if os.path.getsize(ip_filepath)==0:
            return
        with open(ip_filepath, 'r') as read_file:
            for ip in read_file:
                self.ConfigData['IPBlacklist'][ip.rstrip()] = 1

    #--------------------------------------------------------------------------------

    def load_hide_ip_list(self) -> None:
        ip_filepath = '/opt/zzz/data/hide_ips.txt'
        if not os.path.exists(ip_filepath):
            return
        if os.path.getsize(ip_filepath)==0:
            return
        with open(ip_filepath, 'r') as read_file:
            for ip in read_file:
                ip = ip.strip()
                if self.ip_util.is_ip(ip):
                    self.ConfigData['HideIPs'].add(ip)

    #--------------------------------------------------------------------------------
    
    #TODO: change to "select * from countries" ?
    #      watch for upper/lowercase issues in country codes
    def load_country_list(self) -> None:
        """ Load country list
        """
        self.ConfigData['IPdeny']['countries'] = []
        country_filename_regex = re.compile(r'\/([^\/]+)\.zone$')
        #-----only load countries if we have ipdeny files for them-----
        country_files = glob.glob(os.path.join(self.ConfigData['IPdeny']['ipv4']['src_dir'], '*.zone'))
        for filepath in sorted(country_files):
            # get the country code out of the path: /opt/zzz/data/ipdeny-ipv4/ch.zone
            # match = re.search(r'\/([^\/]+)\.zone$', filepath)
            match = country_filename_regex.search(filepath)
            if match:
                country_code = match.group(1)
                self.ConfigData['IPdeny']['countries'].append(country_code)
    
    #--------------------------------------------------------------------------------
    
    def load_official_country_list(self) -> None:
        """ Load the offical country list from JSON
        """
        self.ConfigData['OfficialCountries'] = {}
        country_json_data = '[{"Code": "ZZ", "Name": "TEST"}]'
        with open(self.ConfigData['DataFile']['CountryList'], 'r') as country_list_file:
            country_json_data = country_list_file.read()
        country_list = json.loads(country_json_data)
        for country_item in country_list:
            # self.ConfigData['OfficialCountries'].append(country_item['Code'])
            self.ConfigData['OfficialCountries'][country_item['Code']] = country_item['Name']
        #-----handle special cases (UK instead of GB, etc.)-----
        # https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Exceptional_reservations
        self.ConfigData['OfficialCountriesWithExceptions'] = self.ConfigData['OfficialCountries']
        self.ConfigData['OfficialCountriesWithExceptions']['UK'] = self.ConfigData['OfficialCountries']['GB']
        # self.ConfigData['OfficialCountriesWithExceptions']['SU'] = self.ConfigData['OfficialCountries']['RU']
        # self.ConfigData['OfficialCountriesWithExceptions']['AC'] = self.ConfigData['OfficialCountries']['SH']
    
    #--------------------------------------------------------------------------------
    
    def load_protected_country_list(self) -> None:
        """ Load protected country list for Settings
        """
        if (not self.conf_data_loaded) or self.conf_data_loaded['ProtectedCountries']=='':
            return
        
        countries = self.conf_data_loaded['ProtectedCountries'].upper().replace(' ', '').split(',')
        country_codes = self.ConfigData['OfficialCountries'].keys()
        for country in countries:
            #-----de-duplicate-----
            if country in self.ConfigData['ProtectedCountries']:
                continue
            #-----add only valid country codes-----
            if country in country_codes:
                self.ConfigData['ProtectedCountries'].append(country)
            else:
                print('invalid ProtectedCountries entry: ' + country)
    
    #--------------------------------------------------------------------------------
    
    def load_protected_tld_list(self) -> None:
        if (not self.conf_data_loaded) or (not self.conf_data_loaded.get('ProtectedTLDs', None)):
            return
        custom_tld_list = []
        for tld in self.conf_data_loaded['ProtectedTLDs']:
            tld = tld.replace(' ', '').upper()
            found_tld = self.ConfigData['TLDdict'].get(tld, 0)
            #-----add only valid TLD's-----
            if found_tld:
                custom_tld_list.append(tld)
            else:
                print('invalid ProtectedTLDs entry: ' + tld)
        if custom_tld_list:
            self.ConfigData['ProtectedTLDs'] = custom_tld_list
    
    #--------------------------------------------------------------------------------
    
    def load_vpn_users(self) -> None:
        self.ConfigData['VPNusers'] = []
        usernames = self.conf_data_loaded['VPNusers'].split(',')
        for username in usernames:
            self.ConfigData['VPNusers'].append(username)
    
    #--------------------------------------------------------------------------------
    
    def load_config_file(self) -> bool:
        if not os.access(self.ConfigFile, os.R_OK):
            return False
        with open(self.ConfigFile, 'r') as conf_file:
            try:
                self.conf_data_loaded = yaml.safe_load(conf_file)
            except yaml.YAMLError as e:
                print("ERROR: zzz.conf parsing error")
                if hasattr(e, 'problem_mark'):
                    mark = e.problem_mark
                    print("Config file error position: line={}, column={}".format(mark.line+1, mark.column+1))
                return False
        return True
    
    #--------------------------------------------------------------------------------
    
    def found_expected_keys(self) -> bool:
        expected_keys = ['CA', 'Domain', 'EnableMaxMind', 'IPv4', 'LogParserRowLimit', 'ProtectedCountries', 'ProtectedIPs', 'TimeZoneDisplay', 'VPNusers']
        found_all_keys = True
        for key in expected_keys:
            val = self.conf_data_loaded.get(key, None)
            if val is None:
                print(f'ERROR: missing config entry for "{key}"')
                found_all_keys = False
            elif val=='CA':
                CA_Default = val.get('Default', None)
                if not CA_Default:
                    print('ERROR: missing config entry for "CA: Default"')
                    found_all_keys = False
            elif val=='IPv4':
                IPv4_VPNserver = val.get('VPNserver', None)
                if not IPv4_VPNserver:
                    print('ERROR: missing config entry for "IPv4: VPNserver"')
                    found_all_keys = False
        return found_all_keys
    
    #--------------------------------------------------------------------------------
    
    # user-selectable ports are 1024-65535
    # reserved ports:
    #   Apache: 80, 443
    #   BIND: 53
    #   ICAP: 29999
    #   Squid: 29901, 29902, 29903, 29911, 29912, 29913
    #   SSH: 22
    def validate_ports(self, ports_to_check: list) -> bool:
        #-----check for non-integers or numbers outside the range-----
        for port in ports_to_check:
            if not port:
                return False
            if not port.isdigit():
                return False
            if len(port)>5:
                return False
            port_num = int(port)
            if not (1024 <= port_num <= 65535):
                return False
            if port_num in self.invalid_ports:
                return False
        
        #-----check for duplicates-----
        unique_ports = list(dict.fromkeys(ports_to_check))
        if len(unique_ports)<5:
            return False
        
        return True
    
    #--------------------------------------------------------------------------------

    def validate_favicon_line(self, line: str=None) -> bool:
        if not line:
            return False
        if not self.regex_favicon.match(line):
            return False
        return True
    
    def validate_favicon(self, favicon: dict) -> bool:
        # 'Favicon': {
        #     'use_custom': False,
        #     'line1': 'ZZZ',
        #     'line2': 'VPN',
        #     'line3': '',
        self.ConfigData['Favicon']['use_custom'] = False
        if not(favicon and isinstance(favicon, dict)):
            self.ConfigData['Favicon']['error'] = 'ERROR: invalid Favicon config'
            return False
        use_custom = favicon.get('use_custom', None)
        if not use_custom:
            self.ConfigData['Favicon']['error'] = 'ERROR: use_custom must be True or False'
            return False
        if use_custom.upper() not in self.boolean_values:
            self.ConfigData['Favicon']['error'] = 'ERROR: use_custom must be True or False'
            return False
        if use_custom.upper()=='FALSE':
            # not an error
            return False
        
        #-----apply data tests-----
        line1 = favicon.get('line1', None)
        line2 = favicon.get('line2', None)
        line3 = favicon.get('line3', None)
        if not self.validate_favicon_line(line1):
            self.ConfigData['Favicon']['error'] = 'ERROR: Favicon config line1 is invalid'
            return False
        self.ConfigData['Favicon']['line1'] = line1

        if not line2:
            # one good line is enough
            self.ConfigData['Favicon']['line2'] = ''
            self.ConfigData['Favicon']['line3'] = ''
            return True
        if not self.validate_favicon_line(line2):
            self.ConfigData['Favicon']['error'] = 'ERROR: Favicon config line2 is invalid'
            return False
        self.ConfigData['Favicon']['line2'] = line2

        if not line3:
            self.ConfigData['Favicon']['line3'] = ''
            return True
        if not self.validate_favicon_line(line3):
            self.ConfigData['Favicon']['error'] = 'ERROR: Favicon config line3 is invalid'
            return False
        self.ConfigData['Favicon']['line3'] = line3

        return True

    #--------------------------------------------------------------------------------

    # 15.4 GB total --> 8 GB used by system, 4 GB reserved as general free space, 3.4GB available for DB and iptables
    # returns number of MB available
    def diskspace_available(self) -> int:
        total, used, free = shutil.disk_usage('/')
        available = (total - (12*1024*1024*1024)) / (1024*1024)
        return int(available)

    #-----use default values if some tests fail-----
    # return: (bool, int) - pass/fail, database_megabytes
    def validate_diskspace_database(self, DiskSpace: dict, diskspace_available: int):
        DiskSpace_Database = DiskSpace.get('Database', None)
        if not DiskSpace_Database:
            print(f'DiskSpace_Database missing, using default value {self.ConfigData["DiskSpace"]["Database"]}')
            return True, self.ConfigData["DiskSpace"]["Database"]

        DiskSpace_Database = str(DiskSpace_Database)
        if not DiskSpace_Database.isdigit():
            print('DiskSpace_Database invalid, must be an integer')
            return False, 0

        database_megabytes = int(DiskSpace_Database)
        # more than 10,000MB might make the system too slow?
        config_diskspace_limit = 10000
        if config_diskspace_limit > diskspace_available:
            config_diskspace_limit = diskspace_available
        if database_megabytes<100 or database_megabytes>config_diskspace_limit:
            print(f'DiskSpace_Database invalid, must be between 100 and {config_diskspace_limit}')
            return False, 0

        self.ConfigData['DiskSpace']['Database'] = int(DiskSpace_Database)
        return True, database_megabytes

    #--------------------------------------------------------------------------------

    # return: (bool, int) - pass/fail, iptables_megabytes
    def validate_diskspace_iptables(self, DiskSpace: dict, diskspace_available: int):
        DiskSpace_IPtables = DiskSpace.get('IPtablesLogFiles', None)
        if not DiskSpace_IPtables:
            print(f'DiskSpace_IPtables missing, using default value {self.ConfigData["DiskSpace"]["IPtablesLogFiles"]}')
            return True, self.ConfigData["DiskSpace"]["IPtablesLogFiles"]

        DiskSpace_IPtables = str(DiskSpace_IPtables)
        if not DiskSpace_IPtables.isdigit():
            print('DiskSpace_IPtables invalid, must be an integer')
            return False, 0
        iptables_megabytes = int(DiskSpace_IPtables)

        # 1.5MB in 2 minutes is 0.75MB per minute
        # estimate 500MB for 720 minutes of logs with 1000 packets per minute
        # currently /etc/logrotate.d/zzz-iptables contains:
        #   rotate 360
        #   size 1M
        # with 1000 packets/min, this rotates about every 2 minutes on a busy router, with 1.3MB-1.5MB filesize
        # so 720 minutes of logs is about 500MB
        # currently minutes is fixed and not configurable
        packets_per_minute = self.ConfigData['LogPacketsPerMinute']
        mb_per_minute = 0.75 * packets_per_minute/1000
        minutes_of_logs = 720
        needed_megabytes = int(mb_per_minute * minutes_of_logs) + 1
        max_ppm_decimal = 1000*iptables_megabytes/(mb_per_minute*minutes_of_logs)
        max_LogPacketsPerMinute = int(max_ppm_decimal) + 1

        if iptables_megabytes>diskspace_available:
            print('DiskSpace_IPtables invalid, exceeds available disk space({diskspace_available} MB)')
            return False, 0
        if needed_megabytes>diskspace_available:
            print(f'{packets_per_minute} packets per minute will use {needed_megabytes} MB of disk space')
            print(f'this exceeds available disk space({diskspace_available} MB)')

        #TODO: option to auto-adjust the max number of files in logrotate.d/zzz-iptables
        #      based on the number of packets per minute
        #      require at least 20 minutes of data in case crons are delayed for a bit

        if self.test_mode:
            print(f'''needed_megabytes={needed_megabytes}
iptables_megabytes={iptables_megabytes}
diskspace_available={diskspace_available}
LogPacketsPerMinute={packets_per_minute}
max_LogPacketsPerMinute={max_LogPacketsPerMinute}
----------------
''')

        return True, iptables_megabytes

    #--------------------------------------------------------------------------------

    def validate_diskspace(self, DiskSpace: dict=None) -> bool:
        if not DiskSpace:
            return True

        diskspace_available = self.diskspace_available()
        db_result, database_megabytes = self.validate_diskspace_database(DiskSpace, diskspace_available)
        iptables_result, iptables_megabytes = self.validate_diskspace_iptables(DiskSpace, diskspace_available)
        if not db_result or not iptables_result:
            return False

        space_allocated = database_megabytes + iptables_megabytes
        if space_allocated > diskspace_available:
            print('ERROR: not enough free disk space. Allocate less space to the database and/or iptables log files')
            return False

        if self.test_mode:
            print(f'''database_megabytes={database_megabytes}
iptables_megabytes={iptables_megabytes}
diskspace_available={diskspace_available}
space_allocated={space_allocated}
''')

        return True

    #--------------------------------------------------------------------------------

    #TODO: finish adding tests here
    #      apply default values rather than erroring on bad data?
    #      accumulate all errors and print them all at once, only if a print_err param is True
    def validate_entries(self) -> bool:
        validated_all_keys = True
        
        #TODO: turn this back on when IPv6 is ready
        conf_data_IPv6_Activate = None
        # conf_data_IPv6_Activate = self.conf_data_loaded['IPv6'].get('Activate', None)
        if not conf_data_IPv6_Activate:
            conf_data_IPv6_Activate = 'FALSE'
        boolean_vars = {
            'EnableMaxMind': self.conf_data_loaded['EnableMaxMind'],
            'IPv6:Activate': conf_data_IPv6_Activate
        }
        for key in boolean_vars.keys():
            if boolean_vars[key].upper() not in self.boolean_values:
                print(f'{key} invalid, must be "True" or "False"')
                validated_all_keys = False
        
        # CA
        regex_pattern = r'^[A-Za-z0-9 ]+$'
        match = re.match(regex_pattern, self.conf_data_loaded['CA']['Default'])
        if not match:
            print('CA:Default invalid, must be only letters, numbers, and spaces')
            validated_all_keys = False
        
        # Domain
        regex_pattern = r'^services\.[a-z0-9]{1,60}\.zzz$'
        match = re.match(regex_pattern, self.conf_data_loaded['Domain'])
        if not match:
            print('Domain invalid, keep the name pattern as "services.newdomain.zzz"')
            print('  the "newdomain" part must be lowercase letters and numbers only, 60-character limit')
            validated_all_keys = False

        # LogPacketsPerMinute
        LogPacketsPerMinute = str(self.conf_data_loaded['LogPacketsPerMinute'])
        if LogPacketsPerMinute.isdigit():
            num = int(LogPacketsPerMinute)
            if num<1 or num>20000:
                print('LogPacketsPerMinute invalid, must be between 1 and 20000')
                validated_all_keys = False
            else:
                self.ConfigData['LogPacketsPerMinute'] = num
        else:
            print('LogPacketsPerMinute invalid, must be an integer')
            validated_all_keys = False

        # DiskSpace
        DiskSpace = self.conf_data_loaded.get('DiskSpace', None)
        if DiskSpace and isinstance(DiskSpace, dict):
            validated_all_keys = self.validate_diskspace(DiskSpace)

        # LogParserRowLimit
        LogParserRowLimit = str(self.conf_data_loaded['LogParserRowLimit'])
        if LogParserRowLimit.isdigit():
            num = int(LogParserRowLimit)
            if num<10 or num>100000:
                print('LogParserRowLimit invalid, must be between 10 and 100000')
                validated_all_keys = False
            else:
                self.ConfigData['LogParserRowLimit'] = num
        else:
            print('LogParserRowLimit invalid, must be an integer')
            validated_all_keys = False
        
        # OpenVPN config
        OpenVPN = self.conf_data_loaded.get('OpenVPN', None)
        if OpenVPN and isinstance(OpenVPN, dict):
            OpenVPN_MaxClients = OpenVPN.get('MaxClients', None)
            if OpenVPN_MaxClients:
                OpenVPN_MaxClients = str(OpenVPN_MaxClients)
                if OpenVPN_MaxClients.isdigit():
                    num = int(OpenVPN_MaxClients)
                    if num<1 or num>1000:
                        print('OpenVPN_MaxClients invalid, must be between 1 and 1000')
                        validated_all_keys = False
                    else:
                        self.ConfigData['OpenVPN']['MaxClients'] = num
                else:
                    print('OpenVPN_MaxClients invalid, must be an integer')
                    validated_all_keys = False
        
        # Ports - optional, correct range is (1024-65535), no duplicates
        ports = self.conf_data_loaded.get('Ports', None)
        if ports and isinstance(ports, dict):
            ports_openvpn = ports.get('OpenVPN', None)
            if ports_openvpn and isinstance(ports_openvpn, dict):
                ports_openvpn_dns = ports_openvpn.get('DNS', None)
                ports_openvpn_dns_icap = ports_openvpn.get('DNSICAP', None)
                ports_openvpn_dns_squid = ports_openvpn.get('DNSSquid', None)
                ports_openvpn_open = ports_openvpn.get('Open', None)
                ports_openvpn_open_squid = ports_openvpn.get('OpenSquid', None)
                ports_to_check = [ports_openvpn_dns, ports_openvpn_dns_icap, ports_openvpn_dns_squid, ports_openvpn_open, ports_openvpn_open_squid]
                if self.validate_ports(ports_to_check):
                    self.ConfigData['Ports']['OpenVPN']['dns'] = int(self.conf_data_loaded['Ports']['OpenVPN']['DNS'])
                    self.ConfigData['Ports']['OpenVPN']['dns-icap'] = int(self.conf_data_loaded['Ports']['OpenVPN']['DNSICAP'])
                    self.ConfigData['Ports']['OpenVPN']['dns-squid'] = int(self.conf_data_loaded['Ports']['OpenVPN']['DNSSquid'])
                    self.ConfigData['Ports']['OpenVPN']['open'] = int(self.conf_data_loaded['Ports']['OpenVPN']['Open'])
                    self.ConfigData['Ports']['OpenVPN']['open-squid'] = int(self.conf_data_loaded['Ports']['OpenVPN']['OpenSquid'])
                else:
                    print('OpenVPN Ports entry invalid, set 5 unique port numbers between 1024-65535')
                    print('   other ports not available: ' + ', '.join(self.invalid_ports))
                    validated_all_keys = False
        
        # ProtectedCountries - 1 or more country codes, CSV, uppercase
        regex_pattern = r'^([A-Z]{2}\,)*[A-Z]{2}$'
        match = re.match(regex_pattern, self.conf_data_loaded['ProtectedCountries'])
        if not match:
            print('ProtectedCountries invalid, use 2-letter country codes, comma-separated')
            validated_all_keys = False
        
        # TimeZoneDisplay
        # check if file exists: /usr/share/zoneinfo/America/Los_Angeles
        default_timezone_filepath = '/usr/share/zoneinfo/America/Los_Angeles'
        filepath = '/usr/share/zoneinfo/' + self.conf_data_loaded['TimeZoneDisplay']
        if os.path.exists(filepath):
            self.ConfigData['TimeZoneDisplay'] = self.conf_data_loaded['TimeZoneDisplay']
        elif os.path.exists(default_timezone_filepath):
            self.ConfigData['TimeZoneDisplay'] = default_timezone_filepath
            print(f'TimeZoneDisplay invalid: {filepath}\n    using default timezone file: {default_timezone_filepath}')
        else:
            print(f'TimeZoneDisplay invalid, timezone file not found: {filepath}')
            validated_all_keys = False
        
        # VPNusers - no duplicates
        # min username length 3, max length 50
        # limit characters to letters, numbers, and "-"
        # usernames should not start or end with "-"
        user_list = self.conf_data_loaded['VPNusers'].split(',')
        unique_user_list = list(dict.fromkeys(user_list))
        if len(user_list) != len(unique_user_list):
            print('VPNusers invalid: no duplicates allowed')
            validated_all_keys = False
        match = self.regex_VPNusers.match(self.conf_data_loaded['VPNusers'])
        if not match:
            print('VPNusers invalid:')
            print('    use 3-50 character usernames, comma-separated')
            print('    limit characters to letters, numbers, and "-"')
            print('    usernames should not start or end with "-"')
            validated_all_keys = False

        #-----favicon errors: just print a warning and turn off custom favicon-----
        favicon = self.conf_data_loaded.get('Favicon', None)
        if self.validate_favicon(favicon):
            self.ConfigData['Favicon']['use_custom'] = True

        return validated_all_keys
    
    #TODO: finish this
    # Tests:
    #   is the file a valid YAML format?
    #   field length limits?
    #   verify required params
    # Required Params:
    #     CA:
    #         Default: 'Zzz CA', regex "\w" + "-"
    #     Domain: 'services.zzz.zzz', case-insensitive? (lowercase it)
    #     IPv6:
    #         Activate: 'True' or 'False', case-insensitive?
    #         VPNserver: 'AUTODETECT' or 'valid IP' or 'valid domain name', case-insensitive
    #     ProtectedCountries: 'US', case-insensitive CSV list (1 or more, cannot be empty)
    #     TimeZoneDisplay: 'America/Los_Angeles', ***case-sensitive
    #     VPNserver: 'AUTODETECT' or 'valid IP' or 'valid domain name', case-insensitive
    #     VPNusers: 'ZZZuser1,ZZZuser2,ZZZuser3', CSV list (1 or more, cannot be empty), regex "\w" + "-"
    def configtest(self) -> bool:
        """ Make sure the zzz.conf file is correctly formatted
        """
        #-----make sure this loads without crashing-----
        result_load_config_file = False
        try:
            result_load_config_file = self.load_config_file()
        except:
            # function crashed? not a valid config
            result_load_config_file = False
        if not result_load_config_file:
            return False
        
        result_found_expected_keys = False
        try:
            result_found_expected_keys = self.found_expected_keys()
        except:
            # function crashed? not a valid config
            result_found_expected_keys = False
        if not result_found_expected_keys:
            return False
        
        result_validate_entries = False
        try:
            result_validate_entries = self.validate_entries()
        except:
            # function crashed? not a valid config
            result_validate_entries = False
        if not result_validate_entries:
            return False
        
        return True
    
    #--------------------------------------------------------------------------------
    
    def is_valid(self) -> bool:
        return self.ConfigData['DataValid']
    
    #--------------------------------------------------------------------------------
    
    #TODO: finish this
    # trim leading/trailing chars in each string: spaces, tabs, CR, LF
    # convert to lowercase fields: Domain
    # convert to uppercase: ProtectedCountries
    # convert to first-letter-uppercase: Activate
    def config_cleanup(self) -> None:
        """ Auto-repair defects in the config file entries
        """
        pass
