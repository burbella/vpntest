#-----work with ipset files-----
# generate a shell script that will be called by netfilter-persistent on boot:
#   /usr/share/netfilter-persistent/plugins.d/14-zzz-ipset
#       calls /etc/iptables/create-ipsets.sh
#           blacklist - create an empty list
#           countries - add all countries as empty lists with size 64 (the minimum)
#           allow-ip - hardcode private ip ranges
#                       then add custom IP's from Settings (if any)
#       calls /etc/iptables/update-ipset-blacklist.sh
#           uses ipset restore commands to get ipset data from files
#           /etc/iptables/ipset-blacklist
#       calls /etc/iptables/update-ipset-countries.sh
#           uses ipset restore commands to get ipset data from files
#           /etc/iptables/countries/ipset-cn
#           /etc/iptables/countries/ipset-ru
#
# generate country ip lists from ipdeny files
#   filter-out protected IP's
#   /opt/zzz/data/ipdeny-ipv4/cn.zone --> validate_ip_list() --> /etc/iptables/countries/ipset-cn
#
# call the shell scripts from inside the python daemon with subprocess.run()
#   this will be used to implement list changes while running
#   IPtables.py will have corresponding commands to make the associated rule changes
#   /etc/iptables/create_ipsets.sh
#   /etc/iptables/update-ipset-blacklist.sh
#   /etc/iptables/update-ipset-countries.sh
#
# When the blacklist is updated, edit/call update-ipset-blacklist.sh
#   it will do a create/add/swap/destroy for the blacklist
#
# When countries are added, edit/call update-ipset-countries.sh
#   it will do a create/add/swap/destroy for the countries on the list
#
# When a country is removed:
#   create an empty list2 with size 64, then swap it in (or just leave it in memory?)
#   IPtables.py will remove the relevant iptables entries, so the country is unblocked
#
# Detecting non-empty country lists:
#   > ipset list -terse
#   parse output, expect "Number of entries: 0"
# non-zero list sizes need to be swapped with an empty list if the country is not blocked?
# figure out how much memory is wasted by just leaving the list in memory
# maybe only the largest lists need to be swapped-out when not in use?
#
################################################################################
# Major Functions:
#
# read_settings()
#     determine if any active settings lists have IP's or CIDR's
#         autoplay, social, telemetry, etc
#     check if any countries are blocked
#
# validate_ip_list() - call this function from ListManager
#     check all IP's/CIDR's against the ProtectedIP list
#         Private IP's (127.*, 10.*, etc.)
#         DNS
#         Our server external IP (autodetect in Config.py)
# 
# update_blacklist():
#     ip_list = read from DB
#     update_list(ip_list)
# 
# update_country_lists():
#     foreach country file:
#         ip_list = read from country file
#         update_list(ip_list)
# 
# update_list(ipset_name, ip_list):
#     this does the ipset create-add-swap-destroy
#
# make_script()
#
# run_script()
#
#-----Create ipset scripts that run on boot-----
# create_empty_list()
# update_list()
#
# run_script_create()
# run_script_update()
#

import glob
import os
import re
import urllib.parse

#-----package with all the Zzz modules-----
import zzzevpn

class IPset:
    'IPset file processing'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None
    
    #-----service name is not the same as the class name-----
    # the rest of the system recognizes that IP lists are stored in iptables
    # the IP blacklist was moved to an ipset, but the service name stayed "iptables"
    service_name = 'iptables'
    filedata_str = ''
    ip_requests_data = ''
    ip_validation_fails = []
    ip_validation_OK = []
    
    app_filepath = {
        'netfilter_persistent': '/usr/share/netfilter-persistent/plugins.d/14-zzz-ipset',
        'create_ipsets': '/etc/iptables/create-ipsets.sh',
        'update_ipset_blacklist': '/etc/iptables/update-ipset-blacklist.sh',
        'update_ipset_countries': '/etc/iptables/update-ipset-countries.sh',
    }
    
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
    
    #--------------------------------------------------------------------------------
    
    #-----makes a set of commands for updating an ipset-----
    def make_update_commands(self):
        pass
    
    #--------------------------------------------------------------------------------
    
    #-----installs an empty ipset for each country as a placeholder-----
    # future updates can be done by the standard create/add/swap/destroy
    def install_empty_ipsets(self):
        # get list of country codes
        # foreach country_code:
        #     'create ipset %s hash:net' % (country_code)
        pass
    
    #--------------------------------------------------------------------------------
    
    # read from ipdeny file: /opt/zzz/data/ipdeny-ipv4/XX.zone
    # write to ipset country file: 
    # always create "country2" as the listname
    # this just makes the ipset config file for the country, it will be swapped-in later
    def create_country_list(self, country):
        # ipset create country2
        # ipset add country2
        pass
    
    #--------------------------------------------------------------------------------
    
    #update_blacklist(self)
    #  ip_list = read from DB
    #  calculate the filepath - read from Config.py?
    #  update_list(filepath, ip_list)
    #
    # ipset create whatever2 hash:net
    # ipset add whatever2 2.2.2.3
    # ipset add whatever2 ...
    # ipset add whatever2 ...
    # ipset swap whatever whatever2
    # ipset destroy whatever2
    def update_blacklist(self):
        blacklist_filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath']
        ipset_filepath = self.ConfigData['UpdateFile']['ipset']['blacklist_filepath']
        
        # Why always add entries to IPSET_NAME2 instead of IPSET_NAME?
        #   because "IPSET_NAME" is installed and running
        #   we build a new list separate from the installed list, then swap it in
        with open(blacklist_filepath, 'r') as blacklist_file, open(ipset_filepath, 'w') as write_file:
            data_to_write = ['create blacklist2 hash:net family inet hashsize 1024 maxelem 500000 -quiet\n']
            for item in blacklist_file:
                #TODO: validate IP's (even though they should have been validated on upload)
                item = item.strip("\n")
                # data_to_write += 'add blacklist2 {}\n'.format(item)
                data_to_write.append(f'add blacklist2 {item}\n')
            write_file.write(''.join(data_to_write))
    
    #--------------------------------------------------------------------------------
    
    # calls a bash script subprocess - does the ipset create-add-swap-destroy
    # create-add commands must be pre-compiled in the ipset-update-blacklist.conf file
    def install_blacklist(self):
        #-----only the daemon can use this function, not apache-----
        #if not self.util.running_as_root():
            #TODO - log an error here
            #return
        return self.util.run_script('/etc/iptables/ipset-update-blacklist.sh')
    
    #--------------------------------------------------------------------------------
    
    def update_allowlist(self):
        allowlist_filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath_allow']
        ipset_filepath = self.ConfigData['UpdateFile']['ipset']['allowlist_filepath']
        
        # Why always add entries to IPSET_NAME2 instead of IPSET_NAME?
        #   because "IPSET_NAME" is installed and running
        #   we build a new list separate from the installed list, then swap it in
        with open(allowlist_filepath, 'r') as allowlist_file, open(ipset_filepath, 'w') as write_file:
            data_to_write = ['create allow-ip2 hash:net family inet hashsize 1024 maxelem 500000 -quiet\n']
            for item in allowlist_file:
                #TODO: validate IP's (even though they should have been validated on upload)
                item = item.strip("\n")
                # data_to_write += 'add allow-ip2 {}\n'.format(item)
                data_to_write.append(f'add allow-ip2 {item}\n')
            write_file.write(''.join(data_to_write))
    
    def install_allowlist(self):
        return self.util.run_script('/etc/iptables/ipset-update-allow-ip.sh')
    
    #--------------------------------------------------------------------------------
    
    #-----only swap-in the countries blocked in Settings-----
    # the settings page will make a request to the daemon to do this
    # assumes the country lists have been created already by update_country_lists()
    def install_country_lists(self):
        self.settings.get_settings()
        #-----merge all the changes into a single file and call the installer shell script-----
        ipset_merged_filepath = self.ConfigData['IPdeny']['ipv4']['conf_file']
        with open(ipset_merged_filepath, 'w') as write_file:
            single_ipset_data_to_write = ['create countries-new hash:net family inet hashsize 1024 maxelem 250000 -quiet\n']
            for country_code in self.settings.SettingsData['blocked_country']:
                #-----using lowercase country codes when reading ipset files-----
                # only ipdeny files have lowercase
                # ipset country configs created from ipdeny also uses lowercase
                # the rest of the system assumes uppercase
                ipset_country_filepath = '{}/{}.conf'.format(self.ConfigData['IPdeny']['ipv4']['dst_dir'], country_code.lower())
                print('ipset_country_filepath: ' + ipset_country_filepath)
                with open(ipset_country_filepath, 'r') as read_file:
                    # single_ipset_data_to_write += read_file.read()
                    single_ipset_data_to_write.append(read_file.read())
            single_ipset_data_to_write.append('swap countries countries-new -quiet\n')
            single_ipset_data_to_write.append('destroy countries-new -quiet\n')
            write_file.write(''.join(single_ipset_data_to_write))
        return self.util.run_script('/etc/iptables/ipset-update-countries.sh')
    
    #--------------------------------------------------------------------------------
    
    #TODO: ip validation before creating ipset files
    #      skip invalid IP's and continue adding other IP's in the file
    #      log skipped IP's
    #-----create country ipsets from ipdeny files-----
    #      iptables needs 12 entries per ipset
    #      condense multiple country lists into one installed list: countries
    #      create-add-swap-destroy:
    #          create countries-new
    #          add countries-new
    #          swap countries countries-new
    #          destroy countries-new
    def update_country_lists(self):
        self.ip_validation_fails = []
        self.ip_validation_OK = []
        print('update_country_lists() - START')
        for country_code in self.ConfigData['IPdeny']['countries']:
            ipdeny_filepath = '{}/{}.zone'.format(self.ConfigData['IPdeny']['ipv4']['src_dir'], country_code)
            #-----using lowercase country codes when writing ipset files-----
            # only ipdeny files have lowercase
            # ipset country configs created from ipdeny also uses lowercase
            # the rest of the system assumes uppercase
            ipset_filepath = '{}/{}.conf'.format(self.ConfigData['IPdeny']['ipv4']['dst_dir'], country_code)
            with open(ipdeny_filepath, 'r') as read_file, open(ipset_filepath, 'w') as write_file:
                data_to_write = []
                #-----one big ipset, no create/swap/destroy in individual country configs, just "add"-----
                for item in read_file:
                    item = item.strip("\n")
                    #-----validate IP's because who knows if the 3rd-party data is safe-----
                    err = self.validate_ip(item)
                    #-----log rejected IP's, write OK IP's to ipset country file-----
                    if err:
                        print(err)
                    else:
                        # data_to_write += 'add countries-new {}\n'.format(item)
                        data_to_write.append(f'add countries-new {item}\n')
                write_file.write(''.join(data_to_write))
        print('update_country_lists() - DONE')
    
    #--------------------------------------------------------------------------------
    
    def make_webpage(self, environ, pagetitle):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, 'Edit IP', self.settings)
        
        output = self.webpage.make_webpage(environ, self.make_EditIPPage(environ))
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def handle_post(self, environ, request_body_size):
        if self.webpage is None:
            self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)
        
        #-----read the POST data-----
        request_body = environ['wsgi.input'].read(request_body_size)
        
        #-----decode() so we get text strings instead of binary data, then parse it-----
        raw_data = urllib.parse.parse_qs(request_body.decode('utf-8'))
        action = raw_data.get('action', None)
        if action!=None:
            action = action[0]
        filename = raw_data.get('filename', None)
        if filename!=None:
            filename = filename[0]
        uploaded_ip_list = raw_data.get('ip_list', None)
        if uploaded_ip_list!=None:
            uploaded_ip_list = uploaded_ip_list[0]
        
        #-----return if missing data-----
        if (request_body_size==0 or action==None):
            self.webpage.error_log(environ, 'ERROR: missing data')
            return 'ERROR: missing data'
        
        #-----validate data-----
        if self.data_validation==None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData)
        data = {
            'action': action,
            'filename': filename,
            'ip_list': uploaded_ip_list,
        }
        if not self.data_validation.validate(environ, data):
            return self.webpage.error_log(environ, 'ERROR: data validation failed')
        
        if action=='add_ips':
            return self.process_ips(environ, uploaded_ip_list, action)
        elif action=='replace_ips':
            return self.process_ips(environ, uploaded_ip_list, action)
        elif action=='get_ip_file':
            self.get_ip_replacement_file(filename)
            return self.filedata_str
        
        return self.webpage.error_log(environ, 'ERROR: invalid action')
    
    #--------------------------------------------------------------------------------
    
    def make_EditIPPage(self, environ):
        self.get_ip_requests(30)
        self.get_ip_replacement_file()
        
        EditIpHTML = {
            'CSP_NONCE': environ['CSP_NONCE'],
            'ip_backup_files': self.list_ip_backup_files(environ),
            'ips_to_replace': self.filedata_str,
            'html_ip_requests': self.show_ip_requests(),
        }
        
        body = self.webpage.load_template('EditIP')
        return body.format(**EditIpHTML)
    
    #--------------------------------------------------------------------------------
    
    def get_ip_requests(self, limit: int=50):
        if not self.util.is_int(limit):
            limit = 50
        sql = '''SELECT sr.id as sr_id, sr.req_date, sr.action, sr.status, sr.details, uf.id as uf_id, uf.file_data, uf.src_filepath
                FROM service_request sr left outer join update_file uf on sr.id=uf.service_request_id
                WHERE sr.service_name=?
                ORDER BY sr.id desc
                LIMIT {}''';
        params = (self.service_name,)
        (colnames, rows, rows_with_colnames) = self.db.select_all(sql.format(str(limit)), params)
        self.ip_requests_data = rows_with_colnames
    
    #--------------------------------------------------------------------------------
    
    def show_ip_requests(self):
        html = '''
        <table><tr>
        <th>sr_id</th><th>req_date</th><th>action</th><th>status</th>
        <th class="width_300">Details</th><th>uf_id</th><th class="width_200">File Data</th><th>src_filepath</th>
        </tr>
        {}
        </table>
        '''
        
        options = {
            'collapsable_html': {
                'details': 'details_',
                'file_data': 'file_data_',
            },
        }
        custom_html_table = self.util.custom_html_table(self.ip_requests_data, options)

        return html.format(custom_html_table)
    
    #--------------------------------------------------------------------------------
    
    def get_ip_replacement_file(self, oldfile=''):
        filepath = self.ConfigData['ApacheTempFiles'] + '/' + oldfile;
        if oldfile=='':
            filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath']
        with open(filepath, 'r') as read_file:
            self.filedata_str = read_file.read()
    
    #--------------------------------------------------------------------------------
    
    def list_ip_backup_files(self, environ):
        html = '''
        <table><tr><th>Date</th><th>File</th></tr>
        {}
        </table>
        '''
        
        base_filepath = self.ConfigData['UpdateFile']['iptables']['src_filepath']
        ip_files = glob.glob(os.path.join(self.ConfigData['ApacheTempFiles'], 'iptables-blacklist.txt.*'))
        
        file_regex = r'^' + base_filepath + r'\.(\d\d\d\d)\-(\d\d)\-(\d\d)\-(\d\d)\-(\d\d)\-(\d\d)$'
        regex_pattern = re.compile(file_regex, re.IGNORECASE)
        
        ctr = 0
        html_table_rows = ''
        for item in sorted(ip_files, reverse=True):
            match = regex_pattern.match(item)
            filename = os.path.basename(item)
            if match:
                file_date = '{}-{}-{} {}:{}:{}'.format(match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6))
                html_table_rows += f'<tr><td>{file_date}</td><td><a class="clickable get_ip_backup_file" data-onclick="{filename}">{filename}</a></td></tr>'
                ctr += 1
                # stop after 500 files
                if ctr>=500:
                    break
        
        return html.format(html_table_rows)
    
    #--------------------------------------------------------------------------------
    
    #TODO: finish this, add safety checks
    def process_ips(self, environ, uploaded_ip_list, action):
        if not uploaded_ip_list:
            return 'ERROR: no IPs uploaded'
        ip_list = uploaded_ip_list.rstrip('\n').splitlines()
        
        #-----remove duplicates-----
        ip_list = self.util.unique_sort(ip_list)
        
        if not self.validate_ip_list(environ, ip_list):
            err = 'ERROR: invalid IP found - ' + '\n'.join(self.ip_validation_fails)
            return err
        
        # DB: service_request table (service_name=iptables, action=add_ips)
        self.db.insert_service_request(self.service_name, action)
        
        service_request_id = self.db.cur.lastrowid
        
        # DB: update_file table
        # apache just fills-in the file_data
        # the daemon will fill-in the src filepath and dst filepath
        # 
        sql_update_file = "insert into update_file (service_request_id, file_data) values (?, ?)"
        params_update_file = (service_request_id, '\n'.join(self.ip_validation_OK))
        self.db.query_exec(sql_update_file, params_update_file)
        
        self.util.work_available(1)
        
        return 'success'
    
    #--------------------------------------------------------------------------------
    
    #-----check an IP, return an error or empty string-----
    def validate_ip(self, ip):
        if self.util.is_protected_ip(ip):
            self.ip_validation_fails.append(ip)
            return "validate_ip(): PROTECTED IP: " + ip
        elif self.util.cidr_includes_protected_ip(ip):
            self.ip_validation_fails.append(ip)
            return "validate_ip(): CIDR INCLUDES PROTECTED IP: " + ip
        elif not self.util.is_public(ip):
            #-----validate CIDR entries separately from IP's-----
            self.ip_validation_fails.append(ip)
            return "validate_ip(): PRIVATE IP/CIDR " + ip
        else:
            self.ip_validation_OK.append(ip)
            return ''
    
    #TODO:
    #   auto-detect our public IP and prevent that from being listed
    #   identify overlapping CIDR's and IP's, suggest fixes (warn or error?)
    #   warn if the mask changes the IP number(s)?
    #     Examples:
    #       1.2.33.0/16 --> 1.2.0.0/16
    #       1.2.33.0/12 --> 1.0.0.0/12
    #       1.2.17.0/20 --> 1.2.16.0/20
    #     store the effective CIDR instead of the submitted CIDR?
    #     warn or error?
    #   add allowlist config for selected public IP's/CIDR's to prevent SSH/HTTPS access lockouts
    #   move to a Util library
    #
    #########################################
    # Validate a list of IP's and/or CIDR's
    # block internal IP's for safety, so the VM is not cut off from the internet
    #   10.0.0.0/8
    #   127.0.0.0/8
    #   172.16.0.0/12
    #   192.168.0.0/16
    # EXAMPLES:
    #   10.99.9.0/24 - fail (private CIDR)
    #   10.99.9.1 - fail (private IP)
    #   1.2.3.0/24 - success
    #   1.2.3.4 - success
    #
    def validate_ip_list(self, environ, ip_list):
        self.ip_validation_fails = []
        self.ip_validation_OK = []
        for ip in ip_list:
            if not ip:
                continue
            err = self.validate_ip(ip)
            if err:
                self.webpage.error_log(environ, err)
        if len(self.ip_validation_fails):
            return False
        
        return True
    
    #--------------------------------------------------------------------------------
    
    ###################################
    # IPv6 - requires separate ipsets #
    ###################################
    
    #TODO: skip the country if it doesn't have an IPv6 ipdeny file
    
    
    #--------------------------------------------------------------------------------
