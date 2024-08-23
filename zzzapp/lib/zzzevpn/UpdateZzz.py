#-----Diff and Install Zzz Code Patches for development and testing-----

import json
import pprint
import psutil
import re
import urllib.parse

#-----package with all the Zzz modules-----
import zzzevpn

class UpdateZzz:
    'Diffs and Installs Zzz Patches'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    settings: zzzevpn.Settings = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None
    
    service_name = 'zzz'
    allowed_display_pages = ['coverage', 'db_view', 'update_zzz']
    list_requests_rows = None
    list_requests_colnames = None
    
    squid_latest_version = ''
    zzz_update_requests_html = ''
    code_diff_filedata = ''
    pytest_filedata = ''
    zzz_installer_output_filedata = ''
    zzz_git_output_filedata = ''
    
    dev_tools = ''
    dev_tools_note = ''
    new_favicon = ''

    db_view_formats = []
    #-----put package names here for pip-check output that needs to be highlighted with a gray bar-----
    highlight_package_row = {
        # 'dnspython': 1,
    }

    regex_is_dev_version = re.compile(r'^(\d+)a(.+)$')
    
    # refresh_code_diff: /opt/zzz/apache/dev/zzz-code-diff.txt
    # refresh_installer_output: /opt/zzz/apache/dev/zzz-installer-output.txt
    # refresh_git_output: /opt/zzz/apache/dev/zzz-git-output.txt
    # run_code_diff: /home/ubuntu/bin/diff_code.py
    # run_pytest: /opt/zzz/python/test
    # install_zzz_codebase: sudo /home/ubuntu/bin/diff_code.py -i
    # git_branch: /home/ubuntu/bin/git-branch
    # git_diff: /home/ubuntu/bin/git-diff
    # git_reset: /home/ubuntu/bin/git-checkout main
    allowed_actions_dev = ['db_view', 'db_view_table_info', 'dev_upgrade', 'refresh_code_diff', 'refresh_pytest', 'refresh_installer_output', 'refresh_git_output', 'run_code_diff', 'run_pytest', 'install_zzz_codebase', 'git_branch', 'git_diff', 'git_reset', 'pipdeptree', 'pip_versions', 'queue_upgrades', 'version_checks']
    allowed_actions = ['queue_upgrades', 'version_checks']
    
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
        if not self.settings.SettingsData:
            self.settings.get_settings()
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Update Zzz', self.settings)
        self.db_view_formats = []
        self.db_view_formats.extend(self.ConfigData['SqliteUtilsFormats']['ascii_formats'])
        self.db_view_formats.extend(self.ConfigData['SqliteUtilsFormats']['html_formats'])
        #-----not usable until subprocess.run() can handle unicode output-----
        # self.db_view_formats.extend(self.ConfigData['SqliteUtilsFormats']['unicode_formats'])
        self.db_view_formats.sort()

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
        action = raw_data.get('action', None)
        branch = raw_data.get('branch', None)
        dev_version = raw_data.get('dev_version', None)
        pip_local_only = raw_data.get('pip_local_only', None)
        pip_hide_dependencies = raw_data.get('pip_hide_dependencies', None)
        package_name = raw_data.get('package_name', None)
        all_packages = raw_data.get('all_packages', None)
        
        #-----return if missing data-----
        if action:
            action = action[0]
        else:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        
        #-----optional data-----
        if branch:
            branch = branch[0]
        else:
            branch = None
        if dev_version:
            dev_version = dev_version[0]
        else:
            dev_version = None
        if pip_local_only:
            pip_local_only = pip_local_only[0]
        if pip_hide_dependencies:
            pip_hide_dependencies = pip_hide_dependencies[0]
        if package_name:
            package_name = package_name[0]
            if not package_name:
                package_name = ''
        show_all_packages = False
        if all_packages:
            all_packages = all_packages[0]
            if all_packages == 'TRUE':
                show_all_packages = True

        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
        }
        if action not in ['db_view', 'db_view_table_info']:
            # db_view and db_view_table_info do not require branch or dev_version
            data['branch'] = branch
            data['dev_version'] = dev_version
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')

        if self.settings.is_setting_enabled('show_dev_tools'):
            if not (action in self.allowed_actions_dev):
                self.webpage.error_log(environ, 'allowed_actions_dev: ' + ','.join(self.allowed_actions_dev))
                return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')
        else:
            if not (action in self.allowed_actions):
                self.webpage.error_log(environ, 'allowed_actions: ' + ','.join(self.allowed_actions))
                return self.webpage.error_log(environ, 'ERROR: bad action "' + action + '"')

        if action=='refresh_code_diff':
            #-----send the files-----
            return self.get_all_diff_files()
            # self.get_code_diff_file()
            # return self.util.ascii_to_html_with_line_breaks(self.code_diff_filedata)
        elif action=='refresh_pytest':
            #-----send the file-----
            self.get_pytest_file()
            return self.util.ascii_to_html_with_line_breaks(self.pytest_filedata)
        elif action=='refresh_installer_output':
            #-----send the file-----
            self.get_installer_output_file()
            return self.util.ascii_to_html_with_line_breaks(self.zzz_installer_output_filedata)
        elif action=='refresh_git_output':
            #-----send the file-----
            self.get_git_output_file()
            return self.util.ascii_to_html_with_line_breaks(self.zzz_git_output_filedata, highlight_diff=True)
        elif action=='pip_versions':
            # this may take around 12 seconds to run
            return self.lookup_pip_versions(pip_local_only, pip_hide_dependencies)
        elif action=='pipdeptree':
            return self.lookup_pipdeptree(package_name=package_name, all_packages=show_all_packages)
        elif action=='db_view':
            return self.db_view_lookup(environ, raw_data)
        elif action=='db_view_table_info':
            return self.db_view_column_names(environ, raw_data)
        elif action in ['dev_upgrade', 'run_code_diff', 'run_pytest', 'install_zzz_codebase', 'git_branch', 'git_diff', 'git_reset', 'version_checks', 'queue_upgrades']:
            status = self.request_zzz_update(action, dev_version=dev_version, branch=branch)
            return status
        
        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')
    
    #--------------------------------------------------------------------------------

    def apply_nonces_to_html(self, environ, html_data: str) -> str:
        #-----add nonce to script tag-----
        csp_nonce = environ['CSP_NONCE']
        output = html_data.replace('<script ', f'<script nonce="{csp_nonce}" ')
        
        #-----apply base tag and style tag-----
        # '<head><base href="https://{zzz_domain}/coverage/">'
        # '<head><base href="/coverage/">'
        base_tag = '<base href="/z/coverage/">'
        style_tag = f'<style nonce="{csp_nonce}">#hide_item {{ display: none; }}</style>'
        viewport_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        output = output.replace('<head>', f'<head>{base_tag}{style_tag}{viewport_tag}')
        
        return output

    # URL format options:
    #   https://services.dev.zzz/coverage/
    #   https://services.dev.zzz/coverage/index.html
    #   https://services.dev.zzz/coverage/d_bf11a6af61a184e6_IPset_py.html
    def make_coverage_page(self, environ, sub_page='') -> str:
        #-----check if dev tools are hidden-----
        if not self.settings.is_setting_enabled('show_dev_tools'):
            body = '''<p><span class="warning_text">Dev Tools hidden in Settings</span></p>'''
            self.webpage.update_header(environ, 'Update Zzz - Coverage')
            output = self.webpage.make_webpage(environ, body)
            return output

        # regex_binary_file_extensions = re.compile(r'\.(jpg|jpeg|png|gif)$', re.DOTALL | re.IGNORECASE)
        coverage_dir = self.ConfigData['Directory']['Coverage']
        filepath = f'{coverage_dir}/{sub_page}'
        if sub_page=='':
            filepath = f'{coverage_dir}/index.html'

        output = ''
        if not filepath.endswith('.html'):
            # no edits to non-HTML files
            output = self.util.get_filedata(filepath, file_encoding='ascii')
            return output
        
        coverage_html = self.util.get_filedata(filepath, file_encoding='ascii')
        output = self.apply_nonces_to_html(environ, coverage_html)

        #-----link to original source files-----
        # each module has its own HTML page that needs link-fixing applied
        # <link rel="icon" sizes="32x32" href="favicon_32.png">
        # <img id="keyboard_icon" src="keybd_closed.png" alt="Show/hide keyboard shortcuts">
        # <link rel="stylesheet" href="style.css" type="text/css">
        # <script nonce="" type="text/javascript" src="coverage_html.js" defer></script>
        if not self.new_favicon:
            self.new_favicon = self.webpage.make_all_favicons()
        output = re.sub(r'<link rel="icon" sizes="32x32" href="favicon_32[\w]+\.png">', self.new_favicon, output, 0, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        patterns = {
            r'src="(keybd_closed[\w]+\.png)': 'src="/coverage/',
            r'src="(coverage_html[\w]+\.js)': 'src="/coverage/',
            r'href="(style[\w]+\.css)': 'href="/coverage/',
        }
        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if match:
                filename = match.group(1)
                new_html = f'{patterns[pattern]}{filename}'
                output = re.sub(pattern, new_html, output, 0, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        
        #-----replace style with class-----
        # <div style="display: none;">
        output = output.replace('<div style="display: none;">', '<div class="hide_item">')
        
        #-----add width/height to image-----
        # <img id="keyboard_icon" src="keybd_closed.png" alt="Show/hide keyboard shortcuts">
        output = output.replace('<img id="keyboard_icon"', '<img width="21" height="12" id="keyboard_icon"')

        return output

    #--------------------------------------------------------------------------------

    def db_view_column_names(self, environ, raw_data):
        table = raw_data.get('table', None)
        if table:
            table = table[0]
        else:
            return self.webpage.error_log(environ, '<option>ERROR: no table selected</option>')
        tables = self.db.list_tables()
        if not table:
            return '<option>ERROR: table not specified</option>'
        if table not in tables:
            return '<option>ERROR: invalid table</option>'

        table_columns = self.db.list_table_columns(table)
        if not table_columns:
            return '<option>ERROR: no columns</option>'
        column_menu_options = []
        for colname in table_columns:
            column_menu_options.append(f'<option value="{colname}">{colname}</option>')
        return '\n'.join(column_menu_options)

    #--------------------------------------------------------------------------------

    def make_db_view_page(self, environ, sub_page):
        self.webpage.update_header(environ, 'Update Zzz - DB Viewer')
        
        #-----check if dev tools are hidden-----
        if not self.settings.is_setting_enabled('show_dev_tools'):
            body = '''<p><span class="warning_text">Dev Tools hidden in Settings</span></p>'''
            output = self.webpage.make_webpage(environ, body)
            return output
        
        tables = self.db.list_tables()
        table_options = []
        for table in tables:
            table_options.append(f'<option value="{table}">{table}</option>')

        format_options = []
        for format in self.db_view_formats:
            textcolor = ''
            if format in self.ConfigData['SqliteUtilsFormats']['unicode_formats']:
                textcolor = 'text_red'
            format_options.append(f'<option value="{format}" class="{textcolor}">{format}</option>')

        DBviewHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'db_column_names': '',
            'format_options': '\n'.join(format_options),
            'table_options': '\n'.join(table_options),
        }

        body = self.webpage.load_template('UpdateZzz_db_view')
        output = self.webpage.make_webpage(environ, body.format(**DBviewHTML))

        return output

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle):
        self.webpage.update_header(environ, 'Update Zzz')
        
        url_path = environ['PATH_INFO']
        url_parts = url_path.split('/')
        display_page = url_parts[1]
        sub_page = ''
        if len(url_parts)==3:
            sub_page = url_parts[2]

        if not display_page in self.allowed_display_pages:
            err = 'invalid display_page: ' + display_page
            return self.webpage.error_log(environ, err)
        
        if display_page == 'coverage':
            output = self.make_coverage_page(environ, sub_page)
            return output
        elif display_page == 'db_view':
            output = self.make_db_view_page(environ, sub_page)
            return output

        #-----show the Zzz Updates requests-----
        if self.get_zzz_update_requests()>0:
            self.show_zzz_update_requests()
        
        #-----show the latest version of the Zzz Updates file-----
        self.get_code_diff_file()
        
        self.get_pytest_file()
        
        self.get_installer_output_file()
        
        self.get_git_output_file()
        
        self.get_squid_latest_version()
        
        self.show_dev_tools()
        
        #-----hide the upgrade button by default, show it if an upgrade is available-----
        # show a warning instead if we have a dev version installed
        db_version = self.util.zzz_version()
        show_hide_upgrade_zzz = 'hide_item'
        dev_upgrade_warning = ''
        if db_version['version'] < db_version['available_version']:
            if db_version['dev_version']:
                dev_upgrade_warning = f'''<p class="font-courier warning_text">Auto upgrade not available. Dev version {db_version['dev_version']} is installed. A manual upgrade to release version {db_version['available_version']} is required.</p>'''
            else:
                show_hide_upgrade_zzz = ''
        
        #TODO: test if dev versions are available
        show_hide_upgrade_dev = ''
        
        upgrade_dev_menu = ''
        dev_versions = self.get_zzz_dev_versions()
        if dev_versions:
            dev_menu_options = []
            dev_versions.sort(key=self.util.mixed_sort, reverse=True)
            for version in dev_versions:
                required_version = str(self.calc_required_version(version))
                dev_menu_options.append(f'<option value="{version}">{version} (req. {required_version})</option>')
            upgrade_dev_menu = '\n'.join(dev_menu_options)
        
        zzz_system_info_parsed = self.db.get_zzz_system_info()
        zzz_system_info = zzz_system_info_parsed['zzz_system_info']
        show_dev_version = 'N/A'
        if zzz_system_info['dev_version']:
            show_dev_version = zzz_system_info['dev_version']

        show_branches = self.get_branches()
        zzz_upgrades_needed = self.util.get_filedata(self.ConfigData['VersionFiles']['zzz'])

        #TODO: fix the version check before displaying this output
        if zzz_upgrades_needed.startswith('ERROR:'):
            zzz_upgrades_needed = ''

        #TODO: make a completely separate template without un-needed JS and HTML
        #-----remove data if the dev tools box is not checked in settings-----
        if not self.settings.is_setting_enabled('show_dev_tools'):
            UpdateZzzHTML = {
                'CSP_NONCE': environ['CSP_NONCE'],
                'dev_tools': self.dev_tools,
                'dev_tools_note': self.dev_tools_note,
                'dev_upgrade_warning': dev_upgrade_warning,
                'branch_checked_out': '',
                'show_branches': '',
                'show_hide_upgrade_dev': show_hide_upgrade_dev,
                'show_hide_upgrade_zzz': show_hide_upgrade_zzz,
                'squid_latest_version': '',
                'upgrade_dev_menu': '',
                'zzz_update_requests_html': '',
                'code_diff_filedata': '',
                'pytest_filedata': '',
                'zzz_installer_output_filedata': '',
                'zzz_git_output_filedata': '',
                'zzz_upgrades_needed': zzz_upgrades_needed,
                
                # Zzz system info:
                'installed_version': zzz_system_info['version'],
                'available_version': zzz_system_info['available_version'],
                'show_dev_version': show_dev_version,
                'ip_log_last_time_parsed': zzz_system_info['ip_log_last_time_parsed'],
                'last_updated': zzz_system_info['last_updated'],
            }
            body = self.webpage.load_template('UpdateZzz')
            output = self.webpage.make_webpage(environ, body.format(**UpdateZzzHTML))
            return output

        UpdateZzzHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'dev_tools': self.dev_tools,
            'dev_tools_note': self.dev_tools_note,
            'dev_upgrade_warning': dev_upgrade_warning,
            'branch_checked_out': show_branches['current'],
            'show_branches': show_branches['all'],
            'show_hide_upgrade_dev': show_hide_upgrade_dev,
            'show_hide_upgrade_zzz': show_hide_upgrade_zzz,
            'squid_latest_version': self.squid_latest_version,
            'upgrade_dev_menu': upgrade_dev_menu,
            'zzz_update_requests_html': self.zzz_update_requests_html,
            'code_diff_filedata': self.util.ascii_to_html_with_line_breaks(self.code_diff_filedata),
            'pytest_filedata': self.util.ascii_to_html_with_line_breaks(self.pytest_filedata),
            'zzz_installer_output_filedata': self.util.ascii_to_html_with_line_breaks(self.zzz_installer_output_filedata),
            'zzz_git_output_filedata': self.util.ascii_to_html_with_line_breaks(self.zzz_git_output_filedata, highlight_diff=True),
            'zzz_upgrades_needed': zzz_upgrades_needed,
            
            # Zzz system info:
            'installed_version': zzz_system_info['version'],
            'available_version': zzz_system_info['available_version'],
            'show_dev_version': show_dev_version,
            'ip_log_last_time_parsed': zzz_system_info['ip_log_last_time_parsed'],
            'last_updated': zzz_system_info['last_updated'],
        }
        
        body = self.webpage.load_template('UpdateZzz')
        output = self.webpage.make_webpage(environ, body.format(**UpdateZzzHTML))
        return output

    #--------------------------------------------------------------------------------
    
    def db_view_cleanup_output(self, format, output):
        if format in self.ConfigData['SqliteUtilsFormats']['html_formats']:
            #-----HTML cleanup, CSP issues-----
            output = output.replace('<td', '<td class="wrap_text valign_top" ')
            output = output.replace('style="text-align: right;"', 'class="right_align"')
        elif format in self.ConfigData['SqliteUtilsFormats']['ascii_formats']:
            output = self.util.ascii_to_html_with_line_breaks(output)
        else:
            output = f'WARNING: this format may only work on the command line\n\n{output}'
        return output

    def make_json_options(self, options, colname, td_class_custom='width_max'):
        options['collapsable_html'][colname] = f'{colname}_'
        options['pprint_json'] = [colname]
        # wrap_text makes collapsable_html columns display badly, so override it
        options['td_class_custom'][colname] = td_class_custom
        return options

    # wrap_text makes collapsable_html columns display badly, so override it
    def make_collapsable_html_options(self, options, colnames):
        for colname in colnames:
            options['collapsable_html'][colname] = f'{colname}_'
            options['td_class_custom'][colname] = ''
        return options

    def db_view_html(self, table, max_table_cell_data, sql='', params=()):
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)

        if not rows_with_colnames:
            return f'<tr><td>Empty query results</td></tr>'

        #-----prep the options dictionary-----
        options = {
            'collapsable_html': {
                # 'column': 'html_attr_name',
            },
            'generate_headers': colnames,
            'max_table_cell_data': max_table_cell_data*1024,
            'pprint_json': [],
            'td_class': 'wrap_text valign_top',
            'td_class_custom': {
                # 'column': 'class_data',
            },
        }

        if table=='ipwhois_cache':
            options = self.make_json_options(options, 'json')
            options = self.make_collapsable_html_options(options, ['raw_whois'])
        elif table=='service_request':
            options['collapsable_html']['details'] = 'details_'
            # wrap_text makes collapsable_html columns display badly, so override it
            options['td_class_custom']['details'] = 'width_300'
        elif table=='settings':
            # width_max is too wide when applied to the first column
            options = self.make_json_options(options, 'json', '')
            options = self.make_collapsable_html_options(options, ['squid_nobumpsites', 'squid_hide_domains'])
        elif table=='squid_log':
            options = self.make_collapsable_html_options(options, ['url_str'])
            options['td_class_custom']['url_str'] = 'width_300'
        elif table=='update_file':
            options = self.make_collapsable_html_options(options, ['file_data'])
        elif table=='whois_cache':
            options = self.make_json_options(options, 'json', 'width_300')
            options = self.make_collapsable_html_options(options, ['raw_whois'])
        elif table=='zzz_list':
            options = self.make_collapsable_html_options(options, ['download_data', 'list_url', 'accepted_entries', 'rejected_entries'])

        table_rows = self.util.custom_html_table(rows_with_colnames, options)
        row_count = len(rows_with_colnames)
        table_html = f'<p>Rows: {row_count}</p><table>{table_rows}</table>'
        return table_html

    def db_view_lookup(self, environ, raw_data):
        #TODO: validate data in multiple places
        #-----validate data separately for DB view-----
        # if not self.data_validation.validate(environ, data):
        #     return self.webpage.error_log(environ, 'ERROR: data validation failed')

        default_format = 'html'
        row_limit_max = 10000
        row_limit_default = 100
        table_cell_limit_max = 99999
        table_cell_limit_default = 50
        db_filepath = self.ConfigData['DBFilePath']['Services']

        #-----get data-----
        table = raw_data.get('table', None)
        if table:
            table = table[0]
        else:
            return self.webpage.error_log(environ, 'ERROR: no table selected')
        data = { 'table': table }
        if table == 'schema':
            subprocess_commands = [self.ConfigData['Subprocess']['sqlite-utils'], 'schema', db_filepath]
            output = ''
            if self.util.run_script(subprocess_commands):
                output = self.util.subprocess_output.stdout
            else:
                output = self.util.script_output
            return self.util.ascii_to_html_with_line_breaks(output)

        format = raw_data.get('format', None)
        max_rows = raw_data.get('max_rows', None)
        max_table_cell_data = raw_data.get('max_table_cell_data', None)
        colname = raw_data.get('colname', None)
        column_value = raw_data.get('column_value', None)
        comparison_name = raw_data.get('comparison_name', None)
        order_by = raw_data.get('order_by', None)
        order_asc_desc = raw_data.get('order_asc_desc', None)

        if format:
            format = format[0]
        else:
            format = default_format

        if max_rows:
            max_rows = max_rows[0]
        else:
            max_rows = row_limit_default

        if max_table_cell_data:
            max_table_cell_data = max_table_cell_data[0]
        else:
            max_table_cell_data = table_cell_limit_default

        valid_tables = self.db.list_tables()

        #-----validate-----
        if table not in valid_tables:
            return 'ERROR: invalid table'
        if not format:
            format = default_format
        if format not in self.db_view_formats:
            format = default_format

        if self.util.is_int(max_rows):
            if len(max_rows)>6:
                max_rows = row_limit_max
            max_rows = int(max_rows)
            if max_rows < 1:
                max_rows = 1
            elif max_rows > row_limit_max:
                max_rows = row_limit_max
        else:
            max_rows = row_limit_default

        if self.util.is_int(max_table_cell_data):
            if len(max_table_cell_data) > 5:
                max_table_cell_data = table_cell_limit_default
            max_table_cell_data = int(max_table_cell_data)
            if max_table_cell_data < 1:
                max_table_cell_data = 1
            elif max_table_cell_data > table_cell_limit_max:
                max_table_cell_data = table_cell_limit_max
        else:
            max_table_cell_data = row_limit_default

        #-----optional fields-----
        # colname, column_value
        valid_column_name = False
        valid_column_value = False
        table_columns = []
        if colname or order_by:
            table_columns = self.db.list_table_columns(table)
        if colname:
            colname = colname[0]
        if column_value:
            column_value = column_value[0]
        if colname and column_value:
            #-----column name must be found in the table in the DB, or it doesn't get used-----
            if colname in table_columns:
                valid_column_name = True
            #-----restrict which characters are allowed in the query string-----
            # maybe not a SQL injection risk since the query is parameterized?
            regex_value_pattern = r'^[\w :.-]*$'
            regex_value = re.compile(regex_value_pattern, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if regex_value.match(column_value):
                valid_column_value = True

        if comparison_name:
            comparison_name = comparison_name[0]
            if comparison_name:
                if comparison_name not in ['equals', 'contains', 'starts_with', 'ends_with', 'greater_than', 'less_than']:
                    # bad data, use default value
                    comparison_name = 'equals'

        #-----assemble the WHERE clause-----
        where_query = ''
        sqlite_utils_where_query = ''
        where_param = ()
        placeholder = ':colname'
        if valid_column_name and valid_column_value:
            if comparison_name=='equals':
                # where colname=?
                where_query = f'where {colname}=?'
                sqlite_utils_where_query = f'{colname}={placeholder}'
                where_param = (column_value,)
            elif comparison_name=='greater_than':
                where_query = f'where {colname}>?'
                sqlite_utils_where_query = f'{colname}>{placeholder}'
                where_param = (column_value,)
            elif comparison_name=='less_than':
                where_query = f'where {colname}<?'
                sqlite_utils_where_query = f'{colname}<{placeholder}'
                where_param = (column_value,)
            elif comparison_name in ['contains', 'starts_with', 'ends_with']:
                # where colname like '%' + ? + '%'
                where_query = f'where {colname} like ?'
                sqlite_utils_where_query = f'{colname} like {placeholder}'
                start_percent_sign = ''
                end_percent_sign = ''
                if comparison_name in ['contains', 'starts_with']:
                    end_percent_sign = '%'
                if comparison_name in ['contains', 'ends_with']:
                    start_percent_sign = '%'
                where_param = (start_percent_sign + column_value + end_percent_sign,)

        #-----order by-----
        order_by_param = ''
        if order_by:
            order_by = order_by[0]
            if order_by:
                if order_by in table_columns:
                    order_by_param = f'order by {order_by}'
        if order_by_param and order_asc_desc:
            order_asc_desc = order_asc_desc[0]
            if order_asc_desc:
                if order_asc_desc in ['asc', 'desc']:
                    order_by_param += f' {order_asc_desc}'

        #TODO: fix the syntax errors before enabling sqlite_utils_where_query, then remove this line
        sqlite_utils_where_query = ''

        sql = f'''select * from {table} {sqlite_utils_where_query} {order_by_param} limit {max_rows}'''
        params = ()
        if where_query:
            params = where_param

        #-----HTML format can be handled better by DB/Util functions instead of command-line app-----
        if format=='html':
            # different query format for HTML tables
            sql = f'''select * from {table} {where_query} {order_by_param} limit {max_rows}'''
            return self.db_view_html(table, max_table_cell_data, sql, params)

        # table dump:
        # subprocess_commands = [self.ConfigData['Subprocess']['sqlite-utils'], 'rows', '--limit', str(max_rows), '--fmt', format, db_filepath, table]

        # sudo /opt/zzz/venv/bin/sqlite-utils query --fmt plain /opt/zzz/sqlite/services.sqlite3 \
        # "select * from ip_log_daily where ip like :colname limit 50" \
        # -p colname "8.%"
        subprocess_commands = [self.ConfigData['Subprocess']['sqlite-utils'], 'query', '--fmt', format, db_filepath, sql]
        if where_query:
            #TODO: re-enable this when params syntax errors are fixed
            # where param included (characters should have been safety-checked above)
            # subprocess_commands = [self.ConfigData['Subprocess']['sqlite-utils'], 'query', '--fmt', format, db_filepath, f'"{sql}"', '-p', 'colname', f'"{params[0]}"']
            pass

        #TEST
        test_params = pprint.pformat(params)
        print(f'sql: {sql}\nparams: {test_params}\nsubprocess_commands:')
        pprint.pprint(subprocess_commands)

        output = ''
        if self.util.run_script(subprocess_commands):
            output = self.db_view_cleanup_output(format, self.util.subprocess_output.stdout)
        else:
            output = self.util.ascii_to_html_with_line_breaks(self.util.script_output)
        return output

    #--------------------------------------------------------------------------------

    # remotes/origin/HEAD -> origin/main
    # remotes/origin/branch1
    # remotes/origin/branch2
    # remotes/origin/main
    # remotes/origin/other-branch3
    # remotes/origin/other-branch4
    def get_branches(self) -> dict:
        branches_filedata = self.util.get_filedata(self.ConfigData['UpdateFile']['zzz']['git_branches'])
        current_branch_filedata = self.util.get_filedata(self.ConfigData['UpdateFile']['zzz']['git_branch_current'])

        branches = []
        if branches_filedata:
            branches = branches_filedata.split('\n')
        main_branch = '<option value="main" selected="selected">main</option>'
        menu_options = [main_branch]
        if not branches:
            show_branches = {
                'all': menu_options,
                'current': 'main',
            }
            return show_branches

        #-----cleanup output-----
        for branch in branches:
            branch = branch.strip()
            if not branch:
                continue
            branch = branch.replace('remotes/', '')
            if branch=='origin/main':
                continue
            menu_options.append(f'<option value="{branch}">{branch}</option>')

        show_branches = {
            'all': '\n'.join(menu_options),
            'current': current_branch_filedata,
        }
        return show_branches

    #--------------------------------------------------------------------------------
    
    #-----version 18a1 requires version 17 to be installed for the upgrade to work-----
    def calc_required_version(self, dev_version):
        required_version = 0
        match = self.regex_is_dev_version.match(dev_version)
        if match:
            required_version = int(match.group(1)) - 1
        return required_version
    
    #--------------------------------------------------------------------------------
    
    def get_zzz_dev_versions(self):
        version_list = []
        dev_versions = []
        get_version_cmd = [self.ConfigData['Subprocess']['zzz-list-versions'], '--dev']
        if self.util.run_script(get_version_cmd):
            version_list = self.util.subprocess_output.stdout.split('\n')
        if not version_list:
            return []
        
        for version in version_list:
            match = self.regex_is_dev_version.match(version)
            if match:
                dev_versions.append(version)
        return dev_versions
    
    #--------------------------------------------------------------------------------
    
    def show_dev_tools(self):
        if self.settings.is_setting_enabled('show_dev_tools'):
            self.dev_tools = ''
            self.dev_tools_note = 'hide_item'
            #-----get dev versions-----
            self.get_zzz_dev_versions()
        else:
            self.dev_tools = 'hide_item'
            self.dev_tools_note = ''
    
    #--------------------------------------------------------------------------------
    
    def get_squid_latest_version(self):
        data = ''
        with open(self.ConfigData['VersionFiles']['squid'], 'r') as read_file:
            data = read_file.read()
        self.squid_latest_version = data
    
    #--------------------------------------------------------------------------------
    
    #-----count pending requests-----
    def get_zzz_update_requests(self, action=None):
        num_unprocessed_requests = 0
        
        sql = 'select * from service_request where service_name=? order by id desc limit 20'
        params = (self.service_name,)
        
        if action:
            sql = 'select * from service_request where service_name=? and action=? order by id desc limit 20'
            params = (self.service_name, action)
        
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        self.list_requests_rows = rows
        self.list_requests_colnames = colnames
        
        for row in rows_with_colnames:
            if row['status']==self.ConfigData['ServiceStatus']['Requested'] or row['status']==self.ConfigData['ServiceStatus']['Working']:
                num_unprocessed_requests += 1
        return num_unprocessed_requests
    
    #--------------------------------------------------------------------------------
    
    def show_zzz_update_requests(self):
        self.zzz_update_requests_html = self.db.result_full_table(self.list_requests_colnames, self.list_requests_rows)
    
    #--------------------------------------------------------------------------------

    # send back JSON
    def get_all_diff_files(self):
        self.get_code_diff_file()
        self.get_pytest_file()
        self.get_installer_output_file()
        self.get_git_output_file()
        result = {
            'status': 'success',
            'error_msg': '',
            'code_diff': self.util.ascii_to_html_with_line_breaks(self.code_diff_filedata),
            'pytest': self.util.ascii_to_html_with_line_breaks(self.pytest_filedata),
            'installer_output': self.util.ascii_to_html_with_line_breaks(self.zzz_installer_output_filedata),
            'git_output': self.util.ascii_to_html_with_line_breaks(self.zzz_git_output_filedata),
        }
        return json.dumps(result)

    def get_code_diff_file(self):
        filepath = self.ConfigData['UpdateFile']['zzz']['run_code_diff']
        self.code_diff_filedata = self.util.get_filedata(filepath, file_encoding='ascii')
    
    def get_pytest_file(self):
        filepath = self.ConfigData['UpdateFile']['zzz']['run_pytest']
        self.pytest_filedata = self.util.get_filedata(filepath, file_encoding='ascii')
    
    def get_installer_output_file(self):
        filepath = self.ConfigData['UpdateFile']['zzz']['installer_output']
        self.zzz_installer_output_filedata = self.util.get_filedata(filepath, file_encoding='ascii')
    
    def get_git_output_file(self):
        filepath = self.ConfigData['UpdateFile']['zzz']['git_output']
        self.zzz_git_output_filedata = self.util.get_filedata(filepath, file_encoding='ascii')
    
    #--------------------------------------------------------------------------------
    
    def queue_zzz_update_request(self, action, details=''):
        self.db.insert_service_request(self.service_name, action, details)
        self.util.work_available(1)
        
        return "Zzz Update Request has been queued: " + action
    
    #--------------------------------------------------------------------------------
    
    #-----request a Zzz app update-----
    # available actions: run_code_diff, install_zzz_codebase, git_branch, git_diff, git_reset, version_checks, queue_upgrades
    def request_zzz_update(self, action, dev_version=None, branch=None):
        details = ''
        #-----make sure this dev version can be upgraded from the current installed version-----
        if action=='dev_upgrade':
            if not dev_version:
                return 'ERROR: no dev version specified'
            db_version = self.util.zzz_version()
            required_version = self.calc_required_version(dev_version)
            installed_version = db_version['version']
            if installed_version != required_version:
                return f'ERROR - version mismatch: installed_version={installed_version}, required_version={required_version}'
            details = dev_version
        elif action in ['git_diff', 'git_reset']:
            if re.match(r'^(main|origin\/[A-Za-z0-9-]{1,250})$', branch):
                details = branch
            else:
                return 'ERROR: invalid branch name'

        if self.get_zzz_update_requests(action)>0:
            self.show_zzz_update_requests()
            return 'Request NOT submitted because an existing request is pending.'
        else:
            status = self.queue_zzz_update_request(action, details)
            return "Request submitted.\n" + status
    
    #--------------------------------------------------------------------------------

    def pip_versions_ascii_table(self, table_data, all_requirements_names):
        # making HTML here, so not running util.make_html_display_safe() later (that would break HTML)
        # still need to insert nbsp's to line up columns
        table_data = table_data.replace('  ', ' &nbsp;')

        #-----highlight packages found in requirements files-----
        for pypi_name in all_requirements_names.keys():
            highlighted_name = f'</span><span class="font-courier text_green">{pypi_name}</span><span>'
            table_data = table_data.replace(f'| {pypi_name} ', f'| {highlighted_name} ')

        #-----link the URLs-----
        # EX: https://pypi.python.org/pypi/coverage
        regex_pypi_link = re.compile(r' (https\:\/\/pypi\.python\.org/.+?) ', re.DOTALL)
        urls_found = regex_pypi_link.findall(table_data)
        if urls_found:
            for pypi_url in urls_found:
                linked_url = f'</span><a href="{pypi_url}">{pypi_url}</a><span class="font-courier">'
                table_data = table_data.replace(f'{pypi_url} ', f'{linked_url} ')
        
        return self.util.add_html_line_breaks(f'<span class="font-courier">{table_data}</span>')

    def pip_versions_html_table(self, table_data, all_requirements_names):
        regex_horiz_line = re.compile(r'[\+\-]+')
        notices = []
        pip_link = ''
        html_table_data = []
        horiz_lines_found = 0
        
        # expected set of lines: horiz, header, horiz, row(s), horiz
        for line in table_data.split('\n'):
            if not line:
                continue

            #-----check for notices (usually about a pip upgrade available)-----
            # [notice] A new release of pip is available: 24.1.2 -> 24.2
            # [notice] To update, run: python3 -m pip install --upgrade pip
            line = self.util.remove_ansi_codes(line)
            if line.startswith('[notice] '):
                notices.append(line)
                if line.startswith('[notice] A new release of pip is available'):
                    pip_link = '<br>\nPackage URL: <a href="https://pypi.python.org/pypi/pip">https://pypi.python.org/pypi/pip</a>'
                continue

            match = regex_horiz_line.match(line)
            if match:
                horiz_lines_found += 1
                if horiz_lines_found>=3:
                    html_table_data.append('</table><br>')
                    horiz_lines_found = 0
                continue

            #-----table header-----
            if horiz_lines_found==1:
                columns = line.split('|')
                table_type = columns[1].strip()
                version = columns[2].strip()
                latest = columns[3].strip()
                html_table_data.append(f'<table><tr><th>{table_type}</th><th>{version}</th><th>{latest}</th><th>PipDepTree</th><th>Package URL</th></tr>\n')
                continue

            #-----table rows-----
            if horiz_lines_found==2:
                columns = line.split('|')
                package_name = columns[1].strip()
                version = columns[2].strip()
                latest = columns[3].strip()
                package_url = columns[4].strip()
                linked_url = f'<a href="{package_url}">{package_url}</a>'
                pipdeptree_button = f'<a class="pipdeptree clickable" data-onclick="{package_name}">pipdeptree</a>'
                found_name_in_requirements = all_requirements_names.get(package_name, None)
                highlight_name = ''
                if found_name_in_requirements:
                    highlight_name = 'text_green'
                highlight_row = ''
                found_highlight_package = self.highlight_package_row.get(package_name, None)
                if found_highlight_package:
                    highlight_row = 'gray-bg'
                html_table_data.append(f'<tr class="{highlight_row}"><td class="{highlight_name}">{package_name}</td><td>{version}</td><td><span class="cursor_copy">{latest}</span></td><td>{pipdeptree_button}</td><td>{linked_url}</td></tr>\n')
                continue

            if line=='Loading package versions...':
                continue

            print(f'ERROR: pip_versions_html_table() unmatched line pattern\n{line}', flush=True)

        html_notices = '<br>\n'.join(notices)
        html_table_data_joined = '\n'.join(html_table_data)
        return f'<p class="text_red">{html_notices}{pip_link}</p>{html_table_data_joined}'
    
    # +----------------------+---------+--------+--------------------------------------+
    # | Major Release Update | Version | Latest |                                      |
    # +----------------------+---------+--------+--------------------------------------+
    # | attrs                | 21.4.0  | 22.1.0 | https://pypi.python.org/pypi/attrs   |
    def lookup_pip_versions(self, pip_local_only, pip_hide_dependencies):
        script_commands = [self.ConfigData['Subprocess']['pip-check']]
        if pip_local_only:
            script_commands.append('--local')
        if pip_hide_dependencies:
            script_commands.append('--not-required')

        #-----only allow one copy of pip-check to run at a time-----
        # /opt/zzz/python/bin/subprocess/pip-check.sh
        #   /opt/zzz/venv/bin/pip-check
        # name: pip-check
        # cmdline:  ['/opt/zzz/venv/bin/python3', '/opt/zzz/venv/bin/pip-check']
        err_msg = ''
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username']):
            process_name = proc.info['name']
            if not proc.info['cmdline']:
                continue
            if process_name == 'pip-check':
                err_msg = '<span class="warning_text">ERROR: pip-check is already running</span>'
                return err_msg

        if not self.util.run_script(script_commands):
            return 'ERROR checking PIP versions'

        #-----parse requirements files-----
        filepath_requirements_tools = '/opt/zzz/install/requirements-tools.txt'
        filepath_requirements = '/opt/zzz/install/requirements.txt'
        requirements_tools_filedata = self.util.get_filedata(filepath_requirements_tools)
        requirements_filedata = self.util.get_filedata(filepath_requirements)
        all_requirements_filedata = f'{requirements_tools_filedata}\n{requirements_filedata}'
        if not all_requirements_filedata:
            print('ERROR: lookup_pip_versions() did not find any requirements filedata')
        all_requirements_names = {}
        regex_requirements_name = re.compile(r'^([\w\.\-]+).+$', re.IGNORECASE)
        for line in all_requirements_filedata.split('\n'):
            if not line:
                continue
            clean_line = line.strip()
            match = regex_requirements_name.match(clean_line)
            if match:
                all_requirements_names[match.group(1)] = 1
        if not all_requirements_names:
            print('ERROR: lookup_pip_versions() did not match any requirements entries')

        table_data = self.util.subprocess_output.stdout
        # return self.pip_versions_ascii_table(table_data, all_requirements_names)
        return self.pip_versions_html_table(table_data, all_requirements_names)
    
    #--------------------------------------------------------------------------------

    def check_dependencies(self):
        commands = ['/opt/zzz/venv/bin/python3', '-m', 'pip', 'check']
        if self.util.run_script(commands, binary_mode=True, decode_data=True):
            return self.util.script_output
        return ''

    def lookup_pipdeptree(self, package_name: str='', all_packages: bool=False) -> str:
        dependencies = self.check_dependencies()
        commands = ['/opt/zzz/venv/bin/pipdeptree', '--all']
        if all_packages:
            print('pipdeptree - all packages')
        else:
            regex_package_name = re.compile(r'^[\w-]+$', re.DOTALL | re.IGNORECASE | re.MULTILINE)
            match = regex_package_name.match(package_name)
            if not match:
                return 'ERROR: bad package name'
            commands = ['/opt/zzz/venv/bin/pipdeptree', '--packages', package_name]

        if not self.util.run_script(commands, binary_mode=True, decode_data=True):
            print(self.util.script_output)
            return 'ERROR: script failed'

        display_text = dependencies + '\n' + self.util.script_output
        if self.util.decode_status=='error':
            display_text += '\n\n' + self.util.decode_error_msg
        pipdeptree_data = self.util.ascii_to_html_with_line_breaks(display_text)
        output = f'''
            <p class="font-courier">PipDepTree:</p>
            <table><tr><td>
            {pipdeptree_data}
            </td></tr></table>
        '''
        return output

    #--------------------------------------------------------------------------------
