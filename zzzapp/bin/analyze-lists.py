#!/opt/zzz/venv/bin/python3

#-----analyze lists-----

import argparse
import getpass
import os
import site
import sys

#-----make sure we're running as root or www-data or exit-----
username = getpass.getuser()
if os.geteuid()!=0 and username!='www-data':
    sys.exit('This script must be run as root or www-data')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')
list_manager = zzzevpn.ListManager(ConfigData)

#--------------------------------------------------------------------------------

def diff_lists(args: argparse.Namespace, list_manager: zzzevpn.ListManager):
    print('Show List Differences')

    list1 = args.list1
    list2 = args.list2

    if not (list1 and list2):
        print('ERROR: diff requires --list1 and --list2')
        return

    print(f'List1: {list1}')
    list1_entries = list_manager.get_list_entries(list_name=list1)
    list1_length = len(list1_entries)
    if list1_entries:
        print(f'    length: {list1_length}')
    else:
        print('    ERROR: empty or non-existent list')

    print(f'List2: {list2}')
    list2_entries = list_manager.get_list_entries(list_name=list2)
    list2_length = len(list2_entries)
    if list2_entries:
        print(f'    length: {list2_length}')
    else:
        print('    ERROR: empty or non-existent list')

    if not (list1_entries and list2_entries):
        return

    diff_output = list_manager.util.diff_list(list1_entries, list2_entries)
    diff_output_length = len(diff_output)
    overlap = list1_length - diff_output_length
    print(f'List1 - List2: {diff_output_length} entries ({overlap} overlap)')
    print('\n'.join(diff_output))

#--------------------------------------------------------------------------------

def print_lists(args: argparse.Namespace, list_manager: zzzevpn.ListManager):
    print('Print the Contents of Lists')
    list_names = args.print_lists.split(',')
    if not list_names:
        print('ERROR: no list_names specified')
        return

    combined_list_entries = []
    for list_name in list_names:
        print(f'List: {list_name}')
        list_entries = list_manager.get_list_entries(list_name=list_name)
        if list_entries:
            print(f'    length: ' + str(len(list_entries)))
        else:
            print('    ERROR: empty or non-existent list')
            continue
        combined_list_entries.extend(list_entries)

    if not combined_list_entries:
        print('ERROR: no list data found')
        return
    unique_entries = list_manager.util.unique_sort(combined_list_entries, make_lowercase=True)
    print('Combined Unique Entries: ' + str(len(unique_entries)))
    print('-----')
    print('\n'.join(unique_entries))

#--------------------------------------------------------------------------------

def diff_user_dns_deny(list_manager: zzzevpn.ListManager):
    print('diff user-DNS-deny against all other dns-deny lists, except combined-DNS-deny')

    # get all list names except the combined-DNS-deny and user-DNS-deny
    sql = f'''
    select list_name
    from zzz_list
    where list_type='dns-deny' and list_name not in ('combined-DNS-deny', 'user-DNS-deny')
    '''
    params = ()
    (colnames, rows, rows_with_colnames) = list_manager.db.select_all(sql, params, skip_array=True)
    if not rows_with_colnames:
        print('ERROR: no active tables found')
        return

    # get all list contents and de-dupe
    combined_list_entries = []
    for row in rows_with_colnames:
        list_name = row['list_name']
        print(f'List: {list_name}')
        list_entries = list_manager.get_list_entries(list_name=list_name)
        if list_entries:
            print(f'    length: ' + str(len(list_entries)))
        else:
            print('    ERROR: empty or non-existent list')
            continue
        combined_list_entries.extend(list_entries)

    if not combined_list_entries:
        print('ERROR: no non-user list data found')
        return
    unique_entries = list_manager.util.unique_sort(combined_list_entries, make_lowercase=True)
    unique_entries_length = len(unique_entries)

    # get contents of user-DNS-deny
    user_entries = list_manager.get_list_entries(list_name='user-DNS-deny')
    user_entries_length = len(user_entries)

    # get the diff
    diff_output = list_manager.util.diff_list(user_entries, unique_entries)
    diff_output_length = len(diff_output)

    print(f'Non-User Entries: {unique_entries_length}')
    print(f'user entries: {user_entries_length}')
    print(f'diff entries: {diff_output_length}')
    print('-----')
    print('\n'.join(diff_output))

#--------------------------------------------------------------------------------

# show only items added by the user
def show_items_added(list_manager: zzzevpn.ListManager):
    print('Show Items Added by the User')

    # select count(*) from service_request where action='add_domains'
    # select count(*) from service_request where action='replace_domains'

    add_action = 'add_domains'
    replace_action = 'replace_domains'
    sql = '''select uf.file_data
            from service_request sr, update_file uf
            where sr.id=uf.service_request_id and sr.action=? and sr.status=?
            order by sr.id desc
    '''
    params = (add_action, list_manager.ConfigData['ServiceStatus']['Done'])
    (colnames, rows, rows_with_colnames) = list_manager.db.select_all(sql, params)
    if not rows_with_colnames:
        print('ERROR: no user-added items found')
        return

    combined_entries = []
    for row in rows_with_colnames:
        if not row['file_data']:
            continue
        entries = row['file_data'].strip().split('\n')
        if len(entries)>500:
            # leave out large (probably-downloaded) lists, only manual-added items are needed
            continue
        combined_entries.extend(entries)
    combined_entries = list_manager.util.unique_sort(combined_entries, make_lowercase=True)
    combined_entries_length = len(combined_entries)
    print(f'Total Entries: {combined_entries_length}')
    print('\n'.join(combined_entries))

#--------------------------------------------------------------------------------

process_filename = 'analyze-lists.py'
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
arg_parser.add_argument('--diff-lists', dest='diff_lists', action='store_true', help='show differences between 2 lists, requires --list1 and --list2')
arg_parser.add_argument('--list1', dest='list1', action='store', help='name of list1 in ListManager')
arg_parser.add_argument('--list2', dest='list2', action='store', help='name of list2 in ListManager')

arg_parser.add_argument('--diff-user-dns-deny', dest='diff_user_dns_deny', action='store_true', help='show differences between user-DNS-deny and all other dns-deny lists')
arg_parser.add_argument('--print-lists', dest='print_lists', action='store', help='print all the given lists, comma-separated list names')
arg_parser.add_argument('--show-items-added', dest='show_items_added', action='store_true', help='show user-added items')

args = arg_parser.parse_args()

count_args = 0

if args.diff_lists:
    count_args += 1
    diff_lists(args, list_manager)
elif args.diff_user_dns_deny:
    count_args += 1
    diff_user_dns_deny(list_manager)
elif args.print_lists:
    count_args += 1
    print_lists(args, list_manager)
elif args.show_items_added:
    count_args += 1
    show_items_added(list_manager)

if count_args==0:
    arg_parser.print_help()
