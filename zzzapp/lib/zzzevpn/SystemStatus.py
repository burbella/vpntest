#-----Manages System Commands - reload, restart, etc-----

import re

#-----package with all the Zzz modules-----
import zzzevpn

class SystemStatus:
    'show system status - top, etc'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    data_validation: zzzevpn.DataValidation = None
    
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
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'System Status')
    
    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    def handle_post(self, environ, request_body_size):
        # no POST expected
        return
    
    #--------------------------------------------------------------------------------
    
    #-----status_page functions as pagetitle from zzz.wsgi-----
    def make_webpage(self, environ, status_page):
        output = ''
        pagetitle = ''
        if status_page=='top':
            (output, pagetitle) = self.show_top(environ)
        elif status_page=='installed_packages':
            (output, pagetitle) = self.show_installed_packages()
        elif status_page=='installed_software':
            (output, pagetitle) = self.show_installed_software()

        self.webpage.update_header(environ, pagetitle)
        output = self.webpage.make_webpage(environ, output)
        
        return output
    
    #--------------------------------------------------------------------------------

    def run_command(self, subprocess_commands):
        if self.util.run_script(subprocess_commands):
            return self.util.subprocess_output.stdout
        return self.util.script_output

    #--------------------------------------------------------------------------------
    
    #-----show top output and disk usage-----
    def show_top(self, environ: dict):
        pagetitle = 'System Status'

        datetime_now = self.util.current_datetime()

        #-----top-----
        # subprocess_commands = ['/usr/bin/top', '-b', '-o', '%MEM', '-n', '1']
        subprocess_commands = ['/opt/zzz/python/bin/subprocess/top.sh']
        top_result = self.run_command(subprocess_commands)

        #-----disk usage-----
        subprocess_commands = ['/bin/df', '-h']
        df_result = self.run_command(subprocess_commands)
        disk_usage = []
        for line in df_result.split('\n'):
            if ('G' in line) or ('Filesystem' in line):
                disk_usage.append(line)

        db_filesize = self.util.get_filesize(self.ConfigData['DBFilePath']['Services'])
        db_filesize = round(db_filesize/self.util.standalone.MEGABYTE, 2)

        large_directories = ['/opt/zzz/iptables/log', '/var/log/iptables']
        iptables_files = []
        for dir in large_directories:
            subprocess_commands = ['/usr/bin/du', '-sh', dir]
            result = self.run_command(subprocess_commands)
            iptables_files.append(result)
        memory = zzzevpn.Memory(self.ConfigData, self.db, self.util)
        mem_info = memory.check_system_memory()
        memory_usage = f'''Total: {mem_info['total']} MB<br>Free: {mem_info['free']} MB<br>Used: {mem_info['used']} MB<br>Available: {mem_info['avail']}<br>Effective Available: {mem_info['effective_avail']} MB'''

        SystemStatusHTML = {
            'datetime_now': datetime_now,
            'db_filesize': db_filesize,
            'disk_usage': self.util.ascii_to_html_with_line_breaks('\n'.join(disk_usage)),
            'iptables_files': '<br>\n'.join(iptables_files),
            'memory_usage': memory_usage,
            'top_result': top_result,
        }

        #-----output-----
        self.webpage.update_header(environ, pagetitle)
        body = self.webpage.load_template('SystemStatus')
        return (body.format(**SystemStatusHTML), pagetitle)
    
    #--------------------------------------------------------------------------------
    
    def show_installed_packages(self):
        pagetitle = 'Recently Installed Packages'
        subprocess_commands = ['/opt/zzz/python/bin/subprocess/os-list-installed-packages.sh']
        result = self.run_command(subprocess_commands)
        output = '''<pre>{}</pre>'''.format(result)
        return (output, pagetitle)
    
    #--------------------------------------------------------------------------------
    
    def show_installed_software(self):
        pagetitle = 'Installed Software'
        subprocess_commands = ['/opt/zzz/python/bin/subprocess/list-installed-software.sh']
        result = self.util.ascii_to_html_with_line_breaks(self.run_command(subprocess_commands))

        subprocess_commands = ['/opt/zzz/venv/bin/pip3','list']
        pip3_result = self.run_command(subprocess_commands)

        all_entries = ''
        requirements_filedata = self.util.get_filedata('/opt/zzz/install/requirements.txt')
        if requirements_filedata:
            req_regex = re.compile(r'^(.+?)[=<>]', re.DOTALL | re.IGNORECASE)
            entries = []
            for line in requirements_filedata.split('\n'):
                match = req_regex.search(line)
                if match:
                    entries.append(match.group(1))

            pip3_regex = re.compile(r'^(.+?) ', re.DOTALL | re.IGNORECASE)
            entries_with_versions = []
            for line in pip3_result.split('\n'):
                match = pip3_regex.search(line)
                if match:
                    pip3_match = match.group(1)
                    if pip3_match in entries:
                        entries_with_versions.append(line)
            all_entries = self.util.ascii_to_html_with_line_breaks('\n'.join(entries_with_versions))

        sql = 'select version, ip_log_last_time_parsed, last_updated from zzz_system'
        params = ()
        row = self.db.select(sql, params)
        version = row[0]
        ip_log_last_time_parsed = row[1]
        last_updated = row[2]
        
        output = f'''<p class="font-courier">
Zzz system version: {version} (last updated {last_updated})<br><br>
IP log last parsed: {ip_log_last_time_parsed}<br><br>
{result}
Python PIP packages:<br>
{all_entries}
        </p>'''
        return (output, pagetitle)
    
    #--------------------------------------------------------------------------------
