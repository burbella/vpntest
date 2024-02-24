#-----Zzz WSGI support functions-----
# used by zzz.wsgi and test_wsgi.py(called by pytest)

#-----package with all the Zzz modules-----
import zzzevpn
import zzzevpn.NetworkService
import zzzevpn.ZzzTest

class WSGI:
    'Zzz WSGI support functions'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    data_validation: zzzevpn.DataValidation = None
    environ: dict = None
    start_response = None
    
    path_info: str = ''
    request_body_size: int = 0
    
    #-----special init, doesn't auto-get objects-----
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, data_validation: zzzevpn.DataValidation=None, environ: dict=None, start_response=None):
        self.ConfigData = ConfigData
        self.db = db
        self.data_validation = data_validation
        self.environ = environ
        self.start_response = start_response
        
        self.init_vars()
        self.parse_environ()
    
    #--------------------------------------------------------------------------------
    
    def init_vars(self) -> None:
        self.path_info = ''
        self.request_body_size = 0
    
    def parse_environ(self) -> None:
        if not self.environ:
            return
        self.path_info = self.environ.get('PATH_INFO', '')
        
        #-----CONTENT_LENGTH may be empty or missing-----
        self.request_body_size = 0
        try:
            self.request_body_size = int(self.environ.get('CONTENT_LENGTH', 0))
        except:
            self.request_body_size = 0
    
    #--------------------------------------------------------------------------------
    
    #TODO - duplicated in Webpage.error_log()
    def error_log(self, err: str) -> None:
        if not self.environ:
            return
        error_log_file = self.environ.get('wsgi.errors', None)
        if not error_log_file:
            print('ERROR: environ[\'wsgi.errors\'] is not defined for error printing:')
            print(err)
        print(err, file=error_log_file)
    
    #--------------------------------------------------------------------------------
    
    #TEST: AJAX responses may require a text/plain content type?
    # content_type = 'text/plain'
    def send_output(self, output: str=None, content_type: str='text/html', status: str='200 OK'):
        if output is None:
            output = ''
        response_headers = [('Content-type', content_type),
                            ('Content-Length', str(len(output)))]
        self.start_response(status, response_headers)
        return [output.encode('utf-8')]
    
    #--------------------------------------------------------------------------------
    
    def make_output_or_error(self, output: str=None) -> str:
        err = ''
        if output is None:
            err = self.path_info + ': empty output'
            self.error_log(err)
            webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Zzz ERROR')
            output = webpage.make_webpage(self.environ, err)
        
        return output
    
    #--------------------------------------------------------------------------------
    
    #-----most functions are so similar that they can be abstracted here-----
    # main_object is:
    #    BIND, IndexPage, IPset, IPtablesLogParser, NetworkService, SettingsPage, SquidLogPage
    #    SystemCommand, SystemStatus, TaskHistory, UpdateOS, UpdateZzz, ZzzICAPsettingsPage, ZzzTest
    # log_comment is a note for the log about which function we called
    # EXAMPLE:
    #   generic_process(zzzevpn.IPtablesLogParser(ConfigData, db), 'IP Log', 'iptables_log()')
    def generic_process(self, main_object, pagetitle: str='', log_comment: str=''):
        # self.error_log(log_comment)
        
        #-----check for GET request-----
        if (self.environ['QUERY_STRING'] is not None) and len(self.environ['QUERY_STRING'])>2:
            #-----check if the module supports GET requests, return an error if not supported-----
            if hasattr(main_object, 'handle_get'):
                #-----let the object process the GET request-----
                output = main_object.handle_get(self.environ)
                return output
            #-----call a default require_post() error generator to say "GET not allowed"-----
            webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle)
            return webpage.require_post(self.environ)
        
        #-----process form submit if available-----
        if (self.request_body_size>0):
            # self.error_log('got a POST')
            if hasattr(main_object, 'handle_post'):
                #-----use the object's handle_post() if it has one-----
                output = main_object.handle_post(self.environ, self.request_body_size)
                return output
            #-----return an error for lack of POST handler in the object-----
            webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle)
            return webpage.missing_handle_post(self.environ)
        
        #-----use the object's make_webpage() if it has one-----
        # this is for GET requests that don't have a QUERY_STRING
        if hasattr(main_object, 'make_webpage'):
            output = main_object.make_webpage(self.environ, pagetitle)
            return output

        #-----return an error for lack of make_webpage handler in the object-----
        webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle)
        return webpage.missing_make_webpage(self.environ)
    
    #--------------------------------------------------------------------------------

    def choose_path(self):
        # output = 'Zzz App\nPath: ' + self.path_info
        output = None

        ConfigData = self.ConfigData
        db = self.db

        # https://services.zzz.zzz/z/settings --> '/settings'
        if self.path_info in ['/index', '/', '']:
            output = self.generic_process(zzzevpn.IndexPage(ConfigData, db), 'Zzz Enhanced VPN', 'index()')
        elif self.path_info.startswith('/coverage'):
            output = self.generic_process(zzzevpn.UpdateZzz(ConfigData, db), 'Update Zzz - Coverage Report', 'update_zzz(coverage)')
        elif self.path_info == '/db_view':
            output = self.generic_process(zzzevpn.UpdateZzz(ConfigData, db), 'Update Zzz - DB View', 'update_zzz(db_view)')
        elif self.path_info == '/edit_dns':
            output = self.generic_process(zzzevpn.BIND(ConfigData, db), 'Edit DNS', 'edit_dns()')
        elif self.path_info == '/edit_ip':
            output = self.generic_process(zzzevpn.IPset(ConfigData, db), 'Edit IP', 'edit_ip()')
        elif self.path_info == '/icap_settings':
            output = self.generic_process(zzzevpn.ZzzICAPsettingsPage(ConfigData, db), 'ICAP Settings', 'icap_settings()')
        elif self.path_info == '/installed_packages':
            output = self.generic_process(zzzevpn.SystemStatus(ConfigData, db), 'installed_packages', 'installed_packages()')
        elif self.path_info == '/installed_software':
            output = self.generic_process(zzzevpn.SystemStatus(ConfigData, db), 'installed_software', 'installed_software()')
        elif self.path_info == '/ip_log_raw_data':
            output = self.generic_process(zzzevpn.IpLogRawDataPage(ConfigData, db), 'IP Log Raw Data', 'ip_log_raw_data()')
        elif self.path_info == '/iptables_log':
            # output = self.generic_process(zzzevpn.IPtablesLogParser(ConfigData, db), 'IP Log', 'iptables_log()')
            iptables_log_parser = zzzevpn.IPtablesLogParser(ConfigData, db)

            #TEST - turn off test mode before going live
            # iptables_log_parser.test_memory_usage = True

            output = self.generic_process(iptables_log_parser, 'IP Log', 'iptables_log()')
        # elif self.path_info == '/ipwhois_cache':
        #     output = self.generic_process(zzzevpn.NetworkService.NetworkService(ConfigData, db), 'IP-Whois Cache', 'ipwhois_cache()')
        elif self.path_info == '/list_manager':
            output = self.generic_process(zzzevpn.ListManagerPage(ConfigData, db), 'List Manager', 'list_manager()')
        elif self.path_info == '/network_service':
            output = self.generic_process(zzzevpn.NetworkService.NetworkService(ConfigData, db), 'Network Service', 'network_service()')
        # elif self.path_info == '/nslookup':
        #     output = self.generic_process(zzzevpn.NetworkService.NetworkService(ConfigData, db), 'nslookup', 'nslookup()')
        # elif self.path_info == '/reverse_dns':
        #     output = self.generic_process(zzzevpn.NetworkService.NetworkService(ConfigData, db), 'Reverse DNS', 'reverse_dns()')
        elif self.path_info == '/settings':
            output = self.generic_process(zzzevpn.SettingsPage(ConfigData, db), 'Settings', 'settings()')
        elif self.path_info == '/squid_log':
            #-----new 3-module version loading pre-processed log data from the DB, along with recent data-----
            output = self.generic_process(zzzevpn.SquidLogPage(ConfigData, db), 'Squid Log', 'squid_log()')
        elif self.path_info.startswith('/sys/'):
            #-----process restarts, reloads, etc.-----
            # reload: apache, bind, squid
            # restart: apache, bind, openvpn, squid, zzz
            output = self.generic_process(zzzevpn.SystemCommand(ConfigData, db), 'SystemCommand', 'system_command()')
        elif self.path_info == '/system_status':
            # 'top' i the command recognized by SystemStatus
            output = self.generic_process(zzzevpn.SystemStatus(ConfigData, db), 'top', 'system_status()')
        elif self.path_info == '/task_history':
            output = self.generic_process(zzzevpn.TaskHistory(ConfigData, db), 'Task History', 'task_history()')
        elif self.path_info == '/update_os':
            output = self.generic_process(zzzevpn.UpdateOS(ConfigData, db), 'Update OS', 'update_os()')
        elif self.path_info == '/update_zzz':
            output = self.generic_process(zzzevpn.UpdateZzz(ConfigData, db), 'Update Zzz', 'update_zzz()')
        # elif self.path_info == '/whois':
        #     output = self.generic_process(zzzevpn.NetworkService.NetworkService(ConfigData, db), 'Whois', 'whois()')
        # elif self.path_info == '/whois_cache':
        #     output = self.generic_process(zzzevpn.NetworkService.NetworkService(ConfigData, db), 'Whois Cache', 'whois_cache()')
        elif self.path_info == '/test':
            #-----test various features-----
            output = self.generic_process(zzzevpn.ZzzTest.ZzzTest(ConfigData, db), 'ZzzTest', 'ZzzTest()')
        
        return self.make_output_or_error(output)
    
    #--------------------------------------------------------------------------------

