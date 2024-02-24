#-----manage OpenVPN users-----

import os
import pprint

#-----package with all the Zzz modules-----
import zzzevpn

# VERIFY: compare user list in zzz.conf with user list in zzz_system(json)
#     list of cert files here:
#         /home/ubuntu/easyrsa3/pki-openvpn-int/issued/
#     report duplicates or invalid chars, exit with error
# ADD: list all zzz.conf users not found in zzz_system
#     check cert files dir to be sure
#     call add-user script
#         /opt/zzz/python/bin/subprocess/openvpn-add-user.sh
#             create new cert
#             make OVPN file for the user
# DELETE: list all zzz_system users not found in zzz.conf
#     check cert files dir to be sure
#     call delete-user script:
#         /opt/zzz/python/bin/subprocess/openvpn-delete-user.sh
#             revoke old cert
#         call add-user script
#     update CRL
#     install CRL
# update the users list in zzz_system to match zzz.conf

class UserManager:
    'Manage VPN Users'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    #TODO: remove settings? check if it is needed
    settings: zzzevpn.Settings = None
    
    # user lists
    users_in_conf = {}
    users_in_db = {}
    users_to_add = {}
    users_to_delete = {}
    
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
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    def init_vars(self):
        self.users_in_conf = {}
        self.users_in_db = {}
        self.users_to_add = {}
        self.users_to_delete = {}
    
    #--------------------------------------------------------------------------------
    
    #-----zzz.conf is assumed to have more recent data than the DB-----
    # calculate differences between zzz.conf and the DB
    def verify_users(self):
        self.init_vars()
        
        # user list in zzz.conf - should not be empty
        if not self.ConfigData['VPNusers']:
            print('ERROR: VPNusers list is empty in zzz.conf')
            return
        for username in self.ConfigData['VPNusers']:
            self.users_in_conf[username] = 1
        
        # user list in zzz_system(json) - should only be empty if this is initial setup
        zzz_system_info_parsed = self.db.get_zzz_system_info()
        json_parsed = zzz_system_info_parsed['json_parsed']
        if not json_parsed:
            # no json data found in DB, initialize it
            json_parsed = {}
        db_VPNusers = json_parsed.get('VPNusers', None)
        if not db_VPNusers:
            # no users found in DB, need to add every user from zzz.conf
            for username in self.users_in_conf.keys():
                self.users_to_add[username] = 1
            print('no users found in DB, adding all users from zzz.conf')
            return
        
        # compare users_in_db to users_in_conf
        # if not found in users_in_conf, needs to be DELETED from DB
        for username in db_VPNusers:
            self.users_in_db[username] = 1
            found_conf_username = self.users_in_conf.get(username, None)
            if not found_conf_username:
                self.users_to_delete[username] = 1
        
        # compare users_in_conf to users_in_db
        # if not found in users_in_db, needs to be ADDED to DB
        for username in self.users_in_conf.keys():
            found_db_username = self.users_in_db.get(username, None)
            if not found_db_username:
                self.users_to_add[username] = 1
    
    #--------------------------------------------------------------------------------
    
    def make_add_users_list(self):
        # remove old add-users file
        filepath_users_to_add = self.ConfigData['UpdateFile']['openvpn']['users_to_add']
        if os.path.exists(filepath_users_to_add):
            os.remove(filepath_users_to_add)
        
        if not self.users_to_add:
            print(f'no users to add')
            return
        
        pki_dir = self.ConfigData['Directory']['PKI']['OpenVPN']
        users_approved_to_add = []
        for username in self.users_to_add.keys():
            #-----check if the user key exists on the filesystem-----
            filepath = f'{pki_dir}/issued/{username}.crt'
            if os.path.exists(filepath):
                # skip this if the cert still exists
                # some other process needs to revoke it if it needs to be re-issued
                continue
            users_approved_to_add.append(username)
        
        if not users_approved_to_add:
            print(f'no users approved to add')
            return
        
        show_user_list = pprint.pformat(users_approved_to_add)
        print(f'Adding users: {show_user_list}')
        data_to_write = '\n'.join(users_approved_to_add) + '\n'
        with open(filepath_users_to_add, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------
    
    def make_delete_users_list(self):
        # remove old delete-users file
        filepath_users_to_delete = self.ConfigData['UpdateFile']['openvpn']['users_to_delete']
        if os.path.exists(filepath_users_to_delete):
            os.remove(filepath_users_to_delete)
        
        if not self.users_to_delete:
            print(f'no users to delete')
            return
        
        pki_dir = self.ConfigData['Directory']['PKI']['OpenVPN']
        users_approved_to_delete = []
        for username in self.users_to_delete.keys():
            #-----check if the user key exists on the filesystem-----
            filepath = f'{pki_dir}/issued/{username}.crt'
            if os.path.exists(filepath):
                # cert must exist to be deleted
                users_approved_to_delete.append(username)
        
        if not users_approved_to_delete:
            print(f'no users approved to delete')
            return
        
        show_user_list = pprint.pformat(users_approved_to_delete)
        print(f'Deleting users: {show_user_list}')
        data_to_write = '\n'.join(users_approved_to_delete) + '\n'
        with open(filepath_users_to_delete, 'w') as write_file:
            write_file.write(data_to_write)
    
    #--------------------------------------------------------------------------------
    
    def update_db_users_list(self):
        # no changes? no update needed
        if not (self.users_to_add or self.users_to_delete):
            print(f'no changes to user list')
            return
        
        zzz_system_info_parsed = self.db.get_zzz_system_info()
        json_parsed = zzz_system_info_parsed['json_parsed']
        if not json_parsed:
            # no json data found in DB, initialize it
            json_parsed = {}
        json_parsed['VPNusers'] = []
        for username in self.users_in_conf.keys():
            json_parsed['VPNusers'].append(username)
        if self.db.update_zzz_system_info_json(json_parsed):
            print('system info updated OK')
        else:
            print('ERROR: system info update failed')
    
    #--------------------------------------------------------------------------------
