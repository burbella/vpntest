#-----Zzz ICAP server settings-----

import json
import re

#TEST
import pprint

#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.ZzzRedis

class ZzzICAPsettings:
    'Zzz ICAP server settings'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    settings: zzzevpn.Settings = None
    util: zzzevpn.Util = None
    zzz_redis: zzzevpn.ZzzRedis = None
    
    # settings loaded from the DB
    ICAPsettingsData = {}
    
    # settings uploaded and checked (but not yet saved to the DB)
    validated_ICAPsettingsData = {}
    
    regex_compiled_html_yes = '<a class="text_green">yes</a>'
    regex_compiled_html_no = '<a class="text_red">no</a>'
    
    #TEST
    TESTDATA = ''
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None) -> None:
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
        self.zzz_redis = zzzevpn.ZzzRedis(self.ConfigData)
        self.zzz_redis.redis_connect()
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self) -> None:
        self.ICAPsettingsData = {
            'regexes': {},
            
            # for empty domains because they apply to all requests (dictionary of regex ID's { id: 1, })
            'regexes_for_all_domains': {},
            
            # domain --> { id: 1, }
            'regexes_by_domain': {},
        }
    
    #--------------------------------------------------------------------------------
    
    #TODO: add regex flags processing
    # returns: compiled_ok boolean, error message string
    def compile_test_regex(self, regex_pattern, flags=0):
        regex = None
        try:
            regex = re.compile(regex_pattern, flags)
        except re.error as e:
            #TODO: report error from parsing the exception
            # optional fields (may be None): pos, lineno, colno
            return False, e.msg, None
        except Exception as e:
            error_msg = 'ERROR: regex compile failed'
            return False, error_msg, None
        return True, '', regex
    
    #--------------------------------------------------------------------------------
    
    def get_regexes_by_domain(self, domain: str):
        regexes = self.ICAPsettingsData['regexes_by_domain'].get(domain, None)
        return regexes
    
    #--------------------------------------------------------------------------------
    
    #TODO: called for inserts and updates
    def validate_entry(self, row: dict, row_id=None):
        entry = {
            'compiled_ok': 1,
            'enabled': 0,
            'domain_name': row['domain_name'],
            'regex_pattern': row['pattern'],
            'regex_flags': 0,
            'replacement_str': row['replacement_str'],
            'notes': row['notes'],
            'compile_message': '',
        }
        if row['enabled']=='true':
            entry['enabled'] = 1
        if row_id:
            entry['id'] = row_id
        
        #TODO: map row['flags'] regex flags checkboxes to python regex flags
        
        #TODO: check the domain, report invalid in compile_message
        
        compiled_ok, error_msg, regex_compiled = self.compile_test_regex(entry['regex_pattern'])
        if not compiled_ok:
            # set it to disabled in the DB if the compile fails
            entry['enabled'] = 0
            entry['compiled_ok'] = 0
            entry['compile_message'] = error_msg
        
        return entry
    
    #TODO: finish this
    #-----make sure invalid ICAP Settings don't get saved-----
    # ZzzICAPsettings JSON Example:
    # {
    #  "icap_settings": "[]",
    # }
    def validate_settings(self, uploaded_ICAPsettingsData: dict=None):
        if not uploaded_ICAPsettingsData:
            return 'ERROR: missing uploaded_ICAPsettingsData'
        
        # pull existing data from the DB
        self.get_settings()
        self.validated_ICAPsettingsData = {
            'inserts': [],
            'updates': [],
        }
        
        is_valid = True
        error_msg = None
        error_count = 0
        regex_inserts = uploaded_ICAPsettingsData.get('inserts', None);
        if regex_inserts:
            for row in regex_inserts:
                # no row ID here because it's new data
                entry = self.validate_entry(row)
                if not entry['compiled_ok']:
                    error_count += 1
                self.validated_ICAPsettingsData['inserts'].append(entry)
        
        regex_updates = uploaded_ICAPsettingsData.get('updates', None);
        if regex_updates:
            for row in regex_updates:
                entry = self.validate_entry(row, row['id'])
                if not entry['compiled_ok']:
                    error_count += 1
                self.validated_ICAPsettingsData['updates'].append(entry)
        
        if error_count>0:
            error_msg = f'regex compile errors: {error_count}\n'
        return error_msg
    
    #--------------------------------------------------------------------------------
    
    # JSON-formatted data will safely escape regex characters so they don't interfere with HTML rendering
    # regex_json: pattern, flags
    def load_setting_entry(self, row: dict):
        regex_json = None
        row_id = row['id']
        try:
            regex_json = json.loads(row['regex_json'])
        except:
            print('load_setting_entry(): json.loads() failed for row {row_id} regex_json', flush=True)
        regex_entry = {
            'id': row['id'],
            'compiled_ok': row['compiled_ok'],
            'enabled': row['enabled'],
            'domain_name': row['domain_name'],
            'regex_pattern': regex_json['pattern'],
            'regex_flags': regex_json['flags'],
            'replacement_str': row['replacement_str'],
            'notes': row['notes'],
            'compile_message': row['compile_message'],
        }
        #TODO: remove this? index it by ID?
        self.ICAPsettingsData['regexes'][row['id']] = regex_entry
        
        #-----the ICAP server needs a list searchable by domain name-----
        success, error_msg, regex_compiled = self.compile_test_regex(regex_json['pattern'], regex_json['flags'])
        #TODO: handle case where regex compile fails? (should not happen here since it was checked when saving)
        self.ICAPsettingsData['regexes'][row['id']]['regex_compiled'] = regex_compiled
        
        # no domain? add it to the "all" list
        if not row['domain_name']:
            self.ICAPsettingsData['regexes_for_all_domains'][row['id']] = 1
            return
        
        found_regexes = self.get_regexes_by_domain(row['domain_name'])
        if not found_regexes:
            self.ICAPsettingsData['regexes_by_domain'][row['domain_name']] = {}
        self.ICAPsettingsData['regexes_by_domain'][row['domain_name']][row['id']] = 1
    
    # create table if not exists icap_settings(
    #     id integer primary key,
    #     compiled_ok boolean not null,
    #     enabled boolean not null,
    #     domain_name text,
    #     regex_json text not null,
    #     replacement_str text,
    #     notes text,
    #     compile_message text
    # );
    def get_settings(self):
        # clears self.ICAPsettingsData['regexes'] and self.ICAPsettingsData['regexes_by_domain']
        self.init_vars()
        
        sql = 'select * from icap_settings order by domain_name';
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        if not rows_with_colnames:
            # empty table
            return
        for row in rows_with_colnames:
            self.load_setting_entry(row)
        
        print('icap_settings loaded')
        #TEST
        # pprint.pprint(self.ICAPsettingsData)
    
    #--------------------------------------------------------------------------------
    
    def encode_json(self, entry: dict):
        regex_json = {
            'pattern': entry['regex_pattern'],
            'flags': entry['regex_flags'],
        }
        regex_json_str = json.dumps(regex_json)
        return regex_json_str
    
    def make_db_update_param(self, entry: dict):
        if not entry:
            return None
        regex_json_str = self.encode_json(entry)
        param = (entry['compiled_ok'], entry['enabled'], entry['domain_name'], regex_json_str, entry['replacement_str'], entry['notes'], entry['compile_message'], entry['id'])
        return param
    
    def make_params_update_list(self):
        params_update_list = []
        regex_updates = self.validated_ICAPsettingsData.get('updates', None);
        if regex_updates:
            for row in regex_updates:
                param = self.make_db_update_param(row)
                if param:
                    params_update_list.append(param)
        return params_update_list
    
    def make_db_insert_param(self, entry: dict):
        if not entry:
            return None
        regex_json_str = self.encode_json(entry)
        param = (entry['compiled_ok'], entry['enabled'], entry['domain_name'], regex_json_str, entry['replacement_str'], entry['notes'], entry['compile_message'])
        return param
    
    def make_params_insert_list(self):
        params_insert_list = []
        regex_inserts = self.validated_ICAPsettingsData.get('inserts', None);
        if regex_inserts:
            for row in regex_inserts:
                param = self.make_db_insert_param(row)
                if param:
                    params_insert_list.append(param)
        return params_insert_list
    
    #TODO: write to ICAP settings table
    # only the server app writes to these fields: compiled_ok, compile_message
    def save_settings(self):
        # items that fail testing get auto-disabled even if the user selected "enabled"
        # self.validate_settings() writes compiler error messages to the compile_message field
        
        # updates
        sql_update = 'update icap_settings set compiled_ok=?, enabled=?, domain_name=?, regex_json=?, replacement_str=?, notes=?, compile_message=? where id=?'
        params_update_list = self.make_params_update_list()
        if params_update_list:
            #TODO: catch query crashes?
            self.db.query_exec_many(sql_update, params_update_list)
        
        # inserts
        sql_insert = 'insert into icap_settings (compiled_ok, enabled, domain_name, regex_json, replacement_str, notes, compile_message) values (?, ?, ?, ?, ?, ?, ?)'
        params_insert_list = self.make_params_insert_list()
        if params_insert_list:
            #TODO: catch query crashes?
            self.db.query_exec_many(sql_insert, params_insert_list)
    
    #--------------------------------------------------------------------------------
    
    # returns success=True/False
    def delete_setting(self, row_id):
        if not self.util.is_int(row_id):
            return False
        sql = 'delete from icap_settings where id=?'
        params = (row_id,)
        if self.db.query_exec(sql, params):
            return True
        return False
    
    #--------------------------------------------------------------------------------
    
    #-----insert a service request to update the settings-----
    def queue_settings_update(self):
        # self.db.insert_service_request('settings', 'settings')
        self.db.request_reload('zzz_icap')
        self.util.work_available(1)
        self.zzz_redis.icap_reload_set()
    
    #--------------------------------------------------------------------------------

