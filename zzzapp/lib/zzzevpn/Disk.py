#-----disk management-----

# Make a Config file option to specify the size limit.
# Auto-delete items from big tables:
#     ip log
#     squid log
# Delete the oldest records first.
# Iterative deletion
#     calculate the total number of rows
#     calculate the table size
#     estimate the avg row size
#     calculate how many rows need to be removed in order to get below the size limit specified in the config
#     Delete Data one week at a time:
#         find the oldest date in the table
#             select min(DATE_COLUMN) from TABLE_NAME
#         store in a var DATE_VAR
#         DATE_VAR = DATE_VAR - 7
#         figure out which rows are below the minimum date
#             select count(*) from TABLE_NAME where DATE_COLUMN < DATE_VAR
# about 10,000 rows at a time is enough, or about 1 day's worth of data
# sleep 1 second before deleting more

import pprint
import time
import traceback

#-----package with all the Zzz modules-----
import zzzevpn

class Disk:
    'Disk Management'

    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None

    # daily cron: run for 5 out of every 15 minutes, stop after 20 hours
    limit_runtime_per_time_segment = 5*60 # run for 5 minutes at a time
    sleep_time_between_segments = 10*60 # 10 minutes sleep between runs
    limit_runtime_total = 20*60*60 # stop after 20 hours
    start_time_delete = 0 # limit_runtime_total
    start_time_current_segment = 0 # limit_runtime_per_time_segment
    minimum_rows_to_keep = 100000 # only process logs with over 100,000 rows
    megabyte = 1024 * 1024
    max_db_size = 0
    should_run = True
    test_mode = False

    valid_tables = ['ip_log_daily', 'squid_log']
    process_filenames = ['update-ip-log.py', 'update-squid-log.py']
    current_db_size = 0
    current_db_filesize = 0
    all_table_sizes = {} # calculated sizes for each table
    table_info = {
        'ip_log_daily': {
            'bytes_per_row': 81, # average obeserved in some tests
            'excess_rows': 0,
            'oldest_entry': 0,
            'rows': 0,
            'rows_to_delete': 0,
            'should_process_log': False,
            'size': 0, # bytes
        },
        'squid_log': {
            'bytes_per_row': 209, # average obeserved in some tests
            'excess_rows': 0,
            'oldest_entry': 0,
            'rows': 0,
            'rows_to_delete': 0,
            'should_process_log': False,
            'size': 0, # bytes
        },
    }
    table_indexes = {
        'ip_log_daily': [
            'ip_log_daily_ip_idx',
            'ip_log_daily_country_code_idx',
            'ip_log_daily_log_date_idx',
            'ip_log_daily_updated_idx',
            'ip_log_daily_two_col_idx'
        ],
        'squid_log': [
            'squid_host_idx',
            'squid_ip_idx',
            'squid_log_date_idx',
            'squid_log_start_date_idx'
        ],
    }

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None):
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
        self.init_vars()

    #--------------------------------------------------------------------------------

    def init_vars(self):
        self.max_db_size = self.ConfigData['DiskSpace']['Database'] * self.megabyte

    #--------------------------------------------------------------------------------

    def count_rows(self, table_name: str) -> int:
        if table_name not in self.valid_tables:
            return 0
        sql = f'select count(*) from {table_name}'
        params = ()
        row = self.db.select(sql, params)
        return row[0]

    def count_rows_date_range(self, table_name: str, date_increment: int) -> int:
        if table_name not in self.valid_tables:
            return 0
        # datetime('2022-07-02', '+2 day');
        sql = f"select count(*) from {table_name} where log_date<datetime(?, '+{date_increment} day')"
        params = (self.table_info[table_name]['oldest_entry'],)
        row = self.db.select(sql, params)
        #TEST
        print(f'SQL: {sql}')
        print(f'    params: {params}')

        return row[0]

    def do_delete(self, table_name: str, date_increment: int) -> bool:
        if table_name not in self.valid_tables:
            return False
        start_time = time.time()
        sql = f"delete from {table_name} where log_date<datetime(?, '+{date_increment} day')"
        params = (self.table_info[table_name]['oldest_entry'],)

        #TEST - enable delete when test print-outs look good
        result = self.db.query_exec(sql, params)
        # result = True

        self.print_runtime(start_time, f'''    do_delete(): table_name={table_name}, oldest_entry={self.table_info[table_name]['oldest_entry']}, date_increment={date_increment}, result={result}''')

        return result

    #--------------------------------------------------------------------------------

    def compare_db_size_to_filesize(self, db_filesize, db_size) -> int:
        percent_diff = round(100*db_filesize/db_size, 1)
        print(f'Compare DB filesize to actual data size: {db_filesize}/{db_size}={percent_diff}%')

    #--------------------------------------------------------------------------------

    def calc_db_size(self) -> int:
        print('calc_db_size()')
        sql = f"select name, pgsize from dbstat where aggregate=TRUE"
        params = ()
        start_time = time.time()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        self.print_runtime(start_time, 'calc_db_size()')

        db_size = 0
        for row in rows_with_colnames:
            self.all_table_sizes[row['name']] = row['pgsize']
            db_size += row['pgsize']
        return db_size

    #--------------------------------------------------------------------------------

    def calc_table_size(self, table_name: str) -> int:
        if table_name not in self.valid_tables:
            return 0

        sql = 'select pgsize from dbstat where name=? and aggregate=TRUE'
        params = (table_name,)
        row = self.db.select(sql, params)
        return row[0]

    #--------------------------------------------------------------------------------

    def print_runtime(self, start_time, description: str):
        runtime = round(time.time() - start_time, 4)
        print(f'{description} ran in {runtime} seconds', flush=True)

    #--------------------------------------------------------------------------------

    def delete_old_rows(self, table_name: str):
        if table_name not in self.valid_tables:
            return

        print(f'delete_old_rows({table_name})')
        table_size = self.util.add_commas(self.table_info[table_name]['size'])
        print(f'''    table size={table_size}, rows_to_delete: {self.table_info[table_name]['rows_to_delete']}''', flush=True)

        date_increment = 0
        while self.should_run and self.table_info[table_name]['rows_to_delete']>0:
            if (time.time() - self.start_time_delete) > self.limit_runtime_total:
                self.should_run = False
                print(f'total runtime limit reached ({self.limit_runtime_total} seconds), returning')
                return
            if (time.time() - self.start_time_current_segment) > self.limit_runtime_per_time_segment:
                print(f'segment runtime limit reached, sleeping for {self.sleep_time_between_segments} seconds')
                # release the maintenance flag while sleeping
                self.util.clear_db_maintenance_flag()
                time.sleep(self.sleep_time_between_segments)
                print(f'done sleeping')
                db_maintenance = self.util.wait_for_no_db_maintenance(max_wait=60, sleep_time=3, print_updates=True)
                if db_maintenance:
                    print(f'Waited 60 seconds, the DB maintenance flag is still set, exiting...')
                    self.should_run = False
                    return
                # set the maintenance flag to start again
                self.util.set_db_maintenance_flag('delete_excess_data')
                # reset the segment timer
                self.start_time_current_segment = time.time()

            #-----delete a bunch of rows-----
            # one day of data at a time
            date_increment += 1
            rows_found = self.count_rows_date_range(table_name, date_increment)
            if not rows_found:
                # no data for 1 day --> update the oldest entry, in case there is a large gap between dates
                self.table_info[table_name]['oldest_entry'] = self.get_oldest_entry_date(table_name)
                date_increment = 1
                rows_found = self.count_rows_date_range(table_name, date_increment)
            print(f'    delete rows: {rows_found}')
            if self.do_delete(table_name, date_increment):
                #-----sleep between deletes-----
                self.table_info[table_name]['rows_to_delete'] -= rows_found
                time.sleep(1)
            else:
                print('    ERROR deleting rows')
                self.should_run = False

            print(f'''    rows to delete: {self.table_info[table_name]['rows_to_delete']}''')

        print('*'*50)

    #--------------------------------------------------------------------------------

    def get_table_stats(self, table_name: str):
        # start_time = time.time()
        # #TODO: replace this with size data from self.all_table_sizes[table_name]
        # self.table_info[table_name]['size'] = self.calc_table_size(table_name)
        # self.print_runtime(start_time, f'calc_table_size({table_name})')
        # time.sleep(0.5)
        self.table_info[table_name]['size'] = self.all_table_sizes[table_name]
        #-----include index sizes-----
        table_indexes = self.table_indexes.get(table_name, None)
        if table_indexes:
            for index in table_indexes:
                self.table_info[table_name]['size'] += self.all_table_sizes[index]

        start_time = time.time()
        self.table_info[table_name]['rows'] = self.count_rows(table_name)
        self.print_runtime(start_time, f'count_rows({table_name})')
        time.sleep(0.5)

        if self.table_info[table_name]['rows'] > self.minimum_rows_to_keep:
            self.table_info[table_name]['should_process_log'] = True

        start_time = time.time()
        if self.table_info[table_name]['rows']:
            self.table_info[table_name]['oldest_entry'] = self.get_oldest_entry_date(table_name)
            self.table_info[table_name]['bytes_per_row'] = round(self.table_info[table_name]['size']/self.table_info[table_name]['rows'])
        self.print_runtime(start_time, f'get_oldest_entry_date({table_name})')
        time.sleep(0.5)

    #--------------------------------------------------------------------------------

    def get_oldest_entry_date(self, table_name: str):
        if table_name not in self.valid_tables:
            return

        sql_ip_min_date = f'select min(log_date) from {table_name}'
        params = ()
        start_time = time.time()
        row = self.db.select(sql_ip_min_date, params)
        self.print_runtime(start_time, f'{table_name} min(log_date)')
        oldest_date = row[0]
        print(f'oldest entry in {table_name}: {oldest_date}')
        return oldest_date

    #--------------------------------------------------------------------------------

    #-----how many rows to delete from the deletable tables-----
    # calc: total DB size, size of each table, rows to delete to get the total below the limit
    def calc_rows_to_delete(self):
        total_space_to_clear = self.current_db_size - self.max_db_size
        if total_space_to_clear <= 0:
            # DB is not too big, so exit
            print('total_space_to_clear = self.current_db_size - self.max_db_size')
            total = self.util.add_commas(total_space_to_clear)
            current_db_size = self.util.add_commas(self.current_db_size)
            max_db_size = self.util.add_commas(self.max_db_size)
            print(f'    {total} = {current_db_size} - {max_db_size}')
            return

        # keep 100,000 rows in each table
        excess_rows = self.table_info['squid_log']['rows'] - self.minimum_rows_to_keep
        if excess_rows > 0:
            self.table_info['squid_log']['excess_rows'] = excess_rows
        excess_rows = self.table_info['ip_log_daily']['rows'] - self.minimum_rows_to_keep
        if excess_rows > 0:
            self.table_info['ip_log_daily']['excess_rows'] = excess_rows

        recoverable_space = self.table_info['squid_log']['excess_rows'] * self.table_info['squid_log']['bytes_per_row']
        if recoverable_space > total_space_to_clear:
            # reduce it to the minimum needed
            self.table_info['squid_log']['rows_to_delete'] = 1 + int(total_space_to_clear / self.table_info['squid_log']['bytes_per_row'])
            return

        # delete all the excess rows
        self.table_info['squid_log']['rows_to_delete'] = self.table_info['squid_log']['excess_rows']

        # need more space, include the next table
        recoverable_space += self.table_info['ip_log_daily']['excess_rows'] * self.table_info['ip_log_daily']['bytes_per_row']
        if recoverable_space > total_space_to_clear:
            # reduce it to the minimum needed
            space_to_clear = total_space_to_clear - (self.table_info['squid_log']['rows_to_delete'] * self.table_info['squid_log']['bytes_per_row'])
            self.table_info['ip_log_daily']['rows_to_delete'] = 1 + int(space_to_clear / self.table_info['ip_log_daily']['bytes_per_row'])
            return

        # delete all the excess rows
        self.table_info['ip_log_daily']['rows_to_delete'] = self.table_info['ip_log_daily']['excess_rows']

    #--------------------------------------------------------------------------------

    #TODO: apply runtime limits to prevent it from running too long or choking other processes that need the DB
    # tables: ip_log_daily, squid_log
    def delete_excess_data(self, flush_data: bool=False):
        if not (self.table_info['ip_log_daily']['should_process_log']
                or self.table_info['squid_log']['should_process_log']):
            print('not enough rows to process tables, exiting')
            return

        #TODO: finish this calculation
        #-----figure out how many rows to delete from each table-----
        # prefer to delete squid_log because the rows are larger and there are more of them
        # try to keep 100,000 rows in the table though
        self.calc_rows_to_delete()

        #TEST
        print('table_info:')
        pprint.pprint(self.table_info)
        print('all_table_sizes:')
        pprint.pprint(self.all_table_sizes)

        if not flush_data:
            print('returning without making changes')
            return

        self.start_time_delete = time.time()
        self.start_time_current_segment = time.time()
        print('*'*50)
        if self.table_info['squid_log']['should_process_log'] and self.should_run:
            self.delete_old_rows('squid_log')
        if self.table_info['ip_log_daily']['should_process_log'] and self.should_run:
            self.delete_old_rows('ip_log_daily')

    #--------------------------------------------------------------------------------

    # no need to delete rows if less than 10,000
    # delete from the larger table first
    #
    #TEST:
    # row = self.db.select(sql, params)
    # (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
    #ENDTEST
    def check_db(self, flush_data: bool=False) -> bool:
        self.current_db_filesize = self.util.get_filesize(self.ConfigData['DBFilePath']['Services'])
        if self.current_db_filesize <= self.max_db_size:
            # file is not too large, so no need to run more disk-intensive checks, just exit
            current_db_filesize = round(self.current_db_filesize/self.megabyte)
            max_db_size = round(self.max_db_size/self.megabyte)
            print(f'DB filesize on disk: {current_db_filesize} MB')
            print(f'file size is not above the config limit of {max_db_size} MB, exiting')
            return True

        db_maintenance = self.util.wait_for_no_db_maintenance(max_wait=300, sleep_time=10, print_updates=True)
        if db_maintenance:
            print(f'Waited 300 seconds, the DB maintenance flag is still set, exiting...')
            return False

        #TODO: not needed?
        #-----don't do maintenance while the log parsers are running-----
        stopped = self.util.wait_for_process_to_stop(process_filenames=['update-ip-log.py', 'update-squid-log.py'], max_wait=60, sleep_time=5)
        if not stopped:
            print(f'Waited 60 seconds and the processes are still running, exiting...')
            return False

        maintenance_time = time.time()
        self.util.set_db_maintenance_flag('delete_excess_data')

        self.current_db_size = self.calc_db_size()
        print('DB size: ' + self.util.add_commas(self.current_db_size))
        self.compare_db_size_to_filesize(self.current_db_filesize, self.current_db_size)

        # sleep to let other processes use the DB
        time.sleep(0.5)

        for table_name in self.valid_tables:
            try:
                self.get_table_stats(table_name)
            except:
                print(f'WARNING: get_table_stats({table_name}) crashed')
                print(traceback.format_exc())

        delete_excess_data_worked = True
        try:
            self.delete_excess_data(flush_data)
        except:
            print('ERROR: delete_excess_data() crashed')
            print(traceback.format_exc())
            delete_excess_data_worked = False

        flush_data_worked = True
        if flush_data:
            # optimize the tables after mass deletes
            try:
                start_time = time.time()
                self.db.optimize()
                self.print_runtime(start_time, 'db.optimize()')
            except:
                print('ERROR: db.optimize() crashed')
                print(traceback.format_exc())
                flush_data_worked = False

        # put this outside the delete_excess_data() function so the flag gets cleared even if it crashed
        self.util.clear_db_maintenance_flag()
        self.print_runtime(maintenance_time, 'maintenance_time')

        return delete_excess_data_worked and flush_data_worked
