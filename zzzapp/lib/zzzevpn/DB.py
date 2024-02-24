import json
import pathlib
import sqlite3

# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.Config
import zzzevpn

class DB:
    'Database interface'
    
    ConfigData: dict = None
    
    dbh: sqlite3.Connection = None
    cur: sqlite3.Cursor = None
    last_query_status: bool = True
    readonly: bool = False
    sqlite_file: str = ''

    def __init__(self, ConfigData: dict=None) -> None:
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData

    def db_connect(self, sqlite_file: str, readonly: bool=False) -> bool:
        'connect to a sqlite DB file'
        # db_timeout=5
        # dbh = sqlite3.connect(sqlite_file, timeout=db_timeout, detect_types=sqlite3.PARSE_COLNAMES)
        self.sqlite_file = sqlite_file
        self.readonly = readonly
        try:
            if readonly:
                self.dbh = sqlite3.connect(f'file:{sqlite_file}?mode=ro', uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
            else:
                self.dbh = sqlite3.connect(sqlite_file, detect_types=sqlite3.PARSE_DECLTYPES)
        except:
            # connection failed
            return False
        
        #-----SQLite doesn't have a boolean type, so we make a custom adapter to map python booleans to SQLite integers-----
        sqlite3.register_adapter(bool, int)
        sqlite3.register_converter("boolean", lambda v: bool(int(v)))
        
        self.cur = self.dbh.cursor()
        #TODO: test for connection errors and return False
        return True

    def db_disconnect(self) -> None:
        self.cur.close()
        self.dbh.close()

    def db_reconnect(self) -> None:
        if (not self.sqlite_file) or (not self.dbh):
            # don't try to reconnect if we never connected before
            return
        self.db_disconnect()
        self.db_connect(self.sqlite_file, self.readonly)

    #---------------------------------------------------------------------------------------------------

    def list_tables(self) -> list:
        #NOTE: newer versions of sqlite use sqlite_schema
        sql = '''SELECT name FROM sqlite_master WHERE type='table' ORDER BY name'''
        params = ()
        colnames, rows, rows_with_colnames = self.select_all(sql, params)
        tables = []
        for row in rows_with_colnames:
            tables.append(row['name'])
        return tables

    #---------------------------------------------------------------------------------------------------

    def table_info(self, table_name: str):
        'gets schema info for a given table: (id, name, type, not_null, default_value, primary_key)'
        sql = f"select * from pragma_table_info(?)"
        params = (table_name,)
        return self.select_all(sql, params)

    def list_table_columns(self, table_name: str) -> list:
        (colnames, rows, rows_with_colnames) = self.table_info(table_name)
        if not rows_with_colnames:
            return []
        table_columns = []
        for row in rows_with_colnames:
            table_columns.append(row['name'])
        return table_columns

    #---------------------------------------------------------------------------------------------------

    # DB table info: total rows, oldest entry in a given row
    def get_table_date_info(self, table_name: str, row_with_date: str):
        if table_name not in ['squid_log', 'ip_log_daily']:
            return 0, '' ,''
        if row_with_date not in ['log_date']:
            return 0, '' ,''

        sql = f'select count(*), min({row_with_date}), max({row_with_date}) from {table_name}'
        params = ()
        row = self.select(sql, params)
        rows_in_db: int = 0
        oldest_entry: str = ''
        newest_entry: str = ''
        if row:
            rows_in_db = row[0]
            oldest_entry = row[1] or ''
            newest_entry = row[2] or ''
        return int(rows_in_db), str(oldest_entry), str(newest_entry)

    #--------------------------------------------------------------------------------
    
    # sql must contain SQLite-style formatting for param placeholders (qmark style or named style)
    # params must be an array of params
    def query_exec(self, sql: str, params: tuple) -> bool:
        'For INSERT/UPDATE/DELETE queries'
        try:
            self.cur.execute(sql, params)
            #-----commit the query if it worked-----
            self.dbh.commit()
        except sqlite3.Error as error:
            print("query_exec() Error while executing sqlite query: ", str(error))
            #-----rollback the query if it failed-----
            self.dbh.rollback()
            return False
        return True

    # insert a sequence of objects in the database
    # the sqlite3 module provides the executemany() method to execute a SQL query against a sequence
    # params_list = [
    #     ('test', '123'), 
    #     ('data', '987'), 
    # ]
    def query_exec_many(self, sql: str, params_list: list) -> bool:
        'For INSERT/UPDATE/DELETE queries'
        try:
            self.cur.executemany(sql, params_list)
            self.dbh.commit()
        except sqlite3.Error as error:
            print("query_exec_many() Error while executing sqlite query: ", str(error))
            self.dbh.rollback()
            return False
        return True
    
    #-----run the queries in a SQL file-----
    def exec_script(self, script_filepath: str) -> bool:
        if not script_filepath:
            print('ERROR: script_filepath is empty')
            return False
        path = pathlib.Path(script_filepath)
        if not path.is_file():
            print('ERROR - file not found: ' + script_filepath)
            return False
        
        sql_script = ''
        with open(script_filepath, 'r') as sqlite_file:
            sql_script = sqlite_file.read()
        if not sql_script:
            return False
        try:
            self.cur.executescript(sql_script)
        except sqlite3.Error as error:
            #-----no rollback() here because the SQL file should have a begin-commit transaction section-----
            print("exec_script() Error while executing sqlite script: ", str(error))
            return False
        return True
    
    #---------------------------------------------------------------------------------------------------
    
    #-----just get the first row of a query-----
    def select(self, sql: str, params: tuple):
        self.last_query_status = True
        try:
            self.cur.execute(sql, params)
        except sqlite3.Error as error:
            print("select() Error while executing sqlite query: ", str(error))
            self.last_query_status = False
            return
        row = self.cur.fetchone()
        return row
    
    #---------------------------------------------------------------------------------------------------
    
    #-----get all rows for a given query in a useful dictionary-----
    def select_all(self, sql: str, params: tuple, skip_array: bool=False, skip_dictionary: bool=False):
        ''' For SELECT queries
            Returns a dictionary with all rows from the query result, labeled with their column names
        '''

        self.last_query_status = True
        try:
            self.cur.execute(sql, params)
        except sqlite3.Error as error:
            print("select_all() Error while executing sqlite query: ", str(error))
            self.last_query_status = False
            return None, None, None

        #-----get table header data-----
        colnames = [row[0] for row in self.cur.description]
        
        rows = self.cur.fetchall()
        rows_with_colnames = []
        #-----large data sets don't always require returning the same data in 2 formats-----
        # options to return one or the other
        if not skip_dictionary:
            for row in rows:
                rows_with_colnames.append(dict(zip(colnames, row)))
        if skip_array:
            rows = []

        return colnames, rows, rows_with_colnames
    
    #--------------------------------------------------------------------------------
    
    #-----count pending service requests for a given service/action-----
    # status: Requested, Working
    def count_pending_requests(self, service_name: str, action: str=None) -> int:
        sql = "select count(*) from service_request where service_name=? and status in (?, ?)"
        params = (service_name, self.ConfigData['ServiceStatus']['Requested'], self.ConfigData['ServiceStatus']['Working'])
        if action:
            sql = "select count(*) from service_request where service_name=? and action=? and status in (?, ?)"
            params = (service_name, action, self.ConfigData['ServiceStatus']['Requested'], self.ConfigData['ServiceStatus']['Working'])
        row = self.select(sql, params)
        return int(row[0])

    #--------------------------------------------------------------------------------
    
    #TODO: capture errors, return False and/or some error message
    #-----insert a request for a service-----
    def insert_service_request(self, service_name: str, action: str, details: str='') -> bool:
        sql = "insert into service_request (req_date, service_name, action, details, status) values (datetime('now'), ?, ?, ?, ?)"
        params = (service_name, action, details, self.ConfigData['ServiceStatus']['Requested'])
        return self.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    #-----get a list of pending requests-----
    def get_service_requests(self, service_name: str, action: str=None):
        sql = 'select * from service_request where service_name=? order by id desc'
        params = (service_name,)
        if action:
            sql = 'select * from service_request where service_name=? and action=? order by id desc'
            params = (service_name, action)
        (colnames, rows, rows_with_colnames) = self.select_all(sql, params)
        
        num_unprocessed_requests: int = 0
        for row in rows_with_colnames:
            if row['status']==self.ConfigData['ServiceStatus']['Requested'] or row['status']==self.ConfigData['ServiceStatus']['Working']:
                num_unprocessed_requests += 1
        found_service_requests: dict = {
            'num_unprocessed_requests': num_unprocessed_requests,
            'colnames': colnames,
            'rows_with_colnames': rows_with_colnames,
        }
        return found_service_requests
    
    #-----insert a request for a service, but don't do the insert if a similar unprocessed request exists already-----
    # return True/False to indicate if the insert was done or not
    # (status=Requested or Working)
    # Example: UpdateZzz.py
    #            request_zzz_update(action)
    #              get_zzz_update_requests(action)
    def insert_unique_service_request(self, service_name: str, action: str, details: str='') -> bool:
        if self.count_pending_requests(service_name, action)>0:
            return False
        self.insert_service_request(service_name, action, details)
        return True
    
    #--------------------------------------------------------------------------------
    
    #-----insert a reload request for a service-----
    def request_reload(self, service_name: str) -> None:
        self.insert_service_request(service_name, 'reload')
    
    def request_restart(self, service_name: str) -> None:
        self.insert_service_request(service_name, 'restart')
    
    #--------------------------------------------------------------------------------

    #-----format the given DB result colnames for HTML output-----
    # INPUT: list
    # OUTPUT: HTML string
    def result_header(self, colnames: list) -> str:
        html_items = ['<tr><th>', '</th><th>'.join(colnames), '</th></tr>\n']
        return ''.join(html_items)

    #-----format the given DB result data for HTML output-----
    # INPUT: array of lists (rows)
    # OUTPUT: HTML string
    # only works if all row items are strings or can be safely cast to strings
    # bool will crash?
    def result_data(self, rows: list) -> str:
        html_items = []
        for row in rows:
            html_items.append('<tr><td>')
            html_items.append('</td><td>'.join(map(str, row)))
            html_items.append('</td></tr>\n')
        return ''.join(html_items)
    
    def result_full_table(self, colnames: list, rows: list) -> str:
        html_items = ['<table>', self.result_header(colnames), self.result_data(rows), '</table>']
        return ''.join(html_items)

    #--------------------------------------------------------------------------------
    
    # sample DB table contents:
    # 20|21|JSON|2021-01-08T23:59:02.084237|2020-10-20 01:12:14|21a1
    # JSON --> json_parsed:
    # '{
    #    "EnableMaxMind": "false",
    #    "VPNusers": ["user1","user2","user3"]
    #  }'
    def get_zzz_system_info(self):
        sql = 'select * from zzz_system'
        params = ()
        (colnames, rows, rows_with_colnames) = self.select_all(sql, params)
        zzz_system_info = rows_with_colnames[0]
        json_parsed = None
        try:
            json_parsed = json.loads(zzz_system_info['json'])
        except:
            json_parsed = None
        zzz_system_info_parsed: dict = {
            'zzz_system_info': zzz_system_info,
            'json_parsed': json_parsed
        }
        return zzz_system_info_parsed
    
    #TODO: check the values to make sure they have valid data
    def update_zzz_system_info_json(self, json_parsed) -> bool:
        if not json_parsed:
            return False
        
        #TODO: validate the json_parsed param
        # assume the json_parsed param is generated from self.get_zzz_system_info()
        # no need to convert true/false strings to python booleans since they will auto-convert
        #   1) loads(dumps(python_hash)) != python_hash
        #      conversion issues here: (True --> "true", etc.)
        #   2) dumps(loads(python_hash)) == python_hash
        # we're doing option #2, so no worries about data conversion issues
        
        # parse json_parsed into a string var
        json_dumped: str = ''
        try:
            json_dumped = json.dumps(json_parsed)
        except:
            return False
        
        # write the string to the DB
        sql = 'update zzz_system set json=?'
        params = (json_dumped,)
        return self.query_exec(sql, params)

    #--------------------------------------------------------------------------------

    # https://www.sqlite.org/pragma.html#pragma_optimize
    # optimizing the DB every few hours is supposed to be helpful
    def optimize(self) -> None:
        sql = 'PRAGMA analysis_limit=400'
        params = ()
        self.query_exec(sql, params)

        sql = 'PRAGMA optimize'
        self.query_exec(sql, params)

    #--------------------------------------------------------------------------------
