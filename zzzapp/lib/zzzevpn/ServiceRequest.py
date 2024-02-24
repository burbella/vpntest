#-----ServiceRequest processing-----
# don't let errors crash the app
# catch all errors, log them, update the request status/details with error info, and move on to the next request

import os.path
import pprint
import re
import subprocess
import traceback

#-----import modules from the lib directory-----
import zzzevpn
import zzzevpn.DiffCode

class ServiceRequest:
    'handles ServiceRequest data table processing'
    
    bind: zzzevpn.BIND = None
    ConfigData: dict = None
    db: zzzevpn.DB = None
    ipset: zzzevpn.IPset = None
    iptables: zzzevpn.IPtables = None
    settings: zzzevpn.Settings = None
    update_file: zzzevpn.UpdateFile = None
    util: zzzevpn.Util = None
    zzz_redis: zzzevpn.ZzzRedis = None
    zzz_template: zzzevpn.ZzzTemplate = None
    
    checkwork = True
    reload_config = False
    run = True # setting this to zero will make the daemon gracefully exit, done with signal handling
    
    # Allowed Actions for each Service Name:
    #   bind - needs a remove_domains action?
    #   iptables - needs a remove_ips action?
    #   squid - stop & start are only used with zzz_icap because it cannot restart with squid running
    #   settings - block/clear various services with bind and/or iptables
    #              needs a reload action?
    # 'service_name': [ list of actions ]
    allowed_actions = {
        'apache': [ 'reload', 'restart', ],
        'bind': [ 'add_domains', 'replace_domains', 'reload', 'restart', ],
        'iptables': [ 'add_ips', 'replace_ips', 'delete_log_all', 'delete_log_old', 'parse_logs', ],
        'linux': [ 'list_os_updates', 'install_os_updates', 'restart', ],
        'list_manager': ['download_lists', 'rebuild_lists'],
        'openvpn': [ 'restart', ],
        'settings': [ 'settings', ],
        'squid': [ 'delete_log_all', 'delete_log_old', 'reload', 'restart', 'stop', 'start', ],
        'zzz': [ 'dev_upgrade', 'git_branch', 'git_diff', 'git_pull', 'git_reset', 'install_zzz_codebase', 'queue_upgrades', 'restart', 'run_code_diff', 'run_pytest', 'upgrade', 'version_checks', 'version_checks_cron', ],
        'zzz_icap': [ 'reload', 'restart', ],
    }

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None) -> None:
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
        self.settings.get_settings()
        self.bind = zzzevpn.BIND(self.ConfigData, self.db, self.util, self.settings)
        self.ipset = zzzevpn.IPset(self.ConfigData, self.db, self.util, self.settings)
        self.iptables = zzzevpn.IPtables(self.ConfigData, self.db, self.util, self.settings)
        self.update_file = zzzevpn.UpdateFile(self.ConfigData, self.db, self.util, self.settings)
        self.zzz_redis = zzzevpn.ZzzRedis(self.ConfigData)
        self.zzz_redis.redis_connect()
        self.zzz_template = zzzevpn.ZzzTemplate(self.ConfigData, self.db, self.util)
        
        # no need for this since the bash start script does it
        # self.update_file.create_pid_file()
    
    #--------------------------------------------------------------------------------
    
    def should_checkwork(self, value: bool=None):
        if (value is None):
            return self.checkwork
        else:
            self.checkwork = value
    
    def should_run(self, value: bool=None):
        if (value is None):
            return self.run
        else:
            self.run = value
    
    #--------------------------------------------------------------------------------
    
    def select(self, request_id):
        """ get a specific service request
        """
        sql = 'SELECT * FROM service_request WHERE id=?'
        params = (request_id,)
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        return rows_with_colnames

    def get_all_requests(self):
        """ get all service requests
        """
        sql = 'SELECT * FROM service_request WHERE status in (?) order by req_date'
        params = (self.ConfigData['ServiceStatus']['Requested'],)
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        return rows_with_colnames
    
    #--------------------------------------------------------------------------------
    
    def is_action_allowed(self, service_name: str, action: str):
        found_service_name = self.allowed_actions.get(service_name, None)
        if not found_service_name:
            print(f'service "{service_name}" not found')
            return False
        if action not in self.allowed_actions[service_name]:
            print(f'action "{action}" not found under service "{service_name}"')
            return False
        return True
    
    #--------------------------------------------------------------------------------
    
    def work_on_request_row(self, row: dict):
        request_id = row['id']
        #TODO: mixing service_name and action in IF statements may confuse logic...
        #-----decide which function to call-----
        # check restarts and reloads before other things since the same restart/reload function is used for all services
        if (row['service_name']=='settings'):
            self.process_settings(request_id, row['service_name'], row['action'], row['req_date'])
        elif (row['action']=='restart'):
            self.restart_service(request_id, row['service_name'], row['req_date'])
        elif (row['action']=='reload'):
            self.reload_service(request_id, row['service_name'])
        elif (row['service_name']=='zzz'):
            #-----do restart/reload above-----
            # otherwise, this IF statement will pick up zzz daemon restart requests and fail
            # this processes the following actions: run_code_diff, install_zzz_codebase, upgrade, git_branch, git_diff, git_pull, git_reset
            self.process_zzz(request_id, row['service_name'], row['action'], row['details'], row['req_date'])
        elif (row['service_name']=='list_manager'):
            self.process_list_manager(request_id, row['service_name'], row['action'], row['details'], row['req_date'])
        elif (row['service_name']=='iptables'):
            self.process_iptables(request_id, row['service_name'], row['action'], row['details'], row['req_date'])
        elif (row['service_name']=='squid'):
            self.process_squid(request_id, row['service_name'], row['action'], row['details'], row['req_date'])
        elif (row['action'] in ['add_domains', 'replace_domains']):
            print('DNS: {} {} - {} - {}'.format(row['action'], request_id, row['service_name'], row['req_date']), flush=True)
            self.replace_domains(request_id, row['service_name'], row['action'])
        elif (row['action']=='list_os_updates'):
            self.list_os_updates(request_id)
        elif (row['action']=='install_os_updates'):
            self.install_os_updates(request_id)
        elif (row['action']=='test_action'):
            #TODO - code an action handler for this
            self.report_error("ERROR: action handler is not ready yet", request_id)
        else:
            #-----this should never happen-----
            self.report_error("ERROR: unknown command '{}'".format(row['action']), request_id)
    
    #--------------------------------------------------------------------------------
    
    #-----works on requests based on data from the service_request table-----
    def do_work(self, rows_with_colnames: list):
        #-----go through the given work list-----
        for row in rows_with_colnames:
            #-----exit without doing more work if the run flag is set to stop-----
            if not self.should_run():
                return
            request_id = row['id']
            
            #-----mark the work as started-----
            self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Working'], 'start_date')
            
            if not self.is_action_allowed(row['service_name'], row['action']):
                self.report_error("ERROR: unknown service_name/action '{}/{}'".format(row['service_name'], row['action']), request_id)
                continue
            
            try:
                self.work_on_request_row(row)
            except Exception as e:
                err = "ERROR: crash while running request '{}/{}'\n{}".format(row['service_name'], row['action'], e)
                print(traceback.format_exc())
                self.report_error(err, request_id)
    
    #--------------------------------------------------------------------------------

    def check_for_work(self):
        """ Check if we have any work to do, then do the work
        """
        #-----first set the DB work_available flag to False-----
        self.util.work_available(False)
        self.should_checkwork(False)
        self.zzz_redis.zzz_checkwork_set(False)
        
        #-----check for service requests-----
        sql = 'SELECT * FROM service_request WHERE status=? order by req_date'
        params = (self.ConfigData['ServiceStatus']['Requested'],)
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        if (len(rows_with_colnames)):
            self.do_work(rows_with_colnames)
        else:
            print('check_for_work(): No data', flush=True)
        print('--------------------------------------------------------------------------------', flush=True)
    
    #--------------------------------------------------------------------------------
    
    def set_status(self, request_id, status: str):
        """ Set the status of a service
        """
        sql = "update service_request set status=? where id=?"
        params = (status, request_id)
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    #update service_request set wait_time=round((julianday(start_date)-julianday(req_date))*86400) where wait_time is null;
    #update service_request set work_time=round((julianday(end_date)-julianday(start_date))*86400) where work_time is null;
    def set_status_and_date(self, request_id, status: str, date_field: str, details: str=None):
        """ Set the status of a service
            Set the given date field to the current date/time
        """
        time_diff_field = ''
        date_calc_field = ''
        if (date_field=='end_date'):
            time_diff_field = 'work_time'
            date_calc_field = 'start_date'
        elif (date_field=='start_date'):
            time_diff_field = 'wait_time'
            date_calc_field = 'req_date'
        else:
            #ERROR
            print("set_status_and_date() ERROR: bad date_field value", flush=True)
            return

        sql=''
        params = ()
        if (details is None):
            sql = "update service_request set status=?, " + date_field + "=datetime('now'), "\
                  + time_diff_field + "=round((julianday('now')-julianday(" + date_calc_field + "))*86400) \
                  where id=?"
            params = (status, request_id)
        else:
            sql = "update service_request set status=?, " + date_field + "=datetime('now'), "\
                   + time_diff_field + "=round((julianday('now')-julianday(" + date_calc_field + "))*86400), details=? \
                  where id=?"
            params = (status, details, request_id)
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    def mark_request_done(self, request_id):
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Done'], 'end_date')
    
    #-----general error reporting for service requests-----
    def report_error(self, err_str: str, request_id):
        # save the end time and change status from Working to Error
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Error'], 'end_date', err_str)
    
    #--------------------------------------------------------------------------------
    
    # handles output from this type of error:
    #   except subprocess.CalledProcessError as e
    def report_error_subprocess(self, e, request_id):
        # save the end time and change status from Working to Error
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Error'], 'end_date', self.util.print_error_subprocess(e))
        # raise RuntimeError(err)
    
    #--------------------------------------------------------------------------------
    
    #-----run system commands-----
    # NOTE: iptables does not need restarts; loading a new config auto-applies new settings
    def system_command(self, request_id, service_name: str, command: str):
        """ Run the given system command on the given service
            Log results
            Keep track of the time involved
        """
        
        print(command + ': START', flush=True)
        
        # save the start time and change status from Requested to Working
        # 'update TABLE set status={status}, start_date={start}, wait_time=(start_time-) where id={}'
        run_service = service_name
        subprocess_commands = ['ls']
        err = ''
        if (service_name=='apache'):
            print('APACHE: {} - {}'.format(request_id, service_name), flush=True)
            run_service = 'apache2'
            #-----run the shell command-----
            subprocess_commands = ['systemctl', command, run_service]
        elif (service_name=='bind'):
            print('BIND: {} - {}'.format(request_id, service_name), flush=True)
            run_service = 'bind9'
            #-----run the shell command-----
            subprocess_commands = ['systemctl', command, run_service]
        elif (service_name=='linux'):
            print('LINUX: {} - {}'.format(request_id, service_name), flush=True)
            #-----run subprocess command without waiting for return, so we set the DB status here instead of below-----
            self.mark_request_done(request_id)
            self.util.restart_os()
            return
        elif (service_name=='openvpn'):
            print('OPENVPN: {} - {}'.format(request_id, service_name), flush=True)
            #-----run the shell command-----
            if command=='restart':
                subprocess_commands = ['/opt/zzz/python/bin/subprocess/openvpn-restart.sh']
            else:
                err = 'Bad openvpn command: ' + command
        elif (service_name=='squid'):
            print('SQUID: {} - {}'.format(request_id, service_name), flush=True)
            #-----run the shell command-----
            # subprocess_commands = ['systemctl', command, run_service]
            if command=='restart':
                subprocess_commands = ['/opt/zzz/python/bin/subprocess/squid-restart.sh']
            elif command=='reload':
                subprocess_commands = ['/opt/zzz/python/bin/subprocess/squid-reload.sh']
            elif command=='start':
                subprocess_commands = ['/opt/zzz/python/bin/subprocess/squid-start.sh']
            elif command=='stop':
                subprocess_commands = ['/opt/zzz/python/bin/subprocess/squid-stop.sh']
            else:
                err = 'Bad squid command: ' + command
        elif (service_name=='zzz'):
            print('ZZZ: {} - {}'.format(request_id, service_name), flush=True)
            #-----run subprocess command without waiting for return, so we set the DB status here instead of below-----
            self.mark_request_done(request_id)
            self.util.restart_zzz()
            return
        elif service_name=='zzz_icap':
            print('ZZZ_ICAP: {} - {}'.format(request_id, service_name), flush=True)
            #-----run the shell command-----
            subprocess_commands = ['systemctl', command, service_name]
            if command=='restart':
                # subprocess_commands = ['/opt/zzz/python/bin/subprocess/squid-restart.sh']
                subprocess_commands = ['/home/ubuntu/bin/icap-restart']
        else:
            #-----this should never happen-----
            err = 'Bad service name'
        
        if err != '':
            print(command + ': ' + err, flush=True)
            self.report_error(err, request_id)
            return
        
        #-----trigger the command-----
        try:
            output = subprocess.run(subprocess_commands, stdout=subprocess.PIPE, check=True, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            print('ERROR', flush=True)
            #TEST - this IF statement is only needed to check nonzero return codes, if it ends up being useful
            if e.returncode==0:
                print(e.output, flush=True)
            else:
                self.report_error_subprocess(e, request_id)
                return
        except OSError as e:
            self.report_error("OS ERROR: {0}".format(e), request_id)
            return
        
        #-----strip ANSI color codes from output-----
        stdout = self.util.remove_ansi_codes(output.stdout)
        
        #TEST
        print(command + ': output')
        print(stdout, flush=True)
        
        # save the end time and change status from Working to Done
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Done'], 'end_date', stdout)
        print(command + ': END', flush=True)
    
    #-----restart services-----
    # NOTE: iptables does not need restarts; loading a new config auto-applies new settings
    def restart_service(self, request_id, service_name, req_date):
        """ Restart the given service
        """
        print(f'RESTART: {request_id} - {service_name} - {req_date}', flush=True)
        if service_name=='zzz_icap':
            #-----ICAP server freezes on restart if squid is still running, so we stop squid first-----
            # self.system_command(request_id, 'squid', 'stop')
            self.system_command(request_id, service_name, 'restart')
            # self.system_command(request_id, 'squid', 'start')
        else:
            self.system_command(request_id, service_name, 'restart')
    
    #-----reload services-----
    # NOTE: iptables does not need restarts; loading a new config auto-applies new settings
    def reload_service(self, request_id, service_name):
        """ Reload the given service
        """
        self.system_command(request_id, service_name, 'reload')
    
    #--------------------------------------------------------------------------------
    
    def replace_domains(self, request_id, service_name, action):
        print('replace_domains(): START', flush=True)
        
        #TODO: ListManager will handle this list
        # self.bind.generate_dns_file(request_id, action)
        self.bind.generate_listmanager_dns_file(request_id, action)
        
        #TODO: hit the /z/reload_config URL since it loads faster than a full apache reload
        # self.db.request_reload('apache')
        self.util.apache_config_reload()

        # save the end time and change status from Working to Done
        self.mark_request_done(request_id)
        print('replace_domains(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    def replace_ips(self, request_id, service_name, action):
        print('replace_ips(): START', flush=True)
        
        self.update_file.generate_iptables_file(request_id, service_name, action)
        
        self.ipset.update_blacklist()
        self.ipset.install_blacklist()
        
        #-----useless here because it is a static list that can be installed once-----
        # self.iptables.make_iptables_denylist()
        # self.iptables.install_iptables_config()
        
        #TODO: hit the /z/reload_config URL since it loads faster than a full apache reload
        # self.db.request_reload('apache')
        self.util.apache_config_reload()
        
        # save the end time and change status from Working to Done
        self.mark_request_done(request_id)
        print('replace_ips(): END', flush=True)
    
    #--------------------------------------------------------------------------------

    def process_list_manager(self, request_id, service_name, action, details, req_date):
        print('process_list_manager(): START', flush=True)
        script_command = []
        if action=='download_lists':
            # the daily cron bash file includes a logfile output redirect
            script_command = ['/etc/cron.daily/zzz-download-lists']
            # script_command = ['/opt/zzz/python/bin/download-lists.py', '--all']
            print('download_lists')
        elif action=='rebuild_lists':
            #TODO: move this code into listmanager so a run_script is not needed
            script_command = ['/opt/zzz/python/bin/download-lists.py', '--generate-all-combined-lists', '--reload-bind']
            print('rebuild_lists')
        else:
            self.report_error(f'invalid action for service list_manager: {action}', request_id)
            return

        if self.util.run_script(script_command):
            self.mark_request_done(request_id)
        else:
            err = self.util.script_output
            self.report_error(f'{action} failed:\n{err}', request_id)

        # need the latest settings after a list update
        self.get_settings()

        #NOTE: no need to do bind reload here because download-lists.py will do it

        print('process_list_manager(): END', flush=True)

    #--------------------------------------------------------------------------------

    #-----get the latest settings and make sure all objects have it-----
    def get_settings(self):
        self.settings.get_settings()
        self.bind.settings = self.settings
        self.ipset.settings = self.settings
        self.iptables.settings = self.settings
        self.update_file.settings = self.settings

    #-----process settings changes-----
    # depending on the settings, may require DNS and/or iptables updates
    def process_settings(self, request_id, service_name, action, req_date):
        print(f'SETTINGS: {action} {request_id} - {service_name} - {req_date}', flush=True)
        print('process_settings(): START', flush=True)
        
        #-----always need to do both DNS and iptables-----
        # update the special settings config file and restart BIND
        file_data = ''
        self.get_settings()

        #-----ListManager - new design is a static file for bind settings config-----
        # self.update_file.save_settings_file(use_settings_checkboxes=True)
        self.update_file.save_settings_file()
        
        #-----install new iptables/ipsets based on settings settings-----
        # no need to update country lists - they only update when ipdeny files are updated
        # just run the ipset country install
        self.ipset.install_country_lists()

        #TODO: ListManager will handle these lists
        #-----allowlist needs updating/installing-----
        self.settings.generate_iptables_allowlist()
        self.ipset.update_allowlist()
        self.ipset.install_allowlist()

        # initialized on install with /opt/zzz/python/bin/init-iptables.py
        self.iptables.make_router_config()
        self.iptables.make_iptables_countries(self.settings)
        self.iptables.install_iptables_config()

        #TODO: ListManager will handle this list
        #-----make a new DNS file in case the Settings checkboxes are set: block_country_tld, block_country_tld_always-----
        # self.bind.update_bind_settings_files()

        self.bind.update_country_zone_file()
        
        #-----update other TLD blocks-----
        self.bind.update_tld_zone_file()
        should_block_tld_always = self.settings.is_setting_enabled('block_tld_always')
        should_block_country_tlds_always = self.settings.is_setting_enabled('block_country_tld_always')
        enable_test_server_dns_block = self.settings.is_setting_enabled('test_server_dns_block')
        self.zzz_template.make_bind_configs(should_block_tld_always, should_block_country_tlds_always, enable_test_server_dns_block)
        
        #-----generate new squid.conf and nobumpsites.acl files-----
        self.settings.generate_squid_nobumpsites()
        
        #-----reload apache, BIND, and Squid to make settings take effect-----
        self.db.request_reload('bind')
        self.db.request_reload('squid')
        self.db.request_reload('zzz_icap')
        self.zzz_redis.icap_reload_set()
        self.util.apache_config_reload()
        
        # save the end time and change status from Working to Done
        self.mark_request_done(request_id)

        #-----send the signal to the daemon to check for work-----
        self.util.work_available(1)
        self.zzz_redis.zzz_checkwork_set()

        print('process_settings(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    def run_code_diff(self, request_id, service_name, action):
        print('run_code_diff(): START', flush=True)
        
        stdout = ''
        #-----call module-----
        diff_code = zzzevpn.DiffCode.DiffCode(self.ConfigData)
        found_err = diff_code.file_directory_checks()
        if found_err:
            self.report_error(f'{action} failed:\n{diff_code.errors_found}', request_id)
            return
        diff_code.run_old_diff = True
        try:
            diff_code.run_diff_codebase()
        except:
            self.report_error("ERROR: run_code_diff() failed", request_id)
            return
        stdout = self.util.remove_ansi_codes('\n'.join(diff_code.diffcode_outputs))
        #-----call standalone script-----
        # if self.util.run_script('/opt/zzz/python/bin/diff_code.py'):
        #     stdout = self.util.remove_ansi_codes(self.util.subprocess_output.stdout)
        # else:
        #     self.report_error("ERROR: run_code_diff() failed", request_id)
        #     return

        #-----save the output to a file-----
        header_str = 'Code Diff Prepared: ' + self.util.current_datetime() + "\n\n"
        with open(self.ConfigData['UpdateFile']['zzz']['run_code_diff'], 'w') as updates_file:
            updates_file.write(header_str)
            updates_file.write(stdout)
        
        backup_file = self.update_file.make_backup_file(self.ConfigData['UpdateFile']['zzz']['run_code_diff'])
        
        # save the end time and change status from Working to Done
        self.mark_request_done(request_id)
        print('run_code_diff(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    def install_zzz_codebase(self, request_id, service_name, action):
        print('install_zzz_codebase(): START', flush=True)
        
        stdout = ''
        # if self.util.run_script(['/opt/zzz/python/bin/diff_code.py', '-i']):
        if self.util.run_script(['/opt/zzz/python/bin/subprocess/zzz-app-update.sh']):
            stdout = self.util.remove_ansi_codes(self.util.subprocess_output.stdout)
        else:
            self.report_error("ERROR: install_zzz_codebase() failed", request_id)
            return
        
        #-----save the output to a file-----
        header_str = 'Codebase Installed: ' + self.util.current_datetime() + "\n\n"
        with open(self.ConfigData['UpdateFile']['zzz']['installer_output'], 'w') as updates_file:
            updates_file.write(header_str)
            updates_file.write(stdout)
        
        backup_file = self.update_file.make_backup_file(self.ConfigData['UpdateFile']['zzz']['installer_output'])
        
        # save the end time and change status from Working to Done
        self.mark_request_done(request_id)
        print('install_zzz_codebase(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    # format accepted: "upgrade-zzz_12_13.sh" - script to upgrade from version 12 to 13
    # mandatory upgrade script, which must perform a restart on zzz
    # NOT ALLOWED: "version_12" where 12 is the git tag
    def validate_upgrade_details(self, details):
        print('validate_upgrade_details(): START', flush=True)
        upgrade_details = None
        #-----lookup what's installed-----
        db_version = self.util.zzz_version()
        installed_version = db_version['version']
        expected_version = installed_version+1
        
        #-----check the upgrade filename-----
        match = re.match(r'^upgrade\-zzz\_(\d{1,8})\_(\d{1,8})\.sh$', details)
        if not match:
            print(f'validate_upgrade_details(): ERROR - bad upgrade script in request details "{details}"')
            return None
        
        upgrading_from_version = int(match.group(1))
        upgrading_to_version = int(match.group(2))
        if upgrading_from_version==0 and upgrading_to_version==1:
            #-----allow tests regardless of installed version-----
            installed_version=0
            expected_version=1
        elif upgrading_from_version!=installed_version or upgrading_to_version!=expected_version:
            #-----bad version(s)-----
            print(f'validate_upgrade_details(): ERROR - bad upgrade script in request details - upgrading_from_version={upgrading_from_version}, upgrading_to_version={upgrading_to_version}, was expecting to upgrade version {installed_version} to {expected_version}')
            return None
        
        #-----do a checkout of the version we need if we're not running a test-----
        check_latest_version = zzzevpn.CheckLatestVersion(self.ConfigData)
        check_latest_version.util.set_script_error_output(False)
        if installed_version==0:
            print('validate_upgrade_details(): TEST upgrade, not doing a git checkout')
            if not check_latest_version.checkout_version(0):
                return None
        else:
            print(f'validate_upgrade_details(): git checkout {expected_version}')
            #-----download from github with a hard reset-----
            # similar to git_diff_pull() below
            #TODO: record errors somewhere
            if not check_latest_version.checkout_version(expected_version):
                return None
        
        upgrade_details = {
            'installed_version': installed_version,
            'upgrading_to_version': upgrading_to_version,
            'script_filepath': self.ConfigData['Directory']['UpgradeScript'] + '/' + details,
        }
        
        #-----check if the file exists-----
        if not os.path.isfile(upgrade_details['script_filepath']):
            print(f"validate_upgrade_details(): ERROR - upgrade script not found \"{upgrade_details['script_filepath']}\"")
            return None
        
        print('validate_upgrade_details(): END', flush=True)
        return upgrade_details
    
    #--------------------------------------------------------------------------------
    
    #-----run a given upgrade script to increase the system version by one-----
    # details field has the upgrade scriptname - run that script to perform that upgrade
    def upgrade_zzz(self, request_id, service_name, action, details):
        print('upgrade_zzz(): START', flush=True)
        
        upgrade_details = self.validate_upgrade_details(details)
        if not upgrade_details:
            self.report_error('ERROR: upgrade validation failed', request_id)
            return
        
        #-----mark it as Done now, in case the upgrade script wants to stop/start the daemon-----
        self.mark_request_done(request_id)
        
        print('upgrade_details: ' + pprint.pformat(upgrade_details))
        script_filepath = upgrade_details['script_filepath']
        upgrade_log = self.ConfigData['UpdateFile']['zzz']['upgrade_log']
        
        #-----run the upgrade script without waiting for it to return-----
        if self.util.run_without_wait([script_filepath, '''2>&1''', '''>>''', upgrade_log]):
            #-----assume it ran OK, exit now, expect the upgrade script to restart us-----
            self.should_run(False)
        else:
            #TODO: write error to DB and/or log, then continue
            self.report_error('ERROR: script run failed', request_id)
        
        print('upgrade_zzz(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    #-----run the selected dev upgrade-----
    # only runs one upgrade
    # similar to queue_upgrades() and upgrade_zzz() put together
    def dev_upgrade(self, request_id, service_name, action, details):
        print('dev_upgrade(): START', flush=True)
        
        check_latest_version = zzzevpn.CheckLatestVersion(self.ConfigData)
        check_latest_version.util.set_script_error_output(False)
        
        upgrade_details = check_latest_version.dev_upgrade(details)
        
        if upgrade_details['status']=='error':
            self.report_error(upgrade_details['output'], request_id)
            return
        
        #-----mark it as Done now, in case the upgrade script wants to stop/start the daemon-----
        self.mark_request_done(request_id)
        
        #-----run the upgrade (no need to queue it since we're only running one upgrade)-----
        print('DEV upgrade_details: ' + pprint.pformat(upgrade_details))
        script_filepath = upgrade_details['script_filepath']
        upgrade_log = self.ConfigData['UpdateFile']['zzz']['upgrade_log']
        
        #-----run the upgrade script without waiting for it to return-----
        if self.util.run_without_wait([script_filepath, '''2>&1''', '''>>''', upgrade_log]):
            #-----assume it ran OK, exit now, expect the upgrade script to restart us-----
            self.should_run(False)
        else:
            #TODO: write error to DB and/or log, then continue
            self.report_error('ERROR: script run failed', request_id)
        
        #-----log the results-----
        # self.util.append_output(self.ConfigData['UpdateFile']['zzz']['dev_upgrade_log'], output, True)
        
        print('dev_upgrade(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    # queue zero or more upgrade requests to get from the installed version to the current version
    # the upgrade request(s) are created by CheckLatestVersion.update_zzz_version_status()
    def queue_upgrades(self, request_id, service_name, action):
        print('queue_upgrades(): START', flush=True)
        
        check_latest_version = zzzevpn.CheckLatestVersion(self.ConfigData)
        check_latest_version.util.set_script_error_output(False)
        output = check_latest_version.queue_each_upgrade_script()
        
        #-----schedule a re-run of the version check after upgrades-----
        self.db.insert_service_request('zzz', 'version_checks')
        
        #-----log the results-----
        self.util.append_output(self.ConfigData['UpdateFile']['zzz']['upgrade_log'], output, True)
        
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Done'], 'end_date', output)
        
        print('queue_upgrades(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    def version_checks(self, request_id, service_name, action):
        print('version_checks(): START', flush=True)
        
        #-----do the version checks-----
        check_latest_version = zzzevpn.CheckLatestVersion(self.ConfigData)
        check_latest_version.util.set_script_error_output(False)
        check_latest_version.update_openvpn_version_status()
        check_latest_version.update_squid_version_status()
        
        called_by_cron = False
        if action=='version_checks_cron':
            called_by_cron = True
        status = check_latest_version.update_zzz_version_status(called_by_cron)
        
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Done'], 'end_date', status)
        # self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Error'], 'end_date')
        
        print('version_checks(): END', flush=True)
    
    #--------------------------------------------------------------------------------

    def process_git_branch(self, stdout):
        lines = stdout.split('\n')
        last_line = len(lines)
        git_branches = lines[1:last_line]
        with open(self.ConfigData['UpdateFile']['zzz']['git_branch_current'], 'w') as updates_file:
            updates_file.write(lines[0])
        with open(self.ConfigData['UpdateFile']['zzz']['git_branches'], 'w') as updates_file:
            updates_file.write('\n'.join(git_branches))

    # actions: 'git_branch', 'git_diff', 'git_pull', 'git_reset'
    def git_diff_pull(self, request_id, service_name, action, details):
        print('git_diff_pull(): START', flush=True)

        scriptname = ''
        script_filepath = ''
        cmd_list = []

        if action=='git_branch':
            scriptname = 'git-branch'
            script_filepath = self.ConfigData['Subprocess']['git-branch']
            cmd_list = ['sudo', '-H', '-u', 'ubuntu', script_filepath, '--include-status']
        elif action=='git_diff':
            scriptname = 'git-diff'
            script_filepath = self.ConfigData['Subprocess']['git-diff']
            cmd_list = ['sudo', '-H', '-u', 'ubuntu', script_filepath]
            if details:
                cmd_list.append(details)
        elif action=='git_pull':
            scriptname = 'git-pull'
            script_filepath = self.ConfigData['Subprocess']['git-pull']
            cmd_list = ['sudo', '-H', '-u', 'ubuntu', script_filepath]
        elif action=='git_reset':
            scriptname = 'git-checkout'
            script_filepath = self.ConfigData['Subprocess']['git-checkout']
            #TODO: 'master' --> details
            # cmd_list = ['sudo', '-H', '-u', 'ubuntu', script_filepath, 'master']
            cmd_list = ['sudo', '-H', '-u', 'ubuntu', script_filepath]
            if details:
                cmd_list.append('branch')
                cmd_list.append(details)
        else:
            if not action:
                action = ''
            self.report_error("ERROR: git_diff_pull() invalid action " + action, request_id)
            return

        # sudo -H -u ubuntu /home/ubuntu/bin/git-branch
        # sudo -H -u ubuntu /home/ubuntu/bin/git-diff
        # sudo -H -u ubuntu /home/ubuntu/bin/git-pull
        # sudo -H -u ubuntu /home/ubuntu/bin/git-checkout master
        stdout = ''
        stderr = ''
        ran_OK = True
        if self.util.run_script(cmd_list):
            stdout = self.util.remove_ansi_codes(self.util.subprocess_output.stdout)
            if stdout is None:
                stdout = ''
        else:
            ran_OK = False
            if self.util.subprocess_output:
                if self.util.subprocess_output.stdout is not None:
                    stdout = self.util.remove_ansi_codes(self.util.subprocess_output.stdout)
                if self.util.subprocess_output.stderr is not None:
                    stderr = self.util.remove_ansi_codes(self.util.subprocess_output.stderr)
                stdout += '\n' + stderr
            else:
                stdout = self.util.script_output
        
        #-----save the output to a file-----
        if action=='git_branch':
            self.process_git_branch(stdout)
        else:
            header_str = 'Git Function Completed({}): {}\n\n'.format(action, self.util.current_datetime())
            with open(self.ConfigData['UpdateFile']['zzz']['git_output'], 'w') as updates_file:
                updates_file.write(header_str)
                updates_file.write(stdout)
            backup_file = self.update_file.make_backup_file(self.ConfigData['UpdateFile']['zzz']['git_output'])
        
        # save the end time and change status from Working to Done/Error
        if ran_OK:
            self.mark_request_done(request_id)
        else:
            self.report_error("ERROR: git_diff_pull() failed for script " + scriptname, request_id)
        
        print('git_diff_pull(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    #TODO: process this faster - run_without_wait(pytest)
    def run_pytest(self, request_id, service_name, action):
        print('run_pytest(): START', flush=True)
        
        stdout = ''
        script_command = ['/opt/zzz/python/bin/subprocess/zzz-pytest.sh', '--include-coverage']
        # the script will return an error on any test failure
        # just print all output and errors to the pytest log without reporting it as a script/request failure
        if self.util.run_script(script_command):
            stdout = self.util.subprocess_output.stdout
        else:
            stdout = self.util.script_output
        if not stdout:
            stdout = ''

        #TEST - backup file not needed?
        # backup_file = self.update_file.make_backup_file(self.ConfigData['UpdateFile']['zzz']['run_pytest'])
        
        # save the end time and change status from Working to Done
        self.mark_request_done(request_id)
        print('run_pytest(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    #-----process zzz app updates-----
    def process_zzz(self, request_id, service_name, action, details, req_date):
        print(f'ZZZ: {action} {request_id} - {service_name} - {req_date}', flush=True)
        print('process_zzz(): START', flush=True)
        
        if action=='run_code_diff':
            self.run_code_diff(request_id, service_name, action)
        elif action=='run_pytest':
            self.run_pytest(request_id, service_name, action)
        elif action=='install_zzz_codebase':
            self.install_zzz_codebase(request_id, service_name, action)
        elif action=='dev_upgrade':
            self.dev_upgrade(request_id, service_name, action, details)
        elif action=='queue_upgrades':
            self.queue_upgrades(request_id, service_name, action)
        elif action=='upgrade':
            self.upgrade_zzz(request_id, service_name, action, details)
        elif action in ['version_checks', 'version_checks_cron']:
            self.version_checks(request_id, service_name, action)
        elif action in ['git_branch', 'git_diff', 'git_pull', 'git_reset']:
            self.git_diff_pull(request_id, service_name, action, details)
        else:
            self.report_error('invalid action for service zzz: ' + action, request_id)
        
        print('process_zzz(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    #-----ip log processing-----
    # action=add_ips
    # action=replace_ips
    # action=delete_log_all
    # action=delete_log_old
    # action=parse_logs
    def process_iptables(self, request_id, service_name, action, details, req_date):
        print(f'IPTABLES: {action} ReqID={request_id} - {req_date}', flush=True)
        if (action in ['add_ips', 'replace_ips']):
            self.replace_ips(request_id, service_name, action)
            return
        
        ip_log_parser = zzzevpn.IPtablesLogParser(self.ConfigData)
        if action=='delete_log_all':
            ip_log_parser.delete_ip_log_db(delete_all=True)
        elif action=='delete_log_old':
            ip_log_parser.delete_ip_log_db(entries_older_than=30)
        elif action=='parse_logs':
            #-----call the logrotate command-----
            # logs won't be parsed unless they are rotated first
            # normally they rotate when the size exceeds 3MB, so we have to force an early rotation
            self.util.run_script(['/usr/sbin/logrotate', '--force', '/etc/logrotate.d/zzz-iptables'])
            
            #-----give it time to get the log rotation done before we parse the logs-----
            # touch /var/log/zzz/cron/ip-logs-rotated
            self.util.sleep_until_file_updated(3, '/var/log/zzz/ip-logs-rotated')
            
            #-----call the log parser cron script-----
            # it will auto-quit if it finds a copy of the cron running
            script_filepath = self.ConfigData['Subprocess']['update-ip-log']
            update_ip_log = self.ConfigData['UpdateFile']['iptables']['update-ip-log']
            if not self.util.run_without_wait([script_filepath, '--update', '''2>&1''', '''>>''', update_ip_log]):
                #TODO: write error to DB and/or log, then continue
                self.report_error('ERROR: script run failed', request_id)
        
        ran_OK = True
        # save the end time and change status from Working to Done/Error
        if ran_OK:
            self.mark_request_done(request_id)
        else:
            self.report_error(f'ERROR: process_iptables() failed for action={action}')
    
    #--------------------------------------------------------------------------------
    
    #-----squid log processing-----
    # action=delete_log_all
    # action=delete_log_old
    def process_squid(self, request_id, service_name, action, details, req_date):
        print(f'SQUID: {action} ReqID={request_id} - {req_date}', flush=True)
        
        squid_log_parser = zzzevpn.SquidLogParser(self.ConfigData, self.db, self.util, self.settings)
        if action=='delete_log_all':
            squid_log_parser.delete_squid_log_db(delete_all=True)
        elif action=='delete_log_old':
            squid_log_parser.delete_squid_log_db(entries_older_than=30)
        
        ran_OK = True
        # save the end time and change status from Working to Done/Error
        if ran_OK:
            self.mark_request_done(request_id)
        else:
            self.report_error(f'ERROR: process_squid() failed for action={action}')

    #--------------------------------------------------------------------------------
    
    #-----get updates list for linux and write to a file that apache can read-----
    def list_os_updates(self, request_id):
        print('list_os_updates(): START', flush=True)
        
        try:
            script_filepath = self.ConfigData['Subprocess']['os-list-updates']
            output = subprocess.run([script_filepath], stdout=subprocess.PIPE, check=True, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            self.report_error_subprocess(e, request_id)
            return
        except OSError as e:
            self.report_error("OS ERROR: {0}".format(e), request_id)
            return
        
        #-----strip ANSI color codes from output-----
        stdout = self.util.remove_ansi_codes(output.stdout)

        #-----save the output to a file-----
        header_str = 'List Prepared: ' + self.util.current_datetime() + "\n\n"
        with open(self.ConfigData['UpdateFile']['linux']['list_os_updates'], 'w') as updates_file:
            updates_file.write(header_str)
            updates_file.write(stdout)
        
        backup_file = self.update_file.make_backup_file(self.ConfigData['UpdateFile']['linux']['list_os_updates'])
        
        # save the end time and change status from Working to Done
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Done'], 'end_date', backup_file)
        print('list_os_updates(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    #-----apply updates to linux-----
    def install_os_updates(self, request_id):
        print('install_os_updates(): START', flush=True)
        
        try:
            script_filepath = self.ConfigData['Subprocess']['os-install-updates']
            output = subprocess.run([script_filepath], stdout=subprocess.PIPE, check=True, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            self.report_error_subprocess(e, request_id)
            return
        except OSError as e:
            self.report_error("OS ERROR: {0}".format(e), request_id)
            return
        
        #-----strip ANSI color codes from output-----
        stdout = self.util.remove_ansi_codes(output.stdout)

        #-----save the output to a file-----
        header_str = 'Installation Done: ' + self.util.current_datetime() + "\n\n"
        with open(self.ConfigData['UpdateFile']['linux']['os_update_output'], 'w') as os_update_output_file:
            os_update_output_file.write(header_str)
            os_update_output_file.write(stdout)
        
        backup_file = self.update_file.make_backup_file(self.ConfigData['UpdateFile']['linux']['os_update_output'])
        
        # save the end time and change status from Working to Done
        self.set_status_and_date(request_id, self.ConfigData['ServiceStatus']['Done'], 'end_date', backup_file)
        
        #-----rebuild the MOTD file, ignore errors-----
        self.util.run_script(['/home/ubuntu/bin/regen-motd'])
        
        print('install_os_updates(): END', flush=True)
