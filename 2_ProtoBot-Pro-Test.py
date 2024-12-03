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
	page_title="ProtoBot Pro Test",
	page_icon="🤖",
)
hide_pages(["functions"])

# Resultant Key
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

st.title("🤖 ProtoBot Pro Test")

uploaded_files = st.file_uploader("Upload files", type=("txt", "pdf", "docx", "pptx", "csv", "xlsx"), accept_multiple_files = True)

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
		Settings.llm = OpenAI(model="gpt-4-0125-preview",
							  temperature = temperature,
							  system_prompt = system_prompt)
		# Additional logic for switching to OpenAI GPT
	if "chat_engine" in st.session_state.keys():
		print("Switch LLM")
		st.session_state.chat_engine = index.as_chat_engine(chat_mode = "best", llm = Settings.llm, context_prompt = (system_prompt), verbose=True)

# Now setup your radio button with the callback
model_choice = st.sidebar.radio(
	"LLM_Model",
	options = ["GPT", "Gemini"],
	index = 0,
	horizontal = True,
	on_change = switch_llm,  # Pass the function reference without calling it
	key = 'LLM_Model'  # It's a good practice to provide a key argument for widgets
)

temperature = st.sidebar.slider("Temperature (Creativity)", 0.0, 2.0, 1.0, 0.1)
top_p = st.sidebar.number_input("Top P", 0.0, 1.0, 1.0, 0.1)
top_k = st.sidebar.number_input("Top K", 1, 100, 1)
# print(temperature)

system_prompt = '''
			You are a Gen AI virtual assistant for a consulting company named Resultant. Your name is Proto Bot. 
			Luke Zhang from the Prototyping Team created you.
			'''

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

st.sidebar.title("WARNING!")
st.sidebar.markdown("1. This is the most advanced ProtoBot that is both Q&A Agent and Assistant Agent.")
st.sidebar.markdown("2. ProtoBot Pro can live process files and utitlize all Resultant Data at the same time.")
st.sidebar.markdown("2. It also gives you the ability to use two most powerful LLMs (OpenAI's GPT4 and Google's Gemini) with different Configurations.")
st.sidebar.markdown("3. But it's in testing phrase with lots of bugs.")
st.sidebar.markdown("4. So please bear with me as we are improving it as fast as we can.")
st.sidebar.markdown("4. If you run into any errors or want to start a new chat, please click the Refresh button.")
st.sidebar.markdown("5. Appreciate the support and patience as always.")

# Instruction Side Bar
st.sidebar.title("Example Prompts")
st.sidebar.markdown("1. What does the Prototyping Team do?")
st.sidebar.markdown("2. Help me fix the grammatical and spelling errors in the following text.")
st.sidebar.markdown("3. Draft a holiday thank-you email to my client.")
st.sidebar.markdown("4. Write a High Five note to appreciate a coworker.")
st.sidebar.markdown("5. Show Resultant's values and mission Statement.")
st.sidebar.markdown("6. What kind of services does Resultant provide?")
st.sidebar.markdown("7. Tell me the differences between the files/projects.")
st.sidebar.markdown("8. What's the budget for the file/project?")
st.sidebar.markdown("9. List the deliverables and Timeline of the project.")

# Initialize the chat messages history
if "messages" not in st.session_state.keys(): 
	st.session_state.messages = [
		{"role": "assistant", "content": "My favorite Rezzer, how can I help?📖"}
	]

load_files_text = ""
file_count = 0  
file_names_list = []
# file_pass_llm = False

summarize_flag = False

if uploaded_files: 
	for uploaded_file in uploaded_files:
		bytes_data = uploaded_file.read()
		# print(bytes_data)
		# print(uploaded_file.type)
		# print(uploaded_file)
		if uploaded_file.type == "application/pdf": 
			file_content = read_pdf(bytes_data)
		elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or uploaded_file.type == "application/msword":
			file_content = read_docx(bytes_data)
		elif uploaded_file.type == "text/plain":
			file_content = read_txt(bytes_data)
		elif uploaded_file.type == "text/csv":
			file_content = read_csv(bytes_data)
		elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
			file_content = read_excel(bytes_data)
		else:
			file_content = read_ppt(bytes_data)
		file_count += 1 
		load_files_text += "This is file you need to proces. The file name is: " +str(uploaded_file.name) + ". And the content of the file is: " + os.linesep + file_content + os.linesep
		file_names_list.append(uploaded_file.name)
file_names = ', '.join(map(str, file_names_list))

with st.spinner(text="Loading and indexing docs – hang tight!"):
	index = load_data()
download_chat = []

if "chat_engine" not in st.session_state.keys(): # Initialize the chat engine
	# print("Chat Engine Created")
	st.session_state.chat_engine = index.as_chat_engine(chat_mode = "best", llm = Settings.llm, context_prompt = (system_prompt), verbose=True)

# Prompt for user input and save to chat history
if prompt := st.chat_input("Ask me anyting!"): 
	st.session_state.messages.append({"role": "user", "content": prompt})

try:
	for message in st.session_state.messages:
		with st.chat_message(message["role"]):
			st.write(message["content"])
		download_chat.append(message["role"] + ":")
		download_chat.append(message["content"])

	# If last message is not from assistant, generate a new response
	if st.session_state.messages[-1]["role"] != "assistant":
		with st.chat_message("assistant"):
			with st.spinner("Thinking..."):
				if uploaded_files and prompt and "load_files_text" not in st.session_state:
					response = st.session_state.chat_engine.chat(load_files_text + os.linesep + prompt)
					st.write(response.response)
					message = {"role": "assistant", "content": response.response}
					# Add response to message history
					st.session_state.messages.append(message) 
					st.session_state.load_files_text = True
					# print("hit file + prompt")
				elif prompt:
					# print("Before Exception")
					# print(prompt)
					response = st.session_state.chat_engine.chat(prompt)
					st.write(response.response)
					message = {"role": "assistant", "content": response.response}
					st.session_state.messages.append(message) # Add response to message history
					# print("hit prompt")
				else:
					# print("Hit Pass")
					pass
except Exception as error:
	error_time = datetime.now()
	print("Running into %s at %s. " %(error_time, error))
	st.warning("Running into Error, sorry😞. Please refresh the page and try again later. If error persists, please submit a ticket to protobotsupport@resultant.com.")
	pass    

download_chat = ''.join(str(x) for x in download_chat)

col1, col2, col3 = st.columns(3)
with col1:
	if download_chat:
		st.download_button('Download Chat', download_chat)
with col2:
	if st.button("Refresh"):
		streamlit_js_eval(js_expressions="parent.window.location.reload()")
with col3:
	if file_names:
		if st.button("Summarize"):
			summarize_flag = True
			# summarize_prompt = "Create a summary for the content above."
			summarize_prompt = "Summarize the content for me."
			# prompt = "Based on the " + all_file_names + ", create a 1-page summary that includes the client, scope of work, key technologies, findings, recommendations, and outcomes."
			# st.session_state.messages.append({"role": "user", "content": summarize_prompt}) 
			with st.spinner("Thinking..."):
				if uploaded_files and "load_files_text" not in st.session_state:
					response = st.session_state.chat_engine.chat(load_files_text + os.linesep + summarize_prompt)
					st.session_state.load_files_text = True
				else:
					response = st.session_state.chat_engine.chat(summarize_prompt)
				message = {"role": "assistant", "content": response.response}
				st.session_state.messages.append(message) 

if (summarize_flag):
	with st.chat_message("user"):
		st.write(summarize_prompt)
	with st.chat_message("assistant"):
		st.write(response.response)
	# with st.chat_message(message["role"]):
	# 		st.write(message["content"])
	summarize_flag = False
streamlit_analytics.stop_tracking()
