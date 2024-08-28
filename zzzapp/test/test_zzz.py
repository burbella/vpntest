#!/opt/zzz/venv/bin/python3
#-----Zzz Automated Tests-----

# live venv: /opt/zzz/venv/bin/python3
# test venv: /opt/zzz/venvtest/bin/python3

# live code: /opt/zzz/python/lib, /opt/zzz/python/bin
# pytest code: /opt/zzz/python/test/lib, /opt/zzz/python/test/bin
# repos code: /home/ubuntu/repos/test/zzzapp/lib, /home/ubuntu/repos/test/zzzapp/bin

import os
import pprint
import pytest
import site
import sys

#-----make sure we're running as root or exit-----
# if os.geteuid()!=0:
#     sys.exit('This script must be run as root!')

#-----minimum process priority-----
os.nice(19)

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
# manually import the rest:
import zzzevpn.DiffCode
import zzzevpn.NetworkService
import zzzevpn.WhoisService
import zzzevpn.ZzzHTMLParser
import zzzevpn.ZzzICAPserver
import zzzevpn.ZzzTest

#--------------------------------------------------------------------------------

def test_get_config(zzz_config, ConfigData):
    if not zzz_config:
        sys.exit('empty zzz_config')
    assert zzz_config.configtest()
    assert zzz_config.is_valid()
    assert ConfigData['DataLoaded']
    assert ConfigData['IPv4']['Internal'] is not None
    assert ConfigData['IPv4']['Internal'] != ''
    assert len(ConfigData['IPv4']['Internal']) > 6

#TEST - this should fail:
# def test_force_fail(ConfigData):
#     assert not ConfigData['DataLoaded']

#--------------------------------------------------------------------------------

#-----tests that exercise error-handling code, for more coverage-----

def test_error_config(zzz_error_config, zzz_error_ConfigData):
    if not zzz_error_config:
        sys.exit('empty zzz_error_config')
    assert not zzz_error_config.is_valid()
    assert not zzz_error_ConfigData['DataLoaded']

#--------------------------------------------------------------------------------

#TODO: move data file from ZzzICAPserver into Config
#   icap_data_filepath = '/var/log/zzz/zzz-icap-data'
# use a different data file for pytest
# use the alternate port so the test server doesn't conflict with the main ICAP port in use
# zzz_icap_server = zzzevpn.ZzzICAPserver.ZzzICAPserver(ConfigData, db, util, ConfigData['Ports']['pytest']['ICAP'])

#--------------------------------------------------------------------------------

#-----common support modules-----
def test_data_validation(data_validation):
    assert data_validation is not None

def test_db_connect(db):
    assert db.dbh is not None

def test_dns_service(dns_service):
    assert dns_service is not None

def test_iputil(iputil):
    assert iputil is not None

def test_standalone(standalone):
    assert standalone is not None

def test_util(util):
    assert util is not None

def test_settings(settings):
    assert settings is not None
    assert settings.SettingsData is not None

def test_whois_service(whois_service):
    assert whois_service is not None
    #TODO: prevent excessive whois/RDAP lookups

def test_zzz_template(ConfigData, zzz_template):
    assert zzz_template is not None
    template_filepath = '/opt/zzz/python/test/pytest.template'
    template_data = { 'var_data': 'whatever', }
    output = zzz_template.load_template(filepath=template_filepath, data=template_data)
    assert output == 'TESTwhateverTEST'
    
    output = zzz_template.load_template()
    assert output == 'ERROR: template name/filepath not specified'
    
    output = zzz_template.load_template(name='DoesNotExist')
    expected = 'ERROR: template not found ' + ConfigData['Directory']['Templates'] + '/DoesNotExist.template'
    assert output == expected

#--------------------------------------------------------------------------------

#-----other modules-----
def test_bind(bind):
    assert bind is not None

def test_check_latest_version(check_latest_version):
    assert check_latest_version is not None

def test_diff_code(diff_code):
    assert diff_code is not None

def test_disk(disk):
    assert disk is not None

def test_index_page(index_page):
    assert index_page is not None

def test_ip_log_raw_data(ip_log_raw_data):
    assert ip_log_raw_data is not None

def test_ip_log_raw_data_page(ip_log_raw_data_page):
    assert ip_log_raw_data_page is not None

def test_ipset(ipset):
    assert ipset is not None

def test_iptables(iptables):
    assert iptables is not None

def test_iptables_logparser(iptables_logparser):
    assert iptables_logparser is not None

def test_list_manager(list_manager):
    assert list_manager is not None

def test_list_manager_page(list_manager_page):
    assert list_manager_page is not None

def test_logparser(logparser):
    assert logparser is not None

def test_memory(memory):
    assert memory is not None

def test_network_service(network_service):
    assert network_service is not None

def test_service_request(service_request):
    assert service_request is not None

def test_settings_page(settings_page):
    assert settings_page is not None

def test_squid_log_page(squid_log_page):
    assert squid_log_page is not None

def test_squid_log_parser(squid_log_parser):
    assert squid_log_parser is not None

def test_system_command(system_command):
    assert system_command is not None

def test_system_status(system_status):
    assert system_status is not None

def test_task_history(task_history):
    assert task_history is not None

def test_update_file(update_file):
    assert update_file is not None

def test_update_os(update_os):
    assert update_os is not None

def test_update_zzz(update_zzz):
    assert update_zzz is not None

def test_user_manager(user_manager):
    assert user_manager is not None

def test_webpage(webpage):
    assert webpage is not None

def test_zzz_icap_settings(zzz_icap_settings):
    assert zzz_icap_settings is not None

def test_zzz_icap_settings_page(zzz_icap_settings_page):
    assert zzz_icap_settings_page is not None

def test_zzz_redis(zzz_redis):
    assert zzz_redis is not None

def test_zzz_test_obj(zzz_test_obj):
    assert zzz_test_obj is not None

#WARNING: do not call reload_settings() until a custom config can be specified
def test_zzz_icap_server(zzz_icap_server):
    assert zzz_icap_server is not None

#--------------------------------------------------------------------------------

def make_obj_no_params(main_object, expected_items):
    assert main_object is not None
    for item in expected_items:
        assert hasattr(main_object, item)
        test_item = getattr(main_object, item)
        assert test_item is not None
    return main_object

#--------------------------------------------------------------------------------

# pytest.fail("config invalid")

# objects should auto-create their own needed sub-objects if they are not provided
#     ConfigData, db, util, settings
# These modules do not take params: DNSservice, IPutil, WhoisService
# These modules only take ConfigData: DataValidation, DB
# ConfigData must be provided by conftest.py to make sure that the pytest files/directories/DB is used instead of the default configs
def test_obj_no_params_supplied(ConfigData):
    param_db = ['db']
    param_db_util = ['db', 'util']
    param_db_util_settings = ['db', 'util', 'settings']

    make_obj_no_params(zzzevpn.Util(ConfigData), param_db)

    no_params_settings = make_obj_no_params(zzzevpn.Settings(ConfigData), param_db_util)
    no_params_settings.get_settings()
    assert no_params_settings.SettingsData is not None

    make_obj_no_params(zzzevpn.BIND(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.CheckLatestVersion(ConfigData), param_db_util_settings)

    # do not test these here:
    #       Config, DataValidation, DB, DiffCode, DNSservice, IPutil, WhoisService, ZzzHTMLParser, ZzzRedis
    # anything that takes nothing or only takes ConfigData is useless to test in a no-params test

    # detailed tests in another test file
    # test in test_wsgi.py:
    #   zzzevpn.WSGI
    # test in test_icap.py:
    #   zzzevpn.ZzzICAPserver

    make_obj_no_params(zzzevpn.Disk(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.IndexPage(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.IpLogRawData(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.IpLogRawDataPage(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.IPset(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.IPtables(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.IPtablesLogParser(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.ListManager(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.ListManagerPage(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.LogParser(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.Memory(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.NetworkService.NetworkService(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.ServiceRequest(ConfigData), param_db)
    make_obj_no_params(zzzevpn.Settings(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.SettingsPage(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.SquidLogPage(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.SquidLogParser(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.SystemCommand(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.SystemStatus(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.TaskHistory(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.UpdateFile(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.UpdateOS(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.UpdateZzz(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.UserManager(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.Util(ConfigData), param_db)
    
    # "pagetitle" is not a data type, this will need special handling
    make_obj_no_params(zzzevpn.Webpage(ConfigData), ['db', 'pagetitle', 'settings'])
    
    make_obj_no_params(zzzevpn.ZzzICAPserver.ZzzICAPserver(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.ZzzICAPsettings(ConfigData), param_db_util_settings)
    make_obj_no_params(zzzevpn.ZzzICAPsettingsPage(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.ZzzTemplate(ConfigData), param_db_util)
    make_obj_no_params(zzzevpn.ZzzTest.ZzzTest(ConfigData), param_db_util_settings)

#--------------------------------------------------------------------------------

def test_disk_check(disk: zzzevpn.Disk):
    #TEST - this reduces the timeout time since it may run on to the segment limit before the module is finished
    disk.limit_runtime_per_time_segment = 1
    disk.minimum_rows_to_process = 10

    result = disk.check_db()
    assert result is True
    result = disk.check_db(flush_data=True)
    assert result is True

#--------------------------------------------------------------------------------

