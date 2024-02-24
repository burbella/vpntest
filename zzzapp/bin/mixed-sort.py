#!/opt/zzz/venv/bin/python3

# OLD: !/usr/bin/env python3

#-----sort strings with mixed numbers and letters (EX: 22a3, 22a17)-----

import site
import sys

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.Util

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()

util = zzzevpn.Util(ConfigData, None, False)

items = []
if not sys.stdin.isatty():
    items = sys.stdin.readlines()

if not items:
    sys.exit()

sortable_items = []
for item in items:
    clean_item = item.rstrip('\n').rstrip('\r')
    if clean_item:
        sortable_items.append(clean_item)

if sortable_items:
    sortable_items.sort(key=util.mixed_sort)
    for item in sortable_items:
        print(item)
