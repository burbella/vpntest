#-----Test Module-----
# for testing various WSGI/HTML features

import json
import pprint
import time
import unidecode

#-----package with all the Zzz modules-----
import zzzevpn

class ZzzTest:
    'ZzzTest'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None
    
    TestHTML = {}
    service_name = 'test'
    
    # simple start-stop
    start_time = 0
    runtime = 0
    
    # series of start-stops, add up the total
    start_interval = 0
    accumulated_time = 0
    
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
            self.settings.get_settings(need_html=True)
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        #-----prep the HTML values-----
        self.TestHTML = {
            'DNSDenylist': pprint.pformat(self.ConfigData['DNSDenylist']),
            
            'country_menu': self.settings.SettingsHTML['CountryMenu'],
            'utf8_country_menu': self.utf8_country_menu(),
            
            'TESTDATA': '',
        }
    
    #--------------------------------------------------------------------------------
    
    #-----process GET data-----
    def handle_get(self, environ):
        return 'ZzzTest GET output test'
    
    #--------------------------------------------------------------------------------
    
    #-----process POST data-----
    def handle_post(self, environ, request_body_size):
        return 'success'
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ, pagetitle):
        self.settings.get_settings()
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, pagetitle, self.settings)
        
        output = self.webpage.make_webpage(environ, self.make_TestPage(environ))
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def make_TestPage(self, environ):
        body = self.webpage.load_template('ZzzTest')
        self.TestHTML['CSP_NONCE'] = environ['CSP_NONCE']
        
        return body.format(**self.TestHTML)
    
    #--------------------------------------------------------------------------------
    
    #-----run some execution timing tests-----
    
    # USAGE:
    #   import zzzevpn.ZzzTest
    #   zzz_test = zzzevpn.ZzzTest.ZzzTest()
    #   zzz_test.set_start_time('TEST')
    #   zzz_test.calc_runtime('TEST', 1)
    def set_start_time(self, print_msg=''):
        self.accumulated_time = 0
        self.start_time = time.time()
        if print_msg:
            print(f'TEST_TIMING: START {print_msg}')
    
    def calc_runtime(self, print_msg='', round_digits=0):
        if not self.util.is_int(round_digits):
            round_digits=0
        if round_digits>6:
            round_digits=6
        if not self.start_time:
            # ERROR
            return 0
        runtime = time.time() - self.start_time
        if runtime<=0:
            # ERROR
            self.runtime = 0
            return
        runtime = round(runtime, round_digits)
        if print_msg:
            print(f'TEST_TIMING: END {print_msg} - {runtime} seconds')
        self.runtime = runtime
    
    # USAGE:
    #   zzz_test = zzzevpn.ZzzTest.ZzzTest()
    #   zzz_test.start_counting_intervals()
    #   repeat:
    #     zzz_test.start_interval_time()
    #     zzz_test.stop_interval_time()
    #   zzz_test.print_interval_time('TEST', 1)
    def start_counting_intervals(self):
        self.accumulated_time = 0
    
    def start_interval_time(self):
        self.start_interval = time.time()
    
    def stop_interval_time(self):
        self.accumulated_time += time.time() - self.start_interval
    
    def print_interval_time(self, print_msg='TEST', round_digits=1):
        accumulated_time = round(self.accumulated_time, round_digits)
        print(f'TEST_TIMING: accumulated time for {print_msg} is {accumulated_time} seconds')
    
    #--------------------------------------------------------------------------------
    
    # cp REPOS_DIR/src/country-codes-utf8.json /opt/zzz/data/country-codes-utf8.json
    def utf8_country_menu(self):
        utf8_country_codes_file = self.ConfigData['DataFile']['CountryListUTF8']
        utf8_country_json_data = '[{"Code": "ZZ", "Name": "TEST"}]'
        with open(utf8_country_codes_file, 'r') as country_list_file:
            utf8_country_json_data = country_list_file.read()
        utf8_country_list = json.loads(utf8_country_json_data)
        utf8_OfficialCountries = {}
        for country_item in utf8_country_list:
            # convert country code to ASCII
            country_code = unidecode.unidecode(country_item['Code'])
            utf8_OfficialCountries[country_code] = country_item['Name']
        #-----handle special cases (UK instead of GB, etc.)-----
        # https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Exceptional_reservations
        utf8_OfficialCountriesWithExceptions = utf8_OfficialCountries
        utf8_OfficialCountriesWithExceptions['UK'] = utf8_OfficialCountries['GB']
        
        #-----entries in country menus-----
        CountryMenu = ''
        BlockedCountryMenu = ''
        country_list = self.util.sort_array_by_values(self.settings.Countries)
        for country_row in country_list:
            (country_code, country_name) = country_row
            
            #TEST - show only unicode countries
            if country_name == utf8_OfficialCountries[country_code]:
                continue
            #
            
            #-----use the unicode country name-----
            # check if HTML entity is needed?
            # country_name = unidecode.unidecode(utf8_OfficialCountries[country_code])
            country_name = utf8_OfficialCountries[country_code]
            
            #-----skip ipdeny countries not in maxmind DB (or vice versa)-----
            check_country = self.settings.Countries.get(country_code)
            if not country_code.lower() in self.ConfigData['IPdeny']['countries']:
                continue
            if check_country is None:
                continue
            option_class = ''
            if country_code in self.ConfigData['ProtectedCountries']:
                option_class = 'class="protected_option"'
            option = f'<option value="{country_code}" {option_class}>{country_code}-{country_name}</option>'
            CountryMenu += option
            #TEST - extra entry with unicode-->ASCII conversion
            country_name_converted = unidecode.unidecode(country_name)
            CountryMenu += f'<option value="{country_code}" {option_class}>{country_code}-{country_name_converted}</option>'
            #
            check_blocked = self.settings.BlockedCountries.get(country_code)
            if check_blocked != None:
                BlockedCountryMenu += option
        return CountryMenu
    
    #--------------------------------------------------------------------------------
