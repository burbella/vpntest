#-----Zzz conftest file-----

import pytest
import site
import sys

#-----REPOS TEST - import modules from the lib directory-----
# pytest looks at this directory to determine where to find the modules to test
# ******************************************************
# *** DO NOT USE THE PYTEST DIRECTORIES IN LIVE CODE ***
# ******************************************************
if sys.platform=='linux':
    # LIVE CODE DIRECTORY: site.addsitedir('/opt/zzz/python/lib')
    # pytest directories:
    site.addsitedir('/opt/zzz/python/test/lib')
    site.addsitedir('/opt/zzz/python/test/bin')

#-----import EVERYTHING to test everything-----
# zzzevpn brings in most modules automatically
import zzzevpn
import zzzevpn.DiffCode
import zzzevpn.NetworkService
import zzzevpn.WhoisService
import zzzevpn.WSGI
import zzzevpn.ZzzICAPserver

#TEST modules
import zzzevpn.TEMPLATE_LIB
import zzzevpn.TEMPLATE_LIB_with_WSGI
import zzzevpn.ZzzHTMLParser
import zzzevpn.ZzzTest

config_files_available = [
    '/opt/zzz/python/test/pytest_zzz.conf',
    '/opt/zzz/python/test/pytest_zzz_error.conf',
]

@pytest.fixture(scope="session")
def pagetitle():
    return 'pytest pagetitle'

@pytest.fixture(scope="session")
def default_config():
    return zzzevpn.Config(skip_autoload=True)

@pytest.fixture(scope="session")
def default_ConfigData(default_config):
    return getattr(default_config, 'default_ConfigData')

@pytest.fixture(scope="session")
def make_config(default_config, default_ConfigData):
    #-----factory fixture for passing in a filename-----
    def _make_config(pytest_ConfigFile):
        if not pytest_ConfigFile:
            return
        
        #-----get Config-----
        pytest_ConfigData = default_ConfigData

        #TODO: finish setting up separate pytest vars to avoid using production resources for pytest
        #      this includes: files, ports, redis DB, sqlite DB
        #################### CUSTOMIZE PYTEST VARS BELOW ####################
        #-----modify Config to use TEST config settings-----
        # (NOT FOR USE IN PRODUCTION)
        # pytest_ConfigData['ITEM'] = 'value'
        
        # test DB files
        pytest_ConfigData['DBFilePath']['Services'] = '/opt/zzz/python/test/sqlite/pytest-services.sqlite3'
        pytest_ConfigData['DBFilePath']['CountryIP'] = '/opt/zzz/python/test/sqlite/pytest-country-IP.sqlite3'
        pytest_ConfigData['DBFilePath']['IPCountry'] = '/opt/zzz/python/test/sqlite/pytest-ip-country.sqlite3'
        
        pytest_ConfigData['Ports']['ICAP'] = pytest_ConfigData['Ports']['pytest']['ICAP']
        # pytest redis - separate DB number(1-15 are available)
        pytest_ConfigData['AppInfo']['RedisDBnumber'] = 15
        
        # pytest_ConfigData['Directory']['SquidAccess'] = ''
        
        # /var/log/zzz/icap/zzz-icap-data
        pytest_ConfigData['LogFile']['ICAPdata'] = '/opt/zzz/python/test/zzz-icap-data'
        # /var/log/zzz/icap/zzz-icap-errfile
        # /var/log/zzz/icap/zzz-icap-outfile

        pytest_ConfigData['UpdateFile']['db_maintenance'] = '/opt/zzz/python/test/db_maintenance'

        #################### CUSTOMIZE PYTEST VARS ABOVE ####################
        #-----reload config with the customized pytest values-----
        config = default_config
        ConfigData = config.get_config_data(config_file=pytest_ConfigFile, force_reload=True, custom_ConfigData=pytest_ConfigData)
        
        #-----make sure we got the test DB and not the live DB-----
        # Config() loads the live DB by default
        # this prevents accidental test overwriting of the live DB in case Config() was loaded without the custom DBFilePath
        if ConfigData:
            if ConfigData['DBFilePath']['Services'] != pytest_ConfigData['DBFilePath']['Services']:
                return None
        
        return config
    
    return _make_config

#--------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def zzz_config(make_config):
    pytest_ConfigFile = '/opt/zzz/python/test/pytest_zzz.conf'
    return make_config(pytest_ConfigFile)

@pytest.fixture(scope="session")
def ConfigData(zzz_config):
    if not zzz_config:
        return None
    return getattr(zzz_config, 'ConfigData')

#--------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def zzz_error_config(make_config):
    pytest_ConfigFile_makes_errors = '/opt/zzz/python/test/pytest_zzz_error.conf'
    return make_config(pytest_ConfigFile_makes_errors)

@pytest.fixture(scope="session")
def zzz_error_ConfigData(zzz_error_config):
    if not zzz_error_config:
        return None
    return getattr(zzz_error_config, 'ConfigData')

#--------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db(ConfigData):
    db = zzzevpn.DB(ConfigData)
    db.db_connect(ConfigData['DBFilePath']['Services'])

    #-----dynamically-generated test data-----

    return db

#--------------------------------------------------------------------------------

#-----common support modules-----
@pytest.fixture(scope="session")
def data_validation(ConfigData):
    return zzzevpn.DataValidation(ConfigData)

@pytest.fixture(scope="session")
def dns_service():
    return zzzevpn.DNSservice()

@pytest.fixture(scope="session")
def iputil():
    return zzzevpn.IPutil()

@pytest.fixture(scope="session")
def util(ConfigData, db):
    return zzzevpn.Util(ConfigData, db)

@pytest.fixture(scope="session")
def settings(ConfigData, db, util):
    settings = zzzevpn.Settings(ConfigData, db, util)
    settings.get_settings()
    return settings

@pytest.fixture(scope="session")
def whois_service():
    return zzzevpn.WhoisService.WhoisService()

@pytest.fixture(scope="session")
def zzz_template(ConfigData, db, util):
    return zzzevpn.ZzzTemplate(ConfigData, db, util)

#--------------------------------------------------------------------------------

#-----test modules-----
@pytest.fixture(scope="session")
def zzz_template_lib_obj(ConfigData):
    return zzzevpn.TEMPLATE_LIB.TEMPLATE_LIB(ConfigData)

@pytest.fixture(scope="session")
def zzz_template_lib_with_wsgi_obj(ConfigData):
    return zzzevpn.TEMPLATE_LIB_with_WSGI.TEMPLATE_LIB_with_WSGI(ConfigData)

@pytest.fixture(scope="session")
def zzz_html_parser_obj(ConfigData):
    return zzzevpn.ZzzHTMLParser.ZzzHTMLParser(ConfigData)

@pytest.fixture(scope="session")
def zzz_test_obj(ConfigData):
    return zzzevpn.ZzzTest.ZzzTest(ConfigData)

#--------------------------------------------------------------------------------

#-----other modules-----
@pytest.fixture(scope="session")
def bind(ConfigData, db, util, settings):
    return zzzevpn.BIND(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def check_latest_version(ConfigData, db, util, settings):
    return zzzevpn.CheckLatestVersion(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def diff_code(ConfigData):
    return zzzevpn.DiffCode.DiffCode(ConfigData)

@pytest.fixture(scope="session")
def disk(ConfigData, db, util):
    return zzzevpn.Disk(ConfigData, db, util)

@pytest.fixture(scope="session")
def index_page(ConfigData, db, util):
    return zzzevpn.IndexPage(ConfigData, db, util)

@pytest.fixture(scope="session")
def ip_log_raw_data(ConfigData, db, util, settings):
    return zzzevpn.IpLogRawData(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def ip_log_raw_data_page(ConfigData, db, util, settings):
    return zzzevpn.IpLogRawDataPage(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def ipset(ConfigData, db, util, settings):
    return zzzevpn.IPset(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def iptables(ConfigData, db, util, settings):
    return zzzevpn.IPtables(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def iptables_logparser(ConfigData, db, util, settings):
    return zzzevpn.IPtablesLogParser(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def list_manager(ConfigData, db, util):
    return zzzevpn.ListManager(ConfigData, db, util)

@pytest.fixture(scope="session")
def list_manager_page(ConfigData, db, util, settings):
    return zzzevpn.ListManagerPage(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def logparser(ConfigData, db, util, settings):
    return zzzevpn.LogParser(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def memory(ConfigData, db, util):
    return zzzevpn.Memory(ConfigData, db, util)

@pytest.fixture(scope="session")
def network_service(ConfigData, db, util, settings):
    return zzzevpn.NetworkService.NetworkService(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def service_request(ConfigData, db):
    return zzzevpn.ServiceRequest(ConfigData, db)

@pytest.fixture(scope="session")
def settings_page(ConfigData, db, util):
    return zzzevpn.SettingsPage(ConfigData, db, util)

@pytest.fixture(scope="session")
def squid_log_page(ConfigData, db, util, settings):
    return zzzevpn.SquidLogPage(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def squid_log_parser(ConfigData, db, util, settings):
    return zzzevpn.SquidLogParser(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def system_command(ConfigData, db, util):
    return zzzevpn.SystemCommand(ConfigData, db, util)

@pytest.fixture(scope="session")
def system_status(ConfigData, db, util):
    return zzzevpn.SystemStatus(ConfigData, db, util)

@pytest.fixture(scope="session")
def task_history(ConfigData, db, util, settings):
    return zzzevpn.TaskHistory(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def update_file(ConfigData, db, util, settings):
    return zzzevpn.UpdateFile(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def update_os(ConfigData, db, util):
    return zzzevpn.UpdateOS(ConfigData, db, util)

@pytest.fixture(scope="session")
def update_zzz(ConfigData, db, util, settings):
    return zzzevpn.UpdateZzz(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def user_manager(ConfigData, db, util, settings):
    return zzzevpn.UserManager(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def webpage(ConfigData, db, pagetitle, settings):
    return zzzevpn.Webpage(ConfigData, db, pagetitle, settings)

#WARNING: do not call reload_settings() until a custom config can be specified
@pytest.fixture(scope="session")
def zzz_icap_server(ConfigData, db, util):
    return zzzevpn.ZzzICAPserver.ZzzICAPserver(ConfigData, db, util, ConfigData['Ports']['pytest']['ICAP'])

@pytest.fixture(scope="session")
def zzz_icap_settings(ConfigData, db, util, settings):
    return zzzevpn.ZzzICAPsettings(ConfigData, db, util, settings)

@pytest.fixture(scope="session")
def zzz_icap_settings_page(ConfigData, db, util):
    return zzzevpn.ZzzICAPsettingsPage(ConfigData, db, util)

@pytest.fixture(scope="session")
def zzz_redis(ConfigData):
    tmp_zzz_redis = zzzevpn.ZzzRedis(ConfigData)
    tmp_zzz_redis.redis_connect()
    return tmp_zzz_redis

#--------------------------------------------------------------------------------
