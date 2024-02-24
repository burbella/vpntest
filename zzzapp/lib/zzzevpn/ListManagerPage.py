#-----Web page to manage lists of IPs and DNS entries-----

import json
import pprint
import urllib.parse
import validators

#-----import modules from the lib directory-----
import zzzevpn

class ListManagerPage:
    'Web page to manage lists of IPs and DNS entries'

    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    list_manager: zzzevpn.ListManager = None
    memory: zzzevpn.Memory = None
    settings: zzzevpn.Settings = None
    util: zzzevpn.Util = None
    webpage: zzzevpn.Webpage = None

    service_name = 'list_manager'

    ListManagerHTML = {}

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
        self.data_validation = zzzevpn.DataValidation(ConfigData)
        self.list_manager = zzzevpn.ListManager(self.ConfigData, self.db, self.util)
        self.memory = zzzevpn.Memory(self.ConfigData, self.db, self.util)
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'List Manager', self.settings)

    #--------------------------------------------------------------------------------

    def make_webpage(self, environ, pagetitle):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Manage Lists', self.settings)
        else:
            self.webpage.update_header(environ, 'Manage Lists')

        output = self.webpage.make_webpage(environ, self.make_ListManagerPage(environ))

        return output

    #--------------------------------------------------------------------------------

    def make_return_json(self, environ, status, error_msg=''):
        return_data = {
            'status': status,
            'error_msg': error_msg,
        }
        return_json = json.dumps(return_data)
        if status!='success':
            self.webpage.error_log_json(environ, return_json)
        return return_json

    #--------------------------------------------------------------------------------

    def delete_list_html(self, environ: dict, list_id: int):
        list_info = self.list_manager.get_list_info(list_id)
        if not list_info:
            body = f'''Invalid List ID'''
            return body

        self.webpage.update_header(environ, f'''Delete List: {list_info['list_name']}''')

        DeleteListHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'list_id': list_id,
            'list_name': list_info['list_name'],
            'list_length': self.list_manager.count_list_entries(list_id),
            'list_type': list_info['list_type'],
            'list_url': list_info['list_url'],
        }
        body = self.webpage.load_template('ListManager_delete')
        return body.format(**DeleteListHTML)

    #--------------------------------------------------------------------------------

    # edit types:
    #   list of entries
    #   URL
    # list_data_source: url, entries
    def edit_list_html(self, environ, list_id):
        list_info = self.list_manager.get_list_info(list_id)
        if not list_info:
            body = f'''Invalid List ID'''
            return body

        #-----the user-DNS-deny list redirects to the Edit DNS page-----
        if list_info['list_name'] in ['user-DNS-deny', 'user-IP-deny']:
            EditListHTML = {
                'CSP_NONCE': environ['CSP_NONCE'],
                'INTERNAL_PATH': '',
            }
            if list_info['list_name']=='user-DNS-deny':
                EditListHTML['INTERNAL_PATH'] = '/z/edit_dns'
            elif list_info['list_name']=='user-IP-deny':
                EditListHTML['INTERNAL_PATH'] = '/z/edit_ip'
            body = self.webpage.load_template('Redirect_internal')
            return body.format(**EditListHTML)

        self.webpage.update_header(environ, f'''Edit List: {list_info['list_name']}''')

        #-----check for non-editable lists-----
        if not list_info['allow_edit']:
            return '<p>List Edit is not allowed for this list</p>'

        entries = self.list_manager.get_list_entries(list_id=list_id, return_dict=False)
        list_length = len(entries)
        show_entries = ''
        if list_length:
            show_entries = '\n'.join(entries)

        #-----list can either be a download URL or a textbox of entries-----
        list_url = list_info['list_url']
        list_url_class = ''
        entries_textbox_class = ''
        if list_info['list_data_source'] == 'url':
            entries_textbox_class = 'hide_item'
        else:
            list_url = ''
            list_url_class = 'hide_item'

        list_name_editable = ''
        list_name_readonly = ''
        if list_info['list_name'] in ['user-DNS-allow', 'user-IP-allow']:
            list_name_editable = 'hide_item'
        else:
            list_name_readonly = 'hide_item'

        EditListHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'list_id': list_id,
            'list_name': list_info['list_name'],
            'list_type': list_info['list_type'],
            'list_length': list_length,
            'list_url': list_url,
            'list_url_class': list_url_class,
            'list_name_editable': list_name_editable,
            'list_name_readonly': list_name_readonly,
            'entries_textbox': show_entries,
            'entries_textbox_class': entries_textbox_class,
        }
        body = self.webpage.load_template('ListManager_edit')
        return body.format(**EditListHTML)

    #--------------------------------------------------------------------------------

    def add_list_html(self, environ: dict):
        self.webpage.update_header(environ, 'Add List')

        AddListHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
        }
        body = self.webpage.load_template('ListManager_add')
        return body.format(**AddListHTML)

    #--------------------------------------------------------------------------------

    def view_list_html(self, environ: dict, list_id: int):
        list_info = self.list_manager.get_list_info(list_id)
        if not list_info:
            body = f'''Invalid List ID'''
            return body

        self.webpage.update_header(environ, f'''View List: {list_info['list_name']}''')

        entries = self.list_manager.get_list_entries(list_id=list_id)
        list_length = len(entries)
        show_entries = ''
        if list_length:
            show_entries = '\n'.join(entries)
        else:
            show_entries = 'Empty List'

        list_source = ''
        if list_info['list_url']:
            list_source = f'''<p>Source: {list_info['list_url']}</p>'''

        body = f'''
        <p>Viewing List: {list_info['list_name']}</p>
        {list_source}
        <p>Number of entries: {list_length}</p>
        <pre>{show_entries}</pre>
        '''

        return body

    #--------------------------------------------------------------------------------

    def handle_get(self, environ: dict):
        get_data = urllib.parse.parse_qs(environ['QUERY_STRING'])

        action = get_data.get('action', None)
        if action:
            action = action[0]

        list_id = get_data.get('list_id', None)
        if list_id:
            list_id = list_id[0]
        if action in ['view_list', 'edit_list', 'delete_list']:
            if not self.util.is_int(list_id):
                return self.webpage.make_webpage(environ, 'ERROR: invalid list_id')
            list_id = int(list_id)

        if action=='view_list':
            return self.webpage.make_webpage(environ, self.view_list_html(environ, list_id))
        elif action=='edit_list':
            return self.webpage.make_webpage(environ, self.edit_list_html(environ, list_id))
        elif action=='delete_list':
            return self.webpage.make_webpage(environ, self.delete_list_html(environ, list_id))
        elif action=='add_list':
            return self.webpage.make_webpage(environ, self.add_list_html(environ))

        return self.webpage.make_webpage(environ, 'ERROR: invalid action')

    #--------------------------------------------------------------------------------

    #-----process POST data-----
    def handle_post(self, environ: dict, request_body_size: int):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)

        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)

        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        action = raw_data.get('action', None)
        if action!=None:
            action = action[0]
        entry_id = raw_data.get('entry_id', None)
        if entry_id!=None:
            entry_id = entry_id[0]
        list_id = raw_data.get('list_id', None)
        if list_id:
            list_id = list_id[0]
        json_data = raw_data.get('json', None)
        if json_data!=None:
            json_data = json_data[0]

        #-----return if missing data-----
        if (request_body_size==0 or action==None):
            return self.make_return_json(environ, 'error', 'ERROR: missing data')

        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
            'entry_id': entry_id,
            'list_id': list_id,
            'json_data': json_data,
        }
        if not self.data_validation.validate(environ, data):
            return self.make_return_json(environ, 'error', 'ERROR: data validation failed')

        if action=='save_changes':
            if not json_data:
                return self.make_return_json(environ, 'error', 'ERROR: missing json data')
            return self.save_changes(environ, json_data)
        elif action=='save_entries':
            return self.save_entries(environ, json_data)
        elif action=='download_lists':
            return self.download_lists(environ)
        elif action=='add_list':
            return self.add_list(environ, json_data)
        elif action=='delete_list':
            return self.delete_list(environ, list_id)

        return self.make_return_json(environ, 'error', 'ERROR: invalid action')

    #--------------------------------------------------------------------------------

    #TODO: option to create extra user-edited lists instead of using a URL
    def add_list(self, environ: dict, json_data):
        add_list_data = json.loads(json_data)

        list_name = self.util.cleanup_str(add_list_data['list_name'])
        list_type = add_list_data['list_type']
        list_url = self.util.cleanup_str(add_list_data['list_url'])

        if not list_name:
            return self.make_return_json(environ, 'error', 'missing list name')

        #TODO: add support for other list types
        if list_type not in ['dns-deny']:
            return self.make_return_json(environ, 'error', 'invalid list type')

        if not validators.url(list_url):
            return self.make_return_json(environ, 'error', 'invalid URL')

        error_msg = self.list_manager.check_duplicate_list(list_name, list_url=list_url)
        if error_msg:
            return self.make_return_json(environ, 'error', error_msg)

        if self.list_manager.add_list(list_name, list_type, list_url):
            return self.make_return_json(environ, 'success', '')

        return self.make_return_json(environ, 'error', 'error adding list')

    #--------------------------------------------------------------------------------

    def delete_list(self, environ: dict, list_id: int):
        #-----make sure delete is allowed-----
        list_info = self.list_manager.get_list_info(list_id)
        if not list_info:
            return self.make_return_json(environ, 'error', 'list not found')
        if not list_info['allow_delete']:
            return self.make_return_json(environ, 'error', 'list is flagged as not deletable')

        if self.list_manager.delete_list(list_id):
            return self.make_return_json(environ, 'success', '')
        return self.make_return_json(environ, 'error', 'delete_list failed')

    #--------------------------------------------------------------------------------

    def download_lists(self, environ):
        self.db.insert_service_request(self.service_name, action='download_lists')
        self.util.work_available(1)
        return self.make_return_json(environ, 'success', '')

    #--------------------------------------------------------------------------------

    #TODO: make list_data_source editable? just delete/add instead?
    def save_entries(self, environ: dict, json_data) -> dict:
        list_data_uploaded = json.loads(json_data)

        list_info = self.list_manager.get_list_info(list_data_uploaded['list_id'])
        if not list_info:
            error_msg = 'ERROR: save_entries() empty list_info'
            print(error_msg)
            return self.make_return_json(environ, 'error', error_msg)
        if not list_info['allow_edit']:
            # readonly list
            error_msg = 'ERROR: save_entries() readonly list'
            print(error_msg)
            return self.make_return_json(environ, 'error', error_msg)

        # URL-based lists
        if list_info['list_data_source'] == 'url':
            error_msg = self.list_manager.check_duplicate_list(list_data_uploaded['list_name'], list_url=list_data_uploaded['list_url'], existing_list_id=list_info['id'])
            if error_msg:
                return self.make_return_json(environ, 'error', error_msg)

            result = self.list_manager.update_zzz_list(list_info['id'], list_data_uploaded['list_name'], list_url=list_data_uploaded['list_url'])

            if result['status'] == 'success':
                # queue a download request
                self.db.insert_service_request('list_manager', 'download_lists', 'list_url edited')
                self.util.work_available(1)
            return self.make_return_json(environ, result['status'], result['error_msg'])

        # entries-based lists
        error_msg = self.list_manager.check_duplicate_list(list_data_uploaded['list_name'], existing_list_id=list_info['id'])
        if error_msg:
            return self.make_return_json(environ, 'error', error_msg)

        entries = list_data_uploaded['entries']
        validation_result = self.util.validate_domain_list(entries.split('\n'))
        success = self.list_manager.update_zzz_list_complete(list_info['list_name'], entries, '', validation_result['accepted_domains'], validation_result['rejected_domains'])
        if success:
            #-----queue a rebuild-list command-----
            self.db.insert_service_request('list_manager', 'rebuild_lists')
            self.util.work_available(1)

        return self.make_return_json(environ, 'success', '')

    #--------------------------------------------------------------------------------

    #TODO: remove this?
    def delete_entry(self, environ, entry_id):
        #-----make sure the list is editable-----
        if not self.list_manager.is_entry_editable(entry_id):
            return 'ERROR: entry delete not allowed'

        #TEST
        return 'success'
        if self.list_manager.delete_entry(entry_id):
            return 'success'
        else:
            return 'error'

    #--------------------------------------------------------------------------------

    def get_lists_not_always_active(self):
        sql = 'select id from zzz_list where always_active=0'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        list_ids = []
        for row in rows_with_colnames:
            list_ids.append(row['id'])

        return list_ids

    #--------------------------------------------------------------------------------

    def save_changes(self, environ, json_data):
        list_manager_changes = json.loads(json_data)

        #TEST
        # print('list_manager_changes:')
        # pprint.pprint(list_manager_changes)

        #-----make sure not to de-activate certain builtin lists-----
        # always_active generally applies to the combined lists
        params_list = []
        # TEST_params_list = []
        active_list_ids = []
        activatable_lists = self.list_manager.get_list_id_by_flag(always_active=False)
        # all_list_info = self.list_manager.get_list_info(all_lists=True)

        for list_id in activatable_lists:
            current_list_changes = list_manager_changes.get(str(list_id), None)
            if not current_list_changes:
                #TODO: list not found? is this an error?
                self.webpage.error_log(environ, f'list not found: {current_list_changes}')
                continue

            is_active = current_list_changes.get('is_active', 0)
            if is_active:
                active_list_ids.append(list_id)
            auto_update = current_list_changes.get('auto_update', 0)

            #TEST
            # params = (is_active, auto_update, list_name, list_id)
            # params_list.append(params)
            params = (is_active, auto_update, list_id)
            params_list.append(params)

        #-----combine and de-dupe the lists to get a better memory estimate-----
        # don't just add up active list lengths because this does not account for duplicates between lists
        # duplicates would be eliminated when creating the combined list, which is what installs to BIND
        test_combined_list = self.list_manager.test_combined_list(list_ids=active_list_ids)
        total_list_length = len(test_combined_list)

        #-----check expected memory usage-----
        expected_mem, restart_mem_usage, max_allowed = self.memory.estimate_memory_usage_bind(total_list_length)
        if expected_mem > max_allowed:
            return self.make_return_json(environ, 'error', f'ERROR: active lists memory usage({expected_mem}MB) may exceed available memory ({max_allowed}MB)')

        #TEST
        # self.webpage.error_log(environ, 'params_list:')
        # self.webpage.error_log(environ, pprint.pformat(params_list))

        #-----update the DB-----
        # sql_update = 'update zzz_list set is_active=?, auto_update=?, list_name=? where id=?'
        sql_update = 'update zzz_list set is_active=?, auto_update=? where id=?'
        if not self.db.query_exec_many(sql_update, params_list):
            return self.make_return_json(environ, 'error', 'ERROR saving changes')

        #-----queue a rebuild-list command-----
        self.db.insert_service_request('list_manager', 'rebuild_lists')
        self.util.work_available(1)

        return self.make_return_json(environ, 'success')

    #--------------------------------------------------------------------------------

    def make_ListManagerPage(self, environ):
        expected_mem, restart_mem_usage, max_allowed = self.memory.estimate_memory_usage_bind()
        self.ListManagerHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'lists_table_rows': self.make_table_rows(),
            'estimated_memory_usage': int(expected_mem),
        }

        body = self.webpage.load_template('ListManager')
        return body.format(**self.ListManagerHTML)

    #--------------------------------------------------------------------------------

    def make_short_str(self, long_str):
        if len(long_str)>1024:
            return long_str[0:1024] + '...\n(view button shows full list)'
        return long_str

    #--------------------------------------------------------------------------------

    def make_row_data(self, row, row_color):
        list_id = row['id']

        #-----certain builtin lists are always active-----
        auto_update = ''
        if row['auto_update']:
            auto_update = 'checked'
        auto_update_checkbox = f'<input type="checkbox" class="list_manager_auto_update" id="auto_update_{list_id}" data-onclick="{list_id}" {auto_update}>'
        if row['always_active']:
            auto_update_checkbox = 'yes'

        view_button = f'<a class="clickable list_view" data-onclick="{list_id}">(V)</a>'
        edit_button = ''
        if row['allow_edit']:
            edit_button = f'<a class="clickable list_edit" data-onclick="{list_id}">(E)</a>'
        delete_button = ''
        if row['allow_delete']:
            delete_button = f'<a class="clickable list_delete" data-onclick="{list_id}">(D)</a>'

        is_active = ''
        if row['is_active']:
            is_active = 'checked'
        is_active_checkbox = f'<input type="checkbox" class="list_manager_is_active" id="is_active_{list_id}" data-onclick="{list_id}" {is_active}>'
        if row['always_active']:
            is_active_checkbox = 'yes'

        download_status = ''
        if row['download_status']:
            download_status = self.util.make_collapsable_html(row['download_status'], list_id, 'download_status_')
        rejected_entries = ''
        if row['rejected_entries']:
            rejected_entries = self.util.make_html_display_safe(row['rejected_entries'])
            rejected_entries = self.util.make_collapsable_html(rejected_entries, list_id, id_attr_name='rejected_entries_', width='width_600')
        accepted_entries = ''
        if row['accepted_entries']:
            short_str = self.util.make_html_display_safe(self.make_short_str(row['accepted_entries']))
            accepted_entries = self.util.make_collapsable_html(short_str, list_id, 'list_data_')

        row_data = {
            'row_color': row_color,
            'delete_button': delete_button,
            'edit_button': edit_button,
            'view_button': view_button,

            'list_id': list_id,
            'list_name': row['list_name'],
            'list_type': row['list_type'],
            # 'allow_delete': row['allow_delete'],
            # 'allow_edit': row['allow_edit'],
            'builtin': row['builtin'],
            'is_active_checkbox': is_active_checkbox,
            'auto_update_checkbox': auto_update_checkbox,
            'list_url': self.util.make_collapsable_html(row['list_url'], list_id, id_attr_name='list_url_', width='width_max'),
            'list_length': row['list_length'],
            'zzz_last_updated': row['last_valid_date_updated'],
            'download_status': download_status,
            'list_data': accepted_entries,
            'rejected_entries': rejected_entries,
        }
        return row_data

    # List, URL, Contents, Length, Type, Active?, Auto-Update?, Last Updated, Download Status, Invalid Entries
    # id integer primary key,
    # list_name text not null,
    # list_type text not null,
    # allow_delete boolean not null,
    # allow_edit boolean not null,
    # builtin boolean not null,
    # always_active boolean not null,
    # is_active boolean not null,
    # auto_update boolean not null,
    # list_url text,
    # list_length integer not null,
    # zzz_last_updated integer not null,
    # download_status text,
    # last_valid_date_updated integer,
    # -- download_data --> accepted_data, rejected_data
    # download_data text,
    # accepted_entries text,
    # rejected_entries text
    def make_table_rows(self):
        #-----header-----
        row_template = self.webpage.load_template('ListManager_header')
        header_data = {}
        list_manager_rows = [row_template.format(**header_data)]

        #-----body-----
        row_template = self.webpage.load_template('ListManager_rows')
        row_color = ''

        #-----separate rows by type-----
        last_list_type = ''
        row_separator = {
            'row_color': '',
            'delete_button': '',
            'edit_button': '',
            'view_button': '',

            'list_id': '-',
            'list_name': '-',
            'list_type': '-',
            'builtin': '-',
            'is_active_checkbox': '-',
            'auto_update_checkbox': '-',
            'list_url': '-',
            'list_length': '-',
            'zzz_last_updated': '-',
            'download_status': '-',
            'list_data': '-',
            'rejected_entries': '-',
        }

        sql = 'select * from zzz_list order by list_type, lower(list_name)'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)
        for row in rows_with_colnames:
            if last_list_type!=row['list_type']:
                if last_list_type:
                    # prevents a separator line at the top of the table
                    # list_manager_rows.append(row_template.format(**row_separator))
                    list_manager_rows.append('<tr><td colspan="11">&nbsp;</td></tr>')
                last_list_type=row['list_type']
            row_data = self.make_row_data(row, row_color)
            list_manager_rows.append(row_template.format(**row_data))
            #-----alternate row colors with each row-----
            if row_color == '':
                row_color = ' gray-bg'
            else:
                row_color = ''

        return '\n'.join(list_manager_rows)
