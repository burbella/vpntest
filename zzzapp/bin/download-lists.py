#!/opt/zzz/venv/bin/python3

#-----download lists-----

import argparse
import getpass
import os
import requests
import site
import sys
import time
import validators

#-----make sure we're running as root or www-data or exit-----
# username = getpass.getuser()
# if os.geteuid()!=0 and username!='www-data':
#     sys.exit('This script must be run as root or www-data')
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')
bind = zzzevpn.BIND(ConfigData)
list_manager = bind.list_manager

#--------------------------------------------------------------------------------

def reload_bind(bind: zzzevpn.BIND):
    #TEST - not needed?
    # get latest Settings after the lists are updated
    # bind.settings.get_settings()

    bind.update_bind_config_with_listmanager()

#--------------------------------------------------------------------------------

def log_db_error(db: zzzevpn.DB, list_id, download_status, make_list_inactive: bool=False) -> None:
    if make_list_inactive:
        sql_update = '''update zzz_list
            set download_status=?, zzz_last_updated=datetime('now'), is_active=0
            where id=?'''
        params = (download_status, list_id)
    else:
        sql_update = '''update zzz_list
            set download_status=?, zzz_last_updated=datetime('now')
            where id=?'''
        params = (download_status, list_id)
    db.query_exec(sql_update, params)
    print(download_status)

#--------------------------------------------------------------------------------

def do_download(list_manager: zzzevpn.ListManager, list_id, list_url: str) -> dict:
    download_result = {
        'download_status': True,
        'download_status_msg': 'OK',
        'ascii_data': '',
    }

    if not validators.url(list_url):
        #-----log error and de-activate the list-----
        download_result['download_status'] = False
        download_result['download_status_msg'] = 'ERROR: invalid URL'
        log_db_error(list_manager.db, list_id, download_result['download_status_msg'], make_list_inactive=True)
        return download_result

    #-----download the given list URL, store raw data in zzz_list table------
    print('downloading list')
    downloaded_data = ''
    try:
        response_data = requests.get(list_url, allow_redirects=True)
        # print(response_data.headers.get('content-type'))
        downloaded_data = response_data.text
    except:
        download_result['download_status'] = False
        download_result['download_status_msg'] = 'ERROR: failed to download list'
        log_db_error(list_manager.db, list_id, download_result['download_status_msg'])
        return download_result

    if not downloaded_data:
        download_result['download_status'] = False
        download_result['download_status_msg'] = 'ERROR: Empty list downloaded'
        log_db_error(list_manager.db, list_id, download_result['download_status_msg'])
        return download_result

    #-----handle both ASCII and Unicode-----
    download_result['ascii_data'] = list_manager.util.convert_utf8_to_ascii(downloaded_data)
    if not download_result['ascii_data']:
        print('Unidecode failed, using text without converting')
        download_result['ascii_data'] = downloaded_data

    return download_result

#--------------------------------------------------------------------------------

#-----parse/validate raw data into zzz_list_entries rows-----
def do_validate(list_manager: zzzevpn.ListManager, ascii_data: str) -> dict:
    return list_manager.util.validate_domain_list(ascii_data.split('\n'), list_rejected_domains=True)

#--------------------------------------------------------------------------------

def download_validate_save(list_id, list_url: str, list_manager: zzzevpn.ListManager, args: argparse.Namespace) -> bool:
    print(f'Download List: list_id={list_id}, list_url={list_url}')

    if args.skip_download:
        #-----pull data from the main list table-----
        print('skip download')
        sql = 'select download_data from zzz_list where id=?'
        params = (list_id,)
        row = list_manager.db.select(sql, params)
        if row:
            download_data = row[0]
            if not download_data:
                return False
            validation_result = do_validate(list_manager, download_data)
            print(f'''number of accepted_domains: {validation_result['list_length']}''')
            accepted_domains = '\n'.join(validation_result['accepted_domains'])
            rejected_domains = '\n'.join(validation_result['rejected_domains'])
            sql_update = '''update zzz_list
                set accepted_entries=?, list_length=?, rejected_entries=?
                where id=?'''
            params = (accepted_domains, validation_result['list_length'], rejected_domains, list_id)
            list_manager.db.query_exec(sql_update, params)
            list_manager.update_zzz_list_entries(list_id=list_id, list_data=validation_result['accepted_domains'])
            return True
        return False

    #-----get data from a URL, store in the main list table-----
    download_result = do_download(list_manager, list_id, list_url)
    if not download_result['download_status']:
        #-----update status and date, but don't over-write the backup-----
        sql_update = '''update zzz_list
            set download_status=?, zzz_last_updated=datetime('now')
            where id=?'''
        params = (download_result['download_status_msg'], list_id)
        list_manager.db.query_exec(sql_update, params)
        return False

    validation_result = do_validate(list_manager, download_result['ascii_data'])

    #-----success, log the current list in the backup field also-----
    #TODO: for lists containing both IP's and DNS, process rejected entries as IPs, reject invalid IPs/CIDRs
    #      for now, IP's are just dropped
    list_info = list_manager.get_list_info(list_id)
    list_manager.update_zzz_list_complete(list_info['list_name'], download_result['ascii_data'], download_result['download_status_msg'], validation_result['accepted_domains'], validation_result['rejected_domains'])

    #NOTE: do not rebuild BIND configs or reload BIND here because this function may be called multiple times, once for each list

    print('success\n-----')
    return True

#--------------------------------------------------------------------------------

#-----log the current time-----
datetime_now = bind.util.current_datetime()
print(datetime_now)

process_filename = 'download-lists.py'
process_filepath = f'/opt/zzz/python/bin/{process_filename}'
count_processes = list_manager.util.count_running_processes(name=process_filename, cmdline=[process_filepath])
if count_processes>1:
    print('ERROR: another download-lists process is running')
    sys.exit()

#TODO: only auto-download if a new auto-download arg is submitted
#-----read command-line options-----
# downloads only happen if one of these options are present:
#   --all
#   --list-name LISTNAME
arg_parser = argparse.ArgumentParser(description='Zzz list downloader')
arg_parser.add_argument('--all', dest='all', action='store_true', help='Download all lists')
arg_parser.add_argument('--list-name', dest='list_name', action='store', help='Download a given list name')
arg_parser.add_argument('--force-download', dest='force_download', action='store_true', help='Force a given list name to download')
arg_parser.add_argument('--generate-all-combined-lists', dest='generate_all_combined_lists', action='store_true', help='Generate all the combined lists')

# dns-deny, ip-allow, ip-deny
arg_parser.add_argument('--generate-combined-list', dest='generate_combined_list', action='store', help='Generate the combined list for the specified list_type')

# --generate-all-combined-lists will not update bind by default
arg_parser.add_argument('--reload-bind', dest='reload_bind', action='store_true', help='use with --generate-all-combined-lists to also update BIND config files')

# for processing lists without repeating the downloads
arg_parser.add_argument('--skip-download', dest='skip_download', action='store_true', help='Skip the download, just re-process stored data')

args = arg_parser.parse_args()

count_args = 0

if args.force_download and args.skip_download:
    sys.exit('ERROR: cannot use both options --force-download and --skip-download')
if args.all and args.list_name:
    sys.exit('ERROR: cannot use both options --all and --list-name')

lists_to_process = []
#-----get active lists that have not been updated in at least a day-----
# 23 hours = 82,800 seconds
# 24 hours = 86,400 seconds
# 1 hour less than a week(in seconds): 86400*7 - 3600
sql_conditions = '''
    and auto_update=1
    and (strftime('%s', datetime('now')) - strftime('%s', last_valid_date_updated))>82800
'''
sql_list_name = ''
params = ()
if args.all:
    count_args += 1
    print('downloading all lists')
elif args.list_name:
    count_args += 1
    print(f'downloading selected list: {args.list_name}')
    sql_list_name = 'and list_name=?'
    params = (args.list_name,)

if args.force_download:
    #-----do the download even if the list is not active or not expired-----
    count_args += 1
    sql_conditions = ''
    print('force download')
else:
    print('checking if list(s) are expired and have auto-update on')

rows_with_colnames = None
if args.skip_download:
    #-----re-process existing data from the DB-----
    # sql_conditions var is not needed here since we're not downloading
    count_args += 1
    sql = f'''select id, list_url 
        from zzz_list
        where length(download_data)>2
        {sql_list_name}
    '''
    print('skipping downloads, re-processing existing DB data')
    # print('No expired lists have auto_update on, not downloading anything.')
else:
    #-----download and process the list(s)-----
    sql = f'''select id, list_url
        from zzz_list
        where length(list_url)>5
        {sql_conditions}
        {sql_list_name}
    '''

if args.all or args.list_name:
    #-----only attempt downloads if params indicate it should happen-----
    (colnames, rows, rows_with_colnames) = list_manager.db.select_all(sql, params, skip_array=True)
    if rows_with_colnames:
        for row in rows_with_colnames:
            download_validate_save(row['id'], row['list_url'], list_manager, args)
            # sleep between list downloads
            time.sleep(1)
        list_manager.generate_all_combined_lists()
        reload_bind(bind)
    else:
        print('no lists found')

#-----combined lists can be generated on their own, or after all downloads are done-----
if args.generate_combined_list:
    count_args += 1
    print('\nGenerate Combined List: {}'.format(args.generate_combined_list))
    # param is a list_type
    list_entries = list_manager.generate_combined_list(args.generate_combined_list)

    #TEST: only reload bind if the arg is there
    if args.reload_bind:
        reload_bind(bind)

if args.generate_all_combined_lists:
    count_args += 1
    print('\nGenerate ALL Combined Lists')
    list_manager.generate_all_combined_lists()

    #TEST: only reload bind if the arg is there
    if args.reload_bind:
        reload_bind(bind)

if count_args==0:
    arg_parser.print_help()
