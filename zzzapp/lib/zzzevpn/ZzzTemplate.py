#-----Template Processing Module-----
# makes output based on templates
# apps/features supported:
#   squid
#   openvpn
#   BIND
#   WSGI
#   WSGI - html

import os
import pprint
import re
import shutil

#-----import modules from the lib directory-----
# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.Config
# import zzzevpn.DB
# import zzzevpn.Util
import zzzevpn

class ZzzTemplate:
    'ZzzTemplate'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    
    template_file_content = ''
    
    # calculate ipv6 values below (IP64:10:8:0:0/96, etc.)
    # UDP is best, but is sometimes blocked by ISP's
    openvpn_server_config = {
        'open-squid': { # 10.9.0.*
            # this server is mostly for testing
            'FILENAME': 'server-squid.conf',
            'DHCP_OPTION_IPV4': '10.9.0.1',
            'DHCP_OPTION_IPV6': 'IP64:10:9:0:1',
            'IPP_FILE': 'ipp-squid.txt',
            'OPENVPN_LOG': 'openvpn-squid-status.log',
            'PORT': '39055',

            #TODO: use TCP so that this can be a backup when the other UDP servers are blocked
            #      (protocol flag in zzz.conf or Settings?)
            # 'PROTO': 'tcp',
            'PROTO': 'udp',

            'SERVER_IPV4_SUBNET': '10.9.0.0 255.255.255.0', # /24
            'SERVER_IPV6_SUBNET': '', # /96
        },
        'dns': { # 10.6.0.*
            'FILENAME': 'server-dns.conf',
            'DHCP_OPTION_IPV4': '10.6.0.1',
            'DHCP_OPTION_IPV6': 'IP64:10:6:0:1',
            'IPP_FILE': 'ipp-dns.txt',
            'OPENVPN_LOG': 'openvpn-status-dns.log',
            'PORT': '39077',
            'PROTO': 'udp',
            'SERVER_IPV4_SUBNET': '10.6.0.0 255.255.255.0', # /24
            'SERVER_IPV6_SUBNET': '', # /96
        },
        'dns-icap': { # 10.5.0.*
            'FILENAME': 'server-icap.conf',
            'DHCP_OPTION_IPV4': '10.5.0.1',
            'DHCP_OPTION_IPV6': 'IP64:10:5:0:1',
            'IPP_FILE': 'ipp-icap.txt',
            'OPENVPN_LOG': 'openvpn-icap-status.log',
            'PORT': '39102',
            'PROTO': 'udp',
            'SERVER_IPV4_SUBNET': '10.5.0.0 255.255.255.0', # /24
            'SERVER_IPV6_SUBNET': '', # /96
        },
        'dns-squid': { # 10.7.0.*
            'FILENAME': 'server-filtered.conf',
            'DHCP_OPTION_IPV4': '10.7.0.1',
            'DHCP_OPTION_IPV6': 'IP64:10:7:0:1',
            'IPP_FILE': 'ipp-filtered.txt',
            'OPENVPN_LOG': 'openvpn-filtered-status.log',
            'PORT': '39094',
            'PROTO': 'udp',
            'SERVER_IPV4_SUBNET': '10.7.0.0 255.255.255.0', # /24
            'SERVER_IPV6_SUBNET': '', # /96
        },
        'open': { # 10.8.0.*
            'FILENAME': 'server.conf',
            'DHCP_OPTION_IPV4': '10.8.0.1',
            'DHCP_OPTION_IPV6': 'IP64:10:8:0:1',
            'IPP_FILE': 'ipp.txt',
            'OPENVPN_LOG': 'openvpn-status.log',
            'PORT': '39066',
            'PROTO': 'udp',
            'SERVER_IPV4_SUBNET': '10.8.0.0 255.255.255.0', # /24
            'SERVER_IPV6_SUBNET': '', # /96
        },
    }
    
    # only 4 basic types of openssl configs:
    #   root CA
    #   intermediate CA (openvpn, squid)
    #   server cert
    #   client cert
    # sample output: extendedKeyUsage = clientAuth, serverAuth
    # upcoming Google requirements:
    #   https://www.chromium.org/Home/chromium-security/root-ca-policy/moving-forward-together/
    #   proposed maximum subordinate CA certificate validity: 3 years
    #     if enforced, this might affect the Squid-Top and OpenVPN intermediate certs?
    #   proposed webserver certificate maximum validity: 90 days
    openssl_config = {
        'root-ca': {
            'dst_file': 'openssl-easyrsa-root-ca.cnf',
            'extendedKeyUsage': 'codeSigning, timeStamping, OCSPSigning, serverAuth, clientAuth',
        },
        'int-ca': {
            'dst_file': 'openssl-easyrsa-int-ca.cnf',
            'extendedKeyUsage': 'serverAuth, clientAuth',
        },
        'server-cert': {
            'dst_file': 'openssl-easyrsa-server-cert.cnf',
            'extendedKeyUsage': 'serverAuth',
        },
        'client-cert': {
            'dst_file': 'openssl-easyrsa-client-cert.cnf',
            'extendedKeyUsage': 'clientAuth',
        },
    }
    
    easyrsa_pki_config = {
        'Default': {
            'EASYRSA_PKI': 'pki',
            'EASYRSA_CA_EXPIRE': '10000',
        },
        'OpenVPN': {
            'EASYRSA_CA_EXPIRE': '5000',
            'EASYRSA_PKI': 'pki-openvpn-int',
        },
        'Squid': {
            'EASYRSA_CA_EXPIRE': '700',
            'EASYRSA_PKI': 'pki-squid',
        },
        'Squid-Top': {
            'EASYRSA_CA_EXPIRE': '5000',
            'EASYRSA_PKI': 'pki-squid-top',
        },
    }
    # selected_openssl_config = easyrsa_cert_config[name]['openssl_config']
    # openssl_config[selected_openssl_config]
    easyrsa_cert_config = {
        'Default': {
            'dst_file': 'vars-zzz',
            'EASYRSA_PKI': easyrsa_pki_config['Default']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['Default']['EASYRSA_CA_EXPIRE'],
            
            # need to adjust this for each intermediate CA signing
            'EASYRSA_CERT_EXPIRE': '5000',
            'openssl_config': 'root-ca',
        },
        'Apache': {
            'dst_file': 'vars-apache',
            'EASYRSA_PKI': easyrsa_pki_config['OpenVPN']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['OpenVPN']['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': '90',
            'openssl_config': 'server-cert',
        },
        'OpenVPN-CA': {
            'dst_file': 'vars-openvpn-ca',
            'EASYRSA_PKI': easyrsa_pki_config['OpenVPN']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['OpenVPN']['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': '5000',
            'openssl_config': 'int-ca',
        },
        'OpenVPN-Server': {
            # for user certs
            'dst_file': 'vars-openvpn-server',
            'EASYRSA_PKI': easyrsa_pki_config['OpenVPN']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['OpenVPN']['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': '5000',
            'openssl_config': 'server-cert',
        },
        'OpenVPN-User': {
            # for user certs
            'dst_file': 'vars-openvpn-user-', # append username below
            'EASYRSA_PKI': easyrsa_pki_config['OpenVPN']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['OpenVPN']['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': '5000',
            'openssl_config': 'client-cert',
        },
        #TODO: update this to load under Squid-Top
        'Squid': {
            'dst_file': 'vars-squid-ca',
            'EASYRSA_PKI': easyrsa_pki_config['Squid']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['Squid']['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': '397',
            'openssl_config': 'int-ca',
        },
        'Squid-Top': {
            'dst_file': 'vars-squid-top-ca',
            'EASYRSA_PKI': easyrsa_pki_config['Squid-Top']['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': easyrsa_pki_config['Squid-Top']['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': '700',
            'openssl_config': 'int-ca',
        },
    }
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None) -> None:
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
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self) -> None:
        self.template_file_content = ''
        self.openvpn_server_config['dns']['PORT'] = str(self.ConfigData['Ports']['OpenVPN']['dns'])
        self.openvpn_server_config['dns-icap']['PORT'] = str(self.ConfigData['Ports']['OpenVPN']['dns-icap'])
        self.openvpn_server_config['dns-squid']['PORT'] = str(self.ConfigData['Ports']['OpenVPN']['dns-squid'])
        self.openvpn_server_config['open']['PORT'] = str(self.ConfigData['Ports']['OpenVPN']['open'])
        self.openvpn_server_config['open-squid']['PORT'] = str(self.ConfigData['Ports']['OpenVPN']['open-squid'])
    
    #--------------------------------------------------------------------------------
    
    # defaults to using the Config templates directory
    #   filename: NAME.template
    def load_template(self, name: str=None, filepath: str=None, data: dict=None) -> str:
        self.template_file_content = ''
        template_filepath = ''
        if name:
            template_filepath = f'''{self.ConfigData['Directory']['Templates']}/{name}.template'''
        elif filepath:
            template_filepath = filepath
        if not template_filepath:
            err_str = 'ERROR: template name/filepath not specified'
            print(err_str)
            return err_str
        
        if not os.path.isfile(template_filepath):
            err_str = 'ERROR: template not found ' + template_filepath
            print(err_str)
            return err_str
        with open(template_filepath, 'r') as read_file:
            self.template_file_content = read_file.read()
        if data and self.template_file_content:
            return self.template_file_content.format(**data)
        return ''
    
    #--------------------------------------------------------------------------------
    
    # 5 servers: server, server-dns, server-squid (open w/squid), server-filtered (DNS + squid), server-icap (DNS + squid w/ICAP)
    # template: /opt/zzz/config/openvpn/server.conf.template
    # SRC: /etc/openvpn/ca.crt
    #      /etc/openvpn/ta.key
    #      /etc/openvpn/vpn.zzz.zzz.crt
    #      /etc/openvpn/vpn.zzz.zzz.key
    #      /etc/openvpn/vpn.zzz.zzz_pem_pass.txt
    #
    # DST: /etc/openvpn/server
    # must be root to do this
    def make_openvpn_server_configs(self) -> None:
        src_filepath = self.ConfigData['Directory']['Config'] + '/openvpn/server.conf.template'
        dst_dir = self.ConfigData['Directory']['OpenVPNserver']

        for config_type in self.openvpn_server_config.keys():
            server_protocol = self.openvpn_server_config[config_type]['PROTO']
            if server_protocol=='tcp':
                server_protocol += '-server'
            filename = self.openvpn_server_config[config_type]['FILENAME']
            dst_filepath = f'{dst_dir}/server/{filename}'
            template_data = {
                'PORT': self.openvpn_server_config[config_type]['PORT'],
                'PROTO': server_protocol,
                'SERVER_IPV4_SUBNET': self.openvpn_server_config[config_type]['SERVER_IPV4_SUBNET'],
                'SERVER_IPV6_SUBNET': '', # no IPv6 for now
                'IPP_FILE': self.openvpn_server_config[config_type]['IPP_FILE'],
                'DHCP_OPTION_IPV6': '', # no IPv6 for now
                'DHCP_OPTION_IPV4': self.openvpn_server_config[config_type]['DHCP_OPTION_IPV4'],
                'MaxClients': self.ConfigData['OpenVPN']['MaxClients'],
                'OPENVPN_LOG': self.openvpn_server_config[config_type]['OPENVPN_LOG'],
                'SERVER_PASS_OPENVPN': self.ConfigData['UpdateFile']['easyrsa']['server-pass-openvpn'],
            }
            data_to_write = self.load_template(filepath=src_filepath, data=template_data)
            self.util.save_output(dst_filepath, data_to_write)
    
    #--------------------------------------------------------------------------------
    
    #TODO: better file formats
    #      {servername}_{username}_{config_type}.ovpn
    def write_openvpn_client_config(self, username: str, config_type: str, template_data: dict) -> None:
        template_data['server_port'] = self.openvpn_server_config[config_type]['PORT']
        template_data['PROTO'] = self.openvpn_server_config[config_type]['PROTO']
        if template_data['PROTO']=='tcp':
            template_data['PROTO'] += '-client'

        src_filepath = self.ConfigData['Directory']['Config'] + '/openvpn/openvpn-client.template'
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        
        dst_dir = self.ConfigData['Directory']['OpenVPNclient']
        dst_filepath = f'{dst_dir}/{username}_{config_type}.ovpn'
        
        self.util.save_output(dst_filepath, data_to_write)
        os.chmod(dst_filepath, 0o600)
        shutil.chown(dst_filepath, 'ubuntu', 'ubuntu')
    
    # 5 clients per user: USERNAME_open, USERNAME_open-squid, USERNAME_dns, USERNAME_dns-icap, USERNAME_dns-squid
    # client config types: open, open-squid, dns, dns-icap, dns-squid
    # template: /opt/zzz/config/openvpn/client.ovpn.template
    # must be root to do this
    def make_openvpn_client_configs(self) -> None:
        ta_filepath = self.ConfigData['Directory']['OpenVPNserver'] + '/ta.key'
        ta_data = self.util.get_filedata(ta_filepath)
        
        #-----get minimized certs instead of fulltext certs-----
        #   /opt/zzz/data/ssl-public
        #   the minimized certs must have already been generated by output_minimal_cert_data.sh
        default_ca_cert_data = self.util.get_filedata(self.ConfigData['PKI']['root-ca-cert'])
        openvpn_ca_cert_data = self.util.get_filedata(self.ConfigData['PKI']['openvpn-ca-cert'])
        openvpn_pki_dir = self.ConfigData['Directory']['PKI']['OpenVPN']

        template_data = {
            'ca_cert': f'{default_ca_cert_data}\n{openvpn_ca_cert_data}',
            'ta_key': ta_data,
            'client_cert_public': '',
            'client_cert_private': '',
            'server_name': self.ConfigData['IPv4']['VPNserver'],
            'server_port': '',
        }
        
        for username in self.ConfigData['VPNusers']:
            client_cert_public_filepath = f'{openvpn_pki_dir}/issued/{username}.crt'
            template_data['client_cert_public'] = self.util.get_filedata(client_cert_public_filepath)
            
            client_cert_private_filepath = f'{openvpn_pki_dir}/private/{username}.key'
            template_data['client_cert_private'] = self.util.get_filedata(client_cert_private_filepath)
            
            for config_type in self.openvpn_server_config.keys():
                self.write_openvpn_client_config(username, config_type, template_data)
        
        template_data = {}
    
    #--------------------------------------------------------------------------------
    
    def make_squid_configs(self) -> None:
        config_output = ''
        template_filepath = self.ConfigData['UpdateFile']['squid']['config_template']
        
        #-----squid server-----
        ssl_bump_disabled = '''
ssl_bump peek bump_step1 all
ssl_bump peek bump_step2 all
ssl_bump splice bump_step3 all
        '''

        #TEST - nopeeksites ACL
        ssl_bump_disabled = '''
ssl_bump splice bump_step1 nopeeksites
ssl_bump splice bump_step2 nopeeksites
ssl_bump splice bump_step3 nopeeksites
ssl_bump peek bump_step1 !nopeeksites
ssl_bump peek bump_step2 !nopeeksites
ssl_bump splice bump_step3 !nopeeksites
        '''

        template_data = {
            'access_log': self.ConfigData['Directory']['SquidAccess'] + '/access.log',
            'cache_log': '/var/log/squid/cache.log',
            'icap_activate': 'off',
            'icap_log': 'none',
            'pid_filename': '/var/run/squid.pid',
            'ssl_bump': ssl_bump_disabled,
            'ssl_db_cache': '/var/cache/squid/ssl_db',
            'visible_hostname': self.ConfigData['AppInfo']['Domain'],
            
            'icap_port': str(self.ConfigData['Ports']['ICAP']),
            'non_intercept_port': str(self.ConfigData['Ports']['Squid']['non-intercept']),
            'http_port': str(self.ConfigData['Ports']['Squid']['http']),
            'https_port': str(self.ConfigData['Ports']['Squid']['https']),
        }
        dst_filepath = self.ConfigData['UpdateFile']['squid']['config_squid_dst']
        data_to_write = self.load_template(filepath=template_filepath, data=template_data)
        #-----write new config-----
        with open(dst_filepath, 'w') as write_file:
            write_file.write(data_to_write)
        
        #-----squid-icap server-----
        ssl_bump_enabled = '''
ssl_bump peek bump_step1 all
ssl_bump peek bump_step2 nobumpsites
ssl_bump splice bump_step3 nobumpsites
ssl_bump stare bump_step2
ssl_bump bump bump_step3
        '''
        icap_template_data = {
            'access_log': self.ConfigData['Directory']['SquidAccess'] + '/access-icap.log',
            'cache_log': '/var/log/squid/cache-icap.log',
            'icap_activate': 'on',
            'icap_log': '/var/log/squid/icap-new.log',
            'pid_filename': '/var/run/squid-icap.pid',
            'ssl_bump': ssl_bump_enabled,
            'ssl_db_cache': '/var/cache/squid_icap/ssl_db',
            'visible_hostname': 'icap-' + self.ConfigData['AppInfo']['Domain'],
            
            'icap_port': str(self.ConfigData['Ports']['ICAP']),
            'non_intercept_port': str(self.ConfigData['Ports']['SquidICAP']['non-intercept']),
            'http_port': str(self.ConfigData['Ports']['SquidICAP']['http']),
            'https_port': str(self.ConfigData['Ports']['SquidICAP']['https']),
        }
        dst_filepath = self.ConfigData['UpdateFile']['squid']['config_squid_icap_dst']
        data_to_write = self.load_template(filepath=template_filepath, data=icap_template_data)
        #-----write new config-----
        with open(dst_filepath, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------
    
    # 110_configure-apache.sh:
    # cp $REPOS_APACHE_DIR/zzz-site-http.conf $APACHE_CONF_DIR/sites-available
    #   /opt/zzz/config/httpd/zzz-site-http.conf
    #   /etc/apache2/sites-available
    # cp $REPOS_APACHE_DIR/zzz-site-https.conf $APACHE_CONF_DIR/sites-available
    #   /opt/zzz/config/httpd/zzz-site-https.conf
    #   /etc/apache2/sites-available
    def make_apache_configs(self) -> None:
        dst_dir = self.ConfigData['Directory']['ApacheSites']
        
        # HTTP server
        src_filepath = self.ConfigData['Directory']['Config'] + '/httpd/zzz-site-http.conf.template'
        dst_filepath = f'{dst_dir}/zzz-site-http.conf'
        template_data = {
            'ApacheAllCerts': self.ConfigData['PKI']['apache_all_certs'],
            'Domain': self.ConfigData['AppInfo']['Domain'],
            'IPv4Internal': self.ConfigData['IPv4']['Internal'],
            'VpnIPRange': self.ConfigData['AppInfo']['VpnIPRange'],
        }
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
        
        # HTTPS server
        src_filepath = self.ConfigData['Directory']['Config'] + '/httpd/zzz-site-https.conf.template'
        dst_filepath = f'{dst_dir}/zzz-site-https.conf'
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
        
        #-----zzz config JS-----
        app_domain = self.ConfigData['AppInfo']['Domain']
        data_to_write = f'''
            var app_domain = '{app_domain}';
            var zzz_https_url = 'https://' + app_domain;
        '''
        dst_filepath = self.ConfigData['UpdateFile']['zzz']['config_js']
        self.util.save_output(dst_filepath, data_to_write)
    
    #--------------------------------------------------------------------------------
    
    # 090_configure-bind.sh:
    # cp $NAMED_DIR/null.zone.file /etc/bind
    #   /opt/zzz/config/named/
    #   /etc/bind
    # Files to Process:
    #   /opt/zzz/config/named/named-zzz.conf.template
    #     /etc/bind/named-zzz.conf
    #   /opt/zzz/config/named/zzz.zzz.zone.file.template
    #     /etc/bind/zzz.zzz.zone.file
    #     /etc/bind/$ZZZ_DOMAIN_EXTRACTED.zone.file
    #   /opt/zzz/config/named/null.zone.file.template
    #     /etc/bind/null.zone.file
    def make_bind_configs(self, should_block_tld_always: bool=False, should_block_country_tlds_always: bool=False, enable_test_server_dns_block: bool=False, custom_dst_dir: str='') -> None:
        dst_dir = self.ConfigData['Directory']['BIND']
        if custom_dst_dir:
            if custom_dst_dir not in self.ConfigData['Directory']['BINDallowedCustomDirs']:
                print('error - bad directory')
                return
            dst_dir = custom_dst_dir
        
        # "services.test.zzz" --> "test"
        #-----get domain from subdomain matching TLD-----
        DomainWithoutTLD = self.util.get_zzz_domain_without_tld()
        if not DomainWithoutTLD:
            print('ERROR: failed to extract DomainWithoutTLD from config Domain')
            return
        
        #-----named-zzz.conf - links to zone file-----
        src_filepath = self.ConfigData['Directory']['Config'] + '/named/named-zzz.conf.template'
        dst_filepath = f'{dst_dir}/named-zzz.conf'
        template_data = {
            'DomainWithoutTLD': DomainWithoutTLD,
        }
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
        
        #-----null zone file-----
        src_filepath = self.ConfigData['Directory']['Config'] + '/named/null.zone.file.template'
        dst_filepath = f'{dst_dir}/null.zone.file'
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
        
        #-----zzz zone file-----
        src_filepath = self.ConfigData['Directory']['Config'] + '/named/zzz.zzz.zone.file.template'
        dst_filepath = f'{dst_dir}/{DomainWithoutTLD}.zzz.zone.file'
        template_data = {
            'DomainWithoutTLD': DomainWithoutTLD,
            'IPV6_AAAA_RECORD': '',
        }
        # only make a custom zone file if we're not using the default domain
        if DomainWithoutTLD!='zzz':
            data_to_write = self.load_template(filepath=src_filepath, data=template_data)
            self.util.save_output(dst_filepath, data_to_write)
        
        #TODO: remove this when installer (090_configure-bind.sh) no longer needs it
        #-----also make the default filename with the same content due to installer soft link issues
        dst_filepath = f'{dst_dir}/zzz.zzz.zone.file'
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
        
        #-----named.conf.options file-----
        src_filepath = self.ConfigData['UpdateFile']['bind']['named_options_template_filepath']
        dst_filepath = f'{dst_dir}/named.conf.options'
        block_country_tlds_always = ''
        if should_block_country_tlds_always:
            block_country_tlds_always = 'include "/etc/bind/settings/countries.conf";'
        block_tld_always = ''
        if should_block_tld_always:
            block_tld_always = 'include "/etc/bind/settings/tlds.conf";'
        open_squid_entry = self.util.generate_class_c(self.openvpn_server_config['open-squid']['DHCP_OPTION_IPV4'])
        open_squid_filtered = '#'
        open_squid_unfiltered = open_squid_entry
        if enable_test_server_dns_block:
            open_squid_filtered = open_squid_entry
            open_squid_unfiltered = '#'
        template_data = {
            'BLOCK_COUNTRY_TLDS_ALWAYS': block_country_tlds_always,
            'BLOCK_TLD_ALWAYS': block_tld_always,
            
            'IPV4_DNS': self.ConfigData['IPv4']['NameServers'][0],
            'IPV4_DNS2': self.ConfigData['IPv4']['NameServers'][1],
            
            # 10.5 open-squid
            'IPV4_CLASS_C_OPEN_SQUID': open_squid_entry,
            'IPV4_CLASS_C_OPEN_SQUID_FILTERED': open_squid_filtered,
            'IPV4_CLASS_C_OPEN_SQUID_UNFILTERED': open_squid_unfiltered,
            'DHCP_OPTION_IPV4_OPEN_SQUID': self.openvpn_server_config['open-squid']['DHCP_OPTION_IPV4'],
            # 10.6 dns
            'IPV4_CLASS_C_DNS': self.util.generate_class_c(self.openvpn_server_config['dns']['DHCP_OPTION_IPV4']),
            'DHCP_OPTION_IPV4_DNS': self.openvpn_server_config['dns']['DHCP_OPTION_IPV4'],
            # 10.9 dns-icap
            'IPV4_CLASS_C_DNS_ICAP': self.util.generate_class_c(self.openvpn_server_config['dns-icap']['DHCP_OPTION_IPV4']),
            'DHCP_OPTION_IPV4_DNS_ICAP': self.openvpn_server_config['dns-icap']['DHCP_OPTION_IPV4'],
            # 10.7 dns-squid
            'IPV4_CLASS_C_DNS_SQUID': self.util.generate_class_c(self.openvpn_server_config['dns-squid']['DHCP_OPTION_IPV4']),
            'DHCP_OPTION_IPV4_DNS_SQUID': self.openvpn_server_config['dns-squid']['DHCP_OPTION_IPV4'],
            # 10.8 open
            'IPV4_CLASS_C_OPEN': self.util.generate_class_c(self.openvpn_server_config['open']['DHCP_OPTION_IPV4']),
            'DHCP_OPTION_IPV4_OPEN': self.openvpn_server_config['open']['DHCP_OPTION_IPV4'],
            
            'IPV6_IP6TABLES_SUBNET_64': '',
            'IPV6_DNS': self.ConfigData['IPv6']['NameServers'][0],
            'IPV6_DNS2': self.ConfigData['IPv6']['NameServers'][1],
            
            'IPV6_IP6TABLES_5': '',
            'IPV6_IP6TABLES_6': '',
            'IPV6_IP6TABLES_7': '',
            'IPV6_IP6TABLES_8': '',
            'IPV6_IP6TABLES_9': '',

            'CONFIG_DIRECTORY': dst_dir,
        }
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
    
    #--------------------------------------------------------------------------------
    
    def make_easyrsa_req_cn(self, config_name: str, username: str='') -> str:
        # usernames
        if config_name=='OpenVPN-User':
            return username
        
        # CA names
        elif config_name=='Default':
            return self.ConfigData['AppInfo']['CA']['Default']
        elif config_name=='OpenVPN-CA':
            return self.ConfigData['AppInfo']['CA']['OpenVPN']
        elif config_name=='Squid':
            return self.ConfigData['AppInfo']['CA']['Squid']
        elif config_name=='Squid-Top':
            return self.ConfigData['AppInfo']['CA']['Squid-Top']
        
        # domain names
        elif config_name=='OpenVPN-Server':
            # return 'vpn.zzz.zzz'
            return self.ConfigData['AppInfo']['VpnServerName']
        elif config_name=='Apache':
            return self.ConfigData['AppInfo']['Domain']
        
        return 'TEST'
    
    def openssl_write_file(self, selected_openssl_config: str) -> None:
        src_filepath = self.ConfigData['Directory']['Config'] + '/easyrsa/openssl-easyrsa.cnf.template'
        easyrsa_vars_dir = self.ConfigData['Directory']['EasyRSAvars']
        template_data = {
            'extendedKeyUsage': self.openssl_config[selected_openssl_config]['extendedKeyUsage'],
        }
        dst_filepath = easyrsa_vars_dir + '/' + self.openssl_config[selected_openssl_config]['dst_file']
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
    
    def easyrsa_write_file(self, config_name: str, username: str='') -> None:
        src_filepath = self.ConfigData['Directory']['Config'] + '/easyrsa/vars.template'
        easyrsa_vars_dir = self.ConfigData['Directory']['EasyRSAvars']
        selected_openssl_config = self.easyrsa_cert_config[config_name]['openssl_config']
        openssl_filename = self.openssl_config[selected_openssl_config]['dst_file']
        openssl_filepath = f'{easyrsa_vars_dir}/{openssl_filename}'
        openssl_safe_filepath = f'{easyrsa_vars_dir}/safe-{openssl_filename}'
        
        #TEST
        # default_filename = 'openssl-easyrsa.cnf'
        # openssl_filepath = f'{pki_dir}/{default_filename}'
        # openssl_safe_filepath = f'{easyrsa_vars_dir}/safe-{openssl_filename}'
        
        template_data = {
            'EASYRSA_PKI': self.easyrsa_cert_config[config_name]['EASYRSA_PKI'],
            'EASYRSA_CA_EXPIRE': self.easyrsa_cert_config[config_name]['EASYRSA_CA_EXPIRE'],
            'EASYRSA_CERT_EXPIRE': self.easyrsa_cert_config[config_name]['EASYRSA_CERT_EXPIRE'],
            'EASYRSA_REQ_CN': self.make_easyrsa_req_cn(config_name, username),
            # $EASYRSA_PKI/openssl-easyrsa.cnf
            'EASYRSA_SSL_CONF': openssl_filepath,
            # $EASYRSA_PKI/safessl-easyrsa.cnf
            'EASYRSA_SAFE_CONF': openssl_safe_filepath,
        }
        
        dst_filepath = easyrsa_vars_dir + '/' + self.easyrsa_cert_config[config_name]['dst_file'] + username
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
    
    #TODO: option to not exceed the 32-bit linux date? 19 January 2038
    #   https://en.wikipedia.org/wiki/Year_2038_problem
    #-----make the vars config files used by easyrsa-----
    def make_easyrsa_vars(self) -> None:
        # make openssl config files that are used below
        for selected_openssl_config in self.openssl_config.keys():
            self.openssl_write_file(selected_openssl_config)
        
        # easyrsa files include: current users, users to add, users to delete
        easyrsa_all_users = self.ConfigData['VPNusers']
        users_to_delete = self.util.get_delete_users_list()
        if users_to_delete:
            easyrsa_all_users.extend(users_to_delete)
        
        # make easyrsa vars files
        for config_name in self.easyrsa_cert_config.keys():
            if config_name=='OpenVPN-User':
                for username in easyrsa_all_users:
                    self.easyrsa_write_file(config_name, username)
            else:
                self.easyrsa_write_file(config_name)
    
    #--------------------------------------------------------------------------------
    
    #-----turn the user list into a textfile usable by the user-creating shell scripts-----
    def make_users_file(self) -> None:
        data_to_write = '\n'.join(self.ConfigData['VPNusers']) + '\n'
        dst_filepath = '/opt/zzz/data/openvpn_users.txt'
        self.util.save_output(dst_filepath, data_to_write)
    
    #--------------------------------------------------------------------------------
    
    def make_redis_config(self) -> None:
        src_filepath = self.ConfigData['UpdateFile']['redis']['config_template']
        dst_filepath = self.ConfigData['UpdateFile']['redis']['config_dst']
        template_data = {
            'port': self.ConfigData['Ports']['redis'],
        }
        data_to_write = self.load_template(filepath=src_filepath, data=template_data)
        self.util.save_output(dst_filepath, data_to_write)
    
    #--------------------------------------------------------------------------------
