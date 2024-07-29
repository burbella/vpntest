import json
import urllib.parse

#TEST
import pprint

#-----package with all the Zzz modules-----
import zzzevpn

class SettingsPage:
    'Settings web page display and form handling'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    settings: zzzevpn.Settings = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    #TEST
    TESTDATA = ''
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None):
        self.init_vars()
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
        self.settings = zzzevpn.Settings(self.ConfigData, self.db, self.util)
        # self.settings.get_settings(need_html=True)
    
    #--------------------------------------------------------------------------------
    
    #TODO: not needed?
    #      all vars are in the Settings object?
    #-----clear internal variables-----
    def init_vars(self):
        pass
    
    #--------------------------------------------------------------------------------
    
    #-----make sure invalid Settings don't get saved-----
    # SettingsData JSON Example:
    # {"autoplay": "true",
    #  "social": "true",
    #  "telemetry": "false",
    #  "duplicate_domain": "true",
    #  "links_by_function": "false",
    #  "icap_condensed": "false",
    #  "block_country_tld": "false",
    #  "block_country_tld_always": "false",
    #  "block_country_ip_always": "false",
    #  "block_custom_ip_always": "false",
    #  "block_tld_always": "false",
    #  "dark_mode": "true",
    #  "check_zzz_update": "true",
    #  "auto_install_zzz_update": "false",
    #  "show_dev_tools": "false",
    #  "restart_openvpn_weekly": "true",
    #  "test_server_dns_block": "false",
    #  "test_server_squid": "true",
    #  "blocked_country": ["XX", "YY", "ZZ"]
    #  "blocked_tld": ["XXX", "YYY"],
    # }
    def validate_settings(self, environ):
        countries_not_blocked = self.settings.validate_settings()
        if countries_not_blocked:
            output = ''
            for country in countries_not_blocked:
                output += f'not blocking country "{country}" in ProtectedCountries\n'
            self.webpage.error_log(environ, output)
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ, pagetitle):
        self.settings.get_settings(need_html=True)
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        
        #TODO: move this into webpage.make_webpage() - need to init the webpage object with a settings object
        # dark_mode_value = self.settings.SettingsData.get('dark_mode', 'false')
        # if dark_mode_value=='true':
        #     self.webpage.set_dark_mode(True)
        
        output = self.webpage.make_webpage(environ, self.make_SettingsPage(environ))
        
        return output

    #--------------------------------------------------------------------------------

    def make_return_json(self, status, error_msg=''):
        return_data = {
            'status': status,
            'error_msg': error_msg,
        }
        return_json = json.dumps(return_data)
        return return_json

    #--------------------------------------------------------------------------------

    #-----process POST data-----
    def handle_post(self, environ, request_body_size):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        json_data = raw_data.get('json', None)
        
        #-----return if missing data-----
        if (request_body_size==0 or json_data==None):
            self.webpage.error_log(environ, 'ERROR: missing json_data')
            # return 'ERROR: missing json_data'
            return self.make_return_json('error', 'ERROR: missing json_data')

        #TEST
        # self.webpage.error_log(environ, 'json_data:\n' + pprint.pformat(json_data))
        
        #TODO: safety in case of bad data?  cgi.escape(json_data) fails, try another method
        # json_data = cgi.escape(json_data[0])
        
        self.settings.get_settings(need_html=True)
        self.settings.SettingsData = json.loads(json_data[0])
        self.validate_settings(environ)
        self.settings.save_settings()
        
        #-----tell the daemon to process BIND/iptables changes after settings are uploaded-----
        self.settings.queue_settings_update()
        
        self.webpage.error_log(environ, 'success')
        # return 'success'
        return self.make_return_json('success')
    
    #--------------------------------------------------------------------------------
    
    def make_SettingsPage(self, environ):
        #TEST
        #self.settings.SettingsHTML['TESTDATA'] = pprint.pformat(self.ConfigData)
        
        self.settings.SettingsHTML['CSP_NONCE'] = environ['CSP_NONCE']
        
        body = self.webpage.load_template('Settings')
        
        return body.format(**self.settings.SettingsHTML)
    
    #--------------------------------------------------------------------------------

