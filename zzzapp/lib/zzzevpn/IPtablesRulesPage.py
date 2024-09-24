#-----view/edit iptables rules-----

import copy
import json
import os.path
import pprint

#-----package with all the Zzz modules-----
import zzzevpn

class IPtablesRulesPage:
    'view/edit iptables rules'

    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    iptables_rules: zzzevpn.IPtablesRules = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None

    IPtablesRulesHTML = {}
    service_name = 'iptables'

    # default - return only the table rows, not the entire HTML page
    return_page_header = True
    errors = []

    invalid_ports = {range(1, 1024)} # SSH should not be blocked
    checkbox_fields = [ 'block_non_allowed_ips', 'block_nonzero_tos', 'block_tcp', 'block_udp', 'enable_auto_blocking', ]
    allowed_post_params = [ 'action', 'json_data', ]

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
        self.iptables_rules = zzzevpn.IPtablesRules(self.ConfigData, self.db, self.util, self.settings)
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)
        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        self.return_page_header = True
        self.errors = []

        #-----prevent the user from accidentally cutting off access to SSH or openvpn-----
        # ports less than 1024 are reserved for root
        openvpn_ports = {
            self.ConfigData['Ports']['OpenVPN']['dns'],
            self.ConfigData['Ports']['OpenVPN']['dns-icap'],
            self.ConfigData['Ports']['OpenVPN']['dns-squid'],
            self.ConfigData['Ports']['OpenVPN']['open'],
            self.ConfigData['Ports']['OpenVPN']['open-squid']
        }
        self.invalid_ports.update(openvpn_ports)

        #-----prep the HTML values-----
        openvpn_ports_str = [str(i) for i in openvpn_ports]
        self.IPtablesRulesHTML = {
            'ports_not_allowed': '1-1023,' + ','.join(openvpn_ports_str),
        }

    #--------------------------------------------------------------------------------

    #-----process POST data-----
    # always return JSON
    def handle_post(self, environ, request_body_size):
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')

        self.init_vars()

        #-----get post data-----
        # include all limit_fields
        data = self.webpage.load_data_from_post(environ, request_body_size, self.allowed_post_params)

        #-----validate data-----
        if self.data_validation is None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData, enforce_rules=True, auto_clean=True)
        if not self.data_validation.validate(None, data, validate_dict='json_data-iptables_rules'):
            error_msg = f'''data validation failed<br>{self.data_validation.show_detailed_errors()}'''
            self.webpage.error_log(environ, error_msg)
            return self.webpage.make_return_json('error', error_msg)

        #-----return if missing data in required fields (action)-----
        if data['action'] is None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        if data['json_data'] is None:
            return self.webpage.error_log(environ, 'ERROR: missing json_data')

        # self.load_js_checkbox_data(data)

        if data['action']=='save_iptables_rules':
            cleanup_result = self.data_cleanup(environ, data)
            if cleanup_result['status']=='error':
                return self.webpage.make_return_json('error', self.util.add_html_line_breaks(cleanup_result['error_msg']))
            # save the latest settings
            return self.save_iptables_rules()

        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')

    #--------------------------------------------------------------------------------

    #-----strictly cleanup any bad data-----
    # iptables rules on a router can seriously affect the router's access to the internet or VPN users' access to the internet, or admin access to the router
    # make sure the admin cannot accidentally put bad data in the rules
    # auto-remove any bad data, return the cleaned data along with a status report
    def data_cleanup(self, environ: dict, data: dict) -> dict:
        # clean_data = copy.deepcopy(data)
        self.settings.get_settings()

        cleanup_result = {
            'status': 'success',
            'error_msg': '',
            'dropped_values': {},
        }

        # load the rules that were just uploaded
        try:
            self.settings.IPtablesRules = json.loads(data['json_data'])
        except json.JSONDecodeError as e:
            cleanup_result['status'] = 'error'
            cleanup_result['error_msg'] = f'JSON decode error: {e}'
            self.webpage.error_log(environ, cleanup_result['error_msg'])
            return cleanup_result

        # update the settings object in the iptables_rules object
        self.iptables_rules.settings = self.settings

        # check the data we just loaded into self.settings.IPtablesRules
        if not self.validate_settings():
            error_str = '\n'.join(self.errors)
            cleanup_result['status'] = 'error'
            cleanup_result['error_msg'] = f'Settings validation failed\n{error_str}'
            self.webpage.error_log(environ, cleanup_result['error_msg'])
            return cleanup_result

        #-----do not block critical ports-----
        # self.invalid_ports
        #TODO: block_low_ttl - JS auto-warning on high TTLs?

        #TEST
        print('-'*40)
        print('IPtablesRulesPage.data_cleanup() - uploaded data:')
        pprint.pprint(data)
        print('-'*40)
        print('IPtablesRulesPage.data_cleanup() - cleanup_result:')
        pprint.pprint(cleanup_result)
        print('-'*40)
        clean_data = json.dumps(self.settings.IPtablesRules, indent=4)
        print(f'clean data: {clean_data}')
        print('-'*40)
        #ENDTEST

        return cleanup_result

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle):
        self.webpage.update_header(environ, pagetitle)
        # self.webpage.settings.get_settings()
    
        output = self.webpage.make_webpage(environ, self.make_IPtablesRules(environ))
    
        return output

    #--------------------------------------------------------------------------------

    # settings from the settings.IPtablesRulesView need to be put in self.IPtablesRulesHTML
    def load_settings_into_html(self):
        text_fields = ['allow_ips', 'block_low_ttl', 'bytes_per_sec', 'dst_ports', 'notes', 'packets_per_sec', 'throttle_expire', 'traffic_direction']
        for field in text_fields:
            self.IPtablesRulesHTML[field] = self.settings.IPtablesRules[field]
        # self.IPtablesRulesHTML['enable_auto_blocking'] = self.settings.IPtablesRules['enable_auto_blocking']

        settings_default_value = 'true'
        for checkbox in self.checkbox_fields:
            #TODO: store checkbox values properly
            # self.IPtablesRulesHTML[checkbox] = self.limit_fields[checkbox]
            self.IPtablesRulesHTML[checkbox] = ''
            if self.settings.is_setting_enabled(checkbox, self.settings.SettingTypeIPtablesRules):
                #-----the checked attribute ends up in the HTML <input> tag-----
                self.IPtablesRulesHTML[checkbox] = 'checked'
            else:
                #-----newly-added checkboxes may not be in the DB yet, so set the default value in settings.IPtablesRules-----
                self.settings.IPtablesRules[checkbox] = settings_default_value

    #--------------------------------------------------------------------------------

    def make_IPtablesRules(self, environ: dict, action: str=None) -> str:
        #-----CSP nonce required for JS to run in browser-----
        self.IPtablesRulesHTML['CSP_NONCE'] = environ['CSP_NONCE']
        self.load_settings_into_html()

        #-----initial page load, just return the page header-----
        if self.return_page_header:
            body = self.webpage.load_template('IPtablesRules')
            return body.format(**self.IPtablesRulesHTML)

    #--------------------------------------------------------------------------------

    # assumes data has already been loaded into self.iptables_rules.settings.IPtablesRules
    # drop invalid values in ranges, where practical
    def validate_settings(self) -> bool:
        validation_result = self.iptables_rules.validate_settings()
        self.errors = validation_result['error_msg']
        return validation_result['success']

    #--------------------------------------------------------------------------------

    def save_iptables_rules(self) -> str:

        self.settings.save_iptables_rules_settings()

        # tell the daemon to process iptables changes after settings are uploaded
        self.iptables_rules.queue_settings_update()

        return self.webpage.make_return_json('success', '')

    #--------------------------------------------------------------------------------

    def port_cleanup(self, port_list: list) -> list:
        #-----remove any invalid ports-----
        return [port for port in port_list if port not in self.invalid_ports]

    #--------------------------------------------------------------------------------
