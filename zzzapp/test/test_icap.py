#!/opt/zzz/venv/bin/python3
#-----Zzz Automated Tests-----

# live venv: /opt/zzz/venv/bin/python3
# test venv: /opt/zzz/venvtest/bin/python3

# live code: /opt/zzz/python/lib, /opt/zzz/python/bin
# pytest code: /opt/zzz/python/test/lib, /opt/zzz/python/test/bin
# repos code: /home/ubuntu/repos/test/zzzapp/lib, /home/ubuntu/repos/test/zzzapp/bin

import os
import pytest
import site
import sys
import time

from werkzeug.serving import run_simple
# from werkzeug.urls import url_parse
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
# from jinja2 import Environment, FileSystemLoader

#-----minimum process priority-----
os.nice(19)

#TODO: pytest icap can run as www-data user?

#-----make sure we're running as www-data user or exit-----
# if os.geteuid()!=0:
#     sys.exit('This script must be run as root!')

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
# zzzevpn brings most modules automatically
import zzzevpn

#--------------------------------------------------------------------------------

#-----get pytest Config or exit-----
def test_get_config(zzz_config):
    if not zzz_config:
        sys.exit('empty zzz_config')

#--------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pytest_server_domain(util):
    domain_without_tld = util.get_zzz_domain_without_tld()
    return f'pytest.{domain_without_tld}.zzz'

#WARNING: do not call reload_settings() until a custom config can be specified
@pytest.fixture(scope="module")
def zzz_icap_server_running(zzz_icap_server):
    zzz_icap_server.start_server()
    yield zzz_icap_server
    zzz_icap_server.should_run(False)

#--------------------------------------------------------------------------------

#-----common support modules-----
def test_config_valid(zzz_config):
    assert zzz_config.is_valid()

def test_config_loaded(ConfigData):
    assert ConfigData['DataLoaded']

def test_db_connect(db):
    assert db.dbh is not None

#WARNING: do not call reload_settings() until a custom config can be specified
def test_icap(zzz_icap_server_running):
    assert zzz_icap_server_running.should_run()

#WARNING: do not call reload_settings() until a custom config can be specified
def test_icap_stopped(zzz_icap_server_running):
    time.sleep(6)
    zzz_icap_server_running.should_run(False)
    assert not zzz_icap_server_running.should_run()

#--------------------------------------------------------------------------------

#TODO: threading?


#--------------------------------------------------------------------------------
