#-----DiffCode Module-----
# for checking code differences between the repos and installed code

import difflib
import os
import subprocess

#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.Config

class DiffCode:
    'DiffCode'
    
    ConfigData = None
    
    list_files = False
    run_old_diff = False
    service_name = 'diff_code'
    underscore80 = '_'*80
    
    src_basedir = ''
    python_src_dir = '/zzzapp'
    python_install_dir = '/opt/zzz/python'
    www_src_dir = '/zzzapp/www'
    www_install_dir = '/var/www'
    upgrade_install_dir = '/opt/zzz/upgrade'
    util_install_dir = '/opt/zzz/util'
    zzz_installer_dir = '/opt/zzz/install'
    data_dir = '/opt/zzz/data'
    config_dir = '/opt/zzz/config'
    
    python_src_bin = ''
    python_src_lib = ''
    www_src_html = ''
    www_src_css = ''
    www_src_js = ''
    
    user_bin = ''
    python_install_bin = ''
    python_install_bin_subprocess = ''
    python_install_lib = ''
    python_package_install_lib = ''
    python_test_dir = ''
    templates_install_dir = ''
    www_install_html = ''
    www_install_css = ''
    www_install_js = ''
    wsgi_install_scripts = ''

    errors_found = ''
    diffcode_outputs = []

    executable_dirs = []
    recursive_dir = {}
    source_dir = {}
    source_code = {}
    
    def __init__(self, ConfigData: dict=None):
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
        self.init_vars()
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        self.src_basedir = self.ConfigData['Directory']['Repos']
        self.errors_found = ''
        self.diffcode_outputs = []
        
        self.python_src_bin = self.python_src_dir + '/bin'
        self.python_src_lib = self.python_src_dir + '/lib'
        self.www_src_html = self.www_src_dir + '/html'
        self.www_src_css = self.www_src_dir + '/css'
        self.www_src_js = self.www_src_dir + '/js'
        
        self.user_bin = self.ConfigData['Directory']['LinuxUser'] + '/bin'
        self.python_install_bin = self.python_install_dir + '/bin'
        self.python_install_bin_subprocess = self.python_install_dir + '/bin/subprocess'
        self.python_install_lib = self.python_install_dir + '/lib'
        self.python_package_install_lib = self.python_install_dir + '/lib/zzzevpn'
        self.python_test_dir = self.python_install_dir + '/test'
        self.templates_install_dir = self.python_install_dir + '/templates'
        self.www_install_html = self.www_install_dir + '/html'
        self.www_install_css = self.www_install_html + '/css'
        self.www_install_js = self.www_install_html + '/js'
        self.wsgi_install_scripts = self.www_install_dir + '/wsgi'
        
        self.executable_dirs = [self.python_install_bin, self.python_install_bin_subprocess, self.user_bin, self.upgrade_install_dir, self.util_install_dir, self.zzz_installer_dir]

        #-----list of recursive-scan directories-----
        self.recursive_dir = {
            self.config_dir: '/config',
        }

        #-----list of directories-----
        # all files in directory will be installed
        # dst dir --> src dir (assumes REPOS_DIR)
        self.source_dir = {
            self.python_install_bin: '/zzzapp/bin/',
            self.python_install_bin_subprocess: '/zzzapp/bin/subprocess/',
            self.python_install_lib: '/zzzapp/lib/',
            self.python_package_install_lib: '/zzzapp/lib/zzzevpn',
            self.python_test_dir: '/zzzapp/test',
            self.templates_install_dir: '/zzzapp/templates',
            self.upgrade_install_dir: '/upgrade',
            self.util_install_dir: '/zzzapp/bash',
            self.user_bin: '/bin',
            self.www_install_css: '/zzzapp/www/html/css/',
            self.www_install_js: '/zzzapp/www/html/js/',
            self.zzz_installer_dir: '/install',
        }
        
        #-----list of files-----
        # dst dir --> list of files to install into that dir (must be relative paths to files from REPOS_DIR)
        self.source_code = {
            # self.data_dir: [
            #     '/install/TLD-list.txt',
            #     ],
            self.www_install_html: [
                '/zzzapp/www/html/index.htm',
                '/zzzapp/www/html/zzz.webmanifest',
                '/zzzapp/www/html/serviceworker.js',
                '/zzzapp/www/html/serviceworker-register.js',
                ],
            self.wsgi_install_scripts:[
                #-----all HTTPS requests pass through the WSGI service here-----
                '/zzzapp/www/wsgi/zzz.wsgi',
                ],
            
            #TEST - verify that the file/directory checks work
            # '/dir_does_not_exist': [ '/file_does_not_exist' ],
            # src_basedir + '/www/html/test': [ '/.' ],
        }
    
    #--------------------------------------------------------------------------------
    
    #-----run the code diff-----
    def run_diff(self):
        pass
    
    #--------------------------------------------------------------------------------
    
    def show_err(self, err):
        print("ERROR: ", err)
        self.errors_found += f'{err}\n'
    
    #--------------------------------------------------------------------------------
    
    def file_directory_checks(self):
        found_err = False
        for dst_dir in sorted(self.source_code.keys()):
            if not os.path.exists(dst_dir):
                self.show_err('"{}" directory does not exist'.format(dst_dir))
                found_err = True
            elif not os.path.isdir(dst_dir):
                self.show_err('"{}" is not a directory'.format(dst_dir))
                found_err = True
            for src_file in sorted(self.source_code[dst_dir]):
                src_filepath = self.src_basedir + src_file
                if not os.path.exists(src_filepath):
                    #-----print warning, but don't exit-----
                    self.show_err('"{}" file does not exist'.format(src_filepath))
                elif not os.path.isfile(src_filepath):
                    self.show_err('"{}" is not a file'.format(src_filepath))
                    found_err = True
        return found_err
    
    #--------------------------------------------------------------------------------
    
    def make_dst_file(self, src_filepath: str, dst_dir: str):
        filename = os.path.basename(src_filepath)
        return dst_dir + '/' + filename
    
    #--------------------------------------------------------------------------------
    
    def show_diff_info(self, src_filepath: str, dst_file: str):
        diff_print = f'{self.underscore80}\ndiff {src_filepath} {dst_file}'
        return diff_print
    
    #--------------------------------------------------------------------------------
    
    def get_file(self, filepath: str):
        file_data = ''
        with open(filepath, 'r') as read_file:
            file_data = read_file.readlines()
        return file_data
    
    #--------------------------------------------------------------------------------
    
    # old-style diff on command-line
    def run_diff_file_command_line(self, src_filepath: str, dst_file: str, recursive_dir: bool=False):
        diff_print = self.show_diff_info(src_filepath, dst_file)
        output_str = ''
        script_command = ['diff', src_filepath, dst_file]
        if recursive_dir:
            script_command = ['diff', '-r', src_filepath, dst_file]

        try:
            if self.list_files:
                self.diffcode_outputs.append(diff_print)
            output = subprocess.run(script_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, universal_newlines=True)
            if output.stdout or output.stderr:
                output_str = str(output.stdout + output.stderr)
        except subprocess.CalledProcessError as e:
            self.diffcode_outputs.append(diff_print)
            if e.returncode==1:
                #-----diff throws error code 1 when there are file differences-----
                return e.output
            else:
               raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
        return output_str
    
    #TEST: minor file edits
    # sudo cp REPOS_DIR/zzzapp/lib/zzzevpn/DiffCode.py /opt/zzz/python/lib/zzzevpn/
    # diff REPOS_DIR/zzzapp/lib/zzzevpn/BIND.py /opt/zzz/python/lib/zzzevpn/
    # 4,7d3
    # < #TEST1
    # < #test2
    # < #test3
    # < 
    # 17c13
    # < #-----2import modules from the lib directory-----
    # ---
    # > #-----import modules from the lib directory-----
    def run_diff_file(self, src_filepath: str, dst_file: str):
        diff_print = self.show_diff_info(src_filepath, dst_file)
        diff_text = ''
        try:
            if self.list_files:
                self.diffcode_outputs.append(diff_print)
            src_data = self.get_file(src_filepath)
            dst_data = self.get_file(dst_file)
            # difflib_output = difflib.unified_diff(src_data, dst_data)
            difflib_output = difflib.context_diff(src_data, dst_data)
            # difflib_output = difflib.ndiff(src_data.replace('\r', ''), dst_data.replace('\r', ''))
            diff_text = ''.join(list(difflib_output))
        except Exception as e:
            self.diffcode_outputs.append(f'{diff_print}\nERROR running diff module on files: {src_filepath} {dst_file}')
        return diff_text
    
    #--------------------------------------------------------------------------------
    
    #-----upgrade diff_code.py and DiffCode.py first to avoid errors and crashes-----
    def check_diff_code(self, src_filepath: str, diff_text: str=''):
        src_file = src_filepath.rsplit('/', maxsplit=1)[1]
        if (src_file=='diff_code.py' or src_file=='DiffCode.py') and diff_text:
            self.diffcode_outputs.append('*****diff_code NEEDS AN UPGRADE (run the installer again after upgrade)*****')
    
    #--------------------------------------------------------------------------------
    
    def should_skip_file(self, filepath: str):
        if filepath.endswith('README') or filepath.endswith('.sql'):
            return True
        return False
    
    def run_diff_src_dst(self, src_filepath: str, dst_dir: str):
        dst_file = self.make_dst_file(src_filepath, dst_dir)
        diff_print = self.show_diff_info(src_filepath, dst_file)
        if not os.path.exists(src_filepath):
            self.diffcode_outputs.append("{}\n\tSRC File Not Found: {}".format(diff_print, src_filepath))
            return
        if not os.path.exists(dst_file):
            #-----skip files that will not be installed-----
            if not self.should_skip_file(dst_file):
                self.diffcode_outputs.append("{}\n\tNEW file: {}".format(diff_print, dst_file))
            return
        
        diff_text = ''
        if self.run_old_diff:
            # OLD - calls linux diff on command line
            diff_text = self.run_diff_file_command_line(src_filepath, dst_file)
        else:
            # NEW - uses diff module
            diff_text = self.run_diff_file(src_filepath, dst_file)
        
        self.check_diff_code(src_filepath, diff_text)
        if diff_text:
            self.diffcode_outputs.append(diff_text)

    #--------------------------------------------------------------------------------

    def run_diff_recursive(self, src_dir: str, dst_dir: str, level: int=0, total_files: int=0):
        if self.run_old_diff:
            diff_print = self.show_diff_info(src_dir, dst_dir)
            if not os.path.exists(src_dir):
                self.diffcode_outputs.append("{}\n\tSRC Directory Not Found: {}".format(diff_print, src_dir))
                return
            if not os.path.exists(dst_dir):
                self.diffcode_outputs.append("{}\n\tNEW directory: {}".format(diff_print, dst_dir))
                return
            diff_text = self.run_diff_file_command_line(src_dir, dst_dir, recursive_dir=True)
            if diff_text:
                self.diffcode_outputs.append(diff_text)
            return

        #TEST
        print(f'recursive diff: level={level}, total_files={total_files}\n    src_dir={src_dir}\n    dst_dir={dst_dir}')
        #ENDTEST
        if level>4 or total_files>10000:
            #TEST
            print('returning early due to level/files limit')
            #ENDTEST
            # limit recursion to 5 directory levels and 10,000 files
            return total_files
        for entry in os.scandir(src_dir):
            if entry.is_dir():
                total_files = self.run_diff_recursive(entry.path, f'{dst_dir}/{entry.name}', level+1, total_files)
            if entry.is_file():
                self.run_diff_src_dst(entry.path, dst_dir)
                total_files += 1
        return total_files

    #--------------------------------------------------------------------------------

    #-----print the diffs-----
    # An exit status of 0 means no differences were found, 1 means some differences were found, and 2 means trouble.
    # Normally, differing binary files count as trouble, but this can be altered by using the -a or --text option, or the -q or --brief option.
    def run_diff_codebase(self, print_output: bool=False):
        for dst_dir in sorted(self.recursive_dir.keys()):
            src_dir = self.src_basedir + self.recursive_dir[dst_dir]
            self.run_diff_recursive(src_dir, dst_dir)
        for dst_dir in sorted(self.source_dir.keys()):
            src_dir = self.src_basedir + self.source_dir[dst_dir]
            for entry in os.scandir(src_dir):
                if entry.is_file():
                    self.run_diff_src_dst(entry.path, dst_dir)
        for dst_dir in sorted(self.source_code.keys()):
            for src_file in sorted(self.source_code[dst_dir]):
                src_filepath = self.src_basedir + src_file
                self.run_diff_src_dst(src_filepath, dst_dir)
        if print_output:
            print('\n'.join(self.diffcode_outputs))
    
    #--------------------------------------------------------------------------------
    
    def check_if_running_as_root(self):
        uid = os.geteuid()
        if uid>0:
            print('ERROR: must run code install as root')
            quit()
    
    #--------------------------------------------------------------------------------
    
    #TODO: remove this
    # def install_src_dst(self, src_filepath, dst_dir):
    #     if not os.path.exists(src_filepath):
    #         print("SRC File Not Found: {}".format(src_filepath))
    #         return
    #     print('cp ' + src_filepath + ' ' + dst_dir)
    #     try:
    #         output = subprocess.run(['cp', src_filepath, dst_dir], stdout=subprocess.PIPE, check=True, universal_newlines=True)
    #     except subprocess.CalledProcessError as e:
    #         raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
    #     #-----make sure execute permissions get set for python bin file installations-----
    #     if dst_dir in self.executable_dirs:
    #         dst_file = dst_dir + '/' + os.path.basename(src_filepath)
    #         os.chmod(dst_file, 0o755)
    
    #--------------------------------------------------------------------------------
    
    #TODO: remove this
    def install_codebase(self):
        print('run this to install codebase: /opt/zzz/python/bin/subprocess/zzz-app-update.sh')
        return
        
        # self.check_if_running_as_root()
        # print('installing codebase')
        # for dst_dir in sorted(self.source_dir.keys()):
        #     src_dir = self.src_basedir + self.source_dir[dst_dir]
        #     for entry in os.scandir(src_dir):
        #         if entry.is_file():
        #             self.install_src_dst(entry.path, dst_dir)
        # for dst_dir in sorted(self.source_code.keys()):
        #     for src_file in sorted(self.source_code[dst_dir]):
        #         src_filepath = self.src_basedir + src_file
        #         self.install_src_dst(src_filepath, dst_dir)
        # print('Done')
    
    #--------------------------------------------------------------------------------
    
    # not sure if this is needed
    def install_file(self, filepath: str):
        self.check_if_running_as_root()
        print('file to install: {}'.format(filepath))
    
    #--------------------------------------------------------------------------------
    
    #-----python compile testing-----
    #TODO: finish this
    def compile_python(self, filepath: str):
        # "python3 -m py_compile" + filepath
        pass
    
    #--------------------------------------------------------------------------------

