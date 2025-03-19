#-----AI interfaces-----
# ChatGPT
# https://pypi.org/project/openai/

import json
import pprint
import time

#-----package with all the Zzz modules-----
import zzzevpn

class AIpage:
    'AI web interfaces'
    
    ai: zzzevpn.AI = None
    ConfigData: dict = None
    data_validation: zzzevpn.DataValidation = None
    db: zzzevpn.DB = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None

    allowed_post_params = ['action', 'ai_instructions']
    max_prompt_tokens = 10000

    #--------------------------------------------------------------------------------

    # CONSTANTS

    #-----AI request types-----
    request_types = [
        'completion', # older
        'chat_completion', # old
        'response', # new
    ]

    #-----certain models require certain request types-----
    # chat_completion is the only one currently working
    models_by_request_type = {
        'completion': [
            # older models use the older interface
            'babbage-002',
            'davinci-002',
        ],
        'chat_completion': [
            # new models may use the old interface? test this
            'gpt-3.5-turbo',
            'gpt-4o',
            'gpt-4o-mini',
        ],
        'response': [
            # new models use the new interface
            'gpt-3.5-turbo',
            'gpt-4o',
            'gpt-4o-mini',
        ],
    }
    model_info = {
        'gpt-4o-mini': {
            'costs': {
                # USD cost per million tokens
                'input_rate': 0.15,
                'output_rate': 0.60,
            },
            'max_tokens': 10000,
        },
    }

    #--------------------------------------------------------------------------------

    def __init__(self, ConfigData: dict=None, db: zzzevpn.DB=None, util: zzzevpn.Util=None, settings: zzzevpn.Settings=None):
        #-----get Config-----
        if ConfigData is None:
            config = zzzevpn.Config(skip_autoload=True)
            self.ConfigData = config.get_config_data()
        else:
            self.ConfigData = ConfigData
        #-----use the given DB connection or get a new one-----
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
        self.ai = zzzevpn.AI(self.ConfigData, self.db, self.util, self.settings)
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)

        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        pass

    #--------------------------------------------------------------------------------

    #-----process POST data-----
    # always return JSON
    def handle_post(self, environ, request_body_size):
        #-----return if missing data-----
        if request_body_size==0:
            return self.webpage.error_log(environ, 'ERROR: missing data')

        self.init_vars()

        #-----get post data-----
        # include all limit_fields
        data = self.webpage.load_data_from_post(environ, request_body_size, self.allowed_post_params)

        #-----validate data-----
        if self.data_validation is None:
            self.data_validation = zzzevpn.DataValidation(self.ConfigData, enforce_rules=True, auto_clean=False)
        if not self.data_validation.validate(environ, data):
            err_msg = f'''data validation failed<br>{self.data_validation.show_detailed_errors()}'''
            # return self.make_return_json_error(self.webpage.error_log(environ, err_msg))
            return self.webpage.make_return_json('error', self.webpage.error_log(environ, err_msg))

        #-----return if missing data in required fields (action)-----
        if data['action'] is None:
            return self.webpage.error_log(environ, 'ERROR: missing action')
        if not self.ai.is_api_configured():
            return self.webpage.error_log(environ, 'ERROR: AI is not configured in zzz.conf')
        if not self.ai.is_enabled():
            return self.webpage.error_log(environ, 'ERROR: AI is not enabled in Settings')

        #-----process action-----
        # actions: ai_submit, ai_get_estimate
        if data['action']=='ai_submit':
            return self.ai_submit(environ, data)
        elif data['action']=='ai_get_estimate':
            return self.ai_get_estimate(environ, data)

        #-----this should never happen-----
        return self.webpage.error_log(environ, 'ERROR: unexpected action')

    #--------------------------------------------------------------------------------

    def ai_submit(self, environ, data):
        if not data['ai_instructions']:
            return self.webpage.make_return_json('error', 'missing ai_instructions')

        instruction_len = len(data['ai_instructions'])
        estimated_costs = self.ai.estimate_cost(data['ai_instructions'])
        #-----reject if too many tokens-----
        if estimated_costs['prompt_tokens'] > self.max_prompt_tokens:
            err_msg = f'''too many tokens requested: {estimated_costs['prompt_tokens']}, max: {self.max_prompt_tokens}'''
            data_to_send = {
                'status': 'error',
                'error_msg': err_msg,
                'ai_response': 'test response',
            }
            json_data_to_send = json.dumps(data_to_send)
            self.webpage.error_log(environ, err_msg)
            return json_data_to_send

        #TEST
        self.test_log_params(environ, data)
        time.sleep(2)
        ai_response_text = 'test response'
        actual_costs = {
            # prompt_tokens, completion_tokens, prompt_cost, completion_cost, total_cost
            'prompt_tokens': 1,
            'completion_tokens': 2,
            'prompt_cost': 3,
            'completion_cost': 4,
            'total_cost': 5,
        }
        #ENDTEST

        #-----submit AI request-----
        start_time = time.time()
        ai_response = self.ai.do_query(data['ai_instructions'])
        ai_response_text = ai_response['text']
        runtime = time.time() - start_time

        actual_costs = self.ai.calc_actual_cost(ai_response['response'])

        #-----return response-----
        data_to_send = {
            'status': 'success',
            'error_msg': '',

            'estimated_costs': estimated_costs,
            'actual_costs': actual_costs,

            'ai_response_text': ai_response_text,
            'runtime': round(runtime, 6),
        }
        json_data_to_send = json.dumps(data_to_send)

        return json_data_to_send

    #--------------------------------------------------------------------------------

    #-----get an estimate for the cost of an AI request-----
    def ai_get_estimate(self, environ, data):
        if not data['ai_instructions']:
            return self.webpage.make_return_json('error', 'missing ai_instructions')

        instruction_len = len(data['ai_instructions'])

        #TEST
        self.test_log_params(environ, data)

        estimated_costs = self.ai.estimate_cost(data['ai_instructions'])
        data_to_send = {
            'status': 'success',
            'error_msg': '',
            'estimated_costs': estimated_costs,
        }
        json_data_to_send = json.dumps(data_to_send)
        return json_data_to_send

    #--------------------------------------------------------------------------------

    def test_log_params(self, environ, data):
        #-----log all parameters-----
        instruction_len = len(data['ai_instructions'])
        short_instructions = data['ai_instructions'][:1000]
        #TEST
        log_test_output = f'''
ai_instructions: {short_instructions}
---
instruction_len: {instruction_len}
'''
        self.webpage.error_log(environ, log_test_output)

    #--------------------------------------------------------------------------------
