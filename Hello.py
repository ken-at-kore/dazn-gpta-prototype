import streamlit as st
from streamlit.logger import get_logger
from datetime import datetime
import openai
import pandas as pd
import json
import jmespath
# from jsonpath_ng import jsonpath, parse
# from jsonpath_rw_ext import parse

LOGGER = get_logger(__name__)


class AiBotConfigs:
  
    PAGE_TITLE = "DAZN AI Bot Prototype"

    OPENAI_MODEL = "gpt-4"
    # OPENAI_MODEL = "gpt-3.5-turbo"

    GPT_TEMPERATURE = 0.25

    SHOW_FUNC_CALLING = False # Show function calling in the chat UI?

    WELCOME_BOT_MESSAGE = """Welcome to DAZN 👋 How's it going? 🙂"""

    SYSTEM_PROMPT = open('prompt engineering/system prompt.md').read()



class AiAction:
    def __init__(self):
        assert hasattr(self.__class__, 'execute'), f'{self.__class__.__name__} must define a static execute(args) method'
        assert hasattr(self.__class__, 'get_spec'), f'{self.__class__.__name__} must define a static get_spec() method'
    class Result:
        def __init__(self, val):
            self.value = val
    class Collection:
        def __init__(self, function_classes):
            self.functions = {}
            for function_class in function_classes:
                assert issubclass(function_class, AiAction), f"{function_class} is not a subclass of AiAction"
                function_obj = function_class()
                function_name = function_obj.get_spec()['name']
                self.functions[function_name] = function_obj
        def get_function_specs(self):
            return [function.get_spec() for function in self.functions.values()]
        def get_function(self, name):
            return self.functions.get(name)



class GetDaznScheduleAction(AiAction):

    @staticmethod
    def get_spec():
        return {
            "name": "query_dazn_event_schedule",
            "description": "Query for info on DAZN scheduled programming by querying a Pandas Dataframe in a Python environment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pandas_dataframe_query": {
                        "type": "string",
                        "description": """Consider that there is DAZN scheduled programming data in a Pandas Dataframe in a Python environment. 
                        You will write a query_string that will be passed to a Dataframe.query call: ```
                            dazn_schedule_dataframe = pandas.read_json(json_string, orient='records')
                            current_date = datetime.now().strftime('%Y-%m-%d')
                            dazn_schedule_dataframe.query(query_string, engine='python')```
                        The json_string contains a list of schedule event objects. Example object:
                            {
                                "Title": "KSI vs. Fury: Open Workout",
                                "Description": "As the historic October 15 showdown draws closer, KSI and Tommy Fury take part in ...",
                                "EventURL": "https://www.dazn.com/en-GB/home/8n9pw9ndc80wle43vnle55q42",
                                "Start": "2023-10-11T14:00:00Z",
                                "Competition": "MF & DAZN: X Series 10",
                                "Sport": "Boxing"
                            }
                        Possible values for Sport: 'Mixed Martial Arts', 'Football', 'Live channels', 'American Football', 'Extreme Sports', 'Boxing'
                        """,
                    }
                },
                "required": ["pandas_dataframe_query"],
            }
        }
    
    SCHEDULE_DATA_DF = pd.read_json('data/dazn_sample_schedule_data.json', orient='records')
    
    @staticmethod
    def execute(args):
        query_string = args.get('pandas_dataframe_query')
        query_result_df = None

        current_date = datetime.now().strftime('%Y-%m-%d') # The query string might use this
        query_result_df = GetDaznScheduleAction.SCHEDULE_DATA_DF.query(query_string, engine='python')

        # Get results
        if not query_result_df.empty:
            query_result_df = query_result_df.head(5)
            return AiAction.Result(query_result_df.to_string(index=False))
        else:
            return AiAction.Result("Query result: No events found with that criteria")



class OpenBoxingActions:

    class GetBoxingReigns(AiAction):

        @staticmethod
        def get_spec():
            return {
                "name": "get_boxing_champs_or_bouts_or_reigns",
                "description": "Query for current and past boxing champions, bouts or reigns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection_to_query": { "type": "string", "enum": ["champions", "bouts", "reigns"]
                        },
                        "jmespath_query": {
                            "type": "string",
                            "description": """There is boxing reigns data in a JSON file. 
                            Using the jmespath Python package you will write a simple jmespath_query.
                            jmespath_query will be used like this: ```
                                jmespath.search(jmespath_query, reigns)```
                            The query syntax MUST be valid jmespath syntax. 
                            In the query, project only the required or relevant data.
                            Example champions JSON object:

                            Example bouts JSON object:
                                {"boutId":1,"date":"1912-06-24","boxers":{"boxerA":{"championId":7,"name":{"first":"Frank","last":"Klaus","short":"Klaus"},"born":"1887-12-30"},"boxerB":{"championId":25,"name":{"first":"Georges","last":"Carpentier","short":"Carpentier"},"born":"1894-01-12"}},"status":"FINISHED","result":{"winner":"BOXER A","methodOfVictory":"DQ","totalRounds":19},"scheduledRounds":20,"weight":{"class":"Middleweight","lb":"160"},"titles":[{"weight":{"class":"Middleweight","lb":"160"},"org":{"name":{"full":"New York State Athletic Commission","short":"NYSAC","abbreviation":"NYSAC"}},"active":false}],"location":{"locationId":null,"venue":null,"locality":null,"country":null,"latitude":null,"longitude":null}}
                            Example JSON object:
                                {"reign_id":3112,"period":{"begins":"2023-06-24","ends":null,"current":true},"champion":{"championId":1367,"name":{"first":"Kazuto","last":"Ioka","short":"Ioka"},"born":"1989-03-24"},"title":{"weight":{"class":"Super Flyweight","lb":"115"},"org":{"name":{"full":"World Boxing Association Regular","short":"WBA Regular","abbreviation":"WBAR"}},"active":true}}
                            Example JSON object:
                                {"championId":1,"name":{"first":"Jack","last":"Johnson","short":"Johnson"},"born":"1878-03-31"}
                            """
                        }
                    },
                    "required": ["collection_to_query", "jmespath_query"],
                }
            }

        OPENBOXING_DATA = {}
        with open('data/openboxing_champions.json', 'r') as file:
            OPENBOXING_DATA['champions'] = json.load(file)
        with open('data/openboxing_bouts.json', 'r') as file:
            OPENBOXING_DATA['bouts'] = json.load(file)
        with open('data/openboxing_reigns.json', 'r') as file:
            OPENBOXING_DATA['reigns'] = json.load(file)

        @staticmethod
        def execute(args):
            collection_to_query = args.get('collection_to_query')
            query_string = args.get('jmespath_query')
            query_string = query_string.replace('?[','[') # GPT-4 outptus a leading ? for some reason
            query_result = None

            data = OpenBoxingActions.GetBoxingReigns.OPENBOXING_DATA[collection_to_query]
            query_result = jmespath.search(query_string, data)

            # Get results
            if query_result and isinstance(query_result, list):
                return AiAction.Result(str(query_result[:5]))
            elif query_result:
                return AiAction.Result(str(query_result))
            else:
                return AiAction.Result("Query result: No reigns found with that criteria")



ai_actions = AiAction.Collection([GetDaznScheduleAction, OpenBoxingActions.GetBoxingReigns])



def call_and_process_gpt():
    """
    Use the chat history in st.session_state['gpt_messages'] to call ChatGPT.
    Process the bot message and function call results.
    """

    # Prepare assistant response UI
    function_call_name = ""
    function_call_response = ""
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        bot_content_response = ""

        # Call OpenAI GPT (Response is streamed)
        for response in openai.ChatCompletion.create(
            model=st.session_state["openai_model"],
            messages=st.session_state["gpt_messages"],
            stream=True,
            temperature=AiBotConfigs.GPT_TEMPERATURE,
            functions=ai_actions.get_function_specs()
        ):
            # Handle content stream
            if not response.choices[0].delta.get("function_call",""):
                content_chunk = response.choices[0].delta.get("content", "")
                bot_content_response += content_chunk
                full_response += content_chunk
                message_placeholder.markdown(full_response + "▌")
            
            # Handle function call stream
            else:
                call = response.choices[0].delta.function_call
                if function_call_name == "":
                    function_call_name = call.get("name", "")
                function_call_response += call.get("arguments", "")
                if AiBotConfigs.SHOW_FUNC_CALLING:
                    if function_call_response == "":
                        full_response += "\n\n`Query: "
                    full_response += call.get("arguments", "")
                    message_placeholder.markdown(full_response + "`▌")

        if not function_call_response:
            message_placeholder.markdown(full_response)
        elif not AiBotConfigs.SHOW_FUNC_CALLING: 
            message_placeholder.markdown('Just a sec 🔍')
        else:
            message_placeholder.markdown(full_response + "`" if function_call_response else "")

    # Handle no function call
    if not function_call_response:
        # Store the bot content
        st.session_state['gpt_messages'].append({"role": "assistant", "content": bot_content_response})
        st.session_state.messages.append({"role": "assistant", "content": bot_content_response})

    # Handle function call
    else:
        # Store bot content including function call name and arguments
        st.session_state['gpt_messages'].append({"role": "assistant", "content": bot_content_response,
                                                    "function_call": {"name": function_call_name, 
                                                                    "arguments": function_call_response}})
        if AiBotConfigs.SHOW_FUNC_CALLING:
            st.session_state.messages.append({"role": "assistant", "content": full_response + "`"})
        elif bot_content_response != "":
            st.session_state.messages.append({"role": "assistant", "content": bot_content_response})

        # Execute function call
        function_obj = ai_actions.get_function(function_call_name)
        assert function_obj is not None, f'Function {function_call_name} is not defined in the function collection'
        try:
            func_call_results = function_obj.execute(json.loads(function_call_response))
        except Exception as e:
            func_call_results = AiAction.Result(str(e))
            # raise e

        func_call_results_str = func_call_results.value

        # Store query results for GPT
        st.session_state['gpt_messages'].append({"role": "function", "name": "query_lg_dishwasher_products", 
                                                    "content": func_call_results_str})
        
        # Render query results
        if AiBotConfigs.SHOW_FUNC_CALLING:
            with st.chat_message("query result"):
                st.markdown(func_call_results_str)
                st.session_state.messages.append({"role": "query result", "content": func_call_results_str})


        # Recursively call this same function to process the query results
        call_and_process_gpt()




def run():

    # Set Streamlit app meta info
    st.set_page_config(
        page_title=AiBotConfigs.PAGE_TITLE,
        page_icon="🤖",
    )
    st.title(AiBotConfigs.PAGE_TITLE)

    # Set the OpenAI key and model
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = AiBotConfigs.OPENAI_MODEL

    # Set up the GPT system prompt with the current date
    system_promt = AiBotConfigs.SYSTEM_PROMPT + '\n\nCurrent date: ' + datetime.now().strftime('%Y-%m-%d')

    # Initialize UI messages and GPT messages
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": AiBotConfigs.WELCOME_BOT_MESSAGE}
        ]
        st.session_state["gpt_messages"] = [
            {"role": "system", "content": system_promt},
            {"role": "assistant", "content": AiBotConfigs.WELCOME_BOT_MESSAGE}
        ]


    # Re-render UI messages
    # time.sleep(10) # This is just to work around a Streamlit bug when debugging
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get, store and render user message
    if prompt := st.chat_input("Enter text here"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state["gpt_messages"].append({"role": "user", "content": prompt.replace('$','\$')})
        with st.chat_message("user"):
            st.markdown(prompt.replace('$','\$'))

        # Call GPT with the input and process results
        call_and_process_gpt()


if __name__ == "__main__":
    run()