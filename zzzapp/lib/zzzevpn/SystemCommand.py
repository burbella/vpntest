#-----Manages System Commands - reload, restart, etc-----

import urllib.parse

#-----package with all the Zzz modules-----
import zzzevpn

class SystemCommand:
    'Runs commands on the command line'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    data_validation = None
    command = None
    service_name = None
    list_requests_rows = None
    list_requests_colnames = None
    
    allowed_commands = ['reload', 'restart']
    allowed_service_names = ['apache', 'bind', 'linux', 'openvpn', 'squid', 'zzz', 'zzz_icap']
    SystemCommandHTML = {}
    
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
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'SystemCommand')
    
    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    def handle_post(self, environ: dict, request_body_size: int) -> str:
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        self.command = raw_data.get('command', None)[0]
        self.service_name = raw_data.get('service_name', None)[0]
        # confirm_command=='Confirm'
        
        #-----return if missing data-----
        if self.command==None:
            return self.webpage.error_log(environ, 'ERROR: missing command')
        if self.service_name==None:
            return self.webpage.error_log(environ, 'ERROR: missing service_name')
        
        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'command': self.command,
            'service_name': self.service_name,
        }
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')
        
        if not (self.command in self.allowed_commands):
            self.webpage.error_log(environ, 'allowed_commands: ' + ','.join(self.allowed_commands))
            return self.webpage.error_log(environ, 'ERROR: bad command "' + self.command + '"')
        
        if not (self.service_name in self.allowed_service_names):
            return self.webpage.error_log(environ, 'ERROR: bad service_name')
        
        return self.request_run()
        # return self.webpage.error_log(environ, 'success')
    
    #--------------------------------------------------------------------------------
    
    def request_run(self) -> str:
        if self.get_requests() > 5:
            return self.show_requests()
        else:
            return self.queue_request()
    
    #--------------------------------------------------------------------------------
    
    #-----count pending requests-----
    def get_requests(self) -> int:
        sql = 'select * from service_request where service_name=? and action=? and status in (?, ?)'
        params = (self.service_name, self.command, self.ConfigData['ServiceStatus']['Requested'], self.ConfigData['ServiceStatus']['Working'])
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        self.list_requests_rows = rows
        self.list_requests_colnames = colnames
        
        return len(rows_with_colnames)
    
    #--------------------------------------------------------------------------------
    
    #-----show pending requests-----
    def show_requests(self) -> str:
        output = '<p>Service Request "{} {}" has not been queued because there are too many pending requests:</p>'.format(self.service_name, self.command)
        output += self.db.result_full_table(self.list_requests_colnames, self.list_requests_rows)
        return output
    
    #--------------------------------------------------------------------------------
    
    #-----request a command to run-----
    def queue_request(self) -> str:
        # queue a request for the service
        self.db.insert_service_request(self.service_name, self.command)
        self.util.work_available(1)
        return '<p>Service Request "{} {}" has been queued</p>'.format(self.service_name, self.command)
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ: dict, pagetitle: str) -> str:
        # environ['PATH_INFO'] == '/sys/restart/bind
        url_path = environ['PATH_INFO']
        (junk_str, sys_str, self.command, self.service_name) = url_path.split('/')
        
        err = ''
        if not self.command in self.allowed_commands:
            err += 'invalid command: ' + self.command
        if not self.service_name in self.allowed_service_names:
            err += 'invalid service_name: ' + self.service_name
        
        #-----default restart form-----
        html_body = '''
            <div>
                <p>Do you want to {} {} ?</p>
                <p><a class="clickable" id="confirm_command">Confirm</a></p>
            </div>
            '''
        
        #-----form with double-confirmation for reboots-----
        html_body_reboot = '''
            <div>
                <p>Do you want to reboot linux ?</p>
                <a id="reboot_linux" class="clickable">Reboot Linux</a>
                <a id="cancel_reboot_linux" class="hide_item">CANCEL Reboot</a>
                <a id="confirm_reboot_linux" class="hide_item">Confirm Reboot Linux</a><br>
            </div>
            '''
        
        warning = ''
        if err == '':
            #-----extra warning for OpenVPN-----
            if self.service_name=='openvpn':
                warning = '<h3 class="text_red">Restarting OpenVPN will take down the VPN\'s for about 2 seconds each</h3>'
            elif self.service_name=='zzz_icap':
                if self.command=='restart':
                    warning = '<h3 class="text_red">Restarting the ICAP server will take down squid for a few seconds</h3>'
            #-----handle reboots separately from other commands-----
            if self.service_name=='linux':
                warning = '<h3 class="text_red">Rebooting linux will take down the server for up to 1 minute</h3>'
                html_body = html_body_reboot
            else:
                html_body = html_body.format(self.command, self.service_name)
        else:
            html_body = '<p>ERROR: invalid system command</p><p>{}</p>'.format(err)
        
        self.SystemCommandHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'command': self.command,
            'html_body': html_body,
            'service_name': self.service_name,
            'url': '/z/sys/{}/{}'.format(self.command, self.service_name),
            'warning': warning,
        }
        
        output = self.webpage.load_template('SystemCommand')
        output = output.format(**self.SystemCommandHTML)
        
        self.webpage.update_header(environ, f'Cmd: {self.command} {self.service_name}')
        output = self.webpage.make_webpage(environ, output)
        
        return output
    
    #--------------------------------------------------------------------------------
