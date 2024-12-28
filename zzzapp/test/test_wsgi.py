#!/opt/zzz/venv/bin/python3
#-----Zzz Automated Tests-----

# live venv: /opt/zzz/venv/bin/python3
# test venv: /opt/zzz/venvtest/bin/python3

# live code: /opt/zzz/python/lib, /opt/zzz/python/bin
# pytest code: /opt/zzz/python/test/lib, /opt/zzz/python/test/bin
# repos code: /home/ubuntu/repos/vpntest/zzzapp/lib, /home/ubuntu/repos/vpntest/zzzapp/bin

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

#TODO: apache runs as www-data user, so the werkzeug WSGI app test should also run as that user

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
import zzzevpn.WSGI

#--------------------------------------------------------------------------------

#-----tests WSGI features by interacting with the ZzzWSGItestServer-----
class ZzzWSGItestClient:
    test = None
    def __init__(self):
        pass

#--------------------------------------------------------------------------------

#-----emulates a WSGI server with Werkzeug-----
class ZzzWSGItestServer:
    zzz_wsgi = None
    zzz_redis = None
    
    #TODO: separate redis server for pytest, higher memory limit, clear its data after the test is done
    def __init__(self, zzz_wsgi: zzzevpn.WSGI, zzz_redis):
        self.zzz_wsgi = zzz_wsgi
        self.zzz_redis = zzz_redis
    
    def make_response(self, request):
        return Response('ZZZ TEST RESPONSE')
    
    def wsgi_app(self, environ: dict, start_response):
        request = Request(environ)
        response = self.make_response(request)
        return response(environ, start_response)
    
    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

#--------------------------------------------------------------------------------

#-----get pytest Config or exit-----
def test_get_config(zzz_config):
    if not zzz_config:
        sys.exit('empty zzz_config')

#--------------------------------------------------------------------------------

#TODO: special requirements for WSGI module
#   must pass in the WSGI application's "environ" and "start_response" objects
@pytest.fixture(scope="module")
def zzz_wsgi(ConfigData: dict, db: zzzevpn.DB, data_validation: zzzevpn.DataValidation):
    zzz_wsgi_obj = zzzevpn.WSGI.WSGI(ConfigData, db, data_validation)
    return zzz_wsgi_obj

@pytest.fixture(scope="module")
def pytest_server_domain(util: zzzevpn.Util):
    domain_without_tld = util.get_zzz_domain_without_tld()
    return f'pytest.{domain_without_tld}.zzz'

@pytest.fixture(scope="module")
def zzz_wsgi_test_server(zzz_wsgi, zzz_redis):
    return ZzzWSGItestServer(zzz_wsgi, zzz_redis)

#--------------------------------------------------------------------------------

#-----common support modules-----
def test_config_valid(zzz_config):
    assert zzz_config.is_valid()

def test_config_loaded(ConfigData):
    assert ConfigData['DataLoaded']

def test_db_connect(db):
    assert db.dbh is not None

def test_webpage(webpage):
    assert webpage is not None

def test_zzz_wsgi(zzz_wsgi):
    assert zzz_wsgi is not None

#--------------------------------------------------------------------------------

#-----run the wsgi app-----
# run_simple('localhost', ConfigData['Ports']['pytest']['WSGI'], zzz_test_wsgi, use_debugger=True, use_reloader=True)

#TODO: threading?

# @Request.application
# def wsgi_zzz_test(ConfigData):
#     def application(request):
#         return Response('Hello, World!')
#     if __name__ == '__main__':
#         run_simple('localhost', ConfigData['Ports']['pytest']['WSGI'], application)

def test_wsgi_server(zzz_wsgi, zzz_redis):
    # wsgi_zzz_test();
    zzz_wsgi_test_server = ZzzWSGItestServer(zzz_wsgi, zzz_redis)

def test_wsgi_server_stopped(ConfigData, zzz_wsgi):
    pass

#--------------------------------------------------------------------------------

#TODO: send requests to the server
def test_wsgi_client(ConfigData, zzz_wsgi):
    zzz_wsgi_test_server = ZzzWSGItestClient()

