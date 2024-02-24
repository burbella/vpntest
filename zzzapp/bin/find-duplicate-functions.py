#!/opt/zzz/venv/bin/python3

#-----make sure there are no functions with duplicate names-----

import os
import re
import site
import sys

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

module_dir = '/opt/zzz/python/test/lib/zzzevpn'

regex_class_pattern = r'^\s*class '
regex_class = re.compile(regex_class_pattern, re.DOTALL | re.IGNORECASE)
regex_def_pattern = r'^\s*def (.+?)\('
regex_def = re.compile(regex_def_pattern, re.DOTALL | re.IGNORECASE)

#--------------------------------------------------------------------------------

def check_names_for_duplicates(filepath, names):
    if not names:
        return
    names.sort()
    last_name_seen = ''
    for name in names:
        if last_name_seen==name:
            print(f'Python file: {filepath}')
            print(f'Duplicate Function Name: {name}')
        last_name_seen = name

def check_file(filepath):
    names = []
    with open(filepath) as read_file:
        for line in read_file:
            match_def = regex_def.search(line)
            if match_def:
                names.append(match_def.group(1))
                continue
            match_class = regex_class.search(line)
            if match_class:
                # when a file has multiple classes, start the list over for each class
                check_names_for_duplicates(filepath, names)
                names = []
    # final check
    check_names_for_duplicates(filepath, names)

#--------------------------------------------------------------------------------

for entry in os.scandir(module_dir):
    #-----skip empty files-----
    if (not entry.is_file()) or (entry.stat().st_size==0):
        continue
    if entry.path.endswith('.py'):
        current_log_entry = entry
    check_file(entry.path)
