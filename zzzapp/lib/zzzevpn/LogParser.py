#-----Log Parser common functions-----
# this module was split into 3 modules:
#   LogParser
#   SquidLogParser
#   SquidLogPage
# IPtableLogParser also uses some of these functions

from functools import lru_cache
import time

#-----package with all the Zzz modules-----
import zzzevpn

class LogParser:
    'IP/Squid Log Parser helper functions'
    
    #-----objects-----
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    
    #-----vars-----
    

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
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
        if not self.settings.SettingsData:
            self.settings.get_settings()
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        #-----clear internal vars for a fresh list processing-----
        pass
    
    #--------------------------------------------------------------------------------
    
    # input: country_code
    # output: country_name, with HTML red highlight if blocked
    def country_highlight(self, country_code):
        country_name = self.ConfigData['OfficialCountries'].get(country_code, 'UNKNOWN: ' + country_code)
        if country_code == 'UNKNOWN':
            # avoids printing "UNKNOWN: UNKNOWN"
            country_name = 'UNKNOWN'
        if (self.settings.BlockedCountries.get(country_code, None)):
            return f'<span class="text_red">{country_name}</span>'
        return country_name
    
    #--------------------------------------------------------------------------------
    
    def make_country_input_tags(self, countries):
        if not countries:
            return ''
        country_input_tags = ''
        country_list = self.util.sort_array_subset_by_values(countries.keys(), self.ConfigData['OfficialCountries'])
        # for country_code in sorted(countries.keys()):
        if country_list:
            tag_list = []
            for country_row in country_list:
                (country_code, country_name) = country_row
                safe_css_classname = 'country_' + country_code
                highlighted_country = self.country_highlight(country_code)
                # country_name = self.ConfigData['OfficialCountries'].get(country_code, 'UNKNOWN: ' + country_code)
                tag = f"<input type='radio' name='limit_by_country' value='{safe_css_classname}'>{highlighted_country}<br>"
                tag_list.append(tag)
            country_input_tags = '\n'.join(tag_list)
        found_unknown = countries.get('UNKNOWN', None)
        if found_unknown:
            country_input_tags += "<input type='radio' name='limit_by_country' value='country_UNKNOWN'>UNKNOWN<br>"
        return country_input_tags
    
    #--------------------------------------------------------------------------------
    
    #TODO: highlighting is too slow, so it's off by default for now
    #      implement binary search trees for util.is_ip_blocked(), util.is_protected_ip()
    @lru_cache(maxsize=300)
    def make_ip_analysis_links(self, ip, highlight_ips: bool=True, include_blocking_links: bool=True, include_class_c_blocking: bool=False, rdns_popup: bool=False):
        ip_analysis_links = ''
        highlight_class = 'cursor_copy'
        if self.util.ip_util.is_public_ip(ip):
            #TODO: needs a binary search tree
            is_blocked = False
            if highlight_ips:
                is_blocked = self.util.is_ip_blocked(ip)
            ip_blocking_links = ''
            if include_blocking_links:
                ip_blocking_links = self.get_ip_blocking_links(ip, is_blocked=is_blocked, include_class_c_blocking=include_class_c_blocking)
            rdns_class = 'reverse_dns'
            if rdns_popup:
                rdns_class = 'reverse_dns_popup'
            base64_ip = self.util.encode_base64(ip)
            ip_analysis_links = f'''<br><a class="clickable search_google" data-onclick="{base64_ip}">(G)</a><a class="clickable search_ipinfo" data-onclick="{base64_ip}">(L)</a><a class="clickable {rdns_class}" data-onclick="{ip}">(R)</a><a class="clickable search_whois" data-onclick="{base64_ip}">(W)</a> {ip_blocking_links}
            '''
            
            #TODO: needs a binary search tree
            if highlight_ips:
                if is_blocked:
                    highlight_class += ' text_red'
                elif self.util.is_protected_ip(ip):
                    highlight_class += ' text_green'
        
        highlight_ip = f'<span class="{highlight_class}">{ip}</span>'
        ip_data = {
            'ip_analysis_links': ip_analysis_links,
            'highlight_ip': highlight_ip,
        }
        return ip_data

    #--------------------------------------------------------------------------------

    #-----generates the link that is used to block an IP-----
    def get_ip_blocking_links(self, server_ip: str, is_blocked: bool=False, include_class_c_blocking: bool=False) -> str:
        blocking_links = ''
        if (not is_blocked) and (server_ip not in self.ConfigData['ProtectedIPs']):
            class_c_str = ''
            if include_class_c_blocking:
                class_c_str = f'''<a class="clickable_red block_ip" data-onclick="{self.util.generate_class_c(server_ip)}">(IC)</a>'''
            blocking_links = f'''<a class="clickable_red block_ip" data-onclick="{server_ip}">(I)</a>{class_c_str}'''
        return blocking_links

    #--------------------------------------------------------------------------------

    #-----update missing country codes in log tables-----
    def update_country_codes(self, table_name: str, quit_after_rows: int=0) -> bool:
        if table_name not in ['ip_log_daily', 'squid_log']:
            return False

        sql = f'select distinct ip from {table_name} where country_code="UNKNOWN"'
        params = ()
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql, params, skip_array=True)

        if not rows_with_colnames:
            return False

        print('\n')
        sql_update = f'update {table_name} set country_code=? where country_code="UNKNOWN" and ip=?'
        params_list = []
        total_rows = 0
        rows_to_update = 0
        for row in rows_with_colnames:
            country_code = self.util.lookup_ip_country(row['ip'])
            if country_code:
                total_rows += 1
                if country_code != 'UNKNOWN':
                    params_list.append((country_code, row['ip']))
                    rows_to_update += 1
            #-----print status every 100 rows-----
            if (len(params_list) % 100)==0:
                print(f'{total_rows} rows')
            #-----update DB every 1000 rows-----
            if len(params_list)>=1000:
                self.db.query_exec_many(sql_update, params_list)
                params_list = []
            if total_rows > quit_after_rows:
                break
            # sleep to allow other apps to use the DB
            time.sleep(1)
        #-----final DB update-----
        if params_list:
            self.db.query_exec_many(sql_update, params_list)
        print(f'{total_rows} rows, {rows_to_update} rows updated')

        return True

    #--------------------------------------------------------------------------------
