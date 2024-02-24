#-----Zzz Enhanced VPN init package-----

#-----import common modules-----
# import zzzevpn.Config
# import zzzevpn.DataValidation
# import zzzevpn.DB
# import zzzevpn.DNSservice
# import zzzevpn.IPutil
# import zzzevpn.Settings
# import zzzevpn.Util
# import zzzevpn.Webpage
# import zzzevpn.ZzzTemplate

########################################
# new format for imports
#   skip: DiffCode, NetworkService, WhoisService, WSGI, ZzzHTMLParser, ZzzICAPserver, ZzzTest
########################################
#-----import modules in order by dependencies-----
# this is required for type hints to not crash
# EX: DB must be imported before BIND, because it is needed by BIND
from .IPutil import IPutil
from .DNSservice import DNSservice
from .Config import Config
from .DataValidation import DataValidation
from .ZzzRedis import ZzzRedis

from .DB import DB
from .Util import Util
from .ZzzTemplate import ZzzTemplate
from .Settings import Settings

from .Disk import Disk
from .Memory import Memory
from .Webpage import Webpage
from .TaskHistory import TaskHistory
from .LogParser import LogParser
from .SquidLogParser import SquidLogParser
from .ListManager import ListManager
from .UpdateFile import UpdateFile

from .BIND import BIND
from .CheckLatestVersion import CheckLatestVersion
from .IndexPage import IndexPage
from .IpLogRawData import IpLogRawData
from .IpLogRawDataPage import IpLogRawDataPage
from .IPset import IPset
from .IPtables import IPtables
from .IPtablesLogParser import IPtablesLogParser
from .ListManagerPage import ListManagerPage
from .SettingsPage import SettingsPage
from .SquidLogPage import SquidLogPage
from .SystemCommand import SystemCommand
from .SystemStatus import SystemStatus
from .UpdateOS import UpdateOS
from .UpdateZzz import UpdateZzz
from .UserManager import UserManager
from .ZzzICAPsettings import ZzzICAPsettings
from .ZzzICAPsettingsPage import ZzzICAPsettingsPage

from .ServiceRequest import ServiceRequest

#--------------------------------------------------------------------------------

#-----not importing less-common modules-----
#   from .WSGI import WSGI
# only WSGI needs NetworkService and ZzzTest
#   from .NetworkService import NetworkService
#   from .ZzzTest import ZzzTest
# only NetworkService needs WhoisService (extra 8MB RAM usage and 400ms time just to import it)
#   from .WhoisService import WhoisService
#
# import zzzevpn.NetworkService
# import zzzevpn.WhoisService
# import zzzevpn.WSGI
# import zzzevpn.ZzzHTMLParser
# import zzzevpn.ZzzICAPserver
# import zzzevpn.ZzzTest


#-----imported by __init__.py-----
# import zzzevpn.BIND
# import zzzevpn.CheckLatestVersion
# import zzzevpn.IndexPage
# import zzzevpn.IPset
# import zzzevpn.IPtables
# import zzzevpn.IPtablesLogParser
# import zzzevpn.ListManager
# import zzzevpn.ListManagerPage
# import zzzevpn.LogParser
# import zzzevpn.ServiceRequest
# import zzzevpn.SettingsPage
# import zzzevpn.SquidLogPage
# import zzzevpn.SquidLogParser
# import zzzevpn.SystemCommand
# import zzzevpn.SystemStatus
# import zzzevpn.TaskHistory
# import zzzevpn.UpdateFile
# import zzzevpn.UpdateOS
# import zzzevpn.UpdateZzz
# import zzzevpn.UserManager
# import zzzevpn.ZzzICAPsettings
# import zzzevpn.ZzzICAPsettingsPage
# import zzzevpn.ZzzRedis


#--------------------------------------------------------------------------------

