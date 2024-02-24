#-----Template lib with WSGI-----
#TODO: finish making this a generic template

import urllib.parse

#-----package with all the Zzz modules-----
import zzzevpn

class TEMPLATE_LIB_with_WSGI:
    'Template lib with WSGI'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None
    
    TemplateWsgiHTML = {}
    service_name = 'service_name'
    
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
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        #-----prep the HTML values-----
        self.TemplateWsgiHTML = {
            'TESTDATA': '',
        }
    
    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    def handle_post(self, environ, request_body_size):
        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        
        return 'success'
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ, pagetitle):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        self.webpage.settings.get_settings()
        
        output = self.webpage.make_webpage(environ, self.make_TemplateWsgiPage(environ))
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def make_TemplateWsgiPage(self, environ):
        #-----CSP nonce required for JS to run in browser-----
        self.TemplateWsgiHTML['CSP_NONCE'] = environ['CSP_NONCE']

        body = '''
<h2>TEST TemplateWsgi</h2>
        '''
        
        return body.format(**self.TemplateWsgiHTML)
    
    #--------------------------------------------------------------------------------
