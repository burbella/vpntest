#-----supports connections to redis server for Zzz apps-----

from xmlrpc.client import boolean
import redis

#-----import modules from the lib directory-----
#-----package with all the Zzz modules-----
import zzzevpn

#TODO: remove unused objects
class ZzzRedis:
    'supports connections to redis server for Zzz apps'
    
    ConfigData: dict = None

    redis_server = None
    
    def __init__(self, ConfigData: dict=None):
        #-----get Config-----
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
    
    #--------------------------------------------------------------------------------

    #TODO: make this a ConfigData var so that pytest can pass in a different DB number
    def redis_connect(self, db_number=None):
        # decode_responses=True
        self.redis_server = redis.Redis(
            self.ConfigData['AppInfo']['RedisHostname'], self.ConfigData['Ports']['redis'], db=self.ConfigData['AppInfo']['RedisDBnumber'], decode_responses=False
        )
    
    def redis_init(self):
        if not self.redis_server:
            self.redis_connect()

    #--------------------------------------------------------------------------------

    #TODO: log errors?
    #-----make sure data coming out of the redis server is properly-typed-----
    # all responses are returned as bytes
    # False --> b'0'
    # True --> b'1'
    def get_boolean(self, key):
        value = self.redis_server.get(key)
        if not value:
            return False
        if value==b'1':
            return True
        return False

    #--------------------------------------------------------------------------------

    def zzz_checkwork_get(self):
        return self.get_boolean('zzz_checkwork')

    def zzz_checkwork_set(self, value=True):
        if value:
            self.redis_server.set('zzz_checkwork', b'1')
        else:
            self.redis_server.set('zzz_checkwork', b'0')

    #--------------------------------------------------------------------------------

    def icap_reload_get(self):
        return self.get_boolean('icap_reload')

    def icap_reload_set(self, value=True):
        if value:
            self.redis_server.set('icap_reload', b'1')
        else:
            self.redis_server.set('icap_reload', b'0')

    #--------------------------------------------------------------------------------
