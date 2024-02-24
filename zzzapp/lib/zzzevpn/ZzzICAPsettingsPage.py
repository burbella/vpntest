#-----Zzz ICAP server settings webpage-----

import json
import re
import urllib.parse

#TEST
import pprint

#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.ZzzICAPsettings

class ZzzICAPsettingsPage:
    'Zzz ICAP server settings - web page display and form handling'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    icap_settings: zzzevpn.ZzzICAPsettings = None
    settings: zzzevpn.Settings = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    ICAPsettingsHTML = {}
    
    regex_compiled_html_yes = '<a class="text_green">yes</a>'
    regex_compiled_html_no = '<a class="text_red">no</a>'
    
    #TODO: implement buttons to add these to the regex list
    default_regex_selections = {
        'aside': {},
        'iframe': {},
        'refresh': {},
    }
    
    #TEST
    TESTDATA = ''
    
    # compile_test_regex - tests one regex
    # delete_regex - deletes one regex
    # load_regexes - loads table rows
    # save_settings - saves the entire settings page
    allowed_actions = ['compile_test_regex', 'delete_regex', 'load_regexes', 'save_settings']
    
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
        self.settings = zzzevpn.Settings(self.ConfigData, self.db, self.util)
        self.icap_settings = zzzevpn.ZzzICAPsettings(self.ConfigData, self.db, self.util, self.settings)
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        self.ICAPsettingsHTML = {
            'nobumpsites': '',
            'regex_rows': '',
            'URL_Services': self.ConfigData['URL']['Services'],
            'viewtype': '',
            'TESTDATA': '',
        }
    
    #--------------------------------------------------------------------------------
    
    #TODO: should test the domain_name for validity?
    def compile_test_regex(self, environ: dict, uploaded_ICAPsettingsData: dict):
        regex_pattern = uploaded_ICAPsettingsData.get('regex_pattern', None)
        if not regex_pattern:
            return self.webpage.error_log(environ, 'ERROR: empty regex')
        
        #TODO: handle regex flags from HTML checkboxes
        #      regex_flags = re.IGNORECASE | re.DOTALL | re.MULTILINE
        
        compiled_ok, error_msg, regex_compiled = self.icap_settings.compile_test_regex(regex_pattern)
        if compiled_ok:
            return self.webpage.error_log(environ, 'success')
        
        # report error
        return self.webpage.error_log(environ, error_msg)
    
    #--------------------------------------------------------------------------------
    
    def delete_regex(self, environ: dict, row_id):
        print(f'ZzzICAPsettingsPage: delete_regex({row_id})')
        if not row_id:
            return 'ERROR: no row_id'
        if not self.util.is_int(row_id):
            return 'ERROR: row_id is not an int'
        if self.icap_settings.delete_setting(row_id):
            return 'success'
        return 'ERROR: failed to delete ICAP setting'
    
    #--------------------------------------------------------------------------------
    
    #TODO: finish this
    #-----make sure invalid ICAP Settings don't get saved-----
    # save any valid settings rows
    # report invalid settings rows
    # don't even insert/update a row if there are serious problems with the data
    #
    # ZzzICAPsettings JSON Example:
    # {
    #{"updates":[
    #  {"id":"1","enabled":"false","domain_name":"example.org",
    #"pattern":"ZXhhbXBsZQ==","replacement_str":"VEVTVF9SRVBMQUNFTUVOVA==",
    #"notes":"TESTING NOTES"}
    #],
    #"inserts":[
    #  {"enabled":"true","domain_name":"",
    #  "pattern":"","replacement_str":"YXhhYWFhYWFhYWFhYWFhYWFhYWFhYQ==",
    #  "notes":"ppppp"}
    #]}
    # }
    def validate_settings(self, environ: dict, uploaded_ICAPsettingsData: dict=None):
        error_msg = self.icap_settings.validate_settings(uploaded_ICAPsettingsData)
        if error_msg:
            validation_error = 'ERROR: Invalid ICAP Settings\n' + error_msg
            self.webpage.error_log(environ, validation_error)
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ: dict, pagetitle: str):
        self.settings.get_settings()
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        
        output = self.webpage.make_webpage(environ, self.make_ZzzICAPsettings(environ))
        
        return output
    
    #--------------------------------------------------------------------------------

    #-----process POST data-----
    def handle_post(self, environ: dict, request_body_size: int):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '')
        
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        action = raw_data.get('action', None)
        json_data = raw_data.get('json', None)
        row_id = raw_data.get('row_id', None)
        
        #TEST - disabled until Settings table can safely be updated from outside the Settings page
        # icap_condensed = raw_data.get('icap_condensed', None)
        icap_condensed = None
        
        #-----return if missing data-----
        if row_id:
            row_id = row_id[0]
        if icap_condensed:
            icap_condensed = icap_condensed[0]
        if action:
            action = action[0]
        else:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        #-----parse JSON data into a python array-----
        uploaded_ICAPsettingsData = None
        if json_data:
            json_data = json_data[0]
            #TEST
            self.webpage.error_log(environ, 'json_data:\n' + pprint.pformat(json_data))
            #ENDTEST
            try:
                uploaded_ICAPsettingsData = json.loads(json_data)
            except:
                return self.webpage.error_log(environ, 'ERROR: invalid JSON')
        
        #-----only certain actions require json_data-----
        if (action not in ['load_regexes', 'delete_regex']) and not json_data:
            return self.webpage.error_log(environ, 'ERROR: missing json_data')
        
        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
            'icap_condensed': icap_condensed,
            'json_data': json_data,
            'row_id': row_id,
        }
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')
        
        if not (action in self.allowed_actions):
            self.webpage.error_log(environ, 'allowed_actions: ' + ','.join(self.allowed_actions))
            return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')
        
        if action=='compile_test_regex':
            return self.compile_test_regex(environ, uploaded_ICAPsettingsData)
        elif action=='delete_regex':
            return self.delete_regex(environ, row_id)
        elif action=='load_regexes':
            return self.make_regex_rows(icap_condensed)
            # return self.ICAPsettingsHTML['regex_rows']
        elif action=='save_settings':
            # parse uploaded JSON into a python array
            # check data, process ICAPsettingsData into SQL params arrays
            # invalid settings will be saved as disabled, with an error message in the DB
            self.validate_settings(environ, uploaded_ICAPsettingsData)
            # insert/update DB data
            self.icap_settings.save_settings()
            #-----tell the daemon to process squid/zzz_icap changes after settings are uploaded-----
            self.icap_settings.queue_settings_update()
            self.webpage.error_log(environ, 'success')
            return 'success'
        return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')
    
    #--------------------------------------------------------------------------------
    
    def make_ZzzICAPsettings(self, environ: dict):
        #TEST
        #self.ICAPsettingsHTML['TESTDATA'] = pprint.pformat(self.ConfigData)
        
        self.ICAPsettingsHTML['CSP_NONCE'] = environ['CSP_NONCE']

        self.ICAPsettingsHTML['nobumpsites'] = ''
        if self.settings.SquidNoBumpSites:
            self.ICAPsettingsHTML['nobumpsites'] = '\n'.join(self.settings.SquidNoBumpSites)

        self.ICAPsettingsHTML['viewtype'] = 'expanded'
        if self.settings.is_setting_enabled('icap_condensed'):
            self.ICAPsettingsHTML['viewtype'] = 'condensed'
        
        body = self.webpage.load_template('ZzzICAPsettings')
        
        #-----disabled because AJAX will request the data-----
        # self.make_regex_rows()
        
        return body.format(**self.ICAPsettingsHTML)
    
    #--------------------------------------------------------------------------------
    
    # ZzzICAPsettings_regex_condensed
    # columns: Del, Compiled OK?, Enabled, Regex Pattern, Replacement String
    def format_regex_row(self, html_data: dict):
        if self.settings.is_setting_enabled('icap_condensed'):
            row_template = self.webpage.load_template('ZzzICAPsettings_regex_condensed')
            return row_template.format(**html_data)
        
        row_template = self.webpage.load_template('ZzzICAPsettings_regex')
        return row_template.format(**html_data)
    
    #--------------------------------------------------------------------------------
    
    # (D)elete           Domain
    # Compiled OK? (yes) Regex Pattern
    # Enabled [X]        Regex Replacement
    # Notes: <text>
    # Compiler Message: <readonly text>
    def make_regex_rows(self, icap_condensed: str=None):
        regex_rows = []
        
        self.settings.get_settings()
        self.icap_settings.settings = self.settings
        self.icap_settings.get_settings()
        
        #-----save the new setting if icap_condensed changed-----
        #TODO: find a way to safely update settings from here
        if icap_condensed=='expanded' and self.settings.is_setting_enabled('icap_condensed'):
            print('icap_condensed value changed to expanded')
        if icap_condensed=='condensed' and not self.settings.is_setting_enabled('icap_condensed'):
            print('icap_condensed value changed to condensed')

        #TODO: add regex flags
        #TODO: sync HTML template var names with DB field names, requires JS code changes
        field_data = {
            'domain_name': {},
            'pattern': {},
            'notes': {},
            'replacement_str': {},
        }

        if self.settings.is_setting_enabled('icap_condensed'):
            row_template = self.webpage.load_template('ZzzICAPsettings_header_condensed')
            header_data = {}
            regex_rows.append(row_template.format(**header_data))
        
        #-----always have at least one row in the table, even if it's blank-----
        if not self.icap_settings.ICAPsettingsData['regexes']:
            colspan = '1'
            if self.settings.is_setting_enabled('icap_condensed'):
                colspan = '7'
            regex_rows.append(f'<tr><td colspan="{colspan}">No ICAP Regexes saved</td></tr>')
        
        for row_id in self.icap_settings.ICAPsettingsData['regexes']:
            row = self.icap_settings.ICAPsettingsData['regexes'][row_id]
            html_data = {
                'regex_id': row_id,
                'regex_compiled': '',
                'regex_enabled': '',
                'domain_name': '',
                'regex_pattern': '',
                'regex_flags': '', #TODO: add the flags
                'replacement_str': '',
                'notes': '',
                'compile_message': row['compile_message'],
                'compile_message_class': '',
            }
            if self.settings.is_setting_enabled('icap_condensed'):
                html_data['compile_message'] = '<br>' + row['compile_message']

            if row['compiled_ok']:
                html_data['regex_compiled'] = self.regex_compiled_html_yes
                html_data['compile_message_class'] = 'hide_item'
            else:
                html_data['regex_compiled'] = self.regex_compiled_html_no
            
            if row['enabled']:
                html_data['regex_enabled'] = 'checked="checked"'
            else:
                html_data['regex_enabled'] = ''
            
            field_data['domain_name'][row_id] = row['domain_name']
            field_data['pattern'][row_id] = row['regex_pattern']
            field_data['notes'][row_id] = row['notes']
            field_data['replacement_str'][row_id] = row['replacement_str']
            
            regex_rows.append(self.format_regex_row(html_data))
        
        json_row_data = {
            'html_table_rows': ''.join(regex_rows),
            'field_data': field_data,
        }
        
        return json.dumps(json_row_data)
    
    #--------------------------------------------------------------------------------

