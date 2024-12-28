#-----find the latest versions for installed software-----
# OpenVPN - git package
#   REPOS_DIR/upgrade/upgrade-openvpn.sh
#
# Squid - github (easier)
#   REPOS_DIR/upgrade/upgrade-squid-github.sh
#
# Squid - web page parse
#   REPOS_DIR/upgrade/upgrade-squid.sh
#   http://www.squid-cache.org/Versions/
#   http://www.squid-cache.org/Versions/v4/
#   2/19/2019:
#       4.6 source:
#           http://www.squid-cache.org/Versions/v4/squid-4.6.tar.gz
#       4.6 signature:
#           http://www.squid-cache.org/Versions/v4/squid-4.6.tar.gz.asc#
#   Procedure:
#   1) Parse HTML for string: Current versions suitable for production use.
#   2) Directly below that string:
#        <table><tbody>
#        second <tr>
#        third <td>
#        EXAMPLE: <td>4.6</td>
#
# USAGE: call this from a cron daily
#        cron writes to textfile
#        display the textfile contents on the index page
#

import os
import pprint
import re
# import urllib.request

#-----import modules from the lib directory-----
import zzzevpn
# import zzzevpn.UpdateZzz

class CheckLatestVersion:
    'Check for the latest version of installed software'
    
    db = None
    ConfigData = None
    settings = None
    util = None
    
    regex_is_dev_version = re.compile(r'^\d+a.+')
    
    #-----flag for force-installing from the command line-----
    # this is used to manually run the installer when the auto-install flag is off
    install_zzz = False
    
    #-----constants-----
    EQUAL='EQUAL'
    GREATER='GREATER'
    LESS='LESS'
    
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
    
    #-----get the installed version of openvpn-----
    # Reference: REPOS_DIR/upgrade/upgrade-openvpn.sh
    def get_openvpn_versions(self):
        #-----bash commands-----
        # cd /home/ubuntu/src/openvpn
        # git fetch
        # OPENVPN_LATEST_STABLE_VERSION=`git tag|grep -v '_'|tail -1`
        # INSTALLED_VERSION=`openvpn --version | grep -P 'OpenVPN \d' | cut -d ' ' -f 2`
        # INSTALLED_VERSION="v$INSTALLED_VERSION"
        #
        #-----compare version numbers from installed vs. latest stable, report if a new one is available-----
        latest_version = None
        installed_version = None
        if self.util.run_script([self.ConfigData['Subprocess']['openvpn-latest-stable-version']]):
            latest_version = self.util.subprocess_output.stdout
        if latest_version is not None:
            latest_version = latest_version.rstrip()

        if self.util.run_script(['/usr/local/sbin/openvpn', '--version']):
            installed_version = self.parse_openvpn_version_output(self.util.subprocess_output.stdout)
        else:
            #-----for some reason, this generates a CalledProcessError on success, so parse the output looking for the version-----
            if self.util.script_output is not None:
                installed_version = self.parse_openvpn_version_output(self.util.script_output)
        if installed_version is not None:
            installed_version = installed_version.rstrip()

        versions = {
            'latest_version': latest_version,
            'latest_version_int': self.util.standalone.version_to_int(latest_version.lstrip('v')),
            'installed_version': installed_version,
            'installed_version_int': self.util.standalone.version_to_int(installed_version.lstrip('v')),
        }
        print('get_openvpn_versions()')
        pprint.pprint(versions)
        return versions
    
    #--------------------------------------------------------------------------------
    
    def parse_openvpn_version_output(self, openvpn_version_data):
        regex = r'OpenVPN (\d+\.\d+\.\d+)'
        regex_pattern = re.compile(regex, re.IGNORECASE)
        match = regex_pattern.search(openvpn_version_data)
        if match:
            # add a 'v' to match the github tags
            return 'v' + match[1]
        return None
    
    #--------------------------------------------------------------------------------
    
    #-----indicate if openvpn is running the latest version or not-----
    # this will be displayed on the Index page, so output HTML
    def update_openvpn_version_status(self):
        output = 'OpenVPN version check'
        openvpn_versions = self.get_openvpn_versions()
        if openvpn_versions['installed_version_int']==0 or openvpn_versions['latest_version_int']==0:
            output = 'ERROR checking OpenVPN:<br>\n'
            if openvpn_versions['installed_version_int']==0:
                output += '  failed to get installed version<br>\n'
            if openvpn_versions['latest_version_int']==0:
                output += '  failed to get latest version<br>\n'
            self.util.save_output(self.ConfigData['VersionFiles']['openvpn'], output)
            return
        
        openvpn_update_instructions = f'''<br>
Run in an SSH terminal:<br>
&gt; screen<br>
&gt; sudo /opt/zzz/upgrade/upgrade-openvpn.sh {openvpn_versions['latest_version']}<br>
<br>
OpenVPN client downloads:
<a href="https://openvpn.net/community-downloads/">https://openvpn.net/community-downloads/</a>
'''
        comparison_result = self.compare_versions(openvpn_versions['installed_version_int'], openvpn_versions['latest_version_int'])
        if comparison_result == self.EQUAL:
            output = f'''You have the latest OpenVPN version installed: {openvpn_versions['installed_version']}'''
        elif comparison_result == self.LESS:
            output = f'''
                <span class="text_red">
                A newer version of OpenVPN is available.<br>
                version installed: <b>{openvpn_versions['installed_version']}</b><br>
                latest version: <b>{openvpn_versions['latest_version']}</b><br>
                </span>
                {openvpn_update_instructions}
            '''
        else:
            #ERROR - should not be able to have a newer version installed than exists online
            output = 'ERROR: newer version of OpenVPN installed than online'
        self.util.save_output(self.ConfigData['VersionFiles']['openvpn'], output)
    
    #--------------------------------------------------------------------------------

    #-----get the installed version of squid-----
    # Reference: REPOS_DIR/upgrade/upgrade-squid.sh
    # do not allow major versions earlier than 4
    def get_squid_versions(self):
        #-----bash commands-----
        #/usr/sbin/squid
        #
        #-----compare version numbers from installed vs. latest stable, report if a new one is available-----
        latest_version = None
        if self.util.run_script([self.ConfigData['Subprocess']['squid-latest-stable-version']]):
            latest_version = self.util.subprocess_output.stdout
        if latest_version:
            # reduce it to numbers and dots
            latest_version = self.parse_squid_github_version(latest_version.rstrip())
        else:
            print('ERROR: latest version not found')
        
        installed_version = None
        installed_version_full = None
        if self.util.run_script(['/usr/sbin/squid', '-v']):
            installed_version_full = self.util.subprocess_output.stdout
        else:
            #-----for some reason, this generates a CalledProcessError on success, so parse the output looking for the version-----
            if self.util.script_output is not None:
                installed_version_full = self.util.script_output
        #-----reduce it to numbers and dots-----
        if installed_version_full:
            installed_version = self.parse_squid_version_output(installed_version_full.rstrip())

        latest_version = latest_version
        installed_version = installed_version
        versions = {
            'latest_version': latest_version,
            # 'latest_version_int': self.squid_version_to_int(latest_version.lstrip('SQUID_')),
            'latest_version_int': self.util.standalone.version_to_int(latest_version.lstrip('SQUID_')),
            'installed_version': installed_version,
            # 'installed_version_int': self.squid_version_to_int(installed_version),
            'installed_version_int': self.util.standalone.version_to_int(installed_version),
        }
        return versions
    
    #--------------------------------------------------------------------------------
    
    # github installed version: (command-line output from "squid -v")
    #   Squid Cache: Version 4.8-VCS
    #       returns: 4.8
    #   Squid Cache: Version 5.0.1-VCS
    #       returns: 5.0.1
    def parse_squid_version_output(self, squid_version_data):
        if not squid_version_data:
            return None
        
        regex_pattern = r'Version (\d+\.\d+(|\.\d+))'
        regex = re.compile(regex_pattern, re.IGNORECASE)
        match = regex.search(squid_version_data)
        if match:
            return match.group(1)
        
        return None
    
    # github tags examples:
    #   SQUID_4_0_1
    #   SQUID_4_1
    #   SQUID_4_10
    #   SQUID_5_0_1
    # pattern: "SQUID_major_minor_patch"
    #   patch is optional
    # returns:
    #   parsed_github: { 'complete': 'SQUID_4_0_1', 'parsed': '4.0.1' }
    def parse_squid_github_version(self, squid_github_tag):
        if not squid_github_tag:
            return None
        
        regex_pattern = r'^(SQUID\_)(\d+\_\d+(|\_\d+))$'
        regex = re.compile(regex_pattern, re.IGNORECASE)
        match = regex.match(squid_github_tag)
        if match:
            return '{}{}'.format(match.group(1), match.group(2))
        
        return None
    
    #--------------------------------------------------------------------------------
    
    #-----indicate if squid is running the latest version or not-----
    def update_squid_version_status(self):
        output = 'Squid version check'
        
        squid_versions = self.get_squid_versions()
        if squid_versions['installed_version'] is None or squid_versions['latest_version'] is None:
            output = 'ERROR checking Squid:\n'
            if squid_versions['installed_version'] is None:
                output += '  failed to get installed version\n'
            if squid_versions['latest_version'] is None:
                output += '  failed to get latest version\n'
            self.util.save_output(self.ConfigData['VersionFiles']['squid'], output)
            return
        
        squid_update_instructions = '''
Run in an SSH terminal:
> screen
> sudo /opt/zzz/upgrade/upgrade-squid-github.sh
'''
        comparison_result = self.compare_versions(squid_versions['installed_version_int'], squid_versions['latest_version_int'])
        if comparison_result == self.EQUAL:
            output = f'''You have the latest Squid version installed: {squid_versions['installed_version']}'''
        elif comparison_result == self.LESS:
            output = f'''A newer version of Squid is available.  version installed: {squid_versions['installed_version']}, latest version: {squid_versions['latest_version']}{squid_update_instructions}'''
        else:
            #ERROR - should not be able to have a newer version installed than exists online
            output = 'ERROR: newer version of Squid installed than online'
        
        self.util.save_output(self.ConfigData['VersionFiles']['squid'], output)
    
    #--------------------------------------------------------------------------------
    
    def get_zzz_versions(self, new_version_format=False):
        latest_version_list = None
        
        #OLD
        get_version_cmd = [self.ConfigData['Subprocess']['zzz-latest-stable-version']]
        if new_version_format:
            #NEW
            get_version_cmd = [self.ConfigData['Subprocess']['zzz-list-versions']]
        
        if self.settings.is_setting_enabled('show_dev_tools'):
            #-----include alpha versions if dev tools are enabled in settings-----
            get_version_cmd.append('--dev')
        if self.util.run_script(get_version_cmd):
            latest_version_list = self.util.subprocess_output.stdout.split('\n')
        if latest_version_list:
            latest_version = latest_version_list[0]
        
        #-----Zzz System version is in the DB-----
        db_version = self.util.zzz_version()
        
        versions = {
            # 'latest_version': latest_version.rstrip(),
            'latest_version': latest_version,
            'latest_version_list': latest_version_list,
            'installed_version': str(db_version['version']),
            'dev_version': db_version['dev_version'],
        }
        return versions
    
    #--------------------------------------------------------------------------------
    
    #-----indicate if the Zzz System is running the latest version or not-----
    # this will only be called by cron
    #   check_zzz_update
    #   auto_install_zzz_update
    #   /opt/zzz/apache/zzz_version_check.txt
    # called_by_cron is True when calling this function from the cron
    def update_zzz_version_status(self, called_by_cron=False):
        output = 'Zzz System version check\n\n'
        do_auto_update = False
        
        zzz_versions = self.get_zzz_versions()
        
        #-----compare version numbers from installed vs. latest stable, report if a new one is available-----
        comparison_result = self.compare_versions(zzz_versions['installed_version'], zzz_versions['latest_version'])
        if comparison_result == self.EQUAL:
            output = f'''You have the latest Zzz System version installed: {zzz_versions['installed_version']}'''
        elif comparison_result == self.LESS:
            #-----store a note in the status file, which displays on the Index page-----
            output = f'''<span class="text_red"><b>A newer version of Zzz System is available.</b></span><br>
            version installed: <b>{zzz_versions['installed_version']}</b><br>
            latest version: <b>{zzz_versions['latest_version']}</b>'''
            #-----automatically queue the upgrade request if the Settings box is checked-----
            if self.settings.is_setting_enabled('auto_install_zzz_update') and called_by_cron:
                do_auto_update = True
        else:
            # should only have a newer-than-latest version installed if it is a dev version
            # it should be exactly one version higher than the latest prod version
            if zzz_versions['dev_version']:
                output = f'''<span class="text_red"><b>dev version {zzz_versions['dev_version']} installed</b></span>'''
            else:
                output = 'ERROR: newer version of Zzz System installed than online'
        
        #-----save the latest version to the DB-----
        self.update_available_version(zzz_versions['latest_version'])
        
        #-----log the output-----
        self.util.save_output(self.ConfigData['VersionFiles']['zzz'], output)
        
        #-----cron can run this automatically-----
        # user must pass a param into the command line to run the install: -i
        output = 'update_zzz_version_status()\n'
        if do_auto_update:
            output = 'Auto-Install is enabled\n'
        if self.install_zzz:
            #-----don't mention auto-install here, since we are overriding it with the -i command-line option-----
            output = 'Force-Install from command line'
        
        if do_auto_update or self.install_zzz:
            #-----queue a request to upgrade-----
            update_zzz = zzzevpn.UpdateZzz(self.ConfigData)
            output += update_zzz.request_zzz_update('queue_upgrades')
        elif not called_by_cron:
            if self.settings.is_setting_enabled('auto_install_zzz_update'):
                output = 'Manual Version Check, not doing auto-install\n'
        else:
            output = 'Auto-Install is disabled, returning\n'
        
        self.util.append_output(self.ConfigData['UpdateFile']['zzz']['upgrade_log'], output)
        return output
    
    #--------------------------------------------------------------------------------
    
    #-----version number must be an integer for production, zero is for testing-----
    # dev versions match a pattern
    def checkout_version(self, version_to_install):
        checkout_filepath = self.ConfigData['Subprocess']['git-checkout']
        if self.util.is_int(version_to_install):
            return self.util.run_script(['sudo', '-H', '-u', 'ubuntu', checkout_filepath, str(version_to_install)])
        
        if self.is_dev_version(version_to_install):
            return self.util.run_script(['sudo', '-H', '-u', 'ubuntu', checkout_filepath, str(version_to_install)])
        
        #-----not a prod or dev version, it's an error-----
        return False
    
    # 10 --> 11
    def increment_stable_version(self, version):
        version += 1
        return version
    
    # 11a1 --> 11a2
    def increment_dev_version(self, version, max_version):
        pass
    
    def is_dev_version(self, version):
        match = self.regex_is_dev_version.match(version)
        if match:
            return True
        return False
    
    #-----increment until we get to max_version-----
    def increment_version(self, version, max_version):
        if self.is_dev_version(version):
            return self.increment_dev_version(version)
        return self.increment_stable_version(version)
    
    #-----list all versions needed to get from "version" to "max_version"-----
    # for now, always keep upgrading until we get to the latest version
    # separate branches for stable(main) and dev
    #   
    # when to skip dev versions:
    #   if dev is disabled
    #   if current version is production and the next increment production version is available
    # getting from version 10 to 12:
    #   10 --> 11
    #   11 --> 12
    # getting from version 11a1 to 11a3:
    #   11a1 --> 11a2
    #   11a2 --> 11a3
    # getting from version 10 to 12a2:
    #   10 --> 11
    #   11 --> 12a1
    #   12a1 --> 12a2
    # getting from version 11a1 to 12:
    #   11a1 --> 11a2
    #   11a2 --> 11
    #   11 --> 12
    def list_versions_needed(self, version, max_version):
        pass
    
    #TODO: finish this
    #-----just one script-----
    # the upgrade should should be current_version --> next version
    # also store dev_version in zzz_system
    # to revert the system back to production:
    #   manually undo any changes not compatible with the production version (such as DB schema changes)
    #   clear the dev version from the zzz_system table:
    #       update zzz_system set dev_version=null;
    #   manually checkout the production version and install it
    #
    # this is a combination of CheckLatestVersion.queue_each_upgrade_script() and ServiceRequest.upgrade_zzz() ?
    def dev_upgrade(self, dev_upgrade_details=None):
        if not dev_upgrade_details:
            upgrade_details = { 'status': 'error', 'output': 'ERROR: no dev version specified', }
            return upgrade_details
        
        #-----checkout the version we want to run for installation-----
        if not self.checkout_version(dev_upgrade_details):
            upgrade_details = { 'status': 'error', 'output': f'ERROR: checkout failed for version {dev_upgrade_details}', }
            return upgrade_details
        
        update_zzz = zzzevpn.UpdateZzz(self.ConfigData, self.db, self.util, self.settings)
        
        #-----make sure the upgrade script exists in the checkout-----
        # dev_upgrade_details = 18a1 --> 18
        # prev_version = 17
        # upgrade_script = 'upgrade-zzz_17_18.sh'
        prev_version = update_zzz.calc_required_version(dev_upgrade_details)
        version_to_install = prev_version + 1
        upgrade_script = f'upgrade-zzz_{prev_version}_{version_to_install}.sh'
        script_filepath = self.ConfigData['Directory']['UpgradeScript'] + '/' + upgrade_script
        
        if not os.path.exists(script_filepath):
            upgrade_details = { 'status': 'error', 'output': f'ERROR: for dev_upgrade {dev_upgrade_details}, upgrade script not found: {script_filepath}', }
            return upgrade_details
        
        #-----insert the dev version tag in the DB (the upgrade script will update the zzz_system version field)-----
        sql = 'update zzz_system set dev_version=?'
        params = (dev_upgrade_details,)
        self.db.query_exec(sql, params)
        
        db_version = self.util.zzz_version()
        upgrade_details = {
            'installed_version': db_version['version'],
            'upgrading_to_version': dev_upgrade_details,
            'script_filepath': script_filepath,
            'output': '',
            'status': 'success',
        }
        return upgrade_details
    
    def queue_each_upgrade_script(self):
        # too many hyphens in variables break F-string compiling in some editors?  '-----\n' fails?
        # output = '--------------------------------------------------------------------------------\n'
        datetime_now = self.util.current_datetime()
        output = f'Zzz System Auto-Install {datetime_now}\n\n'
        
        #-----get version info from the DB-----
        db_version = self.util.zzz_version()
        zzz_versions = {
            'installed_version': db_version['version'],
            'latest_version': db_version['available_version']
        }
        if not self.util.is_int(zzz_versions['installed_version']):
            output += 'ERROR: installed_version is not a number\n'
            return output
        if not self.util.is_int(zzz_versions['latest_version']):
            output += 'ERROR: latest_version is not a number\n'
            return output
        
        #-----figure out how many versions back we are-----
        # install code by running the necessary updater scripts in version order
        # EX: we have version 3 installed, the latest version is 6
        #     1) run update_3_4
        #           REPOS_DIR/upgrade/zzz/update_3_4.sh
        #     2) run update_4_5
        #     3) run update_5_6
        installed_version = int(zzz_versions['installed_version'])
        latest_version = int(zzz_versions['latest_version'])
        if latest_version<=installed_version:
            output += f'ERROR: latest_version({latest_version}) is not greater than installed_version({installed_version})\n'
            return output
        
        prev_version = installed_version
        for version_to_install in range(installed_version+1, latest_version+1):
            output += f'installing version {version_to_install}\n'
            scriptname = f'upgrade-zzz_{prev_version}_{version_to_install}.sh'
            script_filepath = self.ConfigData['Directory']['UpgradeScript'] + '/' + scriptname
            
            #-----checkout the version we want to queue for installation-----
            if not self.checkout_version(version_to_install):
                output += self.util.script_output
                break
            
            #-----stop the upgrades as soon as one file is not available (previous upgrades will go through)-----
            if not os.path.exists(script_filepath):
                output += f'upgrade script not found: {script_filepath}\nskipping further upgrades\n'
                break
            
            output += f'queuing upgrade script: {script_filepath}\n'
            
            #-----queue a series of status=Requested entries in the DB-----
            #   service_name='zzz', action='upgrade', details='upgrade-zzz_{prev_version}_{version_to_install}.sh'
            self.queue_upgrade(scriptname)
            prev_version += 1
        
        #-----tell the daemon to start working-----
        self.util.work_available(1)
        
        return output
    
    #--------------------------------------------------------------------------------
    
    def queue_upgrade(self, details):
        self.db.insert_service_request('zzz', 'upgrade', details)
    
    #--------------------------------------------------------------------------------
    
    #-----set the latest available version in the DB-----
    def update_available_version(self, available_version):
        sql = "update zzz_system set available_version=?"
        params = (available_version,)
        self.db.query_exec(sql, params)
    
    #--------------------------------------------------------------------------------
    
    #-----report if v1==v2, v1>v2, or v1<v2-----
    # returns: EQUAL, LESS, GREATER
    def compare_versions(self, v1, v2):
        v1 = str(v1)
        v2 = str(v2)
        if self.util.is_int(v1) and self.util.is_int(v2):
            v1=int(v1)
            v2=int(v2)
        if v1==v2:
            return self.EQUAL
        elif v1>v2:
            return self.GREATER
        return self.LESS
    
    #--------------------------------------------------------------------------------
    
    #TODO: finish this
    #-----download a given webpage-----
    # returns: HTTP status
    #          string containing HTML from the website
    # http://www.squid-cache.org/Versions/
    # http://www.squid-cache.org/Versions/v4/
    # http://www.squid-cache.org/Versions/v4/squid-4.9.tar.gz
    def download_webpage(self, url):
        # f = urllib.request.urlopen('http://www.squid-cache.org/Versions/')
        # main_page_data = f.read().decode('utf-8')
        # parser = zzzevpn.ZzzHTMLParser.ZzzHTMLParser()
        # parser.feed(main_page_data)
        pass
    
    #--------------------------------------------------------------------------------
