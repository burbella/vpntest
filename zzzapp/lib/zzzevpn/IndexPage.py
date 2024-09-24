import psutil
import re

#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.TaskHistory

class IndexPage:
    'Index page'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    settings: zzzevpn.Settings = None
    task_history: zzzevpn.TaskHistory = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    body: str = ''
    IndexHTML: dict = {}
    is_running = '<span class="text_green">yes</span>'
    is_not_running = '<span class="text_red">no</span>'
    
    # regex_pattern_limited_motd = r'\d+ package(|s) can be updated.+$'
    # regex_pattern_packages = r'(\d+) package(|s) can be updated\.'
    # regex_pattern_security = r'(\d+) update(|s) (is a security update|are security updates)\.'
    # regex_pattern_restart_required = r'\*\*\* System restart required \*\*\*'
    #
    # ubuntu 20.04 example:
    #   121 updates can be installed immediately.
    #   8 of these updates are security updates.
    #   *** System restart required ***
    #
    # ubuntu 20.04.2 example:
    #   54 updates can be applied immediately.
    #   6 of these updates are standard security updates.
    regex_pattern_could_not_install = r'\n2 updates could not be installed automatically. For more details,\nsee /var/log/unattended-upgrades/unattended-upgrades.log'
    regex_pattern_limited_motd = r'\d+ update(|s) can be (installed|applied) immediately.+$'
    regex_pattern_packages = r'(\d+) update(|s) can be (installed|applied) immediately\.'
    regex_pattern_security = r'(\d+) of these update(|s) (is a|are) (|standard )security update(|s)\.'
    
    #-----text is in this file: /var/run/reboot-required -----
    # the file only exists when a reboot is needed
    regex_pattern_restart_required = r'\*\*\* System restart required \*\*\*'
    
    regex_pattern_trailing_newlines = r'\n+$'
    
    regex_could_not_install = re.compile(regex_pattern_could_not_install, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    # regex_linefeed = re.compile(r'\n', re.DOTALL | re.IGNORECASE | re.MULTILINE)
    regex_limited_motd = re.compile(regex_pattern_limited_motd, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    regex_packages = re.compile(regex_pattern_packages, re.IGNORECASE)
    regex_security = re.compile(regex_pattern_security, re.IGNORECASE)
    regex_restart_required = re.compile(regex_pattern_restart_required, re.IGNORECASE)
    regex_trailing_newlines = re.compile(regex_pattern_trailing_newlines, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    
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
        self.init_vars()
        if not self.settings.SettingsData:
            self.settings.get_settings()
        self.task_history = zzzevpn.TaskHistory(self.ConfigData, self.db, self.util, self.settings)
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self) -> None:
        #-----prep the HTML values-----
        self.IndexHTML = {
            'CSP_NONCE': '',
            'MOTD': '',
            'TaskStatus': '',
            'OpenVPNUpdatesNeeded': '',
            'ZzzUpdatesNeeded': '',
            'RunningProcesses': '',
            'RebootNeededWarning': '',
            
            'hide_links_default': '',
            'hide_links_by_function': '',
        }
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ: dict, pagetitle: str=None) -> str:
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)

        OpenVPNUpdatesNeeded = self.util.get_filedata(self.ConfigData['VersionFiles']['openvpn'])

        self.IndexHTML['MOTD'] = self.get_motd()
        self.IndexHTML['TaskStatus'] = self.task_history.get_task_status(100)
        self.IndexHTML['OpenVPNUpdatesNeeded'] = OpenVPNUpdatesNeeded
        self.IndexHTML['RunningProcesses'] = self.show_running_processes()
        self.IndexHTML['RebootNeededWarning'] = ''
        
        ZzzUpdatesNeeded = self.util.get_filedata(self.ConfigData['VersionFiles']['zzz'])
        
        if self.util.reboot_needed():
            favicon_custom = self.webpage.WebpageHeaderHTML['favicon_custom']
            self.IndexHTML['RebootNeededWarning'] = f'''
            <table class="no_border">
                <tr>
                    <td class="no_border"><img src="/img/{favicon_custom}favicon-48.png" class="zzz_img_logo"></td>
                    <td class="no_border text_red font-large valign_middle"><b>Reboot Needed</b></td>
                </tr>
            </table>
            '''
        
        db_version = self.util.zzz_version()
        if db_version['version']<db_version['available_version']:
            zzz_upgrade_url = self.ConfigData['URL']['UpdateZzz']
            ZzzUpdatesNeeded = f'{ZzzUpdatesNeeded}<br><a href="{zzz_upgrade_url}">Zzz Upgrade Page</a>'
        
        self.IndexHTML['ZzzUpdatesNeeded'] = ZzzUpdatesNeeded
        
        if self.settings.is_setting_enabled('links_by_function'):
            self.IndexHTML['hide_links_default'] = 'hide_item'
            self.IndexHTML['hide_links_by_function'] = ''
        else:
            self.IndexHTML['hide_links_default'] = ''
            self.IndexHTML['hide_links_by_function'] = 'hide_item'
        
        #-----Content Security Policy(CAP) nonce generated by apache, must be included or inline JS gets disabled-----
        self.IndexHTML['CSP_NONCE'] = environ['CSP_NONCE']
        
        output = self.webpage.make_webpage(environ, self.make_IndexPage())
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def make_IndexPage(self) -> str:
        body = self.webpage.load_template('IndexPage')
        return body.format(**self.IndexHTML)
    
    #--------------------------------------------------------------------------------
    
    #-----get MOTD file contents and format it for the web-----
    # EXAMPLE:
    #   43 packages can be updated. (<a href="/z/update_os">Package Update Page</a>)
    #   1 update is a security update. (this will auto-install within 24 hours)
    #   *** System restart required *** (bold)
    def get_motd(self) -> str:
        motd_data = self.util.get_filedata(self.ConfigData['DataFile']['motd'])
        #-----apply web formatting-----
        match = self.regex_limited_motd.search(motd_data)
        if match:
            motd_data = match[0]
        #-----highlight text if new (non-security) packages are available-----
        match = self.regex_packages.search(motd_data)
        if match:
            num_packages = int(match[1])
            if num_packages>0:
                replacement_str = '<span class="text_red"><b>{}</b></span> (<a href="{}">Package Update Page</a>)'.format(match[0], self.ConfigData['URL']['UpdateOS'])
                motd_data = self.regex_packages.sub(replacement_str, motd_data)
        #-----highlight text if OS security updates are available-----
        match = self.regex_security.search(motd_data)
        if match:
            num_security = int(match[1])
            if num_security>0:
                replacement_str = '<span class="text_red"><b>{}</b><br>&nbsp;&nbsp;&nbsp;&nbsp;(this will auto-install within 24 hours)</span>'.format(match[0])
                motd_data = self.regex_security.sub(replacement_str, motd_data)
        #-----highlight text if a system restart is required (from previous OS auto-updates)-----
        match = self.regex_restart_required.search(motd_data)
        if match:
            motd_data = self.regex_restart_required.sub('<span class="text_red"><b>{}</b></span>'.format(match[0]), motd_data)
            self.util.reboot_needed(True)
        
        #-----hide the squid could-not-install warning-----
        # squid consists of exactly 2 updates
        # warning text:
        #   2 updates could not be installed automatically. For more details,
        #   see /var/log/unattended-upgrades/unattended-upgrades.log
        # the number could be higher if there are real problems with other ubuntu updates
        # squid is never updated through apt-get, so this "2 updates" warning should be hidden
        match = self.regex_could_not_install.search(motd_data)
        if match:
            motd_data = self.regex_could_not_install.sub('', motd_data)
        
        #-----clear trailing newlines-----
        motd_data = self.regex_trailing_newlines.sub('', motd_data)
        
        #-----add <br> tags for all linefeeds-----
        return self.util.add_html_line_breaks(motd_data)
    
    #--------------------------------------------------------------------------------
    
    #TODO: the non-display part of this belongs in Util.py
    # OS default: 'python3'
    # venv: '/opt/zzz/venv/bin/python3'
    def show_running_processes(self) -> str:
        # in process list: name --> cmdline --> display_name/found
        python3_processes = ['services_zzz.py', 'zzz-icap-server']
        processes_to_check = {
            # name - abbreviated to 15 chars by psutil
            'services_zzz.py': {
                # cmdline
                '/opt/zzz/python/bin/services_zzz.py': {
                    # show this in webpage
                    'display_name': 'zzz',
                    'found': False,
                },
            },
            'zzz-icap-server': {
                '/opt/zzz/python/bin/zzz-icap-server.py': {
                    'display_name': 'zzz_icap',
                    'found': False,
                },
            },
            'squid': {
                '/usr/sbin/squid': {
                    'display_name': 'Squid',
                    'found': False,
                    'servers_expected': {
                        '/etc/squid/squid.conf': 'squid',
                        '/etc/squid/squid-icap.conf': 'squid-icap',
                    },
                    'servers_running': [], # squid, squid-icap
                },
            },
            'apache2': {
                '/usr/sbin/apache2': {
                    'display_name': 'Apache',
                    'found': False,
                    'child_processes': 0,
                },
            },
            'named': {
                '/usr/sbin/named': {
                    'display_name': 'BIND',
                    'found': False,
                },
            },
            'openvpn': {
                '/usr/local/sbin/openvpn': {
                    'display_name': 'OpenVPN',
                    'found': False,
                    'servers_expected': {
                        'server.conf': 'open',
                        'server-squid.conf': 'open-squid',
                        'server-icap.conf': 'dns-icap',
                        'server-dns.conf': 'dns',
                        'server-filtered.conf': 'dns-squid',
                    },
                    'servers_running': [], # open, open-squid, dns, dns-squid, dns-icap
                },
            },
        }
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username']):
            process_name = proc.info['name']
            process_needed = processes_to_check.get(process_name, None)
            if process_needed is None:
                continue
            
            if not proc.info['cmdline']:
                continue
            
            process_cmdline = proc.info['cmdline'][0]
            if process_name in python3_processes:
                process_cmdline = proc.info['cmdline'][1]
            
            if process_cmdline not in process_needed.keys():
                continue
            
            #-----deal with duplicates-----
            process_username = proc.info['username']
            if process_name=='apache2' and process_username=='www-data':
                processes_to_check[process_name][process_cmdline]['child_processes'] += 1
                continue
            
            #-----flag it as found-----
            processes_to_check[process_name][process_cmdline]['found'] = True
            
            if process_name=='squid':
                squid_conf_file = '/etc/squid/squid.conf'
                if len(proc.info['cmdline'])>3:
                    squid_conf_file = proc.info['cmdline'][3]
                squid_servername = processes_to_check[process_name][process_cmdline]['servers_expected'].get(squid_conf_file, None)
                if squid_servername:
                    processes_to_check[process_name][process_cmdline]['servers_running'].append(squid_servername)
            
            if process_name=='openvpn':
                openvpn_conf_file = proc.info['cmdline'][7]
                openvpn_servername = processes_to_check[process_name][process_cmdline]['servers_expected'][openvpn_conf_file]
                processes_to_check[process_name][process_cmdline]['servers_running'].append(openvpn_servername)
        
        #-----make HTML rows for found processes-----
        body_rows = []
        for process_name in processes_to_check.keys():
            for process_cmdline in processes_to_check[process_name].keys():
                display_name = processes_to_check[process_name][process_cmdline]['display_name']
                show_running = self.is_running
                process_details = ''
                if processes_to_check[process_name][process_cmdline]['found']:
                    if process_name == 'apache2':
                        child_processes = processes_to_check[process_name][process_cmdline]['child_processes']
                        process_details = '(' + str(child_processes) + ' servers)'
                    elif process_name == 'squid':
                        #-----check all expected squid servers-----
                        for squid_servername in processes_to_check[process_name][process_cmdline]['servers_expected'].values():
                            if squid_servername in processes_to_check[process_name][process_cmdline]['servers_running']:
                                show_running = self.is_running
                            else:
                                show_running = self.is_not_running
                            table_row = f'<tr><td>{display_name}</td><td>{show_running} {squid_servername}</td></tr>'
                            body_rows.append(table_row)
                        continue
                    elif process_name == 'openvpn':
                        #-----check all expected openvpn servers-----
                        for openvpn_servername in processes_to_check[process_name][process_cmdline]['servers_expected'].values():
                            if openvpn_servername in processes_to_check[process_name][process_cmdline]['servers_running']:
                                show_running = self.is_running
                            else:
                                show_running = self.is_not_running
                            table_row = f'<tr><td>{display_name}</td><td>{show_running} {openvpn_servername}</td></tr>'
                            body_rows.append(table_row)
                        continue
                else:
                    # unless openvpn and apache are both running, this page will not be accessible
                    show_running = self.is_not_running
                table_row = f'<tr><td>{display_name}</td><td>{show_running} {process_details}</td></tr>'
                body_rows.append(table_row)
        
        return '\n'.join(body_rows)
    
    #--------------------------------------------------------------------------------
