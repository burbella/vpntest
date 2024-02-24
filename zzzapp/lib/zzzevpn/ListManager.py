#-----Manages lists of IPs and DNS entries-----


#-----import modules from the lib directory-----
# import zzzevpn.Config
# import zzzevpn.DB
# import zzzevpn.Util
import zzzevpn

class ListManager:
    'Manages lists of IPs and DNS entries'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None

    service_name = 'list_manager'

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
    
    #--------------------------------------------------------------------------------
    
    def assemble_list_new(self, request_id, service_name, action, add_action, replace_action):
        print('assemble_list_new(): START', flush=True)
        item_list = []
        
        #-----generate a new list from the latest REPLACE plus all subsequent ADDs-----
        sql = 'select uf.file_data \
               from service_request sr, update_file uf \
               where sr.id=uf.service_request_id and sr.service_name=? and sr.action=? and sr.status=? \
               order by sr.id desc \
               limit 1'
        params = (service_name, replace_action, self.ConfigData['ServiceStatus']['Done'])
        row = self.db.select(sql, params)
        
        #TEST - handle empty results
        if (row==None):
            #TODO: don't return ... in the next query, search using a req_date of 1/1/2017
            return item_list
        
        item_list = row[0].split("\n")
        
        sql_items_added = 'select sr.id, sr.req_date, uf.file_data, uf.src_filepath \
                   from service_request sr, update_file uf \
                   where sr.id=uf.service_request_id and sr.service_name=? and sr.action=? and sr.status=? and sr.req_date>? \
                   order by sr.id desc'
        params_items_added = (service_name, add_action, self.ConfigData['ServiceStatus']['Done'], row['req_date'])
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql_items_added, params_items_added)
        if (rows_with_colnames!=None):
            for row in rows_with_colnames:
                item_list.extend(row['file_data'].split("\n"))
        
        print('assemble_list_new(): END', flush=True)
        return item_list
    
    #--------------------------------------------------------------------------------
    
    def assemble_list_with_id(self, request_id, service_name, action, add_action, replace_action):
        print('assemble_list_with_id(): START', flush=True)
        item_list = []
        
        #-----use the list associated with the given request_id to make the file-----
        if (action==replace_action):
            #   if request is REPLACE:
            #     use the list associated with the given request_id
            sql = 'select file_data from update_file where service_request_id=?'
            params = (request_id,)
            row = self.db.select(sql, params)
            if (row!=None):
                item_list = row[0].split("\n")
        else:
            #   if request is ADD:
            #     get the latest REPLACE that's Done (if any)
            #     ID of the REPLACE must be less than the ID of the current ADD
            sql_items_replaced = 'select sr.req_date, uf.file_data \
                       from service_request sr, update_file uf \
                       where sr.id=uf.service_request_id and sr.service_name=? and sr.action=? and sr.status=? and sr.id<? \
                       order by sr.id desc \
                       limit 1'
            params_items_replaced = (service_name, replace_action, self.ConfigData['ServiceStatus']['Done'], request_id)
            (colnames, rows, rows_with_colnames) = self.db.select_all(sql_items_replaced, params_items_replaced)
            req_date = '2017-01-01' # no REPLACE?  just get all the ADDs
            if (rows_with_colnames!=None):
                for row in rows_with_colnames:
                    item_list.extend(row['file_data'].split("\n"))
                    req_date = row['req_date']
            #     get all subsequent ADDs that are Done (if any)
            #     get the given ADD (status will be Working)
            sql_items_added = 'select uf.file_data \
                       from service_request sr, update_file uf \
                       where sr.id=uf.service_request_id and sr.service_name=? and sr.action=? and (sr.status=? or sr.id=?) and sr.req_date>?'
            params_items_added = (service_name, add_action, self.ConfigData['ServiceStatus']['Done'], request_id, req_date)
            (colnames, rows, rows_with_colnames) = self.db.select_all(sql_items_added, params_items_added)
            if (rows_with_colnames!=None):
                for row in rows_with_colnames:
                    item_list.extend(row['file_data'].split("\n"))
        
        print('assemble_list_with_id(): END', flush=True)
        return item_list
    
    #--------------------------------------------------------------------------------
    
    #-----assemble a list of domains or IP's (specified in a param)-----
    #TODO: DB and code changes
    #      use action=replace instead of replace_domains and replace_ips
    #      use action=add instead of add_domains and add_ips
    #WORKAROUND: use IF statements to generate the proper add/replace strings for queries
    #TODO: make sure this handles all possible combinations of REPLACE and ADD (request status will vary)
    # request_id==None
    #   generate a new list from the latest REPLACE plus all subsequent ADDs (only where status=Done)
    # request_id is given:
    #   if request is REPLACE:
    #     use the list associated with the given request_id
    #   if request is ADD:
    #     get the latest REPLACE that's Done (if any)
    #     get all subsequent ADDs that are Done (if any)
    #     get the given ADD (status will be Working)
    def assemble_list(self, request_id, service_name, action):
        print('assemble_list(): START', flush=True)
        item_list = []
        
        #WORKAROUND
        # Query Params:
        #   service_name, add_action
        #   service_name, replace_action
        add_action = 'add_domains'
        replace_action = 'replace_domains'
        if (action=='replace_ips' or action=='add_ips'):
            add_action = 'add_ips'
            replace_action = 'replace_ips'
        
        if (request_id == None):
            #-----generate a new list from the latest REPLACE plus all subsequent ADDs-----
            item_list = self.assemble_list_new(request_id, service_name, action, add_action, replace_action)
        else:
            #-----use the list associated with the given request_id to make the file-----
            item_list = self.assemble_list_with_id(request_id, service_name, action, add_action, replace_action)
        item_list.sort()

        #TODO: separate entry for user-IP-deny list
        #-----write to new zzz_list table-----
        if action=='replace_domains' or action=='add_domains':
            download_data = '\n'.join(item_list)
            self.update_zzz_list_complete('user-DNS-deny', download_data, '', item_list, [])

        print('assemble_list(): END', flush=True)
        return item_list

    #--------------------------------------------------------------------------------

    # mostly this is used for URL-based list updates
    def update_zzz_list(self, list_id: int, list_name: str, list_url: str='', item_list: list=[]):
        '''list can have either a url or a list of entries'''
        list_info = self.get_list_info(list_id)
        if not list_info:
            return { 'status': 'error', 'error_msg': f'ERROR: list_id={list_id} not found', }

        # replace the URL, flag the list for downloading
        if list_info['list_data_source'] == 'url':
            sql_zzz_last_updated = "zzz_last_updated=datetime('now')"
            if list_url != list_info['list_url']:
                # URL changed? a date in the past forces an update at the next download time
                sql_zzz_last_updated = "zzz_last_updated='2022-01-01 02:00:00'"
            sql_update = f'''update zzz_list
                set list_name=?, list_url=?, {sql_zzz_last_updated}
                where id=?'''
            params = (list_name, list_url, list_id)
            result = { 'status': 'success', 'error_msg': '', }
            if not self.db.query_exec(sql_update, params):
                result = { 'status': 'error', 'error_msg': 'ERROR: list update query failed', }
            return result

        result = { 'status': 'error', 'error_msg': 'ERROR: not a URL list', }
        return result

        #NOTE: update_zzz_list_complete() is used for updating an entry-based list

        # list_data = '\n'.join(item_list)
        # sql_update = '''update zzz_list
        #     set download_data=?, list_length=?, zzz_last_updated=datetime('now')
        #     where list_name=?'''
        # params = (list_data, len(item_list), list_name)
        # self.db.query_exec(sql_update, params)
        # self.update_zzz_list_entries(list_name=list_name, list_data=item_list)

    #--------------------------------------------------------------------------------

    # used for entries-based list updates
    # currently will not process list_name changes
    #TODO: if user-created lists are going to allow entries, change the WHERE clause to use ID instead of LIST_NAME
    def update_zzz_list_complete(self, list_name: str, download_data: str, download_status: str, accepted_entries: list, rejected_entries: list):
        sql_update = '''update zzz_list
            set download_data=?, accepted_entries=?, list_length=?, download_status=?, rejected_entries=?, zzz_last_updated=datetime('now'), last_valid_date_updated=datetime('now')
            where list_name=?'''

        accepted_entries_str = ''
        list_length = 0
        if accepted_entries:
            accepted_entries_str = '\n'.join(accepted_entries)
            list_length = len(accepted_entries)
        rejected_entries_str = ''
        if rejected_entries:
            rejected_entries_str = '\n'.join(rejected_entries)

        params = (download_data, accepted_entries_str, list_length, download_status, rejected_entries_str, list_name)
        if not self.db.query_exec(sql_update, params):
            print('ERROR: update_zzz_list_complete() query failed')
            return False
        return self.update_zzz_list_entries(list_name=list_name, list_data=accepted_entries)

    #--------------------------------------------------------------------------------

    #-----test-build the combined list in memory-----
    def test_combined_list(self, list_type: str='', list_ids=[]) -> list:
        if list_type:
            combined_list = self.get_list_entries_by_type(list_type)
            return combined_list

        if list_ids:
            #TODO: could be more efficient with just one DB query
            #  select * from zzz_list where id in (1,2,3,4)
            combined_list = []
            for list_id in list_ids:
                entries = self.get_list_entries(list_id=list_id)
                combined_list.extend(entries)
            return combined_list

        return []

    #--------------------------------------------------------------------------------

    #TODO: optimize this function
    # Example:
    #   sub.example.com is on the dns_deny_list
    #   example.com is on the dns_allow_list
    # Result:
    #   sub.example.com will not be added to the updated_deny_list
    #   all domains not covered by by a dns_allow_list entry will be added to updated_deny_list
    def remove_allowed_domains_from_deny_list(self, dns_deny_list: list, dns_allow_list: list) -> list:
        if not dns_allow_list:
            return dns_deny_list

        updated_deny_list = []
        for denied_domain in dns_deny_list:
            should_add_item = True
            for allowed_domain in dns_allow_list:
                if denied_domain.endswith(allowed_domain):
                    should_add_item = False
                    break
            if should_add_item:
                updated_deny_list.append(denied_domain)

        return updated_deny_list

    #--------------------------------------------------------------------------------

    # combined-DNS-deny:
    #     combine all DNS-deny lists:
    #         user-DNS-deny
    #         outside lists
    #         Settings
    #     de-dup combined list
    #     TODO: subtract user-DNS-allow from combined list
    #     save to /etc/bind/dns-blacklist
    #
    # combined-IP-deny: (IP or CIDR)
    #     combine all IP-deny lists:
    #         user-IP-deny
    #         IP's from the "both-deny" type outside lists
    #
    # combined-IP-allow: (IP or CIDR)
    #     combine all DNS-allow lists:
    #         user-IP-allow from Settings
    #         zzz.conf protected IP's
    #-----generate the combined list and save it to the DB-----
    def generate_combined_list(self, list_type: str='') -> list:
        if not list_type:
            return []
        combined_list_name = self.ConfigData['CombinedLists'].get(list_type, None)
        if not combined_list_name:
            # ERROR: unknown list type
            print('ERROR: unknown list type')
            return []
        list_id = self.get_list_id(combined_list_name)
        if not list_id:
            print('ERROR: list ID not found')
            return []

        combined_list = self.get_list_entries_by_type(list_type)
        if not combined_list:
            return []

        #TODO: subtract from this list with .endswith() comparison
        if list_type=='dns-deny':
            # download dns-allow
            dns_allow_list = self.get_list_entries_by_type('dns-allow')
            if dns_allow_list:
                # more thorough would be to check each combined-list entry against .endswith(allow-list entry), but it could be slow
                # combined_list = self.remove_allowed_domains_from_deny_list(combined_list, dns_allow_list)
                combined_list = self.util.diff_list(combined_list, dns_allow_list)
        combined_list = self.util.unique_sort(combined_list, make_lowercase=True)

        # save changes to the given list name
        sql_update = '''update zzz_list
            set list_length=?, zzz_last_updated=datetime('now'), last_valid_date_updated=datetime('now')
            where list_name=?
        '''
        params = (len(combined_list), combined_list_name)
        self.db.query_exec(sql_update, params)

        self.update_zzz_list_entries(list_id=list_id, list_name=combined_list_name, list_data=combined_list)

        return combined_list

    #--------------------------------------------------------------------------------

    def generate_all_combined_lists(self) -> None:
        # combined-DNS-deny, combined-IP-allow, combined-IP-deny
        # dns-deny, ip-allow, ip-deny
        for list_type in self.ConfigData['CombinedLists'].keys():
            self.generate_combined_list(list_type)

    #--------------------------------------------------------------------------------

    #-----only active lists are used-----
    # pull matching lists NOT INCLUDING the combined list that is being updated
    def get_list_entries_by_type(self, list_type:str)->list:
        sql_combined_list_name = ''
        combined_list_name = self.ConfigData['CombinedLists'].get(list_type, None)
        if combined_list_name:
            sql_combined_list_name = f"and zl.list_name!='{combined_list_name}'"

        sql = f'''select distinct entry_data
        from zzz_list zl, zzz_list_entries zle
        where zl.id=zle.zzz_list_id and zl.is_active=1 and zl.list_type=? {sql_combined_list_name}
        order by entry_data
        '''
        params = (list_type, )
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_dictionary=True)
        entries = []
        if rows:
            for row in rows:
                entries.append(row[0])

        return entries

    #--------------------------------------------------------------------------------

    def count_list_entries(self, list_id=None):
        sql = f'''select count(*) from zzz_list_entries where zzz_list_id=?'''
        params = (list_id,)
        num_entries = self.db.select(sql, params)
        if num_entries:
            return num_entries[0]
        return 0

    #--------------------------------------------------------------------------------

    # select zle.id as "entry_id", entry_data from zzz_list_entries zle limit 10
    #TODO: id->entry_data
    #   entries.values()
    #-----make list in memory-----
    # return a list by default, otherwise return dict
    def get_list_entries(self, list_id=None, list_name:str=None, return_dict:bool=False):
        sql_search_field = ''
        params = ()
        if self.util.is_int(list_id):
            sql_search_field = 'zl.id=?'
            params = (list_id,)
        elif list_name:
            sql_search_field = 'zl.list_name=?'
            params = (list_name,)
        else:
            return []
        sql = f'''select zle.id as "entry_id", entry_data
        from zzz_list zl, zzz_list_entries zle
        where zl.id=zle.zzz_list_id and {sql_search_field}
        '''
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)
        entries = []
        if rows_with_colnames:
            for row in rows_with_colnames:
                entry = None
                if return_dict:
                    entry = { 'entry_id': row['entry_id'], 'entry_data': row['entry_data'], }
                else:
                    entry = row['entry_data']
                entries.append(entry)
        return entries

    #--------------------------------------------------------------------------------

    def get_list_id(self, list_name:str):
        #TEST
        print(f'get_list_id({list_name})')

        if not list_name:
            return
        sql = 'select id from zzz_list where list_name=?'
        params = (list_name,)
        row = self.db.select(sql, params)
        if row:
            return row[0]

    #--------------------------------------------------------------------------------

    # returns either a dictionary or array of dictionaries(for all_lists)
    # list_data_source: url, entries, combined
    def get_list_info(self, list_id=None, all_lists: bool=False):
        '''provides: id, list_name, list_url, list_type, allow_edit, allow_delete, builtin'''
        if (not list_id) and (not all_lists):
            return None

        sql = 'select id, list_name, list_url, list_type, list_data_source, allow_edit, allow_delete, builtin from zzz_list'
        params = ()
        if not all_lists:
            sql = f'{sql} where id=?'
            params = (list_id,)
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        if not rows_with_colnames:
            return None
        if all_lists:
            return rows_with_colnames
        else:
            return rows_with_colnames[0]

    #--------------------------------------------------------------------------------

    def get_list_id_by_flag(self, always_active: bool=False, list_type: str=''):
        if always_active:
            sql_always_active = 'always_active=1'
        else:
            sql_always_active = 'always_active=0'
        
        sql = f'select id from zzz_list where {sql_always_active}'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        list_ids = []
        for row in rows_with_colnames:
            list_ids.append(row['id'])

        return list_ids

    #--------------------------------------------------------------------------------

    def get_list_lengths(self):
        sql = 'select id, list_length from zzz_list'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)
        list_lengths = {}
        for row in rows_with_colnames:
            list_lengths[row['id']] = row['list_length']
        return list_lengths

    #--------------------------------------------------------------------------------

    #-----make sure the given list data is not already in the DB-----
    # ways this function used:
    #   when adding a new list, always check name and url
    #   when editing an existing list, always check name, maybe check url
    # send existing_list_id when editing an existing list
    # returns an error message or empty string
    def check_duplicate_list(self, list_name: str, list_url: str='', existing_list_id: int=0) -> str:
        sql = 'select id, list_name, list_url, list_data_source from zzz_list where list_name=? or list_url=?'
        params = (list_name, list_url)
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        if not rows_with_colnames:
            return ''

        # check list_name
        list_data_source = ''
        for row in rows_with_colnames:
            if existing_list_id:
                if existing_list_id == row['id']:
                    # save this info for later
                    list_data_source = row['list_data_source']
                    # found the list we're checking against, so this does not count as a duplicate
                    continue
            if row['list_name'] == list_name:
                # name duplicated
                return 'a list already exists with that name'

        if list_data_source == 'entries':
            # don't do the URL check for existing entries-based lists
            return ''

        # check list_url
        if not list_url:
            return 'empty URL'
        for row in rows_with_colnames:
            if existing_list_id:
                if existing_list_id == row['id']:
                    # found the list we're checking against, so this does not count as a duplicate
                    continue
            if row['list_data_source'] == 'entries':
                # only check URL's for lists that use them
                continue
            if row['list_url'] == list_url:
                # url duplicated
                return f'''URL is already assigned to another list: {row['list_name']}'''

        return ''

    #--------------------------------------------------------------------------------

    # zzz_list
    # zzz_list_entries: zzz_list_id, entry_data
    def update_zzz_list_entries(self, list_id=None, list_name: str=None, list_data: list=None) -> bool:
        if list_name and not list_id:
            list_id = self.get_list_id(list_name)
        if not list_id:
            return False

        #-----delete all zzz_list_entries for the list in the DB-----
        if not self.delete_all_entries(list_id):
            return False

        #-----empty list is OK-----
        if not list_data:
            return True

        #-----upload new entries for the list-----
        sql_insert = 'insert into zzz_list_entries (zzz_list_id, entry_data) values (?, ?)'
        params_list = []
        for list_entry in list_data:
            if not list_entry:
                continue
            params = (list_id, list_entry)
            params_list.append(params)
            #-----do inserts in batches of 10,000-----
            if len(params_list)>=10000:
                self.db.query_exec_many(sql_insert, params_list)
                params_list = []
        if params_list:
            self.db.query_exec_many(sql_insert, params_list)
        return True

    #--------------------------------------------------------------------------------

    def is_entry_editable(self, entry_id):
        #TEST
        print(f'is_entry_editable({entry_id})')

        sql = '''select allow_edit
            from zzz_list zl, zzz_list_entries zle
            where zl.id=zle.zzz_list_id and zle.id=?
        '''
        params = (entry_id,)
        row = self.db.select(sql, params)
        if row:
            return row[0]

    #--------------------------------------------------------------------------------

    def is_list_deletable(self, list_id: int):
        sql = 'select allow_delete from zzz_list where id=?'
        params = (list_id,)
        row = self.db.select(sql, params)
        if row:
            return row[0]
        return 0

    # don't delete lists flagged as not-deletable
    def delete_list(self, list_id: int) -> bool:
        list_info = self.get_list_info(list_id)
        if not list_info:
            return False
        if not list_info['allow_delete']:
            return False

        if not self.delete_all_entries(list_id):
            return False

        sql = 'delete from zzz_list where id=?'
        params = (list_id,)
        return self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    def add_list(self, list_name: str, list_type: str, list_url: str):
        #TODO: add support for list_data_source='entries'
        list_data_source = 'url'
        sql = '''insert into zzz_list (list_name, list_type, list_data_source,
            allow_delete, allow_edit, builtin, always_active,
            is_active, auto_update, list_url,
            list_length, zzz_last_updated, last_valid_date_updated)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        allow_delete = 1
        allow_edit = 1
        builtin = 0
        always_active = 0
        is_active = 0
        auto_update = 1
        list_length = 0
        zzz_last_updated = '2022-01-01 02:00:00'
        last_valid_date_updated = zzz_last_updated
        params = (list_name, list_type, list_data_source,
            allow_delete, allow_edit, builtin, always_active,
            is_active, auto_update, list_url,
            list_length, zzz_last_updated, last_valid_date_updated
        )
        return self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    def delete_all_entries(self, list_id: int):
        sql_delete = 'delete from zzz_list_entries where zzz_list_id=?'
        params_delete = (list_id,)
        return self.db.query_exec(sql_delete, params_delete)

    def delete_entry(self, entry_id):
        sql = 'delete from zzz_list_entries where id=?'
        params = (entry_id,)
        return self.db.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    # lists with both domains and IPs will get the IPs dumped in the rejected_entries field
    # compile all those items into an auto-generated ip-deny list
    def make_ip_deny_from_dns_deny(self):
        # select id, list_name, rejected_entries from zzz_list where list_type='both-deny' and is_active=1
        ip_deny_list = 'ip-deny-auto-generated'
        pass

    #--------------------------------------------------------------------------------
