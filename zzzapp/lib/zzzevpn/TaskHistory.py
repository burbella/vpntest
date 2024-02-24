#-----Task History display-----

#-----package with all the Zzz modules-----
import zzzevpn

class TaskHistory:
    'TaskHistory page'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None
    
    body: str = ''
    TaskHistoryHTML: dict = {}
    
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
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self) -> None:
        #-----prep the HTML values-----
        self.TaskHistoryHTML = {
            'TaskStatus': '',
        }
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ: dict, pagetitle: str) -> str:
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        
        self.TaskHistoryHTML['TaskStatus'] = self.get_task_status();
        
        output = self.webpage.make_webpage(environ, self.make_TaskHistoryPage(environ))
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def make_TaskHistoryPage(self, environ: dict) -> str:
        body = self.webpage.load_template('TaskHistory')
        self.TaskHistoryHTML['CSP_NONCE'] = environ['CSP_NONCE']
        return body.format(**self.TaskHistoryHTML)
    
    #--------------------------------------------------------------------------------
    
    def get_task_status(self, query_limit: int=None):
        # default - not more than 2000 rows until pagination is installed
        default_limit = 2000
        
        if query_limit:
            # drop bad data
            if not self.util.is_int(query_limit):
                query_limit = default_limit
            if query_limit>10000:
                query_limit = 10000
        else:
            query_limit = default_limit

        sql = "select id, req_date, service_name, action, status, status_msg, details, start_date, wait_time, end_date, work_time from service_request order by id desc"
        if query_limit:
            sql += ' limit ' + str(query_limit)
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params)
        
        if len(rows_with_colnames)==0:
            return "<p>No tasks in database</p>"
        
        timezone_code = self.util.format_timezone()
        options = {
            'custom_timezone': True,
            'collapsable_html': {
                'details': 'details_',
                'status_msg': 'status_msg_',
            },
        }
        table_html = self.util.custom_html_table(rows_with_colnames, options)
        output = f'''
            <table>
            <tr><th>ID</th><th>Request Date ({timezone_code})</th><th>Service<br>Name</th><th>Action</th><th>Status</th>
            <th>Status<br>Message</th><th class="width_300">Details (click to expand)</th>
            <th>Start Date ({timezone_code})</th><th>Wait<br>Time</th><th>End Date ({timezone_code})</th><th>Work<br>Time</th></tr>
            {table_html}
            </table>
            '''
        
        return output
    
    #--------------------------------------------------------------------------------

