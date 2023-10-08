import streamlit as st
from streamlit.logger import get_logger
import openai
import pandas as pd
import json

LOGGER = get_logger(__name__)


class Consts:
  
  PAGE_TITLE = "DAZN AI Agent Prototype"

  OPENAI_MODEL = "gpt-4"

  GPT_TEMPERATURE = 0.25

  SHOW_FUNC_CALLING = True # Show function calling in the chat UI?

  WELCOME_BOT_MESSAGE = """Welcome to DAZN 👋 How's it going? 🙂"""

  SYSTEM_PROMPT = open('prompt engineering/system prompt.md').read()



def call_and_process_gpt():
  """
  Use the chat history in st.session_state['gpt_messages'] to call ChatGPT.
  Process the bot message and function call results.
  """

  # Prepare assistant response UI
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
          temperature=Consts.GPT_TEMPERATURE,
          # functions=Consts.GPT_FUNCTIONS
      ):
          # Handle content stream
          if not response.choices[0].delta.get("function_call",""):
              content_chunk = response.choices[0].delta.get("content", "")
              bot_content_response += content_chunk
              full_response += content_chunk
              message_placeholder.markdown(full_response + "▌")
          
          # Handle function call stream
          else:
              function_call_response += response.choices[0].delta.function_call.get("arguments", "")
              if Consts.SHOW_FUNC_CALLING:
                  if function_call_response == "":
                      full_response += "\n\n`Database Query: "
                  full_response += response.choices[0].delta.function_call.get("arguments", "")
                  message_placeholder.markdown(full_response + "`▌")

      if not function_call_response:
          message_placeholder.markdown(full_response)
      elif not Consts.SHOW_FUNC_CALLING: 
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
      # Store bot content
      st.session_state['gpt_messages'].append({"role": "assistant", "content": bot_content_response,
                                                  "function_call": {"name": "query_lg_dishwasher_products", "arguments": function_call_response}})
      if Consts.SHOW_FUNC_CALLING:
          st.session_state.messages.append({"role": "assistant", "content": full_response + "`"})
      elif bot_content_response != "":
          st.session_state.messages.append({"role": "assistant", "content": bot_content_response})

      
      # Execute and parse query
      query = json.loads(function_call_response).get('sql_query')

      # Process query results
      query_result_df = None
      query_result_df_string = ""
      query_result_text = ""
      try:
          # Apply query to pseudo-DB
          # query_result_df = sqldf(query, {"lg_product_data": lg_product_data_frame})
          query_result_df = "todo"

          # Get results
          if not query_result_df.empty:
              query_result_df = query_result_df.head(5)
              query_result_df_string = query_result_df.to_string(index=False)
          else:
              query_result_text = "Query result: No products found with that criteria"
      except Exception as e:
          query_result_text = str(e) 
  
      # Store query results for GPT
      st.session_state['gpt_messages'].append({"role": "function", "name": "query_lg_dishwasher_products", 
                                                  "content": query_result_df_string if query_result_df_string != "" else query_result_text})
      
      # Render query results
      if Consts.SHOW_FUNC_CALLING:
          with st.chat_message("query result"):
              rendered_query_results = "Error rendering query results"
              if query_result_df is not None and not query_result_df.empty:
                  rendered_query_results = f"Found {query_result_df.shape[0]} product results."
              elif query_result_text != "":
                  rendered_query_results = query_result_text
              st.markdown(rendered_query_results)
              st.session_state.messages.append({"role": "query result", "content": rendered_query_results})
      
      # I wanted to render the results as a table but couldn't get it to work
      # with st.chat_message("SQL Result"):
      #     if query_result_text != "":
      #         st.markdown(query_result_text)
      #     if query_result_df is not None and not query_result_df.empty:
      #         st.markdown("<style>table.dataframe {font-size: 6px;}</style>", unsafe_allow_html=True)
      #         st.write(query_result_df)


      # Recursively call this same function to process the query results
      call_and_process_gpt()




def run():

  # Set Streamlit app meta info
  st.set_page_config(
      page_title=Consts.PAGE_TITLE,
      page_icon="🤖",
  )
  st.title(Consts.PAGE_TITLE)

  # Set the OpenAI key and model
  openai.api_key = st.secrets["OPENAI_API_KEY"]

  if "openai_model" not in st.session_state:
      st.session_state["openai_model"] = Consts.OPENAI_MODEL

  # Initialize UI messages and GPT messages
  if "messages" not in st.session_state:
      st.session_state.messages = [
          {"role": "assistant", "content": Consts.WELCOME_BOT_MESSAGE}
      ]
      st.session_state["gpt_messages"] = [
          {"role": "system", "content": Consts.SYSTEM_PROMPT},
          {"role": "assistant", "content": Consts.WELCOME_BOT_MESSAGE}
      ]


  # Re-render UI messages
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