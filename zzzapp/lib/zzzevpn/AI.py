#-----AI interfaces-----
# ChatGPT
# https://pypi.org/project/openai/

import json
import openai
import pprint
import tiktoken

#-----package with all the Zzz modules-----
import zzzevpn

class AI:
    'AI interfaces'
    
    ConfigData: dict = None
    db: zzzevpn.DB = None
    openai_client: openai.OpenAI = None
    util: zzzevpn.Util = None
    settings: zzzevpn.Settings = None
    webpage: zzzevpn.Webpage = None

    max_tokens_input = 10000
    max_tokens_output = 10000
    max_tokens_total = 20000

    model = 'gpt-4o-mini'

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
        self.webpage = zzzevpn.Webpage(self.ConfigData, self.db, '', self.settings)

        #-----set the tiktoken cache directory-----
        self.util.standalone.set_tiktoken_cache_dir()
        self.init_vars()

    #--------------------------------------------------------------------------------

    #-----clear internal variables-----
    def init_vars(self):
        pass

    #--------------------------------------------------------------------------------

    def is_enabled(self) -> bool:
        return self.settings.is_setting_enabled('enable_ai')

    def is_api_configured(self) -> bool:
        return self.settings.is_ai_api_configured()

    #--------------------------------------------------------------------------------

    def print_runtime(self, start_time, stop_time, label):
        runtime = stop_time - start_time
        print(f'{label}: {runtime:.3f} seconds')

    #--------------------------------------------------------------------------------

    def is_model_allowed(self, model, request_type):
        if model in self.models_by_request_type[request_type]:
            return True
        return False

    #--------------------------------------------------------------------------------

    def is_valid_request_type(self, request_type):
        if request_type in self.request_types:
            return True
        return False

    #--------------------------------------------------------------------------------

    def set_model(self, model) -> bool:
        if not self.is_model_allowed(model, 'chat_completion'):
            return False
        self.model = model
        return True

    #--------------------------------------------------------------------------------

    def estimate_tokens(self, prompt):
        # o200k_base works for gpt-4o-mini
        # encoding = tiktoken.get_encoding("o200k_base")

        # get tokenizer by model
        encoding = tiktoken.encoding_for_model(self.model)

        # text-to-tokens
        tokens = encoding.encode(prompt)
        num_tokens = len(tokens)

        # print(f"Estimated Tokens: {num_tokens}")
        return num_tokens

    #--------------------------------------------------------------------------------

    # https://community.openai.com/t/how-to-calculate-the-cost-of-a-specific-request-made-to-the-web-api-and-its-reply-in-tokens/270878
    def estimate_cost(self, query_str, completion_tokens=1000):
        prompt_tokens = self.estimate_tokens(query_str)
        prompt_cost = prompt_tokens * self.model_info[self.model]['costs']['input_rate'] / self.util.standalone.MILLION
        completion_cost = completion_tokens * self.model_info[self.model]['costs']['output_rate'] / self.util.standalone.MILLION

        estimated_costs = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'prompt_cost': round(prompt_cost, 6),
            'completion_cost': round(completion_cost, 6),
            'total_cost': round(prompt_cost + completion_cost, 6),
        }
        return estimated_costs

    #--------------------------------------------------------------------------------

    #-----calculate the actual cost for a completed query-----
    # the query response includes actual token counts: completion_tokens, prompt_tokens, total_tokens
    def calc_actual_cost(self, chat_completion) -> float:
        if not chat_completion:
            return 0

        # pull data out of the chat_completion object
        total_tokens = chat_completion.usage.total_tokens
        completion_tokens = chat_completion.usage.completion_tokens
        prompt_tokens = chat_completion.usage.prompt_tokens

        # calculate the cost
        prompt_cost = prompt_tokens * self.model_info[self.model]['costs']['input_rate'] / self.util.standalone.MILLION
        completion_cost = completion_tokens * self.model_info[self.model]['costs']['output_rate'] / self.util.standalone.MILLION

        actual_costs = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'prompt_cost': round(prompt_cost, 6),
            'completion_cost': round(completion_cost, 6),
            'total_cost': round(prompt_cost + completion_cost, 6),
        }
        return actual_costs

    #--------------------------------------------------------------------------------

    def get_client(self) -> bool:
        if self.openai_client:
            return True

        # get a new connection if we don't have one
        api_key = self.ConfigData['AI']['openai']['api_key']
        try:
            self.openai_client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            return False

        return True

    #--------------------------------------------------------------------------------

    def do_completion(self, prompt: str, max_tokens: int=100):
        completion = None
        try:
            completion = self.openai_client.completions.create(
                model=self.model,
                messages=[
                    # {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt,},
                ],
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(e)
            return None
        return completion

    def do_chat_completion(self, prompt: str, max_completion_tokens: int=100):
        chat_completion = None
        try:
            chat_completion = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    # {"role": "system", "content": "system instructions",},
                    {"role": "user", "content": prompt,},
                ],
                max_completion_tokens=max_completion_tokens,
            )
        except Exception as e:
            print(e)
            return None
        return chat_completion

    def do_response(self, prompt: str, max_output_tokens: int=100):
        response = None
        try:
            response = self.openai_client.responses.create(
                model=self.model,
                input=prompt,
                max_output_tokens=max_output_tokens,
            )
        except Exception as e:
            print(e)
            return None
        return response

    #--------------------------------------------------------------------------------

    #-----query OpenAI and return response-----
    # returns a dict with status and response
    def do_query(self, query_str: str) -> dict[str, openai.ChatCompletion]:
        if not self.is_api_configured():
            return "ERROR: OpenAI API key not configured"

        if not self.is_enabled():
            return "ERROR: AI not enabled in Settings"

        if not self.get_client():
            return "ERROR: Could not connect to OpenAI"

        if not query_str:
            return "ERROR: No query provided"

        ai_response = { 'status': '', 'response': None, }
        try:
            response = self.do_chat_completion(
                prompt=query_str,
                max_completion_tokens=1000,
            )
            ai_response['response'] = response
            ai_response['text'] = response.choices[0].message.content
            ai_response['status'] = 'success'
        except openai.InvalidRequestError as e:
            ai_response['status'] = "ERROR: The request was invalid\n"
            ai_response['status'] += pprint.pformat(e)
        except openai.APIConnectionError as e:
            ai_response['status'] = "ERROR: The server could not be reached\n"
            # an underlying Exception, likely raised within httpx.
            ai_response['status'] += e.__cause__
            ai_response['status'] += pprint.pformat(e)
        except openai.RateLimitError as e:
            ai_response['status'] = "ERROR: A 429 status code was received (rate limit); we should back off a bit.\n"
            ai_response['status'] += pprint.pformat(e)
        except openai.AuthenticationError as e:
            ai_response['status'] = "ERROR: Authentication with the OpenAI API failed\n"
            ai_response['status'] += pprint.pformat(e)
        except openai.APIStatusError as e:
            ai_response['status'] = "ERROR: Another non-200-range status code was received\n"
            ai_response['status'] += f'  status_code: {e.status_code}\n  response: {e.response}\n'
            ai_response['status'] += pprint.pformat(e)
        except Exception as e:
            ai_response['status'] = "ERROR: Could not get response from OpenAI"
            ai_response['status'] += pprint.pformat(e)

        return ai_response

    #--------------------------------------------------------------------------------
