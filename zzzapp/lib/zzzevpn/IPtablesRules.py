#-----parse raw IP log data-----

import datetime
import os
import re
import time

#-----package with all the Zzz modules-----
import zzzevpn

class IPtablesRules:
    'process iptables rules'

    ConfigData: dict = None
    db: zzzevpn.DB = None
    ipset: zzzevpn.IPset = None
    iptables: zzzevpn.IPtables = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None

    # IPs/CIDRs that are exempt from the rules
    # EX: private IPs, the VPN server IP, IPs entered in the web page
    exempted_ips = set()

    #--------------------------------------------------------------------------------

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
        #-----get Config-----
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
        #-----use the given DB connection or get a new one-----
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
        self.ipset = zzzevpn.IPset(self.ConfigData, self.db, self.util, self.settings)
        self.iptables = zzzevpn.IPtables(self.ConfigData, self.db, self.util, self.settings)

        #TEST
        self.iptables.test_mode = True

        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        self.exempted_ips = set(self.ConfigData['ProtectedIPs'])

    #--------------------------------------------------------------------------------

    #-----validate and cleanup iptables rules-----
    def validate_settings(self) -> dict:
        validation_result = {
            'error_msg': [],
            'success': True,

            'invalid_ips': set(),
            'invalid_ports': set(),

            'valid_ips': set(),
            'valid_ports': set(),
        }

        #-----ports list-----
        dst_ports = self.settings.IPtablesRules['dst_ports']
        if not dst_ports:
            validation_result['error_msg'].append('ERROR: No destination ports specified')
            validation_result['success'] = False
            return validation_result
        translation_result = self.translate_ranges_str_to_set(dst_ports, 65535, field_name='dst_ports')
        ports_result = self.util.standalone.validate_ports(translation_result['numbers'])
        validation_result['valid_ports'] = ports_result['valid_ports']
        validation_result['invalid_ports'] = ports_result['invalid_ports']
        if translation_result['error_msg']:
            validation_result['error_msg'].extend(translation_result['error_msg'])
        if ports_result['error_msg']:
            validation_result['error_msg'].extend(ports_result['error_msg'])

        #-----IPs list-----
        ips_csv = self.util.standalone.whitespace_to_commas(self.settings.IPtablesRules['allow_ips'])
        ip_result = self.util.ip_util.validate_ips(ips_csv.split(','))
        validation_result['valid_ips'] = ip_result['valid']
        if ip_result['invalid']:
            validation_result['invalid_ips'] = ip_result['invalid']
            validation_result['error_msg'].extend(ip_result['error_msg'])

        #-----save dropped values to a separate list-----
        if translation_result['dropped_values']:
            validation_result['dropped_values'] = translation_result['dropped_values']

        if validation_result['error_msg']:
            validation_result['success'] = False

        return validation_result

    #--------------------------------------------------------------------------------

    #-----insert a service request to update the settings-----
    def queue_settings_update(self):
        self.db.insert_service_request('iptables', 'update_iptables_rules')
        self.util.work_available(1)

    #--------------------------------------------------------------------------------

    # 1-5,22,32-35 --> {1,2,3,4,5,22,32,33,34,35}
    def translate_ranges_str_to_set(self, ranges_csv: str, valid_max: int, invalid_values: set={}, field_name='') -> dict:
        translation_result = { 'numbers': set(), 'dropped_values': set(), 'error_msg': [] }

        # data cleanup
        ranges_csv = self.util.standalone.whitespace_to_commas(ranges_csv)

        result = self.util.standalone.translate_ranges_to_set(ranges_csv.split(','), 1, valid_max, invalid_values=invalid_values)
        if result['values']:
            translation_result['numbers'].update(result['values'])
        if result['dropped_values']:
            dropped_values = ', '.join([str(x) for x in result['dropped_values']])
            error_msg = f'''WARNING: dropping invalid values from {field_name}: {dropped_values}'''
            translation_result['error_msg'].append(error_msg)
        if result['error_msg']:
            error_msg = f'''ERROR in {field_name}:\n{result['error_msg']}'''
            translation_result['error_msg'].append(error_msg)

        return translation_result

    #--------------------------------------------------------------------------------

    #-----update the iptables configs and load them into the OS-----
    # must be run as root, usually called by the daemon
    def implement_iptables_rules(self):
        # check if root
        if not self.util.is_running_as_root():
            return False

        # iptables_rules flags: block_non_allowed_ips, block_nonzero_tos, block_tcp, block_udp, enable_auto_blocking

        # iptables_rules strings/ints: allow_ips, block_low_ttl, bytes_per_sec, dst_ports, packets_per_sec, throttle_expire

        self.ipset.update_allowlist()
        self.ipset.install_allowlist()

        # these will be handled by IPtables.make_custom_rules_header()
        # make_iptables_allowlist() --> make_iptables_header() --> make_custom_rules_header()
        # block_low_ttl = self.settings.IPtablesRules['block_low_ttl']
        # bytes_per_sec = self.settings.IPtablesRules['bytes_per_sec']
        # dst_ports = self.settings.IPtablesRules['dst_ports']
        # packets_per_sec = self.settings.IPtablesRules['packets_per_sec']
        # throttle_expire = self.settings.IPtablesRules['throttle_expire']
        # traffic_direction = self.settings.IPtablesRules['traffic_direction']

        # write the iptables rules to a file, using the template
        self.iptables.make_iptables_allowlist()

        #-----call the iptables updater script-----
        self.iptables.install_iptables_config()

        return True
    #--------------------------------------------------------------------------------
