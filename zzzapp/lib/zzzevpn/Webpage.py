import copy
import os
import pprint
import urllib.parse

#-----import modules from the lib directory-----
# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.Config
# import zzzevpn.DB
# import zzzevpn.Settings
import zzzevpn

class Webpage:
    'Generates webpages for the site'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    settings: zzzevpn.Settings = None
    
    HTMLHeader: str = None
    HTMLFooter: str = None
    pagetitle: str = None
    WebpageFooterHTML = {}
    WebpageHeaderHTML = {}
    
    dark_mode = False
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, pagetitle: str=None, settings: zzzevpn.Settings=None):
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
        if settings is None:
            self.settings = zzzevpn.Settings(self.ConfigData, self.db)
        else:
            self.settings = settings
        if not self.settings.SettingsData:
            self.settings.get_settings()
        #-----string to show in the browser-----
        if pagetitle is None:
            self.pagetitle = self.ConfigData['AppInfo']['Domain']
        else:
            self.pagetitle = pagetitle
        #-----these are static, so pre-compute when making the object-----
        self.init_vars()
        #-----init_vars()-->set_dark_mode() calls this, no need to call it again-----
        # self.HTMLHeader = self.make_HTMLHeader()
        self.HTMLFooter = self.make_HTMLFooter()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        #-----check for custom favicons-----
        # images should have been generated already
        favicon_custom = ''
        if self.ConfigData['Favicon']['use_custom']:
            favicon_custom = 'custom/'

        #-----prep the HTML values-----
        self.WebpageHeaderHTML = {
            'app_domain': self.ConfigData['AppInfo']['Domain'],
            'CSP_NONCE': '',
            'favicon_custom': favicon_custom,
            # 'js_header': '', # user can pass in custom JS code to go in the <head>
            'pagetitle': self.pagetitle,
            'selected_colors': 'colors',
            
            # cache-buster for an auto-generated JS file
            'zzz_config_js_updated': self.ConfigData['AppInfo']['ConfigJSupdated'],
        }

        self.WebpageFooterHTML = {
            'favicon_custom': favicon_custom,
            'url_index': self.ConfigData['URL']['Services'],
        }

        #-----check for dark mode-----
        environ = { 'CSP_NONCE': '', }
        if self.settings.is_setting_enabled('dark_mode'):
            self.set_dark_mode(environ, True)
        else:
            self.set_dark_mode(environ, False)
    
    #--------------------------------------------------------------------------------
    
    def set_dark_mode(self, environ: dict, value=False) -> None:
        if value:
            self.dark_mode = True
            self.WebpageHeaderHTML['selected_colors'] = 'colors-dark'
        else:
            self.dark_mode = False
            self.WebpageHeaderHTML['selected_colors'] = 'colors'
        #-----re-compute the header static content for dark mode changes-----
        self.HTMLHeader = self.make_HTMLHeader(environ)
    
    #--------------------------------------------------------------------------------
    
    #TODO: standardize this function for any app that needs webpages generated
    def make_webpage(self, environ: dict, body: str='') -> str:
        if self.settings.is_setting_enabled('dark_mode'):
            self.set_dark_mode(environ, True)
        else:
            self.set_dark_mode(environ, False)
        return '{}{}{}'.format(self.HTMLHeader, body, self.HTMLFooter)
    
    #--------------------------------------------------------------------------------
    
    #-----common header for all pages-----
    # js_header - customize JS in the page header
    def make_HTMLHeader(self, environ: dict, js_header: str='') -> str:
        #TODO: remove this? may not be compatible with Content Security Policy, also not currently in use
        # self.WebpageHeaderHTML['js_header'] = js_header
        
        # Content Security Policy nonce - allows header scripts to execute
        self.WebpageHeaderHTML['CSP_NONCE'] = environ['CSP_NONCE']
        
        body = self.load_template('header')
        return body.format(**self.WebpageHeaderHTML)

    #-----common footer for all pages-----
    def make_HTMLFooter(self) -> str:
        body = self.load_template('footer')
        return body.format(**self.WebpageFooterHTML)

    #--------------------------------------------------------------------------------

    def error_log(self, environ: dict, err: str) -> str:
        print(err, file=environ['wsgi.errors'])
        #-----makes it possible for the caller to print and return the err in one line-----
        return err

    def error_log_json(self, environ: dict, json_data):
        self.error_log(environ, pprint.pformat(json_data))
        #-----makes it possible for the caller to print and return the err in one line-----
        return json_data

    #--------------------------------------------------------------------------------
    
    def update_header(self, environ: dict, pagetitle: str) -> str:
        self.pagetitle = pagetitle
        self.init_vars()
        self.HTMLHeader = self.make_HTMLHeader(environ)
    
    #--------------------------------------------------------------------------------
    
    #-----return an error for lack of make_webpage handler in the object-----
    def missing_make_webpage(self, environ: dict) -> str:
        self.error_log(environ, 'ERROR: missing missing_make_webpage()')
        body = 'ERROR: missing missing_make_webpage()'
        output = self.make_webpage(environ, body)
        return output
    
    #--------------------------------------------------------------------------------
    
    #-----return an error for lack of POST handler in the object-----
    def missing_handle_post(self, environ: dict) -> str:
        self.error_log(environ, 'ERROR: missing handle_post()')
        body = 'ERROR: missing handle_post()'
        output = self.make_webpage(environ, body)
        return output
    
    #--------------------------------------------------------------------------------
    
    #-----return a generic warning for GET requests on pages that require POST-----
    def require_post(self, environ: dict) -> str:
        self.error_log(environ, 'ERROR: POST required')
        body = 'ERROR: POST required'
        output = self.make_webpage(environ, body)
        return output

    #--------------------------------------------------------------------------------

    def make_parsed_data_from_raw_data(self, raw_data: dict, allowed_params: list) -> dict:
        data = {}
        if not raw_data or not allowed_params:
            return data
        for key in allowed_params:
            data[key] = raw_data.get(key, None)
            if data[key] is not None:
                # get the first item in the list, only one copy of each param is allowed
                data[key] = data[key][0]
        return data

    #-----load each allowed GET param into the data dict-----
    def load_data_from_get(self, environ: dict, allowed_get_params: list) -> dict:
        #TODO: decode() needed? are GET params always ASCII?
        get_data = urllib.parse.parse_qs(environ['QUERY_STRING'])
        return self.make_parsed_data_from_raw_data(get_data, allowed_get_params)

    #-----load each allowed POST param into the data dict-----
    def load_data_from_post(self, environ: dict, request_body_size: int, allowed_post_params: list) -> dict:
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)

        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))

        return self.make_parsed_data_from_raw_data(raw_data, allowed_post_params)

    #--------------------------------------------------------------------------------

    # filename: NAME.template
    def load_template(self, template_name: str) -> str:
        data = ''
        filepath = f'''{self.ConfigData['Directory']['Templates']}/{template_name}.template'''
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            err_str = f'ERROR: template not found {filepath}'
            print(err_str)
            return err_str
        with open(filepath, 'r') as read_file:
            data = read_file.read()
        return data

    #--------------------------------------------------------------------------------

    def make_favicon_link(self, link_type: str, favicon_custom: str, image_size) -> str:
        return f'<link rel="{link_type}" href="/img/{favicon_custom}favicon-{image_size}.png" sizes="{image_size}x{image_size}">'

    # reference: build-favicon.py
    def make_all_favicons(self) -> str:
        favicon_custom = ''
        if self.ConfigData['Favicon']['use_custom']:
            favicon_custom = 'custom/'
        image_sizes = copy.deepcopy(self.ConfigData['Favicon']['sizes']['android'])
        image_sizes.extend(self.ConfigData['Favicon']['sizes']['browser'])
        image_sizes.extend(self.ConfigData['Favicon']['sizes']['high_density'])
        favicons = []
        for image_size in image_sizes:
            favicons.append(self.make_favicon_link('icon', favicon_custom, image_size))
        for image_size in self.ConfigData['Favicon']['sizes']['apple']:
            favicons.append(self.make_favicon_link('apple-touch-icon', favicon_custom, image_size))
        return '\n'.join(favicons)

    #--------------------------------------------------------------------------------
