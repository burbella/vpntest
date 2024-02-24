#!/opt/zzz/venv/bin/python3

#-----initialize the pytest DB for each test run-----
# assumes that init_pytest_db.sh has already cleared the DB

import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

#-----import modules from the pytest lib directory-----
# ******************************************************
# *** DO NOT USE THE PYTEST DIRECTORIES IN LIVE CODE ***
# ******************************************************
if sys.platform=='linux':
    # LIVE CODE DIRECTORY: site.addsitedir('/opt/zzz/python/lib')
    # pytest directories:
    site.addsitedir('/opt/zzz/python/test/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.Settings

#TEST
sys.exit()

#-----get the pytest Config, NOT the live Config-----
config = zzzevpn.Config()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')
ConfigData = getattr(config, 'ConfigData')

settings = zzzevpn.Settings(ConfigData)
# Do NOT run get_settings() here, we are resetting the contents of the settings DB

# settings.init_webserver_domain()
# settings.init_settings_db()
# settings.init_country_db()
# settings.init_tld_db()

#-----IP-country map: load country name-code map-----
# settings.init_ip_country_db()

#-----close cursor and DB when done using them-----
settings.db.db_disconnect()
