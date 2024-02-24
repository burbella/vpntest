#!/opt/zzz/venv/bin/python3

#-----build config files from templates-----

import argparse
import os
import site
import sys

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
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

#--------------------------------------------------------------------------------

# Examples:
#
# sudo /opt/zzz/python/bin/build-config.py --apache
#
# sudo /opt/zzz/python/bin/build-config.py --bind
#
# sudo /opt/zzz/python/bin/build-config.py --easyrsa
#
# sudo /opt/zzz/python/bin/build-config.py --openvpn-client
# sudo /opt/zzz/python/bin/build-config.py --openvpn-client -q
#
# sudo /opt/zzz/python/bin/build-config.py --openvpn-server -q
#
# sudo /opt/zzz/python/bin/build-config.py --openvpn-users
#
# sudo /opt/zzz/python/bin/build-config.py --redis
#
# sudo /opt/zzz/python/bin/build-config.py --squid -q
#
# sudo /opt/zzz/python/bin/build-config.py --tld

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='Zzz script to build config files from templates')
arg_parser.add_argument('--apache', dest='apache', action='store_true', help='build apache server configs')
arg_parser.add_argument('--bind', dest='bind', action='store_true', help='build BIND server configs')
arg_parser.add_argument('--easyrsa', dest='easyrsa', action='store_true', help='build easyrsa vars configs')
arg_parser.add_argument('--openvpn-client', dest='openvpn_client', action='store_true', help='build OpenVPN client configs')
arg_parser.add_argument('--openvpn-server', dest='openvpn_server', action='store_true', help='build OpenVPN server configs')
arg_parser.add_argument('--openvpn-users', dest='openvpn_users', action='store_true', help='list users, write users textfile')
arg_parser.add_argument('--redis', dest='redis', action='store_true', help='build redis server config')
arg_parser.add_argument('--squid', dest='squid', action='store_true', help='build squid server configs')
arg_parser.add_argument('--tld', dest='tld', action='store_true', help='update the TLD list in the DB')
arg_parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help='Quiet')
args = arg_parser.parse_args()

if not args.quiet:
    print('Zzz script to build config files from templates', flush=True)

db = zzzevpn.DB(ConfigData)
db.db_connect(ConfigData['DBFilePath']['Services'])

zzz_template = zzzevpn.ZzzTemplate(ConfigData, db)

count_args = 0

if args.apache:
    count_args += 1
    if not args.quiet:
        print('build apache server configs')
    zzz_template.make_apache_configs()

if args.bind:
    count_args += 1
    if not args.quiet:
        print('build bind server configs')
    settings = zzzevpn.Settings(ConfigData, db)
    settings.get_settings()
    should_block_tld_always = settings.is_setting_enabled('block_tld_always')
    should_block_country_tlds_always = settings.is_setting_enabled('block_country_tld_always')
    enable_test_server_dns_block = settings.is_setting_enabled('test_server_dns_block')
    zzz_template.make_bind_configs(should_block_tld_always, should_block_country_tlds_always, enable_test_server_dns_block)

if args.easyrsa:
    count_args += 1
    if not args.quiet:
        print('build EasyRSA vars configs')
    zzz_template.make_easyrsa_vars()

if args.openvpn_client:
    count_args += 1
    if not args.quiet:
        print('build OpenVPN client configs')
    zzz_template.make_openvpn_client_configs()

if args.openvpn_server:
    count_args += 1
    if not args.quiet:
        print('build OpenVPN server configs')
    zzz_template.make_openvpn_server_configs()

if args.openvpn_users:
    count_args += 1
    if not args.quiet:
        print('Users: {}'.format(', '.join(ConfigData['VPNusers'])))
        print('Servers: {}'.format(', '.join(zzz_template.openvpn_server_config.keys())))
    zzz_template.make_users_file()

if args.redis:
    count_args += 1
    if not args.quiet:
        print('build redis config')
    zzz_template.make_redis_config()

if args.squid:
    count_args += 1
    if not args.quiet:
        print('build squid server configs')
    zzz_template.make_squid_configs()

if args.tld:
    count_args += 1
    if not args.quiet:
        print('update TLD list in the DB')
    settings = zzzevpn.Settings(ConfigData, db)
    settings.get_settings()
    settings.update_tld_db()

if count_args==0:
    arg_parser.print_help()
    sys.exit()

if not args.quiet:
    print("Done", flush=True)

