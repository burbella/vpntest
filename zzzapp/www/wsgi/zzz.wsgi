#-----Zzz web app-----
# apache mod_wsgi execution starts with application()

import gc
import site
import sys
import threading
import time

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

#-----package with all the Zzz modules-----
import zzzevpn
import zzzevpn.NetworkService
import zzzevpn.WSGI
import zzzevpn.ZzzTest

ConfigData: dict = None
ConfigDataLoaded: bool = False

#TODO: new db_list format
#  db_list = {
#      thread_id: { 'db': DB object, 'last_access': datetime, }
#  }
#-----due to multithreading, this needs to be an array of DB connections-----
# store a map: thread ID --> db connection
db_list = {}

data_validation: zzzevpn.DataValidation = None

def application(environ: dict, start_response):
    thread_id = threading.get_ident()
    
    #-----no DB connection needed in some objects, so it's OK to re-use the objects between threads-----
    # ConfigData (important, because making a new object hits a few files and a few network IP/DNS lookups)
    # db_list
    # data_validation
    global ConfigData
    global ConfigDataLoaded
    global db_list
    global data_validation
    
    zzz_wsgi = zzzevpn.WSGI.WSGI(environ=environ, start_response=start_response)
    
    if ConfigData:
        # ConfigData is defined, but not marked as DataLoaded
        # another thread is probably working on loading it
        # wait for the other thread to finish loading it
        if not ConfigDataLoaded:
            time_start = time.time()
            seconds_waited = 0
            # give up waiting after 10 seconds
            while seconds_waited<10 and not ConfigDataLoaded:
                time.sleep(0.2)
                seconds_waited = time.time() - time_start
            seconds_waited = round(seconds_waited, 6)
            zzz_wsgi.error_log(f'waited {seconds_waited} seconds for config to load in another thread')
    if (not ConfigData) or (not ConfigDataLoaded):
        #-----load ConfigData-----
        ConfigDataLoaded = False
        time_start = time.time()
        # config = zzzevpn.Config.Config()
        config = zzzevpn.Config(skip_autoload=True)
        new_ConfigData = config.get_config_data()
        #-----count loading time-----
        seconds_waited = time.time() - time_start
        if config.is_valid():
            #TODO: maybe only report slow loads?
            # if seconds_waited>2:
            seconds_waited = round(seconds_waited, 6)
            zzz_wsgi.error_log(f'config loaded in {seconds_waited} seconds')
        else:
            zzz_wsgi.error_log('ERROR: invalid zzz config file')
            return zzz_wsgi.send_output('ERROR: invalid zzz config file')
        #-----load the new ConfigData into WSGI-----
        ConfigData = new_ConfigData
        ConfigDataLoaded = True
        data_validation = None
    
    if (data_validation is None):
        data_validation = zzzevpn.DataValidation(ConfigData)
    
    #TODO: prevent infinite growth of db_list
    #      identify threads that no longer exist and remove corresponding DB object from db_list
    #      run whenever db_list has over 25 items?
    #      track the last access datetime of the thread and only delete the oldest?
    #      db_list size reported in apache logs:
    #        grep thread_count /var/log/apache2/error.log|cut -d '=' -f 2|cut -d ',' -f 1|sort -u|less 
    #-----db_list is almost as good as a DB connection pool-----
    # passing a global db object around results in this error:
    #   sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread. The object was created in thread id 139745295329024 and this is thread id 139745191511808
    # FIX:
    #   each WSGI thread gets its own db connection object
    #   use the thread ID as a dictionary key
    #   apache mod_wsgi has 25 threads max:
    #     config/httpd/mpm_event.conf:17:       ThreadsPerChild          25
    #   threads may get re-used at any time, but they are re-used 100% after the thread count gets to 25
    use_db = db_list.get(thread_id, None)
    thread_count = len(db_list)
    if thread_count>25:
        #-----temporary fix to prevent infinite growth of db_list-----
        # it would be more efficient to only remove DB entries from threads that no longer exist?
        db_list = {}
    if (use_db is None):
        new_db = zzzevpn.DB(ConfigData)
        new_db.db_connect(ConfigData['DBFilePath']['Services'])
        db_list[thread_id] = new_db
        use_db = new_db
        zzz_wsgi.error_log('INFO: thread ID {} gets a new DB object\n      thread_count={}'.format(thread_id, thread_count))
    else:
        zzz_wsgi.error_log('INFO: thread ID {} RE-USES EXISTING DB object'.format(thread_id))
    
    if not data_validation.check_content_length(zzz_wsgi.environ, zzz_wsgi.request_body_size):
        zzz_wsgi.error_log('ERROR: excessive data in GET/POST')
        return zzz_wsgi.send_output('ERROR: excessive data in GET/POST')
    
    #TODO: finish implementing global data validation
    #-----validate data-----
    data_to_validate = {
        # 'action': action,
    }
    if not data_validation.validate(zzz_wsgi.environ, data_to_validate):
        zzz_wsgi.error_log('ERROR: data validation failed')
        return zzz_wsgi.send_output('ERROR: data validation failed')

    #-----set the vars here that we did not have when the object was created-----
    zzz_wsgi.ConfigData = ConfigData
    zzz_wsgi.db = use_db
    
    #-----process the request-----
    output = choose_path(zzz_wsgi)

    # force garbage collection
    gc.collect()

    return zzz_wsgi.send_output(output)

#--------------------------------------------------------------------------------

def choose_path(zzz_wsgi: zzzevpn.WSGI.WSGI):
    #TEST
    # output = 'Zzz App\nPath: ' + zzz_wsgi.path_info

    #-----this updates app global vars-----
    ConfigData = zzz_wsgi.ConfigData
    db = zzz_wsgi.db
    
    if zzz_wsgi.path_info == '/config_reload':
        output = config_reload(zzz_wsgi.environ)
        return zzz_wsgi.make_output_or_error(output)
    
    return zzz_wsgi.choose_path()

#--------------------------------------------------------------------------------

#-----this can't be moved into WSGI.py since it edits app globals-----
# curl --resolve services.zzz.zzz:443:10.7.0.1 https://services.zzz.zzz/z/config_reload
def config_reload(environ: dict):
    global ConfigData
    global ConfigDataLoaded
    global db_list
    global data_validation
    #-----make a webpage object while we still have ConfigData-----
    webpage = zzzevpn.Webpage(ConfigData=ConfigData, pagetitle='Config Reload')
    #-----erase global vars-----
    # on the next call to application(), all vars will auto-init
    ConfigDataLoaded = False
    ConfigData = None
    db_list = {}
    data_validation = None
    #-----webpage object still has the old ConfigData, so we can make output html with it-----
    body = '''<pre>Config has been reloaded</pre>'''
    return webpage.make_webpage(environ, body)

#--------------------------------------------------------------------------------

