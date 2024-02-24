#-----memory management-----

import psutil

#-----package with all the Zzz modules-----
import zzzevpn

class Memory:
    'Memory Management'

    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None

    megabyte = 1024 * 1024

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
    
    #--------------------------------------------------------------------------------

    def check_system_memory(self):
        system_memory = psutil.virtual_memory()

        mem_total = round(system_memory.total/self.megabyte)
        mem_free = round(system_memory.free/self.megabyte)
        mem_used = round(system_memory.used/self.megabyte)
        mem_avail = round(system_memory.available/self.megabyte)

        mem_info = {
            'total': mem_total,
            'free': mem_free,
            'used': mem_used,
            'avail': mem_avail,
            'system_memory': system_memory,
        }
        return mem_info

    #--------------------------------------------------------------------------------

    #-----lookup current memory usage-----
    def check_all_memory_usage(self):
        all_memory_usage = {
            'bind': 0,
            'squid': 0,
        }

        for p in psutil.process_iter(['username', 'name', 'memory_info']):
            # {'memory_info': pmem(rss=630161408, vms=1020604416, shared=4980736, text=319488, lib=0, data=687501312, dirty=0), 'name': 'named', 'username': 'bind'}
            if p.info['username']=='bind' and p.info['name']=='named':
                all_memory_usage['bind'] = round(p.info['memory_info'].rss/self.megabyte)
            elif p.info['username']=='proxy' and p.info['name']=='squid':
                squid_memory_usage = round(p.info['memory_info'].rss/self.megabyte)
                if squid_memory_usage > all_memory_usage['squid']:
                    all_memory_usage['squid'] = squid_memory_usage

        return all_memory_usage

    #--------------------------------------------------------------------------------

    #-----estimate BIND memory usage for a given DNS list length-----
    # expected_mem - the current list is expected to use this much memory
    # restart_mem_usage - when bind grows to use this much, it should be restarted
    # max size that bind can get to before it uses too much system memory
    def estimate_memory_usage_bind(self, list_length=0):
        if not list_length:
            #-----estimate actual memory usage from the currently-installed DNS-block file-----
            sizes = []
            if self.util.run_script(['wc', self.ConfigData['UpdateFile']['bind']['dst_filepath']]):
                output = self.util.subprocess_output.stdout
                output = output.strip()
                sizes = output.split(' ')
            if sizes:
                list_length = int(sizes[0])

        expected_mem = self.ConfigData['MemoryUsage']['bind']['base_mem'] + (list_length*self.ConfigData['MemoryUsage']['bind']['mb_per_domain'])
        expected_mem = round(expected_mem)
        # max_allowed = 100+expected_mem
        restart_mem_usage = expected_mem + self.ConfigData['MemoryUsage']['bind']['excess_allowed']

        mem_info = self.check_system_memory()
        #TODO: keep 1200MB available for non-bind apps
        max_allowed = mem_info['total'] - 1000

        return expected_mem, restart_mem_usage, max_allowed
