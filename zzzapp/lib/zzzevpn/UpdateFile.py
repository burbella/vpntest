import os
import pathlib
import shutil
import subprocess
import time

#-----import modules from the lib directory-----
# import zzzevpn.Config
# import zzzevpn.DB
# import zzzevpn.ListManager
# import zzzevpn.Util
import zzzevpn

#-----Update and Install Config Files-----
# BIND:
# add_domains:
#   look for the previous config file
#   if found:
#       append the given file_data to the list
#   else:
#       generate a new list from the latest REPLACE plus all subsequent ADDs
#   call save_and_install()
#
# replace_domains:
#   generate a new domains list from the given file_data
#   call save_and_install()
##############################
# save_and_install(list, service, action, src_filepath):
#   de-dup and sort the new list
#   save it as a new config file
#   save the src filepath in the DB
#   install the config file
##############################
# SQUID:
# similar to BIND add/replace
# TWO config files: subdomains(for HTTP), IP's(for HTTPS)
# IP's need daily auto-refreshing in case of DNS changes
#   use a cron:
#       insert a service_request daily
#       re-check IP's for all subdomains
#       update configs
#       reload squid
#
# add_subdomains:
#   look for the previous config files(subdomains, IP's)
#   if found:
#       dns_lookup IP's for all new subdomains, append it to the current IP list
#       append the given file_data to the subdomains list
#   else:
#       generate a new subdomains list from the latest REPLACE plus all subsequent ADDs
#       dns_lookup IP's for all subdomains
#   call save_and_install(subdomains)
#   call save_and_install(IP's)
#
# replace_subdomains:
#   generate a new subdomains list from the given file_data
#   dns_lookup IP's for all subdomains
#   call save_and_install(subdomains)
#   call save_and_install(IP's)
class UpdateFile:
    'Update and Install Config Files'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    list_manager: zzzevpn.ListManager = None
    settings: zzzevpn.Settings = None
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
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
        # no need to do self.settings.get_settings() here, it is only needed by save_settings_file() below
        self.list_manager = zzzevpn.ListManager(self.ConfigData, self.db, self.util)
    
    #--------------------------------------------------------------------------------
    
    #-----create a pid file for controlling the process-----
    # def create_pid_file(self):
    #     with open(self.ConfigData['UpdateFile']['pid'], 'w') as pid_file:
    #         pid_file.write(str(os.getpid()))
    
    #--------------------------------------------------------------------------------
    
    def make_backup_file(self, filepath: str):
        #-----backup the given file to keep an updates history-----
        # file.txt --> file.txt.2017-11-30-01-02-03 (YYYY-MM-DD-HH-MI-SS)
        #TODO: make sure filepath exists, make sure backup_file does not exist
        backup_file = filepath + '.' + self.util.filename_datetime()
        
        #-----if the file exists, wait a second to get a new filename and try again-----
        path = pathlib.Path(backup_file)
        if path.is_file():
            time.sleep(1)
            backup_file = filepath + '.' + self.util.filename_datetime()
        
        try:
            # print('TEST: cp -p ' + filepath + ' ' + backup_file, flush=True)
            output = subprocess.run(['cp', '-p', filepath, backup_file], stdout=subprocess.PIPE, check=True, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            #-----backup problems are not a fatal error, so we just print an error message without updating the service request table status-----
            self.util.print_error_subprocess(e)
            return
        return backup_file
    
    #--------------------------------------------------------------------------------
    
    def save_file(self, src_filepath: str, domain_list: list, set_owner: str='root', make_backup: bool=True):
        print('save_file(): START', flush=True)
        
        # save it as the main domain list file
        with open(src_filepath, 'w') as updates_file:
            updates_file.write("\n".join(domain_list))

        if not make_backup:
            return

        # copy to a new backup file
        backup_file = self.make_backup_file(src_filepath)
        
        # make sure apache can only read it (chmod 644, chown root.root)
        allowed_owners = ['root']
        if set_owner not in allowed_owners:
            set_owner = 'root'
        shutil.chown(backup_file, set_owner, set_owner)
        os.chmod(backup_file, 0o644)
        
        print('save_file(): END', flush=True)
        return backup_file
    
    #--------------------------------------------------------------------------------
    
    #TODO: re-write to call IPset.py for most of these operations
    #-----make the latest iptables config-----
    # default iptables rules for VPN & routing are set in the NAT tables (don't edit this here)
    # custom IP blocks are set in the FILTER tables (use this)
    #
    #TODO: similar to generate_dns_file() - make a common function
    #TODO: support for ip6tables
    #TODO: support for CIDR blocks (/24, etc)
    #
    # EXAMPLE FILE:
    # *filter
    # :INPUT ACCEPT
    # :FORWARD ACCEPT
    # :OUTPUT ACCEPT
    # -A INPUT -d 0.0.0.0 -j DROP
    # -A FORWARD -d 0.0.0.0 -j DROP
    # COMMIT
    #
    def generate_iptables_file(self, request_id, service_name, action):
        print('generate_iptables_file(): START', flush=True)
        
        # assembled_list = self.assemble_list(request_id, service_name, action)
        assembled_list = self.list_manager.assemble_list(request_id, service_name, action)
        
        #TODO: make this like generate_dns_file()
        #   use get_settings_ips() instead of get_settings_domains()
        #-----combine the settings list with the main list-----
        # settings_list = self.settings_list_ips(request_id, service_name, action)
        # assembled_list.extend(settings_list)
        
        #TEST
        print('Assembled List:')
        print(assembled_list, flush=True)
        
        # de-dup and sort the new list
        # ip_list = sorted(set(assembled_list))
        ip_list = self.util.unique_sort(assembled_list)
        
        #-----set this to the filename being copied, after generating the file and saving it with a date in the filename-----
        src_filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath']
        backup_file = self.save_file(src_filepath, ip_list)
        
        # save the src filepath in the DB
        sql = 'update update_file set src_filepath=? where service_request_id=?'
        params = (backup_file, request_id)
        self.db.query_exec(sql, params)
        
        print('generate_iptables_file(): END', flush=True)
    
    #--------------------------------------------------------------------------------
    
    def save_settings_file(self, use_settings_checkboxes=False):
        print('save_settings_file(): START', flush=True)
        
        if not self.settings.SettingsData:
            self.settings.get_settings()
        
        file_data = "// Zzz auto-generated settings file\n\n"
        file_data += 'include "{}/countries.conf";\n'.format(self.ConfigData['Directory']['Settings'])
        file_data += 'include "{}/tlds.conf";\n'.format(self.ConfigData['Directory']['Settings'])

        # ListManager will handle these lists in the new design
        if use_settings_checkboxes:
            for checkbox in ['autoplay', 'social', 'telemetry']:
                if self.settings.is_setting_enabled(checkbox):
                    file_data += 'include "{}/{}.conf";\n'.format(self.ConfigData['Directory']['Settings'], checkbox);
                    print('set '+ checkbox, flush=True)

        filepath = self.ConfigData['UpdateFile']['bind']['named_settings']
        with open(filepath, 'w') as settings_file:
            settings_file.write(file_data)
        
        # set permissions (chmod 644, chown root.bind)
        shutil.chown(filepath, 'root', 'bind')
        os.chmod(filepath, 0o644)
        
        print('save_settings_file(): END', flush=True)
    
    #--------------------------------------------------------------------------------
