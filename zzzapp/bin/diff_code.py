#!/opt/zzz/venv/bin/python3

#-----run diffs between user src directories and installed src directories to do code review before installation-----
# use the -i option to install all code
# use the -f FILENAME option to install a single file

import argparse
import os
import site
import sys

#-----run at minimum priority-----
os.nice(19)

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
import zzzevpn.DiffCode

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

#---------------------------------------------------------------------------------------------------

#-----command-line arg -i installs the code-----
parser = argparse.ArgumentParser(description='Zzz code diff/installer')
parser.add_argument('-d', '--diffcode', dest='diffcode', action='store_true', help='use the new DiffCode module')
parser.add_argument('-i', '--install', dest='install', action='store_true', help='install the entire codebase')
parser.add_argument('-f', '--file-install', dest='file_install', help='install a single file')
parser.add_argument('-l', '--list-files', dest='list_files', action='store_true', help='list all files, including those with no differences')
args = parser.parse_args()

diff_code = zzzevpn.DiffCode.DiffCode(ConfigData)
diff_code.list_files = args.list_files

#-----file/directory checks-----
found_err = diff_code.file_directory_checks()
if found_err:
    quit()

if args.install:
    diff_code.install_codebase()
elif args.file_install is not None:
    diff_code.install_file(args.file_install)
elif args.diffcode:
    diff_code.run_diff_codebase(print_output=True)
else:
    diff_code.run_old_diff = True
    diff_code.run_diff_codebase(print_output=True)

