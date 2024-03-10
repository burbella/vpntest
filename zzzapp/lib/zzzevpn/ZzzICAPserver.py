#-----Zzz ICAP Server-----
# used by squid to process web data

import brotli
import gzip
import importlib.util
import magic
import os
import pprint
import re
# python 2: SocketServer (outdated, do not use)
# python 3: socketserver
import socketserver
import sys
import threading
import time
import zlib

from pyicap import *

#-----import modules from the lib directory-----
#-----package with all the Zzz modules-----
import zzzevpn
# import zzzevpn.ZzzICAPsettings
# import zzzevpn.ZzzRedis

#--------------------------------------------------------------------------------

# in the handler, access vars this way: self.server.ZzzFeatures.zzz_SettingsData
class ZzzFeatures:
    # thread-safe items only? nothing with a DB object in it
    ConfigData: dict = None
    zzz_SettingsData: dict = None
    zzz_redis: zzzevpn.ZzzRedis = None
    custom_icap = None

    def __init__(self):
        pass

#--------------------------------------------------------------------------------

class ZzzExtendedICAPServer(ICAPServer):
    #TEST - since this extends an existing class, avoid var name collisions
    zzz_ConfigData = 'ZzzExtendedICAPServer config'
    zzz_SettingsData = 'ZzzExtendedICAPServer settings'

#--------------------------------------------------------------------------------

#-----threaded server processing starts here-----
class ZzzICAPthreading(socketserver.ThreadingMixIn, ZzzExtendedICAPServer):
    ZzzFeatures = None
    def __init__(self, host_port, zzz_handler, ZzzFeatures):
        super().__init__(host_port, zzz_handler)
        self.ZzzFeatures = ZzzFeatures

#--------------------------------------------------------------------------------

#TODO: connect to DB here, because sqlite DB handles are not safe to pass between threads
class ICAPHandler(BaseICAPRequestHandler):
    
    body = b''
    content_encoding = ''
    content_length = 0
    content_type = ''
    
    # decoded from UTF-8?
    host_header = ''
    host = ''
    
    # ICAP headers
    zzz_host = ''
    
    use_utf8 = False
    length_limit = 4*1024*1024
    unsupported_http_types = [b'NONE']
    settings_last_update = 0

    #-----zzzevpn objects-----
    # db = None
    icap_settings: zzzevpn.ZzzICAPsettings = None
    zzz_redis: zzzevpn.ZzzRedis = None
    
    #TEST
    DEBUG = True
    
    ##################################################
    content_types_to_skip = [
        'audio/mpeg',
        'application/octet-stream',
        'application/pdf',
        'binary/octet-stream',
        'text/css',
    ]
    headers_to_skip = {
        # app security keys, etc. - safer not to log it
        'authorization': 1,
        'cookie': 1,
        'set-cookie': 1,
    }
    
    #TODO: get this list from SettingsData or icap_settings?
    request_types_to_block = {
        '.ts': [ b'example.zzz.zzz', ],
    }
    
    #-----regexes (replace with an array of regexes)-----
    regex_content_type = r'^(application/font|font|image|video)'
    regex_content_type_pattern = re.compile(regex_content_type, re.IGNORECASE)
    
    ##################################################

    #TODO: find custom script referenced in Config?
    # self.server.ZzzFeatures.ConfigData['icap_custom_module']
    def load_custom_module(self, icap_settings: zzzevpn.ZzzICAPsettings, module_filename: str):
        custom_module_dir: str = '/opt/zzz/python/lib/custom'
        custom_module_filepath = f'{custom_module_dir}/{module_filename}'
        spec = None
        custom_module = None
        if not os.path.exists(custom_module_filepath):
            #TODO: log the error
            # icap_settings.util.log_stderr(f'file not found: {custom_module_filepath}')
            return None

        try:
            spec = importlib.util.spec_from_file_location('custom_module', custom_module_filepath)
        except:
            #TODO: log the error
            icap_settings.util.log_stderr('ERROR: spec_from_file_location() failed')
            return None

        try:
            custom_module = importlib.util.module_from_spec(spec)
        except:
            #TODO: log the error
            icap_settings.util.log_stderr('ERROR: module_from_spec() failed')
            return None

        try:
            spec.loader.exec_module(custom_module)
        except:
            #TODO: log the error
            icap_settings.util.log_stderr('ERROR: exec_module() failed')
            return None

        # success
        return custom_module.CustomICAP(icap_settings)

    #TODO: last_lookup_time var to prevent checking the redis server more than once a second
    #-----update local var from thread settings-----
    def zzz_get_icap_settings(self):
        time_now = time.time()
        if (time_now-self.settings_last_update)<1:
            return
        self.settings_last_update = time_now
        if not self.zzz_redis:
            self.zzz_redis = zzzevpn.ZzzRedis(self.server.ZzzFeatures.ConfigData)
            self.zzz_redis.redis_connect()
        if self.zzz_redis.icap_reload_get() or not self.icap_settings:
            #-----not including Settings param here, so that ZzzICAPsettings will get a fresh copy in its __init__-----
            self.icap_settings = zzzevpn.ZzzICAPsettings(self.server.ZzzFeatures.ConfigData)
            self.icap_settings.get_settings()
            #TODO: if there is more than one thread, make sure all threads get new data before setting this to False
            self.zzz_redis.icap_reload_set(False)
        #TODO - check a config param before trying to load the custom module
        # if not self.server.ZzzFeatures.custom_icap:
        #     self.server.ZzzFeatures.custom_icap = self.load_custom_module(self.icap_settings, 'CustomICAP.py')

    def zzz_log_message(self, data):
        self.icap_settings.util.log_stderr(data)
        # data_str = data
        # try:
        #     data_str = str(data)
        # except Exception:
        #     # what to do when it fails to decode bytes to str?
        #     sys.stderr.write('zzz_log_message() - Exception converting data to str()\n')
        # sys.stderr.write('{}\n'.format(data_str))
        # sys.stderr.flush()
    
    def zzz_debug_log_message(self, data):
        if self.DEBUG:
            self.zzz_log_message(data)
    
    #-----bytes() --> str()-----
    # non-destructive decoding, catch errors
    # data.decode('utf-8', 'ignore')
    # data.decode('iso-8859-1', 'ignore')
    def zzz_decode_data(self, data):
        decoded_data = data
        try:
            decoded_data = data.decode()
        except AttributeError:
            #-----can't decode? it's already decoded, just return it-----
            return data
        except UnicodeDecodeError as e:
            # ???
            self.zzz_log_message('zzz_decode_data(): UnicodeDecodeError')
            # return data
        #-----might have a UnicodeDecodeError if we got here, so try decoding with ASCII-----
        try:
            decoded_data = decoded_data.decode('iso-8859-1')
        except AttributeError:
            #-----can't decode? it's already decoded, just return it-----
            return decoded_data
        except UnicodeDecodeError as e:
            # ???
            self.zzz_log_message('zzz_decode_data(): UnicodeDecodeError')
        return decoded_data
    
    #-----str() --> bytes()-----
    def zzz_encode_data(self, data):
        encoded_data = data
        try:
            encoded_data = data.encode()
        except AttributeError:
            #-----can't encode? it's already encoded, just return it-----
            return data
        except UnicodeEncodeError as e:
            # ???
            self.zzz_log_message('zzz_encode_data(): UnicodeEncodeError')
            return data
        return encoded_data
    
    def zzz_icap_log_write(self, logdata):
        logdata_str = self.zzz_decode_data(logdata)
        try:
            logdata_str = str(logdata_str)
        except Exception:
            # what to do when it fails to decode bytes to str?
            sys.stderr.write('zzz_icap_log_write() - Exception converting logdata to str()\n')
        
        with open(self.server.ZzzFeatures.ConfigData['LogFile']['ICAPdata'], 'a') as write_file:
            write_file.write(logdata_str)
    
    #-----gzipped bytes() --> bytes() --> str()-----
    def zzz_decompress_data_to_str(self, data):
        decompressed_data = None
        if self.content_encoding == 'gzip':
            decompressed_data = gzip.decompress(data)
        elif self.content_encoding == 'br':
            decompressed_data = brotli.decompress(data)
        elif self.content_encoding == 'deflate':
            decompressed_data = zlib.decompress(data)
        else:
            decompressed_data = data
        return str(self.zzz_decode_data(decompressed_data))
    
    #-----str() --> bytes() --> gzipped bytes()-----
    def zzz_compress_data(self, data):
        utf8_data = self.zzz_encode_data(data)
        if self.content_encoding == 'gzip':
            return gzip.compress(utf8_data)
        elif self.content_encoding == 'br':
            return brotli.compress(utf8_data)
        elif self.content_encoding == 'deflate':
            return zlib.compress(utf8_data)
        return utf8_data
    
    #-----check which headers we should save to the log-----
    def should_save_headers(self):
        if self.content_type=='':
            return True
        if self.regex_content_type_pattern.match(self.content_type) or (self.content_type in self.content_types_to_skip):
            return False
        return True
    
    #TODO: finish this
    #-----provides visibility into gzipped content-----
    # application/gzip
    def analyze_gzip(self):
        detected_type = magic.from_buffer(self.body[:4096])
        
        header = f'\nUNZIPPED DATA:\n==============================\ndetected_type: {detected_type}'
        # tmp_body = self.zzz_decompress_data_to_str(self.body)
        tmp_body = decompressed_data = gzip.decompress(self.body)
        data_limit = 2048
        if len(tmp_body)>data_limit:
            tmp_body = tmp_body[:data_limit]
        footer = '\n==============================\n'
        self.zzz_icap_log_write(f'{header}{tmp_body}{footer}')
    
    #-----skip content types we're not going to make edits on-----
    def should_process_content(self):
        #-----skip content over 4MB in length-----
        if self.content_length>self.length_limit:
            return False
        
        if self.content_type.startswith('text/html'):
            return True
        elif self.content_type.startswith('application/gzip'):
            #-----check stuff inside application/gzip-----
            # make sure the unzipped size will not be over 4MB
            # content type(s) inside the zip?  rely on file extension or heuristics?
            
            #TEST - remove this or move it elsewhere after testing
            self.analyze_gzip()
        return False
    
    def skip_or_log_header(self, header, value):
        header_ascii = self.zzz_decode_data(header)
        skip_header = self.headers_to_skip.get(header_ascii, None)
        if skip_header:
            return f'    {header_ascii}: (not logged)'
        return '    {}: {}'.format(header_ascii, self.zzz_decode_data(value))
    
    #--------------------------------------------------------------------------------
    
    #-----save REQUEST headers to file-----
    def zzz_save_headers_req(self):
        self.zzz_debug_log_message('zzz_save_headers_req()')
        
        request_items = []
        if self.enc_req:
            for item in self.enc_req:
                request_items.append(self.zzz_decode_data(item))
            self.zzz_log_message(' '.join(request_items))
        
        if not self.enc_req_headers:
            self.zzz_debug_log_message('zzz_save_headers_req() - empty enc_req_headers, returning')
            return
        
        tmp_headers = []
        for header in sorted(self.enc_req_headers):
            for value in self.enc_req_headers[header]:
                tmp_headers.append(self.skip_or_log_header(header, value))
                #-----save the Host header-----
                # skip: "host: localhost:29999" (port number from config?)
                if header == b'host':
                    self.host = self.zzz_decode_data(value)
                    self.zzz_log_message('host: ' + str(self.host))
        
        if not tmp_headers:
            self.zzz_debug_log_message('zzz_save_headers_req() - empty tmp_headers, returning')
            return
        
        if not self.should_save_headers():
            self.zzz_debug_log_message('zzz_save_headers_req() - not saving, returning')
            return
        
        logdata = [
            'HEADERS(zzz_save_headers_req):',
            '{}'.format('\n'.join(tmp_headers)),
            '    zzz thread ID: ' + str(threading.get_ident()),
            '##################################################\n',
        ]
        self.zzz_icap_log_write('\n'.join(logdata))
    
    def zzz_detect_unsupported_http_type(self):
        if self.enc_req and (self.enc_req[0] in self.unsupported_http_types):
            return True
        return False
    
    def zzz_handle_headers_req(self):
        self.zzz_debug_log_message('zzz_handle_headers_req()')
        self.set_icap_response(200)
        for header in self.enc_req_headers:
            for value in self.enc_req_headers[header]:
                self.set_enc_header(header, value)
    
    #--------------------------------------------------------------------------------
    
    #-----save RESPONSE headers to file-----
    # need content-type for later to determine if the body gets processed or not
    #
    # HEADERS:
    # content-encoding: gzip
    # accept-ranges: bytes
    # age: 236403
    # cache-control: max-age=604800
    # content-type: text/html; charset=UTF-8
    # date: Sat, 01 Feb 2020 22:40:35 GMT
    # expires: Sat, 08 Feb 2020 22:40:35 GMT
    # last-modified: Thu, 30 Jan 2020 05:00:32 GMT
    # server: ECS (sjc/4E91)
    # vary: Accept-Encoding
    # x-cache: 404-HIT
    # content-length: 648
    #
    # EXAMPLE: "header: value"
    #   Encodings:
    #       b'content-encoding': b'gzip'
    #       content-encoding: br
    #   Types:
    #       b'content-type': b'text/html; charset=UTF-8'
    #       content-type: application/json
    #       content-type: application/javascript
    #       content-type: application/javascript; charset=utf-8
    def zzz_save_headers(self):
        self.zzz_debug_log_message('zzz_save_headers()')
        self.content_type = ''
        self.content_length = 0
        self.content_encoding = ''
        self.use_utf8 = False
        
        tmp_headers = []
        for header in sorted(self.enc_res_headers):
            for value in self.enc_res_headers[header]:
                # tmp_headers.append('{}: {}'.format(self.zzz_decode_data(header), self.zzz_decode_data(value)))
                tmp_headers.append(self.skip_or_log_header(header, value))
                #-----save the content-type header-----
                if header == b'content-type':
                    self.content_type = self.zzz_decode_data(value)
                    check_content_type = self.content_type.lower()
                    if check_content_type.endswith('charset=utf-8') or check_content_type.endswith('charset="utf-8"'):
                        self.use_utf8 = True
                    self.zzz_log_message('content-type: ' + self.content_type)
                #-----save the content-encoding header-----
                elif header == b'content-encoding':
                    self.content_encoding = self.zzz_decode_data(value)
                    self.zzz_log_message('content-encoding: ' + self.content_encoding)
                #-----save the content-length header-----
                elif header == b'content-length':
                    self.content_length = int(self.zzz_decode_data(value))
                    self.zzz_log_message('content-length: ' + str(self.content_length))
        
        if not tmp_headers:
            self.zzz_debug_log_message('zzz_save_headers() - empty tmp_headers, returning')
            return
        
        if not self.should_save_headers():
            self.zzz_debug_log_message('zzz_save_headers() - not saving, returning')
            return
        
        logdata = [
            'HEADERS(zzz_save_headers):',
            '{}'.format('\n'.join(tmp_headers)),
            '    zzz thread ID: ' + str(threading.get_ident()),
            '##################################################\n',
        ]
        self.zzz_icap_log_write('\n'.join(logdata))
    
    #-----save body to file-----
    def zzz_save_body(self, tmp_body, data_limit=0):
        if not tmp_body:
            return
        show_data_limit = ''
        tmp_body = str(tmp_body)
        if data_limit>0:
            show_data_limit = f'(first {data_limit} chars)'
            if len(tmp_body)>data_limit:
                tmp_body = tmp_body[:data_limit]
        logdata = 'BODY: {}\n{}'.format(show_data_limit, str(self.zzz_encode_data(tmp_body)))
        logdata += '\n\n--------------------------------------------------------------------------------\n'
        self.zzz_icap_log_write(logdata)
    
    def zzz_handle_headers(self):
        self.zzz_debug_log_message('zzz_handle_headers()')
        #-----standard header processing from pyicap example-----
        # https://github.com/netom/pyicap/blob/master/examples/respmod_402.py
        # https://github.com/netom/pyicap/blob/master/examples/respmod_copy.py
        self.set_icap_response(200)
        if self.enc_res_status is not None:
            self.set_enc_status(b' '.join(self.enc_res_status))
        for header in self.enc_res_headers:
            for value in self.enc_res_headers[header]:
                #-----update the content length, in case the body was modified-----
                # prevents browser error net::ERR_CONTENT_LENGTH_MISMATCH
                if header==b'content-length':
                    new_content_length = str(len(self.body))
                    value = self.zzz_encode_data(new_content_length)
                    self.zzz_log_message('NEW content-length: ' + new_content_length)
                self.set_enc_header(header, value)
    
    #-----read binary chunks into the body var-----
    #TODO: solve the blocking read problem
    #      want to be able to restart the ICAP server independently of the squid server
    def zzz_get_body(self):
        self.zzz_debug_log_message('zzz_get_body()')
        self.body = b''
        chunks = []
        while True:
            chunk = self.read_chunk()
            if chunk == b'':
                self.body = b''.join(chunks)
                return
            else:
                # self.body += chunk
                chunks.append(chunk)
    
    # self.icap_settings.ICAPsettingsData['regexes'][id]
    # self.icap_settings.ICAPsettingsData['regexes_for_all_domains'][id] --> ['regexes'][id]
    # self.icap_settings.ICAPsettingsData['regexes_by_domain'][domain_name][id] --> ['regexes'][id]
    def apply_regexes(self, tmp_body):
        self.zzz_debug_log_message('apply_regexes()')
        if (not self.zzz_host) or (self.zzz_host=='-'):
            self.zzz_debug_log_message('    no zzz_host found')
            return tmp_body
        self.zzz_debug_log_message('    zzz_host: ' + self.zzz_host)
        
        found_regexes = []
        
        # all
        regexes_for_all_domains = self.icap_settings.ICAPsettingsData['regexes_for_all_domains']
        if regexes_for_all_domains:
            found_regexes.extend(list(regexes_for_all_domains))
        
        #TODO: extract domain from self.zzz_host
        regexes_by_domain = self.icap_settings.get_regexes_by_domain(self.zzz_host)
        # domain: {1:1, 3:1, 4:1, etc.}
        if regexes_by_domain:
            found_regexes.extend(list(regexes_by_domain))
            self.zzz_debug_log_message('    found_regexes: ' + pprint.pformat(found_regexes))
        
        #TEST
        # self.zzz_debug_log_message('^'*30)
        # self.zzz_debug_log_message('ConfigData/AppInfo/Domain: ' + self.server.ZzzFeatures.ConfigData['AppInfo']['Domain'])
        # self.zzz_debug_log_message('icap_settings.ConfigData/AppInfo/Domain: ' + self.icap_settings.ConfigData['AppInfo']['Domain'])
        # self.zzz_debug_log_message('found_regexes: ' + pprint.pformat(found_regexes))
        # self.zzz_debug_log_message('regexes_for_all_domains: ' + pprint.pformat(regexes_for_all_domains))
        # self.zzz_debug_log_message('regexes_by_domain: ' + pprint.pformat(regexes_by_domain))
        # self.zzz_debug_log_message('^'*30)
        
        # nothing to do? return body unchanged
        if not found_regexes:
            return tmp_body
        
        #-----apply each regex to the body-----
        for regex_id in found_regexes:
            #TEST
            # self.zzz_debug_log_message(f'  found_regexes: regex_id={regex_id}')
            
            # if any regex completely removes everything from the body, we're done
            if not tmp_body:
                return ''
            
            regex_domain_entry = self.icap_settings.ICAPsettingsData['regexes'][regex_id]
            if not regex_domain_entry.get('enabled', 0):
                #-----skip processing disabled regexes-----
                continue
            replacement_str = regex_domain_entry.get('replacement_str', '')
            regex = regex_domain_entry.get('regex_compiled', None)
            if not regex:
                #TODO: compiled regex is missing, log the error and move on?
                self.zzz_debug_log_message(f'    ERROR: regex {regex_id} is not compiled')
                continue
            #-----run the regex on the body-----
            regex_output = ''
            try:
                regex_output = regex.sub(replacement_str, tmp_body)
            except:
                #TODO: error running the regex, log the error and move on?
                self.zzz_debug_log_message(f'    ERROR: regex {regex_id} failed')
                continue
            tmp_body = regex_output
        
        return tmp_body

    def zzz_custom_module_processing(self):
        status = 'skipped'
        tmp_body = self.body
        if self.server.ZzzFeatures.custom_icap:
            tmp_body, status = self.server.ZzzFeatures.custom_icap.process_icap_data(tmp_body)
        return tmp_body, status

    #-----apply string modifications-----
    # starts with gzipped utf-8 bytes(), returns str()
    def zzz_modify_body(self):
        tmp_body, status = self.zzz_custom_module_processing()
        if status=='modified':
            return tmp_body

        #-----convert to str() for processing, then back to encoded bytes() for sending-----
        tmp_body = self.zzz_decompress_data_to_str(self.body)
        
        #-----ICAP regexes from the icap_settings table-----
        tmp_body = self.apply_regexes(tmp_body)
        
        return tmp_body
    
    def zzz_parse_body(self):
        self.zzz_debug_log_message('zzz_parse_body()')
        self.zzz_log_message('modifying HTML...')
        
        tmp_body = self.zzz_modify_body()
        
        #TEST - save to file, return without modifying the body
        # self.zzz_save_body(tmp_body)
        # return
        #
        #TEST - activate this when going LIVE
        self.zzz_save_body(tmp_body, 1024)
        self.body = self.zzz_compress_data(tmp_body)
    
    #-----encode the body so it becomes a bytes string for sending-----
    def zzz_send_body(self):
        self.zzz_debug_log_message('zzz_send_body()')
        try:
            self.write_chunk(self.body)
            #-----to prevent browser endless waiting for content, write an empty chunk at the end-----
            self.write_chunk()
        except ICAPError as e:
            self.zzz_log_message('Caught ICAPError, continuing...')
            return False
        except ConnectionResetError as e:
            self.zzz_log_message('Caught ConnectionResetError, continuing...')
            return False
        except Exception as e:
            self.zzz_log_message('Caught Exception, continuing...')
            return False
        return True
    
    ###################################################
    
    #TODO: load domains list from Settings
    #
    # self.set_enc_request(b' '.join(self.enc_req))
    # for h in self.enc_req_headers:
    #     for v in self.enc_req_headers[h]:
    #         self.set_enc_header(h, v)
    def should_block_request(self):
        # if (mimetype=TS) and (domain in ts_domain_list):
        #     drop request, don't send it to the server
        # regex_domain = re.compile(r'/', re.IGNORECASE | re.DOTALL| re.MULTILINE)
        req_uri = self.enc_req[1]
        if not req_uri.endswith(b'.ts'):
            return False
        
        host_header = b''
        for header in self.enc_req_headers:
            if header==b'host':
                host_header = self.enc_req_headers[header]
                break
        #TODO: change this to a dictionary lookup
        if host_header in self.request_types_to_block['.ts']:
            self.zzz_debug_log_message('should_block_request(): host_header')
            return True
        return False
    
    #-----works for both request and response-----
    def zzz_save_icap_headers(self, description=''):
        self.zzz_debug_log_message(f'zzz_save_icap_headers({description})')
        tmp_headers = []
        for header in sorted(self.headers):
            for value in self.headers[header]:
                tmp_headers.append(self.skip_or_log_header(header, value))
                if header == b'x-zzz-host':
                    #-----server SNI host passed from squid into an ICAP header-----
                    self.zzz_host = self.zzz_decode_data(value)
        logdata = [
            f'HEADERS(zzz_save_icap_headers - {description}):',
            '{}'.format('\n'.join(tmp_headers)),
            '##################################################\n',
        ]
        self.zzz_icap_log_write('\n'.join(logdata))
    
    #-----catch exceptions during sending and handle it safely-----
    # EXAMPLE:
    #     ConnectionResetError: [Errno 104] Connection reset by peer
    def zzz_safe_send_headers(self):
        try:
            if self.has_body:
                self.send_headers(True)
            else:
                self.send_headers(False)
        except:
            #TODO: log the error
            self.zzz_log_message('ERROR: send_headers() failed')
            return False
        return True
    
    ###################################################
    
    # icap://localhost:29999/zzzdataclean
    def zzzdataclean_OPTIONS(self):
        self.set_icap_response(200)
        self.set_icap_header(b'Methods', b'RESPMOD')
        self.set_icap_header(b'Methods', b'REQMOD')
        self.set_icap_header(b'Preview', b'0')
        self.set_icap_header(b'Service', b'Zzz ICAP Server')
        self.send_headers(False)
    
    #TODO: handle errors
    #   self.no_adaptation_required()
    #   self.set_icap_response(404)
    def zzzdataclean_REQMOD(self):
        #TEST - disable request processing (tells squid the service is not available)
        # self.set_icap_response(404)

        #-----check if settings need a reload-----
        self.zzz_get_icap_settings()
        
        self.zzz_debug_log_message('zzzdataclean_REQMOD: START')
        self.zzz_save_headers_req()
        self.zzz_save_icap_headers('REQMOD')
        
        # HTTP "NONE" request type should not be processed
        if self.zzz_detect_unsupported_http_type():
            self.zzz_debug_log_message('zzzdataclean_REQMOD: detected NONE, returning')
            # self.no_adaptation_required()
            self.set_icap_response(404)
            return
        
        self.zzz_handle_headers_req()
        self.zzz_debug_log_message('zzzdataclean_REQMOD: send_headers()')
        if not self.zzz_safe_send_headers():
            return
        
        if not self.should_block_request():
            #-----default behavior is no modifications-----
            self.no_adaptation_required()
            return
        
        self.zzz_debug_log_message('zzzdataclean_REQMOD: DONE')
    
    def zzzdataclean_RESPMOD(self):
        # lookup ConfigData: self.server.ZzzFeatures.ConfigData
        # lookup SettingsData: self.server.ZzzFeatures.zzz_SettingsData
        
        #-----check if settings need a reload-----
        self.zzz_get_icap_settings()
        
        #-----get a thread ID-----
        # ???
        self.zzz_debug_log_message('zzzdataclean_RESPMOD: START')
        self.zzz_save_icap_headers('RESPMOD')
        if not self.has_body:
            self.zzz_debug_log_message('zzzdataclean_RESPMOD: NO BODY - returning')
            #-----default behavior is no modifications-----
            self.no_adaptation_required()
            return
        #-----read the headers, but don't return anything to the client yet-----
        self.zzz_save_headers()
        #-----only modify selected formats: text/html, etc.-----
        if not self.should_process_content():
            self.zzz_debug_log_message('zzzdataclean_RESPMOD: not processing content, returning')
            self.no_adaptation_required()
            return
        #-----body-----
        self.zzz_get_body()
        self.zzz_parse_body()
        #-----handle/send headers AFTER parsing the body, in case content length needs updating-----
        self.zzz_handle_headers()
        self.zzz_debug_log_message('zzzdataclean_RESPMOD: send_headers()')
        self.send_headers(True)
        self.zzz_send_body()
        self.zzz_debug_log_message('zzzdataclean_RESPMOD: DONE')
    
    ###################################################
    
    # icap://localhost:29999/echo
    def echo_OPTIONS(self):
        self.set_icap_response(200)
        self.set_icap_header(b'Methods', b'RESPMOD')
        self.set_icap_header(b'Methods', b'REQMOD')
        self.set_icap_header(b'Preview', b'0')
        self.set_icap_header(b'Service', b'Zzz ICAP Server')
        self.send_headers(False)
    
    def echo_REQMOD(self):
        self.no_adaptation_required()
    
    def echo_RESPMOD(self):
        self.no_adaptation_required()

#--------------------------------------------------------------------------------

class ZzzICAPHandler(ICAPHandler):
    #TEST - since this extends an existing class, avoid var name collisions
    zzz_ConfigData = 'ZzzICAPHandler config'
    zzz_SettingsData = 'ZzzICAPHandler settings'
    
    def set_host(self, thread_id, host):
        pass

#--------------------------------------------------------------------------------

#-----Zzz ICAP server module starts here-----
class ZzzICAPserver:
    'ZzzICAPserver'
    
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    # icap_settings = None
    zzz_icap_threading = None
    
    port = 0
    service_name = 'zzz_icap'
    reload = False # set to True when Settings needs to be reloaded from the DB, usually when a SIGHUP is received
    run = True # setting this to zero will make the daemon gracefully exit, done with signal handling
    
    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, port: int=None):
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
        self.settings = zzzevpn.Settings(self.ConfigData, self.db, self.util)
        self.settings.get_settings()
        # self.icap_settings = zzzevpn.ZzzICAPsettings(self.ConfigData, self.db, self.util, self.settings)
        # self.icap_settings.get_settings()
        self.print_settings()
        if port:
            self.port = port
        else:
            self.port = self.ConfigData['Ports']['ICAP']
    
    #--------------------------------------------------------------------------------
    
    #-----clear internal variables-----
    def init_vars(self):
        pass
    
    def clear_data_log(self):
        with open(self.ConfigData['LogFile']['ICAPdata'], 'w') as write_file:
            write_file.write('')

    #--------------------------------------------------------------------------------
    
    #-----process ICAP data response-----
    def handle_icap_response(self, environ):
        return 'ICAPserver response test'
    
    #--------------------------------------------------------------------------------
    
    def should_run(self, value=None):
        if (value is None):
            return self.run
        else:
            self.run = value
    
    #--------------------------------------------------------------------------------
    
    #TEST
    #TODO: show new settings from the icap_settings table
    def print_settings(self):
        # print_icap_settings = 'ICAP Settings: '
        # print(print_icap_settings, flush=True)
        pass
    
    #--------------------------------------------------------------------------------
    
    #TODO: set flag in redis to make the threading server get the latest settings
    # reloads modules: Config, DB, Settings
    def reload_settings(self):
        #-----set the flag to false so this only runs once per SIGHUP-----
        self.should_reload(False)
        if not self.settings:
            return
        
        #-----get the latest ConfigData and settings-----
        config = zzzevpn.Config(skip_autoload=True)
        self.ConfigData = config.get_config_data()

        self.settings = zzzevpn.Settings(self.ConfigData)
        # self.icap_settings = zzzevpn.ZzzICAPsettings(self.ConfigData, self.settings.db, self.settings.util, self.settings)
        #-----settings will get a new DB connection, then we save it here-----
        self.db = self.settings.db
        self.util = self.settings.util
        self.settings.get_settings()
        # self.icap_settings.get_settings()
        
        #-----push the settings data into the threaded server-----
        self.zzz_icap_threading.ZzzFeatures.ConfigData = self.ConfigData
        self.zzz_icap_threading.ZzzFeatures.zzz_SettingsData = self.settings.SettingsData
        # self.zzz_icap_threading.ZzzFeatures.icap_settings = self.icap_settings
        
        #-----print ICAP settings to the log-----
        self.print_settings()
    
    #--------------------------------------------------------------------------------
    
    #-----check/set the reload flag-----
    # tells the server to reload Settings
    def should_reload(self, value=None):
        if (value is None):
            return self.reload
        else:
            self.reload = value
    
    #--------------------------------------------------------------------------------

    #TODO: function to check if the server is started?
    #-----start the threaded server-----
    def start_server(self):
        self.zzz_icap_threading = ZzzICAPthreading(('', self.port), ZzzICAPHandler, ZzzFeatures)
        #-----push the settings data into the threaded server-----
        self.zzz_icap_threading.ZzzFeatures.ConfigData = self.ConfigData
        self.zzz_icap_threading.ZzzFeatures.zzz_SettingsData = self.settings.SettingsData
        # self.zzz_icap_threading.ZzzFeatures.icap_settings = self.icap_settings

    #--------------------------------------------------------------------------------
