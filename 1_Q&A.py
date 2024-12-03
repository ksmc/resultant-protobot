import re
import io
import os
import sys
import fitz
import logging
import os.path
import streamlit as st
# from docx import Document
from pptx import Presentation
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval
import streamlit_analytics2 as streamlit_analytics
from st_pages import hide_pages, show_pages, Page, add_page_title
from functions import read_pdf, read_docx, read_ppt, read_txt, read_csv, read_excel, load_data
from llama_index.core import (
	Settings,
	VectorStoreIndex,
	ServiceContext,
	Document,
	SimpleDirectoryReader,
	StorageContext,
	load_index_from_storage
)
from llama_index.llms.openai import OpenAI
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.base.llms.types import ChatMessage, ChatResponse

streamlit_analytics.start_tracking()

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

st.set_page_config(
	page_title="ProtoBot Q&A Agent",
	page_icon="🤖",
)
hide_pages(["functions", "ProtoBot-Pro-Test"])

# Resultant Key
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

st.title("🤖 ProtoBot Q&A Agent")

# Instruction Side Bar
# Set up the model configuration options
st.sidebar.title("LLM Configuration")

# Define your switch_llm function before using it as a callback
def switch_llm():
	# Access the selected option via session state
	model_choice = st.session_state['LLM_Model'] 
	if model_choice == 'Gemini':
		# Assuming Settings and Gemini are defined/imported elsewhere in your script
		print("Gemini")
		Settings.llm = Gemini(model="gemini-pro",
							  temperature = temperature,
							  system_prompt = system_prompt)
		# Additional logic for switching to Gemini
	else:
		# Assuming Settings and OpenAI are defined/imported elsewhere in your script
		print("OpenAI")
		Settings.llm = OpenAI(model="gpt-4o",
							  temperature = temperature,
							  system_prompt = system_prompt)
		# Additional logic for switching to OpenAI GPT
	if "chat_engine" in st.session_state.keys():
		print("Switch LLM")
		st.session_state.chat_engine = index.as_chat_engine(chat_mode = "best", llm = Settings.llm, context_prompt = (system_prompt), verbose=True)

# Now setup your radio button with the callback
model_choice = st.sidebar.radio(
	"LLM_Model",
	# options = ["GPT", "Gemini"],
	options = ["Gemini"],
	index = 0,
	horizontal = True,
	on_change = switch_llm,  # Pass the function reference without calling it
	key = 'LLM_Model'  # It's a good practice to provide a key argument for widgets
)

temperature = st.sidebar.slider("Temperature (Creativity)", 0.0, 2.0, 1.0, 0.1)
# top_p = st.sidebar.number_input("Top P", 0.0, 1.0, 1.0, 0.1)
# top_k = st.sidebar.number_input("Top K", 1, 100, 1)
# print(temperature)

system_prompt = '''
			You are a Gen AI virtual assistant for a consulting company named Resultant. Your name is Proto Bot. 
			Luke Zhang from the Prototyping Team created you.
			'''

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

st.sidebar.title("Instructions")
st.sidebar.markdown("1. ProtoBot Q&A Agent has access to the entire Resultant Content Hub, HR Resources & Policies and selected Project Documents (SOW, RFP, RFQ etc)")
st.sidebar.markdown("2. Fire your questions away!")
st.sidebar.markdown("3. If you run into any errors or want to start a new chat, please click the Refresh button.")


# Instruction Side Bar
st.sidebar.title("Example Prompts")
st.sidebar.markdown("1. What does the Prototyping Team do?")
st.sidebar.markdown("2. List some projects that's related to Education.")
st.sidebar.markdown("3. What's our cell phone policy?")
st.sidebar.markdown("3. Tell me about our PTO Policy")
st.sidebar.markdown("5. Show Resultant's values and mission Statement.")

# Initialize the chat messages history
if "messages" not in st.session_state.keys(): 
	st.session_state.messages = [
		{"role": "assistant", "content": "My favorite Rezzer, how can I help?📖"}
	]

with st.spinner(text="Loading and indexing docs – hang tight!"):
	index = load_data()
download_chat = []

if "chat_engine" not in st.session_state.keys(): # Initialize the chat engine
	# print("Chat Engine Created")
	default_llm = OpenAI(model="gpt-4-0125-preview", temperature = temperature, system_prompt = system_prompt)
	st.session_state.chat_engine = index.as_chat_engine(chat_mode = "best", llm = default_llm, context_prompt = (system_prompt), verbose=True)

# Prompt for user input and save to chat history
if prompt := st.chat_input("Ask me anyting!"): 
	st.session_state.messages.append({"role": "user", "content": prompt})

try:
	# for message in st.session_state.messages:
	# 	if message["role"] == "system":
	# 		streamlit_js_eval(js_expressions="parent.window.location.reload()")
	# 	else:
	# 		with st.chat_message(message["role"]):
	# 			st.write(message["content"])
	# 		download_chat.append(message["role"] + ":")
	# 		download_chat.append(message["content"])
	for message in st.session_state.messages:
		with st.chat_message(message["role"]):
			st.write(message["content"])
		download_chat.append(message["role"] + ":")
		download_chat.append(message["content"])		
	# If last message is not from assistant, generate a new response
	if st.session_state.messages[-1]["role"] != "assistant":
		with st.chat_message("assistant"):
			with st.spinner("Thinking..."):
				response = st.session_state.chat_engine.chat(prompt)
				st.write(response.response)
				message = {"role": "assistant", "content": response.response}
				# Add response to message history
				st.session_state.messages.append(message) 

except Exception as error:
	error_time = datetime.now()
	print("Running into %s at %s. " %(error_time, error))
	st.warning("Running into Error, sorry😞. Please refresh the page and try again later. If error persists, please submit a ticket to protobotsupport@resultant.com.")
	pass    

download_chat = '\n'.join(str(x) for x in download_chat)

col1, col2 = st.columns(2)
with col1:
	if download_chat:
		st.download_button('Download Chat', download_chat)
with col2:
	if st.button("Refresh"):
		streamlit_js_eval(js_expressions="parent.window.location.reload()")

streamlit_analytics.stop_tracking()
