#-----Install OS Patches-----

import json
import urllib.parse

#-----package with all the Zzz modules-----
import zzzevpn

class UpdateOS:
    'Installs OS Patches'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    service_name = 'linux'
    list_requests_rows = None
    list_requests_colnames = None
    os_update_requests_html = ''
    pending_updates_filedata = ''
    os_update_output_filedata = ''
    
    allowed_actions = ['refresh_list', 'refresh_os_update_output', 'list_os_updates', 'install_os_updates']
    
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
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Update OS Packages')
    
    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    def handle_post(self, environ, request_body_size):
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        action = raw_data.get('action', None)[0]
        
        #-----return if missing data-----
        if action==None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        
        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
        }
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')
        
        if not (action in self.allowed_actions):
            self.webpage.error_log(environ, 'allowed_actions: ' + ','.join(self.allowed_actions))
            return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')
        
        if action=='refresh_list':
            #-----send the file-----
            return self.get_all_files()
            # self.get_os_updates_file()
            # return self.pending_updates_filedata
        elif action=='refresh_os_update_output':
            #-----send the file-----
            self.get_os_update_output_file()
            return self.os_update_output_filedata
        elif action=='list_os_updates':
            status = self.request_os_update('list_os_updates')
            return status
        elif action=='install_os_updates':
            status = self.request_os_update('install_os_updates');
            return status
        
        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ, pagetitle):
        #-----show the OS Updates requests-----
        if self.get_os_update_requests()>0:
            self.show_os_update_requests()
        
        #-----show the latest version of the OS Updates file-----
        self.get_os_updates_file()
        
        self.get_os_update_output_file()
        
        UpdateOsHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'os_update_requests_html': self.os_update_requests_html,
            'pending_updates_filedata': self.pending_updates_filedata,
            'os_update_output_filedata': self.os_update_output_filedata,
        }
        
        body = self.webpage.load_template('UpdateOS')
        output = self.webpage.make_webpage(environ, body.format(**UpdateOsHTML))
        return output
    
    #--------------------------------------------------------------------------------
    
    #-----count pending requests-----
    def get_os_update_requests(self, action=None):
        num_unprocessed_requests = 0
        
        sql = 'select * from service_request where service_name=? order by id desc'
        params = (self.service_name,)
        
        if action:
            sql = 'select * from service_request where service_name=? and action=? order by id desc'
            params = (self.service_name, action)
        
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        self.list_requests_rows = rows
        self.list_requests_colnames = colnames
        
        for row in rows_with_colnames:
            if row['status']==self.ConfigData['ServiceStatus']['Requested'] or row['status']==self.ConfigData['ServiceStatus']['Working']:
                num_unprocessed_requests += 1
        return num_unprocessed_requests
    
    #--------------------------------------------------------------------------------
    
    def show_os_update_requests(self):
        self.os_update_requests_html = self.db.result_full_table(self.list_requests_colnames, self.list_requests_rows)
    
    #--------------------------------------------------------------------------------

    def get_all_files(self):
        self.get_os_updates_file()
        self.get_os_update_output_file()
        result = {
            'status': 'success',
            'error_msg': '',
            'pending_updates': self.pending_updates_filedata,
            'os_update_output': self.os_update_output_filedata,
        }
        return json.dumps(result)

    #--------------------------------------------------------------------------------

    def get_os_updates_file(self):
        self.pending_updates_filedata = self.util.get_filedata(self.ConfigData['UpdateFile']['linux']['list_os_updates'])
        self.pending_updates_filedata = self.util.add_html_line_breaks(self.pending_updates_filedata)

    #--------------------------------------------------------------------------------
    
    def get_os_update_output_file(self):
        self.os_update_output_filedata = self.util.get_filedata(self.ConfigData['UpdateFile']['linux']['os_update_output'])
        self.os_update_output_filedata = self.util.add_html_line_breaks(self.os_update_output_filedata)

    #--------------------------------------------------------------------------------
    
    # queue a restart request for squid
    def queue_os_update_request(self, action):
        self.db.insert_service_request(self.service_name, action)
        self.util.work_available(1)
        
        return "OS Update Request has been queued: " + action;
    
    #--------------------------------------------------------------------------------
    
    #-----request an OS update-----
    # available actions: list_os_updates, install_os_updates
    def request_os_update(self, action):
        if self.get_os_update_requests(action)>0:
            self.show_os_update_requests()
            return 'Request NOT submitted because an existing request is pending.'
        else:
            status = self.queue_os_update_request(action)
            return "Request submitted.\n" + status
    
    #--------------------------------------------------------------------------------
