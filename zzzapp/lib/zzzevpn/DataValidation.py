#-----validates data coming into the webserver-----

import pprint
import re

#-----import modules from the lib directory-----
# This module cannot import the full zzzevpn because it would cause import loops
# import zzzevpn.Config
import zzzevpn

class DataValidation:
    'check POST data for problems'
    
    ConfigData: dict = None
    standalone: zzzevpn.Standalone = None

    megabyte = 1024 * 1024
    max_get_size = 2048
    # 20MB max POST
    max_post_size = 20*megabyte

    #-----regex patterns-----
    # these are just basic tests, modules should do more specific tests
    comma_whitespace_pattern = r'[,\s]+'
    #
    ip_regex_pattern = r'(\d{1,3}\.){3}\d{1,3}'
    # commas or newlines as separators in the list
    ip_list_regex_pattern = r'^({}[,\n]+)*{}$'.format(ip_regex_pattern, ip_regex_pattern)
    cidr_subnet_regex_pattern = r'\/\d{1,2}'
    cidr_regex_pattern = r'{}(|{})'.format(ip_regex_pattern, cidr_subnet_regex_pattern)
    cidr_list_regex_pattern = r'^({}{})*{}$'.format(cidr_regex_pattern, comma_whitespace_pattern, cidr_regex_pattern)
    
    # json_regex_pattern = r'^\{[\w\s.{}":,-]+\}$'
    json_regex_pattern = r'^\s*\{.+\}\s*$'
    
    subdomain_regex_pattern = r'[\w.-]{3,400}'
    subdomain_list_regex_pattern = r'^({}[,\n]+)*{}$'.format(subdomain_regex_pattern, subdomain_regex_pattern) # commas or newlines as separators
    text_regex_pattern = r'^[\w\s.,/-]+$' #TODO: make this match most printable text characters

    #-----data cleanup regexes-----
    regex_commas = re.compile(r',')
    regex_comma_newline = re.compile(r'[,\n]')
    regex_comma_space = re.compile(r'[, ]')
    regex_newline_space = re.compile(r'[\n ]')
    regex_spaces = re.compile(r' ')
    regex_multi_spaces = re.compile(r' [ ]+')
    regex_tab_cr = re.compile(r'[\t\r]')

    list_types = { 'cidr-list', 'int-list', 'int-range-list', 'ip-list', 'subdomain-list' }
    skip_auto_clean_datatypes = { 'blob', 'json', 'text-huge', 'text-large', 'text-small' }

    #-----list of DataTypes for use in the Rules below-----
    # the regex validations are used to match associated URL GET/POST param names in Rules
    # also length limits
    # TypeName => (length, regex, regex_description)
    # regex_description: english description of the regex pattern
    DataTypes = {
        # compiled regex will be stored in 'regex_compiled' under each item

        # just enforce length limits and allow any content
        'blob': {
            'length': 10*megabyte,
            'regex_pattern': r'.+',
        },

        'boolean': {
            'length': 5,
            # 'regex_pattern': r'^([Tt]rue|[Ff]alse)$',
            'regex_pattern': r'^(0|1|true|false)$',
            'regex_flags': re.IGNORECASE,
            'regex_description': 'true/false or 0/1',
        },
        'cidr-list': {
            'length': 5*megabyte,
            #TODO: make code accept "\s*" and comma as separators, then update the regex to allow spaces
            # 'regex_pattern': r'((\d{1,3}\.){3}\d{1,3}(|\/\d{1,2})(|\n))*',
            'regex_pattern': cidr_list_regex_pattern,
        },
        'domain': {
            'length': 100,
            'regex_pattern': r'^[\w.-]+$'
        },
        'filename': {
            'length': 100,
            'regex_pattern': r'^[\w.-]+$'
        },
        'int': {
            'length': 10,
            'regex_pattern': r'^[0-9]+$',
        },
        'int-list': {
            'length': 1000,
            'regex_pattern': r'^[0-9,]+$',
        },
        'int-range-list': {
            # EX: 1-100,200-300,400,999
            'length': 1000,
            'regex_pattern': r'^[0-9,-]+$',
        },
        'ip': {
            'length': 15,
            'regex_pattern': r'^{}$'.format(ip_regex_pattern),
            'regex_description': 'must look like an IP address'
        },
        'ip-list': {
            'length': 5*megabyte,
            'regex_pattern': ip_list_regex_pattern,
        },
        'json': {
            'length': megabyte,
            'regex_pattern': json_regex_pattern,
        },
        'subdomain': {
            'length': 253,
            'regex_pattern': r'^{}$'.format(subdomain_regex_pattern),
        },
        'subdomain-list': {
            'length': 10*megabyte,
            'regex_pattern': subdomain_list_regex_pattern,
        },
        'text-huge': {
            'length': 10*megabyte,
            'regex_pattern': text_regex_pattern,
        },
        'text-large': {
            'length': megabyte,
            'regex_pattern': text_regex_pattern,
        },
        'text-small': {
            'length': 255,
            'regex_pattern': text_regex_pattern,
        },
        'url': {
            'length': 2048,
            'regex_pattern': r'^[\w./:%-]+$',
        },
        'word': {
            'length': 50,
            'regex_pattern': r'^[\w]+$',
        },
    }
    
    Rules = {
        # global param rules apply to all URL's
        'global': {
            'action': 'word',
            'command': 'word',
            # 'domain_list': 'text-large',
            'domain_list': 'subdomain-list',
            'filename': 'filename',
            'host': 'subdomain',
            'id': 'int',
            'ip': 'ip',
            'ip_list': 'cidr-list',
            'json': 'json',
            'json_data': 'json',
            'service_name': 'word',
        },
        
        # overrides the default max POST size on a per-URL basis
        # can only go lower, not higher
        'max_post_size': {
            '/whois': 1024,
        },
        
        # EX: '/index'
        # '/URI/PATH': {
        #     'PARAM': 'DATATYPE',
        #     'PARAM2': 'DATATYPE',
        # },

        '/db_view': {
            'table': 'word',
        },
        '/edit_dns': {
            'handle_invalid_domains': 'word',
        },
        '/icap_settings': {
            'icap_condensed': 'boolean',
            'row_id': 'int',
        },
        '/index': {
            'test': 'int',
        },
        '/ip_log_raw_data': {
            # 'src_ip': 'ip-list',
            # 'dst_ip': 'ip-list',
            'src_ip': 'cidr-list',
            'dst_ip': 'cidr-list',
            'src_ports': 'int-range-list',
            'dst_ports': 'int-range-list',
            'extra_analysis': 'boolean',
            'flag_bps_above_value': 'int',
            'flag_pps_above_value': 'int',
            ####################
            'auto_update_file_list': 'boolean',
            'connection_external': 'boolean',
            'connection_internal': 'boolean',
            'flags_any': 'boolean',
            'flags_none': 'boolean',
            'include_accepted_packets': 'boolean',
            'include_blocked_packets': 'boolean',
            'min_displayed_packets': 'int',
            'prec_tos_zero': 'boolean',
            'prec_tos_nonzero': 'boolean',
            'protocol_icmp': 'boolean',
            'protocol_other': 'boolean',
            'protocol_tcp': 'boolean',
            'protocol_udp': 'boolean',
            'search_length': 'int-range-list',
            'show_max_bps_columns': 'boolean',
            'sort_by': 'word',
            'ttl': 'int-range-list',
        },
        '/iptables_log': {
            'highlight_ips': 'boolean',
            'lines_to_analyze': 'int',
            'max_age': 'word',
            'sort_by': 'word',
        },
        '/list_manager': {
            'entry_id': 'int',
            'list_id': 'int',
        },
        '/network_service': {
            'do_delete': 'boolean',
            'ip': 'ip-list', # this is a list here, while it is a single IP in the global rules
            'nslookup_dns_blocked': 'boolean',
            'whois_server_only': 'boolean',
        },
        # '/nslookup': {
        #     'nslookup_dns_blocked': 'boolean',
        #     'whois_server_only': 'boolean',
        # },
        # '/reverse_dns': {
        #     'ip': 'ip-list',
        #     'nslookup_dns_blocked': 'boolean',
        #     'whois_server_only': 'boolean',
        # },
        '/squid_log': {
            'lines_to_analyze': 'int',
        },
        # update_zzz
        '/update_zzz': {
            'branch': 'text-small',
            'dev_version': 'word',
        },
        # '/whois': {
        #     'do_delete': 'boolean',
        #     'nslookup_dns_blocked': 'boolean',
        #     'whois_server_only': 'boolean',
        # },
    }
    
    command = None
    service_name = None
    allow_undeclared_params = True # set to True to allow un-declared params in the data content
    enforce_rules = False # set to True to enforce blocking of requests that violate the rules
    should_auto_clean = False # set to True to auto-clean data that fails validation
    should_print_errors = True # set to True to print errors
    should_print_test_results = False # set to True to print all test results

    # auto-cleaned data, stores params if auto_clean is True
    # should only be needed if the original data failed validation
    auto_cleaned_data = {}
    
    validation_detailed_errors = {} # detailed error messages for each param, parsable by the client javascript to highlight the problem fields
    validation_status_msgs = [] # print to apache log

    #TODO: update all Rules so that self.enforce_rules is safe to default to True without breaking things
    def __init__(self, ConfigData: dict=None, allow_undeclared_params: bool=True, enforce_rules: bool=False, auto_clean: bool=False, print_errors: bool=True, print_test_results: bool=False):
        self.standalone = zzzevpn.Standalone()
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData

        if allow_undeclared_params is not None:
            self.allow_undeclared_params = allow_undeclared_params
        if enforce_rules is not None:
            self.enforce_rules = enforce_rules
        if auto_clean is not None:
            self.should_auto_clean = auto_clean
        if print_errors is not None:
            self.should_print_errors = print_errors
        if print_test_results is not None:
            self.should_print_test_results = print_test_results

        self.init_vars()

    #--------------------------------------------------------------------------------

    def init_vars(self):
        self.auto_cleaned_data = {}
        self.validation_detailed_errors = {}
        self.validation_status_msgs = []

        # don't pre-compile regexes, just return
        return

        # pre-compile regexes
        for key in self.DataTypes.keys():
            item = self.DataTypes[key]
            if not isinstance(item, dict):
                #TEST
                print(f'ERROR parsing item: {key}')
                #ENDTEST
                continue
            regex_pattern = item.get('regex_pattern', None)
            regex_flags = item.get('regex_flags', None)
            if not regex_pattern:
                #TODO: log missing pattern?
                continue
            regex_compiled = None
            try:
                if not regex_flags:
                    regex_flags = 0
                regex_compiled = re.compile(regex_pattern, regex_flags)
            except:
                #TODO: log errors somewhere other than stdout?
                print(f'ERROR compiling regex_pattern: {regex_pattern}')
            self.DataTypes[key]['regex_compiled'] = regex_compiled

    #--------------------------------------------------------------------------------

    def is_list_type(self, data_type_name: str) -> bool:
        if data_type_name in self.list_types:
            return True
        return False

    #--------------------------------------------------------------------------------

    def print_error(self, data):
        self.validation_status_msgs.append(data)
        if self.should_print_errors:
            print(data)

    def print_test_result(self, data):
        self.validation_status_msgs.append(data)
        if self.should_print_test_results:
            print(data)

    #--------------------------------------------------------------------------------

    def check_content_length(self, environ, request_body_size):
        # POST
        if request_body_size>self.max_post_size:
            return False
        
        # get the path
        # check for custom max_post_size
        
        # GET
        query_string = environ.get('QUERY_STRING', None)
        if query_string:
            if len(query_string)>self.max_get_size:
                return False
        return True

    #--------------------------------------------------------------------------------

    def run_regex(self, value, data_type_name: str, pattern: str, flags=0) -> bool:
        regex_compiled = self.DataTypes[data_type_name].get('regex_compiled', None)
        if not regex_compiled:
            # compile and save in self.DataTypes
            try:
                regex_compiled = re.compile(pattern, flags)
            except:
                self.print_error(f'run_regex() - ERROR compiling regex pattern under DataTypes[{data_type_name}]')
                return False
            self.DataTypes[data_type_name]['regex_compiled'] = regex_compiled

        # test the regex
        match = None
        try:
            match = regex_compiled.search(value)
        except Exception as e:
            # self.print_error(f'  type(value)={type(value)}')
            # self.print_error(f'  value={value}')
            self.print_error(f'run_regex() - ERROR testing regex_compiled for: DataTypes[{data_type_name}]')
            # self.print_error(pprint.pformat(e))
            return False

        if not match:
            return False
        return True

    #--------------------------------------------------------------------------------

    # html version of the detailed error messages
    def show_detailed_errors(self) -> str:
        if not self.validation_detailed_errors:
            return ''
        output = []
        for var_name in self.validation_detailed_errors:
            output.append(f'''{var_name}: {self.validation_detailed_errors[var_name]}<br>''')
        return '\n'.join(output)
    
    #--------------------------------------------------------------------------------

    # apply length and regex rules to the given value
    def apply_rule_to_data(self, data_type_name, value, var_name: str) -> bool:
        #EX: 'subdomain' --> lookup in DataTypes - contains 'length', 'regex_pattern', 'regex_flags'
        rule = self.DataTypes.get(data_type_name, None)
        if not rule:
            self.print_error(f'apply_rule_to_data() - ERROR: data_type_name "{data_type_name}" not found in DataTypes')
            return False
        if value in [None, '']:
            # don't process empty values, but zero is still OK to process
            return True

        #-----special case for python bool type-----
        # handle_post() may have converted the string 'true' or 'false' to a python bool before calling data_validation.validate()
        if data_type_name=='boolean' and isinstance(value, bool):
            return True

        # length rule
        rule_length = rule.get('length', None)
        if rule_length and len(value)>rule_length:
            self.print_error('validate_item() - ERROR: data length exceeded')
            self.validation_detailed_errors[var_name] = f'data length: {len(value)}, max allowed: {rule_length}'
            return False

        if self.should_auto_clean:
            list_separator = rule.get('list_separator', None)
            value = self.apply_auto_clean(value, data_type_name, list_separator)
            self.auto_cleaned_data[var_name] = value

        # regex rule
        rule_regex_pattern = rule.get('regex_pattern', None)
        if rule_regex_pattern:
            rule_regex_flags = rule.get('regex_flags', 0)
            if not self.run_regex(value, data_type_name, rule_regex_pattern, rule_regex_flags):
                self.print_error('validate_item() - ERROR: data failed the regex test')
                regex_description = rule.get('regex_description', '')
                self.validation_detailed_errors[var_name] = f'failed data pattern test: {regex_description}'
                return False
        return True

    #--------------------------------------------------------------------------------

    #TODO: finish this
    #-----check the data value against the Rules-----
    # lookup the global rule (if any) based on the name
    # lookup the specific rule (if any) based on the path_info and name
    def validate_item(self, path_info, name, value) -> bool:
        self.print_test_result(f'validate_item(): path_info={path_info}, name={name}')

        #-----specific rules override global rules-----
        found_specific = False
        specific_rule = self.Rules.get(path_info, None)
        if specific_rule:
            #EX: '/nslookup' --> contains 'host': 'subdomain'
            param_rule_data_type = specific_rule.get(name, None)
            if param_rule_data_type:
                found_specific = True
                # check the specific rule for this param
                return self.apply_rule_to_data(param_rule_data_type, value, name)

        found_global = False
        global_rule_data_type = self.Rules['global'].get(name, None)
        if global_rule_data_type:
            found_global = True
            # check the global rule for this param
            return self.apply_rule_to_data(global_rule_data_type, value, name)

        #TODO: max_post_size is another global rule set, maybe move it under the relevant specific rules?

        if not found_global and not found_specific:
            # no rules found for this param
            self.print_error(f'validate_item() - ERROR: undeclared param "{name}" in path_info "{path_info}"')
            if self.allow_undeclared_params:
                # allow the param
                self.print_test_result('validate_item() - allow_undeclared_params is True')
                return True
            else:
                # deny the param
                self.print_test_result('validate_item() - allow_undeclared_params is False')
                return False

        # probably will never get here?
        self.print_test_result('got to the end of validate_item()')
        return True

    #--------------------------------------------------------------------------------

    #-----automatically remove junk from a value to improve its chances of passing validation-----
    # try to avoid damaging the data or combining multiple values in a list into one value
    def apply_auto_clean(self, value, data_type_name: str, list_separator: str='') -> str:
        # don't clean empty values
        if value in [None, '']:
            return value

        # don't clean certain data types
        if data_type_name in self.skip_auto_clean_datatypes:
            return value
        if not isinstance(value, str):
            # only clean strings
            return value

        # tabs and carriage returns can be converted to spaces, except for lists with a newline separator
        # clean_value = self.regex_tab_cr.sub(' ', clean_value)

        # lists can have a separator specified: space, comma, newline
        # if self.is_list_type(data_type_name) and list_separator:
        #     if list_separator==' ':
        #         # replace commas and newlines with spaces
        #         clean_value = self.regex_comma_newline.sub(' ', clean_value)
        #     elif list_separator==',':
        #         # replace newlines and spaces with commas
        #         clean_value = self.regex_newline_space.sub(',', clean_value)
        #     elif list_separator=='\n':
        #         # replace commas and spaces with newlines
        #         clean_value = self.regex_comma_space.sub('\n', clean_value)

        # most data can have multiple spaces reduced to one space
        value = self.regex_multi_spaces.sub(' ', value)

        # almost all data has no need for leading or trailing whitespace
        value = value.strip()

        return value

    #--------------------------------------------------------------------------------

    #TODO: auto-clean any data that fails validation
    #-----run the Rules against given GET/POST params-----
    def validate(self, environ: dict, data: dict) -> bool:
        self.validation_status_msgs = []
        if not data:
            # empty data is always valid
            return True

        success = True
        script_path = environ.get('SCRIPT_NAME', None)
        path_info = environ.get('PATH_INFO', None)
        for name in data.keys():
            value = data[name]
            if self.validate_item(path_info, name, value):
                self.print_test_result(f'valid data for param "{name}"')
            else:
                self.print_error(f'invalid data for param "{name}"')
                if self.enforce_rules:
                    success = False

        return success

    #--------------------------------------------------------------------------------
