#-----manages iptables configs-----

#TODO: break UpdateFile.generate_iptables_file into multiple functions in IPtables and IPset

import socket

#-----package with all the Zzz modules-----
import zzzevpn

class IPtables:
    'iptables functions'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    ip_util: zzzevpn.IPutil = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None

    filter_table_list = ['INPUT', 'FORWARD', 'OUTPUT']
    valid_chains = ['CUSTOMRULES', 'PREROUTING']
    valid_protocols = ['tcp', 'udp']
    log_packets_per_minute = 1000

    # set to True to write to a test directory instead of the real directory
    test_mode = False

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
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
        self.log_packets_per_minute = self.ConfigData['LogPacketsPerMinute']

    #--------------------------------------------------------------------------------

    # logfiles rotated once per minute, only if they exceed 1MB in size
    # assume 225 bytes per log entry
    # config vars:
    #   DiskSpace.IPtablesLogFiles=2048
    #   LogPacketsPerMinute=10000
    # bytes per minute: 225 * 10000 = 2.25MB
    # calculate max logfiles: 2048 / 2.25 = 910 files
    def make_iptables_logrotate_config(self):
        if self.ConfigData['LogRotate']['NumFilesError']:
            print(self.ConfigData['LogRotate']['NumFilesError'])

        read_filepath = self.ConfigData['UpdateFile']['iptables']['logrotate_template']
        template_data = {
            'numfiles': self.ConfigData['LogRotate']['NumFiles'],
        }
        zzz_template = zzzevpn.ZzzTemplate(self.ConfigData, self.db, self.util)
        data_to_write = zzz_template.load_template(filepath=read_filepath, data=template_data)
        
        write_filepath = self.ConfigData['UpdateFile']['iptables']['logrotate_dst']
        with open(write_filepath, 'w') as write_file:
            write_file.write(data_to_write)

    #--------------------------------------------------------------------------------

    #-----routes traffic thru the physical network interface(s)-----
    def make_router_config(self):
        # this comments-out the iptables-zzz.conf line to disable the iptables squid redirect for the open-squid VPN
        disable_open_squid = '# '
        if self.settings.is_setting_enabled('test_server_squid'):
            disable_open_squid = ''
        read_filepath = self.ConfigData['UpdateFile']['iptables']['router_config_template']
        template_data = {
            'disable_open_squid': disable_open_squid,
            'class_b_open_squid': self.ConfigData['IPv4']['iptables']['class-b']['open-squid'],
            'class_b_dns': self.ConfigData['IPv4']['iptables']['class-b']['dns'],
            'class_b_dns_squid': self.ConfigData['IPv4']['iptables']['class-b']['dns-squid'],
            'class_b_open': self.ConfigData['IPv4']['iptables']['class-b']['open'],
            'class_b_dns_icap': self.ConfigData['IPv4']['iptables']['class-b']['dns-icap'],
            # eth0, ens5, etc.
            'network_interface_internal': self.ConfigData['PhysicalNetworkInterfaces']['internal'],
            # open-squid/dns-squid port 80 --> Squid-http
            'port_squid_http': self.ConfigData['Ports']['Squid']['http'],
            # open-squid/dns-squid port 443 --> Squid-https
            'port_squid_https': self.ConfigData['Ports']['Squid']['https'],
            # dns-icap port 80 --> SquidICAP-http
            'port_squid_icap_http': self.ConfigData['Ports']['SquidICAP']['http'],
            # dns-icap port 443 --> SquidICAP-https
            'port_squid_icap_https': self.ConfigData['Ports']['SquidICAP']['https'],
        }
        zzz_template = zzzevpn.ZzzTemplate(self.ConfigData, self.db, self.util)
        data_to_write = zzz_template.load_template(filepath=read_filepath, data=template_data)
        
        write_filepath = self.ConfigData['UpdateFile']['iptables']['router_config_dst']
        with open(write_filepath, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------

    def is_rule_enabled(self, setting_name: str) -> bool:
        return self.settings.is_setting_enabled(setting_name, self.settings.SettingTypeIPtablesRules)

    #--------------------------------------------------------------------------------

    #TODO: finish this or remove it
    # iptables -t mangle --append PREROUTING --source  192.168.1.0/24 -j MARK --set-mark 1
    # build-config.py should have built ipsets to always allow from self.ConfigData['IPtablesCustomRules']['ProtectedIPs']
    def mangle_packets_config(self):
        #-----mark traffic for tc to provide QoS-----
        # if
        # custom_rules += ':MARKACCEPT -\n'

        mangle_chain = '*mangle\n'
        mangle_chain += ':PREROUTING ACCEPT\n'
        mangle_chain += ':INPUT ACCEPT\n'
        mangle_chain += ':FORWARD ACCEPT\n'
        mangle_chain += ':OUTPUT ACCEPT\n'
        mangle_chain += ':POSTROUTING ACCEPT\n'

        header_prefixes = self.make_custom_rules_prefix('PREROUTING')
        bytes_per_sec = self.settings.IPtablesRules['bytes_per_sec']
        packets_per_sec = self.settings.IPtablesRules['packets_per_sec']
        # mangle_chain += f'{header_prefix} -m limit --limit {bps_limit}/sec -j MARK --set-mark 1\n'
        # mangle_chain += f'{header_prefix} -m limit --limit {pps_limit}/sec -j MARK --set-mark 1\n'

        mangle_chain += 'COMMIT\n\n'

        return mangle_chain

    #--------------------------------------------------------------------------------

    #TODO: translate dst_ports from a CSV to a list, break up ranges into individual ports
    #   this should happen in Settings.py
    def make_custom_rules_prefix(self, chain_name: str) -> list:
        if chain_name not in self.valid_chains:
            return []

        dst_ports_ranges = self.util.standalone.whitespace_to_commas(self.settings.IPtablesRules['dst_ports'])
        result = self.util.standalone.translate_ranges_to_set(dst_ports_ranges.split(','), 1, 65535)
        dports = result['values']
        if len(dports) > 15:
            # limit of 15 ports for now, from the ConfigData
            # more than 15 ports will require multiple rules, due to iptables limitations
            dports = dports[:15]
            print('WARNING: too many destination ports, only using the first 15')
        dports_csv = ','.join(str(dport) for dport in sorted(dports))

        #TODO: use self.settings.IPtablesRules['KEY']

        bytes_per_sec = self.settings.IPtablesRules['bytes_per_sec']
        packets_per_sec = self.settings.IPtablesRules['packets_per_sec']

        protocols_to_use = []
        if self.is_rule_enabled('block_tcp'):
            protocols_to_use.append('tcp')
        if self.is_rule_enabled('block_udp'):
            protocols_to_use.append('udp')

        #TODO: user-selected direction may reverse source and destination
        vpn_ip_range = self.ConfigData['AppInfo']['VpnIPRange']
        header_prefixes = []
        for protocol in protocols_to_use:
            header_prefix = f'''-A {chain_name} -p {protocol} -m multiport --dports {dports_csv} --destination {vpn_ip_range} ! --source {vpn_ip_range}'''
            header_prefixes.append(header_prefix)
        return header_prefixes

    #--------------------------------------------------------------------------------

    def make_rules_by_protocol(self, header_prefixes, rule_details):
        rules = []
        for header_prefix in header_prefixes:
            rule = f'''{header_prefix} {rule_details}\n'''
            rules.append(rule)
        return rules

    #--------------------------------------------------------------------------------

    def make_rate_limit_rules(self, header_prefixes, rate_limit_name, hashlimit_above, hashlimit_burst):
        rules = []

        #-----expire the hashlimit after 3 hours-----
        # entries_expire_ms = 3 * self.util.standalone.MILLISECONDS_PER_HOUR
        entries_expire_minutes = self.util.get_int_safe(self.settings.IPtablesRules['throttle_expire'])
        entries_expire_ms = entries_expire_minutes * self.util.standalone.MILLISECONDS_PER_MINUTE

        #TODO: user-selected direction may change "srcip" to "dstip", also "srcmask" to "dstmask"
        for header_prefix in header_prefixes:
            rule = f'''{header_prefix} -m hashlimit --hashlimit-name {rate_limit_name} --hashlimit-mode srcip --hashlimit-srcmask 32 --hashlimit-above {hashlimit_above} --hashlimit-burst {hashlimit_burst} --hashlimit-htable-expire {entries_expire_ms} --hashlimit-rate-interval 1 -j LOGDROP\n'''
            rules.append(rule)
        return rules

    def make_bytes_per_sec_rules(self, header_prefixes):
        rules = []
        bytes_per_sec = self.util.get_int_safe(self.settings.IPtablesRules['bytes_per_sec'])
        if not bytes_per_sec:
            # zero disables this rule
            return rules

        #TODO: make this a setting
        hashlimit_burst = bytes_per_sec * 5

        rules = self.make_rate_limit_rules(header_prefixes, 'BPSLIMIT', f'{bytes_per_sec}b/second', hashlimit_burst)
        return rules

    def make_packets_per_sec_rules(self, header_prefixes):
        rules = []
        packets_per_sec = self.util.get_int_safe(self.settings.IPtablesRules['packets_per_sec'])
        if not packets_per_sec:
            # zero disables this rule
            return rules

        packets_per_minute = packets_per_sec * 60
        #TODO: make this a setting
        hashlimit_burst = packets_per_sec * 5

        rules = self.make_rate_limit_rules(header_prefixes, 'PPSLIMIT', f'{packets_per_minute}/minute', hashlimit_burst)
        return rules

    #--------------------------------------------------------------------------------

    #-----build the custom rules-----
    # iptables_rules flags: block_non_allowed_ips, block_nonzero_tos, block_tcp, block_udp, enable_auto_blocking
    # iptables_rules strings/ints: allow_ips, block_low_ttl, bytes_per_sec, dst_ports, packets_per_sec, throttle_expire
    # if TCP and UDP protocols are both selected, we need to make two rules, one for each protocol
    def make_custom_rules_header(self):
        block_low_ttl = self.settings.IPtablesRules['block_low_ttl']
        block_nonzero_tos = self.is_rule_enabled('block_nonzero_tos')
        vpn_ip_range = self.ConfigData['AppInfo']['VpnIPRange']

        custom_rules = ':CUSTOMRULES -\n'
        custom_rules_footer = '-A CUSTOMRULES -j LOGACCEPT\n'
        # ports and IP ranges are the same for all custom rules
        header_prefixes = self.make_custom_rules_prefix('CUSTOMRULES')

        #TODO: just merge these in with the main allow list?
        # accept_allowed_ips = f'--destination {vpn_ip_range} --match set --match-set custom-allow-ip src\n'

        # drop all traffic not on the allowed list
        block_non_allowed_ips = self.is_rule_enabled('block_non_allowed_ips')
        rule_drop_non_allowed = ''
        if block_non_allowed_ips:
            for header_prefix in header_prefixes:
                rule_drop_non_allowed += f'''{header_prefix} -j LOGDROP\n'''
            custom_rules += rule_drop_non_allowed
            #-----no need to continue if we're blocking all non-allowed IP's-----
            # just add the footer and return
            # custom_rules += custom_rules_footer
            # return custom_rules

        #-----drop packets with excessive traffic-----
        rule_drop_excessive_pps = self.make_packets_per_sec_rules(header_prefixes)
        if rule_drop_excessive_pps:
            custom_rules += ''.join(rule_drop_excessive_pps)
        rule_drop_excessive_bps = self.make_bytes_per_sec_rules(header_prefixes)
        if rule_drop_excessive_bps:
            custom_rules += ''.join(rule_drop_excessive_bps)

        # drop packets with TTL under the specified value, unless it's zero
        if block_low_ttl:
            for header_prefix in header_prefixes:
                custom_rules += f'''{header_prefix} -m ttl --ttl-lt {block_low_ttl} -j LOGDROP\n'''
        # block TOS (Type of Service) packets with nonzero values
        if block_nonzero_tos:
            for header_prefix in header_prefixes:
                # TOS: first, accept incoming matched dports with TOS=0x00
                custom_rules += f'''{header_prefix} -m tos --tos 0x00 -j LOGACCEPT\n'''
                # TOS: next, drop incoming matched dports with all other TOS values
                custom_rules += f'''{header_prefix} -j LOGDROP\n'''

        # fake command? iptables -A INPUT -p tcp -m ip --frag 0x4000/0x4000 -j DROP

        # finally, accept everything else
        custom_rules += custom_rules_footer

        #-----mark traffic for tc to provide QoS-----
        # if
        # custom_rules += ':MARKACCEPT -\n'

        return custom_rules

    #--------------------------------------------------------------------------------

    #-----iptables config file header-----
    def make_iptables_header(self):
        enable_auto_blocking = self.is_rule_enabled('enable_auto_blocking')
        header = '#-----Zzz app auto-generated custom IP blocking rules-----\n\n'
        if enable_auto_blocking:
            # this goes first since the "*mangle" chains get configured separately from "*filter"
            header += self.mangle_packets_config()

        header += '*filter\n'
        header += ':INPUT ACCEPT\n'
        header += ':FORWARD ACCEPT\n'
        header += ':OUTPUT ACCEPT\n'

        #-----new chain to log and reject-----
        header += ':LOGREJECT -\n'
        header += f'-A LOGREJECT -m limit --limit {self.log_packets_per_minute}/min -j LOG --log-prefix "zzz blocked " --log-level 7\n'
        # make the browser give up retrying, so pages load faster
        header += '-A LOGREJECT -j REJECT -p tcp --reject-with tcp-reset\n'
        # block all other non-TCP requests
        header += '-A LOGREJECT -j REJECT\n'

        #-----new chain to log and drop-----
        header += ':LOGDROP -\n'
        header += f'-A LOGDROP -m limit --limit {self.log_packets_per_minute}/min -j LOG --log-prefix "zzz blocked " --log-level 7\n'
        header += '-A LOGDROP -j DROP\n'

        #-----new chain to log and accept, used by allowlist, stops further processing-----
        header += ':LOGACCEPT -\n'
        header += f'-A LOGACCEPT -m limit --limit {self.log_packets_per_minute}/min -j LOG --log-prefix "zzz accepted " --log-level 7\n'
        header += '-A LOGACCEPT -j ACCEPT\n'

        #-----new chain to apply custom rules-----
        # -m multiport --dports 6672,61455,61457,61456,61458
        # port 6672, all 10.* VPN IP's, TOS=0x00, accept
        if enable_auto_blocking:
            header += self.make_custom_rules_header()

        return header

    #-----iptables config file header-----
    def make_iptables_country_header(self):
        header = '#-----Zzz app auto-generated COUNTRY IP blocking rules-----\n\n'
        header += '*filter\n'
        return header
    
    #--------------------------------------------------------------------------------
    
    #-----iptables config file footer-----
    def make_iptables_footer(self):
        footer = 'COMMIT\n'
        return footer

    #--------------------------------------------------------------------------------

    #-----drop unacceptable packets with LOGDROP-----
    # ports 137-139 NetBIOS - tends to cause ICMP rejection replies
    def make_logdrop_entries(self) -> str:
        logdrop_entries = []
        for filter_table in self.filter_table_list:
            for protocol in ['tcp', 'udp']:
                logdrop_entries.append(f'-A {filter_table} -p {protocol} -m multiport --dports 137:139 -j LOGDROP\n')
        return ''.join(logdrop_entries)

    #--------------------------------------------------------------------------------

    ##################################################
    # combine iptables FILTER entries into a single config file to import
    #   header
    #   allow-list
    #   deny-list
    #   country-block
    #   log accepted
    #   footer
    ##################################################
    
    #-----enable logging of traffic-----
    # -I OUTPUT 1 -j LOG --log-prefix "iptables blocked: "
    # -A INPUT -d 192.168.100.10 -p tcp -m tcp --dport 80 -j LOG --log-prefix "[10010] REQUEST Port 80: " --log-level 7
    # MATCH command: --match-set
    #   (used for logging blocked packets)
    # NOT MATCH command: ! --match-set
    #   (used for logging accepted packets)
    # entry_start = '-I {} 1 -s {} -m set --match-set {} dst -j LOG --log-prefix "iptables blocked: " --log-level 7'
    #
    # NEW: send rejected stuff to the LOGREJECT chain
    #   -A INPUT -s 10.6.0.0/15 -m set --match-set blacklist dst -j LOGREJECT
    #   -A {} -s {} -m set --match-set {} dst -j LOGREJECT
    def make_iptables_logreject_entry(self, filter_table, host_ip, ipset_name, src_cidr, make_host_ip_entry=True):
        if not src_cidr:
            src_cidr = self.ConfigData['AppInfo']['BlockedIPRange']
        ipset_entry_src = '--append {} --source {} --match set --match-set {} dst -j LOGREJECT\n'
        #-----switch this back to LOGREJECT if TCP connections keep retrying instead of stopping immediately-----
        ipset_entry_dst = '--append {} --destination {} --match set --match-set {} src -j LOGREJECT\n'
        # ipset_entry_dst = '--append {} --destination {} --match set --match-set {} src -j LOGDROP\n'
        
        #-----non-squid connections-----
        ipset_entry = ipset_entry_src.format(filter_table, src_cidr, ipset_name)
        ipset_entry += ipset_entry_dst.format(filter_table, src_cidr, ipset_name)
        
        #-----when we're going thru squid, the source IP is different-----
        if make_host_ip_entry:
            ipset_entry += ipset_entry_src.format(filter_table, host_ip, ipset_name)
            ipset_entry += ipset_entry_dst.format(filter_table, host_ip, ipset_name)
        return ipset_entry
    
    #-----accept and log anything on the allowlist-----
    # private_IP=10.0.0.0/12
    # src=private_IP, dst=LIST_ENTRY, log & accept
    # src=LIST_ENTRY, dst=private_IP, log & accept
    def make_iptables_allowlist_entry(self, filter_table, host_ip):
        ipset_name = 'allow-ip'
        
        #-----allow both directions-----
        ipset_entry_src = '--append {} --source {} --match set --match-set {} dst -j LOGACCEPT\n'
        ipset_entry_dst = '--append {} --destination {} --match set --match-set {} src -j LOGACCEPT\n'
        
        #-----non-squid connections-----
        ipset_entry = ipset_entry_src.format(filter_table, self.ConfigData['AppInfo']['VpnIPRange'], ipset_name)
        ipset_entry += ipset_entry_dst.format(filter_table, self.ConfigData['AppInfo']['VpnIPRange'], ipset_name)
        
        #-----when we're going thru squid, the source IP is different-----
        ipset_entry += ipset_entry_src.format(filter_table, host_ip, ipset_name)
        ipset_entry += ipset_entry_dst.format(filter_table, host_ip, ipset_name)
        
        return ipset_entry
    
    #-----log accepted traffic-----
    # simple log-everything rule:
    #    -A INPUT -m limit --limit 1000/min -j LOG --log-prefix "zzz accepted " --log-level 7
    #TODO: need more complex rule(s) to rule-out internal IP's?
    #      maybe only if src and dst are both internal?
    #      reduce useless logging where practical
    #      may need a static ipset with a list of internal IP's
    def make_iptables_logaccept_entry(self, filter_table):
        enable_auto_blocking = self.is_rule_enabled('enable_auto_blocking')
        if enable_auto_blocking:
            # apply custom rules if enabled
            # CUSTOMRULES will jump to LOGACCEPT/LOGREJECT/LOGDROP as needed
            return f'-A {filter_table} -j CUSTOMRULES\n'
        return f'-A {filter_table} -m limit --limit {self.log_packets_per_minute}/min -j LOG --log-prefix "zzz accepted " --log-level 7\n'
    
    #--------------------------------------------------------------------------------
    
    #TODO: not used anymore?
    #   replaced by make_iptables_logreject_entry(), make_iptables_allowlist_entry(), and make_iptables_logaccept_entry()
    #-----an iptables-ipset entry is 4 lines per filter table-----
    # this works with ipsets
    # -m set --match-set IPSET_NAME src
    # ipset_name is either "blacklist" or "countries"
    # 1/23/2021:
    #   accept all local traffic (src ipset "allow")
    #       src=10.0.0.0/8, dst=10.0.0.0/8
    #       src=172.30.0.141, dst=10.0.0.0/8 (note that the localhost IP is a var, not hardcoded)
    #   block incoming traffic also, but only from outside the VPN
    #       reverse src and dst
    #       for src, exclude VPN traffic
    def make_iptables_ipset_entry(self, filter_table, host_ip, ipset_name):
        ipset_entry = '-A {} -s {} -m set --match-set {} dst -j REJECT -p tcp --reject-with tcp-reset\n'.format(filter_table, self.ConfigData['AppInfo']['BlockedIPRange'], ipset_name)
        ipset_entry += '-A {} -s {} -m set --match-set {} dst -j REJECT\n'.format(filter_table, self.ConfigData['AppInfo']['BlockedIPRange'], ipset_name)
        #-----when we're going thru squid, the source IP is different-----
        ipset_entry += '-A {} -s {} -m set --match-set {} dst -j REJECT -p tcp --reject-with tcp-reset\n'.format(filter_table, host_ip, ipset_name)
        ipset_entry += '-A {} -s {} -m set --match-set {} dst -j REJECT\n'.format(filter_table, host_ip, ipset_name)
        
        return ipset_entry
    
    #--------------------------------------------------------------------------------
    
    #-----format the iptables denylist config file-----
    # make_iptables_config
    def make_iptables_denylist(self, new_settings=None):
        #-----only the daemon can use this function, not apache-----
        #if not self.util.running_as_root():
            #TODO - log an error here
            #return

        #-----option to pass in settings so we don't have to look them up-----
        if new_settings is None:
            self.settings.get_settings()
        else:
            self.settings = new_settings

        src_cidr = self.ConfigData['AppInfo']['BlockedIPRange']
        if self.settings.is_setting_enabled('block_custom_ip_always'):
            src_cidr = self.ConfigData['AppInfo']['VpnIPRange']
        # src_cidr_dns_icap = self.ConfigData['AppInfo']['BlockedIPRangeICAP']

        host_ip = socket.gethostbyname(self.ConfigData['AppInfo']['Hostname'])
        file_data = ''
        for filter_table in self.filter_table_list:
            #-----record blocked IP's to logs-----
            file_data += self.make_iptables_logreject_entry(filter_table, host_ip, 'blacklist', src_cidr)
        #-----footer is not needed, conf file will be assembled by update_iptables.sh-----
        # file_data += self.make_iptables_footer()
        filepath = self.ConfigData['UpdateFile']['iptables']['dst_filepath']
        
        with open(filepath, 'w') as write_file:
            write_file.write(file_data)
    
    #--------------------------------------------------------------------------------
    
    #-----install iptables main config, blacklist, and countries configs-----
    # don't run this for blacklist-only updates, just do IPset.install_blacklist()
    def install_iptables_config(self):
        # must be root to do this
        # get blocked country list from Settings
        # get the config file data
        # write the config file
        # re-install iptables config with a subprocess
        # blacklist file:
        #   self.ConfigData['UpdateFile']['iptables']['dst_filepath']
        # after running make_iptables_denylist(), run this to install the updates:
        #   /etc/iptables/update_iptables.sh
        #-----only the daemon can use this function, not apache-----
        #if not self.util.running_as_root():
            #TODO - log an error here
            #return
        return self.util.run_script('/etc/iptables/update_iptables.sh')
    
    #--------------------------------------------------------------------------------
    
    #-----check settings, 12 iptables entries per country selected-----
    def make_iptables_countries(self, new_settings=None):
        #-----option to pass in settings so we don't have to look them up-----
        if new_settings is None:
            self.settings.get_settings()
        else:
            self.settings = new_settings
        host_ip = socket.gethostbyname(self.ConfigData['AppInfo']['Hostname'])
        
        #-----set this to cover all VPN's if the Settings box is checked "Apply country-IP blocks to all traffic"-----
        src_cidr = self.ConfigData['AppInfo']['BlockedIPRange']
        if self.settings.is_setting_enabled('block_country_ip_always'):
            src_cidr = self.ConfigData['AppInfo']['VpnIPRange']
        
        #-----write iptables countries config-----
        #   no ACCEPT headers, because the blacklist file has that already
        #   headers not needed at all, conf file will be assembled by update_iptables.sh
        # data_to_write = self.make_iptables_country_header()
        data_to_write = ''
        if self.settings.SettingsData['blocked_country']:
            #-----one set of iptables rules for all countries, using one big ipset-----
            for filter_table in self.filter_table_list:
                #-----record blocked IP's to logs-----
                data_to_write += self.make_iptables_logreject_entry(filter_table, host_ip, 'countries', src_cidr)
        #-----footer is not needed, conf file will be assembled by update_iptables.sh-----
        # data_to_write += self.make_iptables_footer()
        
        filepath = self.ConfigData['UpdateFile']['iptables']['dst_countries_filepath']
        with open(filepath, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------
    
    def make_iptables_allowlist(self, new_settings=None):
        #-----option to pass in settings so we don't have to look them up-----
        if new_settings is None:
            self.settings.get_settings()
        else:
            self.settings = new_settings
        host_ip = socket.gethostbyname(self.ConfigData['AppInfo']['Hostname'])
        
        #-----this is the first file in the list of appended files, so put a header at the top-----
        # install_iptables_config() calls the script that combines the files
        data_to_write = self.make_iptables_header() + self.make_logdrop_entries()
        
        for filter_table in self.filter_table_list:
            data_to_write += self.make_iptables_allowlist_entry(filter_table, host_ip)
        
        #-----write iptables allowlist config-----
        filepath = self.ConfigData['UpdateFile']['iptables']['dst_allowlist_filepath']
        with open(filepath, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------
    
    def make_iptables_log_accept(self):
        data_to_write = ''
        for filter_table in self.filter_table_list:
            data_to_write += self.make_iptables_logaccept_entry(filter_table)
        
        #-----write iptables log_accept config-----
        filepath = self.ConfigData['UpdateFile']['iptables']['dst_log_accepted_filepath']
        with open(filepath, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------
    
    ###############################################
    # IPv6 - requires ip6tables, separate entries #
    ###############################################
    
    #-----IPv6 - format the entire ip6tables config file-----
    def make_ip6tables_config(self):
        #-----only the daemon can use this function, not apache-----
        #if not self.util.running_as_root():
            #TODO - log an error here
            #return
        host_ip = self.ConfigData['IPv6']['VPNserver']
        file_data = self.make_iptables_header()
        for filter_table in self.filter_table_list:
            file_data += self.make_iptables_ipset_entry(filter_table, host_ip, 'blacklist-ipv6')
        #-----footer is not needed, conf file will be assembled by update_ip6tables.sh-----
        filepath = self.ConfigData['UpdateFile']['ip6tables']['dst_filepath']
        with open(filepath, 'w') as write_file:
            write_file.write(file_data)
    
    #-----install ip6tables main config, allowlist, denylist, and countries configs-----
    # don't run this for blacklist-only updates, just do IPset.install_blacklist_ipv6()
    def install_ip6tables_config(self):
        #-----only the daemon can use this function, not apache-----
        #if not self.util.running_as_root():
            #TODO - log an error here
            #return
        return self.util.run_script('/etc/iptables/update_ip6tables.sh')
    
    def make_ip6tables_countries(self, new_settings=None):
        #-----option to pass in settings so we don't have to look them up-----
        if new_settings is None:
            self.settings.get_settings()
        else:
            self.settings = new_settings
        #-----Config should have looked-up the IP when it loaded-----
        host_ip = self.ConfigData['IPv6']['VPNserver']
        
        #-----write iptables countries config-----
        #   no ACCEPT headers, because the blacklist file has that already
        #   headers not needed at all, conf file will be assembled by update_ip6tables.sh
        data_to_write = ''
        if self.settings.SettingsData['blocked_country']:
            for filter_table in self.filter_table_list:
                data_to_write += self.make_iptables_ipset_entry(filter_table, host_ip, 'countries-ipv6')
        #-----footer is not needed, conf file will be assembled by update_iptables.sh-----
        
        filepath = '/etc/iptables/ip6-countries.conf'
        with open(filepath, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------

