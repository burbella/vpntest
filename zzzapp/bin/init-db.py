#!/opt/zzz/venv/bin/python3

#-----initialize the DB at install time-----

import argparse
import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz DB init', flush=True)
else:
    sys.exit('This script must be run as root!')

os.nice(19)

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

settings = zzzevpn.Settings(ConfigData)
# Do NOT run get_settings() here, we are resetting the contents of the settings DB

#--------------------------------------------------------------------------------

zzz_last_updated_default = '2022-01-01 01:00:00'
zzz_list_columns = ['list_name', 'list_type', 'list_data_source', 'allow_delete', 'allow_edit', 'always_active', 'is_active', 'auto_update', 'list_url', 'list_length', 'zzz_last_updated']
zzz_list_config = [
    #-----default lists-----
    {
        'list_name': 'easylist',
        'list_type': 'dns-deny',
        'list_data_source': 'url',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 0,
        'is_active': 0,
        'auto_update': 1,
        'list_url': 'https://raw.githubusercontent.com/0Zinc/easylists-for-pihole/master/easylist.txt',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'easylist-privacy',
        'list_type': 'dns-deny',
        'list_data_source': 'url',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 0,
        'is_active': 0,
        'auto_update': 1,
        'list_url': 'https://raw.githubusercontent.com/0Zinc/easylists-for-pihole/master/easyprivacy.txt',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'ShadowWhisperer-malware',
        'list_type': 'dns-deny',
        'list_data_source': 'url',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 0,
        'is_active': 0,
        'auto_update': 1,
        'list_url': 'https://raw.githubusercontent.com/ShadowWhisperer/BlockLists/master/Lists/Malware',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },

    #-----combined lists-----
    {
        'list_name': ConfigData['CombinedLists']['dns-deny'],
        'list_type': 'dns-deny',
        'list_data_source': 'combined',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 1,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': ConfigData['CombinedLists']['ip-deny'],
        'list_type': 'ip-deny',
        'list_data_source': 'combined',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 1,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': ConfigData['CombinedLists']['ip-allow'],
        'list_type': 'ip-allow',
        'list_data_source': 'combined',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 1,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },

    #-----user-defined lists-----
    {
        'list_name': 'user-DNS-deny',
        'list_type': 'dns-deny',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 1,
        'always_active': 0,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'user-DNS-allow',
        'list_type': 'dns-allow',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 1,
        'always_active': 0,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'user-IP-deny',
        'list_type': 'ip-deny',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 1,
        'always_active': 0,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'user-IP-allow',
        'list_type': 'ip-allow',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 1,
        'always_active': 0,
        'is_active': 1,
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },

    #-----settings lists-----
    {
        'list_name': 'settings-autoplay',
        'list_type': 'dns-deny',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 0,
        'is_active': 0, # this will be affected by the checkbox on the /settings page
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'settings-social',
        'list_type': 'dns-deny',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 0,
        'is_active': 0, # this will be affected by the checkbox on the /settings page
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
    {
        'list_name': 'settings-telemetry',
        'list_type': 'dns-deny',
        'list_data_source': 'entries',
        'allow_delete': 0,
        'allow_edit': 0,
        'always_active': 0,
        'is_active': 0, # this will be affected by the checkbox on the /settings page
        'auto_update': 1,
        'list_url': '',
        'list_length': 0,
        'zzz_last_updated': zzz_last_updated_default,
    },
]

#--------------------------------------------------------------------------------

def add_settings_entries(list_manager: zzzevpn.ListManager, list_name: str):
    sql_update = '''update zzz_list
        set download_data=?, accepted_entries=?, rejected_entries=?, list_length=?, zzz_last_updated=datetime('now'), last_valid_date_updated=datetime('now')
        where list_name=?'''
    bind_settings_dir = list_manager.ConfigData['Directory']['Settings']

    # "settings-autoplay" --> "autoplay"
    list_name_parts = list_name.split('-')
    filename = list_name_parts[1]
    if not filename in ['autoplay', 'social', 'telemetry']:
        return

    src_filepath = f'{bind_settings_dir}/{filename}.txt'
    filedata = list_manager.util.get_filedata(src_filepath)
    if not filedata:
        return

    validation_result = list_manager.util.validate_domain_list(filedata.split('\n'))
    params_update = (filedata, '\n'.join(validation_result['accepted_domains']), '\n'.join(validation_result['rejected_domains']), validation_result['list_length'], list_name)
    print(f'add_settings_entries({list_name}) - updating zzz_list')
    list_manager.db.query_exec(sql_update, params_update)
    if not validation_result['accepted_domains']:
        return

    print(f'add_settings_entries({list_name}) - adding zzz_list_entries')
    list_manager.update_zzz_list_entries(list_name=list_name, list_data=validation_result['accepted_domains'])

#--------------------------------------------------------------------------------

def init_zzz_list_db(settings: zzzevpn.Settings, args: argparse.Namespace):
    list_name = args.zzz_list or ''
    # args.zzz_list_all overrides args.zzz_list
    print(f'init_zzz_list_db({list_name})')
    builtin = 1
    sql_delete = "delete from zzz_list"
    sql_delete_entries = "delete from zzz_list_entries"
    params_delete = ()
    if not args.zzz_list_all:
        sql_delete = "delete from zzz_list where list_name=?"
        sql_delete_entries = "delete from zzz_list_entries where zzz_list_id in (select id from zzz_list where list_name=?)"
        params_delete = (list_name,)

    sql = '''insert into zzz_list (list_name, list_type, list_data_source,
        allow_delete, allow_edit, builtin, always_active,
        is_active, auto_update, list_url,
        list_length, zzz_last_updated, last_valid_date_updated)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params_list = []
    for list_details in zzz_list_config:
        if not args.zzz_list_all:
            if list_name != list_details['list_name']:
                continue
        param = (list_details['list_name'], list_details['list_type'], list_details['list_data_source'],
            list_details['allow_delete'], list_details['allow_edit'], builtin, list_details['always_active'],
            list_details['is_active'], list_details['auto_update'], list_details['list_url'],
            list_details['list_length'], list_details['zzz_last_updated'], list_details['zzz_last_updated']
        )
        params_list.append(param)

    if not params_list:
        print('ERROR: zzz-list name not found')
        return

    print('clear zzz_list_entries table')
    settings.db.query_exec(sql_delete_entries, params_delete)
    print('clear zzz_list table')
    settings.db.query_exec(sql_delete, params_delete)
    print('fill zzz_list table')
    settings.db.query_exec_many(sql, params_list)

    list_manager = zzzevpn.ListManager(settings.ConfigData, settings.db, settings.util)
    for list_details in zzz_list_config:
        if not args.zzz_list_all:
            if list_name != list_details['list_name']:
                continue
        if list_details['list_name'] in ['settings-autoplay', 'settings-social', 'settings-telemetry']:
            add_settings_entries(list_manager, list_details['list_name'])

#--------------------------------------------------------------------------------

def zzz_list_show_info():
    print('downloadable lists configured in init-db')
    for list_details in zzz_list_config:
        if not list_details['list_url']:
            continue
        print(f'''{list_details['list_name']}: {list_details['list_url']}''')

#--------------------------------------------------------------------------------

#-----select one or more tables to init-----
#-----command-line args-----
parser = argparse.ArgumentParser(description='Zzz DB initialize')
parser.add_argument('--country', dest='country', action='store_true', help='init the country DB')
parser.add_argument('--domain', dest='domain', action='store_true', help='init the webserver_domain field')
parser.add_argument('--settings', dest='settings', action='store_true', help='init the settings DB table')
parser.add_argument('--tld', dest='tld', action='store_true', help='init the TLD DB')
parser.add_argument('--zzz-list', dest='zzz_list', action='store', help='init the zzz_list DB table for a given list name')
parser.add_argument('--zzz-list-all', dest='zzz_list_all', action='store_true', help='init the zzz_list DB table for all lists')
parser.add_argument('--zzz-list-show-info', dest='zzz_list_show_info', action='store_true', help='show downloadable lists configured in init-db')

#TEST
parser.add_argument('--ip-country', dest='ip_country', action='store_true', help='init the IP-country DB')

args = parser.parse_args()

count_args = 0

if args.domain:
    settings.init_webserver_domain()
    count_args += 1

if args.settings:
    settings.init_settings_db()
    count_args += 1

#-----load country name-code map-----
if args.country:
    settings.init_country_db()
    count_args += 1

#-----load TLD table-----
if args.tld:
    settings.init_tld_db()
    count_args += 1

#-----load zzz_list table-----
# need to load settings for this one
if args.zzz_list or args.zzz_list_all:
    loaded_settings = zzzevpn.Settings(ConfigData)
    loaded_settings.get_settings()
    init_zzz_list_db(loaded_settings, args)
    count_args += 1

#-----just show list info without doing any DB updates-----
if args.zzz_list_show_info:
    zzz_list_show_info()
    count_args += 1

#-----IP-country map: load country name-code map-----
if args.ip_country:
    settings.init_ip_country_db()
    count_args += 1

#-----close cursor and DB when done using them-----
settings.db.db_disconnect()

if count_args==0:
    parser.print_help()
else:
    print("Done", flush=True)
