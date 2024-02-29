from io import BytesIO
import os
import re
import logging
import csv
import datetime
import base64
from flask import Flask, request, jsonify, send_file
from bs4 import BeautifulSoup
import openai
import requests
import base64

from MicroserviceServer.LLMIntegration.ChatHistory.ChatHistoryChain import ChatHistoryChain
from config.ExternalConfiguration import ExternalConfiguration

from MicroserviceServer.OpenAIDocSearch.AIEnrichmentHelper import AIEnrichmentHelper
from MicroserviceServer.OpenAIDocSearch.AIVideoIndexerHelper import VideoIndexer

from MicroserviceServer.OpenAIDocSearch.Approaches.ChatReadRetrieveReadApproach import (
    ChatReadRetrieveReadApproach,
)

from MicroserviceServer.OpenAIDocSearch.AITextToSpeechHelper import (
    SpeechSynthesis
)

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
# Importing the external configuration
config = ExternalConfiguration()


# Setting the OpenAI API key from the configuration
os.environ["AZURE_OPENAI_API_KEY"] = config.OPENAIDOCS_OPENAI_APIKEY
os.environ["AZURE_OPENAI_API_INSTANCE_NAME"] = config.OPENAIDOCS_OPENAI_GPT_DEPLOYMENT
os.environ["AZURE_OPENAI_API_DEPLOYMENT_NAME"] = config.OPENAIDOCS_OPENAI_GPT_DEPLOYMENT
os.environ["AZURE_OPENAI_API_VERSION"] = config.OPENAIDOCS_OPENAI_VERSION
os.environ["AZURE_OPENAI_BASE_PATH"] = config.OPENAIDOCS_OPENAI_BASEURL

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

# Creating a Flask application instance
app = Flask(__name__)

# Set up clients for Cognitive Search
searchCredentialKey = AzureKeyCredential(config.OPENAIDOCS_SEARCH_SERVICE_KEY)
search_client = SearchClient(
    endpoint=f"https://{config.OPENAIDOCS_SEARCH_SERVICE}.search.windows.net",
    index_name=config.OPENAIDOCS_SEARCH_INDEX,
    credential=searchCredentialKey,
)

chat_approach = ChatReadRetrieveReadApproach(
        search_client,
        config.OPENAIDOCS_CHATGPT_DEPLOYMENT,
        config.OPENAIDOCS_OPENAI_GPT_DEPLOYMENT,
        KB_FIELDS_CONTENT,
    )

# Function to remove HTML tags from a string using regex
def remove_html_tags(text):
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)

# Function to remove all HTML tags from a string using BeautifulSoup
def remove_html_all_tags(text):
    return BeautifulSoup(text, "html.parser").get_text()

CHAT_HISTORY_COLLECTION = ChatHistoryChain()

def validate_logs_existence(path_to_file: str) -> bool:
    if os.path.isfile(os.path.abspath(path_to_file)) is True:
        return True
    else:
        return False

# WE ARE IDENTIFYING USERS UNIQUELY BY THEIR COOKIE ID
def maintain_user_chat_logs(cookie_id: str, date_time: datetime, message_from: str, message: str):
    try:
        path_to_file = str(os.path.abspath("user_chat_logs/user-chat-logs-" + date_time.strftime('%Y-%m-%d') + ".csv"))
        formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S %p")
        if validate_logs_existence(path_to_file) is True:
            with open(path_to_file, 'a', encoding='UTF-8', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow([formatted_time, cookie_id, message_from, message])
        else:
            with open(path_to_file, 'w+', encoding='UTF-8', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["Date Time", "User Id", "User/AI", "Message"])
                csv_writer.writerow([formatted_time, cookie_id, message_from, message])
    except Exception as e:
        print(str(e))

@app.route("/api/docs/logs", methods=['GET'])
def get_chat_logs_path():
    input_date = request.json["for_date"]
    lookup_path = str(os.path.abspath("user_chat_logs/user-chat-logs-" + input_date + ".csv"))
    if os.path.isfile(os.path.abspath(lookup_path)) is True:
        with open(lookup_path, 'rb') as logs_file_bytes:
            return send_file(BytesIO(logs_file_bytes.read()), download_name="user-chat-logs-" + input_date + ".csv", as_attachment=True)
    else:
        return 'No logs exists for the given date.'

# /api/docs/chat
@app.route("/api/docs/chat", methods=["POST"])
def chat():
    try:
        request_user_id = str(request.json["CookiesId"])
        if CHAT_HISTORY_COLLECTION.exists(request_user_id):
            CHAT_HISTORY_COLLECTION.append_history_record(user_id = request_user_id, user_message = str(request.json['question']))
        else:
            CHAT_HISTORY_COLLECTION.add_new_user_history(user_id = request_user_id, user_message = str(request.json['question']))
        maintain_user_chat_logs(str(request.json['CookiesId']), datetime.datetime.now() ,"User", str(request.json['question']))
        r = chat_approach.run(
            CHAT_HISTORY_COLLECTION.retrieve(request_user_id).user_chat_collection, request.json.get("overrides") or {}
        )
        CHAT_HISTORY_COLLECTION.append_prompt_response(user_id=request_user_id, user_message=request.json['question'], response = str(r.get('answer')))
        maintain_user_chat_logs(str(request.json['CookiesId']), datetime.datetime.now() ,"AI", str(r.get('answer')))

        text_to_speech_synthesizer = SpeechSynthesis()
        r["audio"] =  base64.b64encode(text_to_speech_synthesizer.generte_neural_speech_for_text(r["answer"])).decode('utf-8')

        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500

@app.route("/api/docs/blobupload", methods=["POST"])
def upload_docs():
    helper = AIEnrichmentHelper()
    file = request.files["file"]
    helper.upload_blobs(file)
    print("Upload Successfull.")
    return "Upload Successfull."

@app.route("/api/docs/processfile", methods=["POST"])
def process_docs():
    file = request.files["file"]
    helper = AIEnrichmentHelper()
    helper.upload_file(file)
    return "Upload Successfull."

@app.route("/api/docs/enrichment", methods=["GET"])
def index_blobs():
    helper = AIEnrichmentHelper()
    helper.ai_enrichment_pipeline()
    return "Indexing Successfull."

@app.route("/api/docs/aideployments", methods=["GET"])
def ai_deployments():
    openai.api_type = "azure"
    openai.api_key = config.OPENAIDOCS_OPENAI_APIKEY
    openai.api_base = config.OPENAIDOCS_OPENAI_BASEURL
    openai.api_version = "2022-12-01"
    url = openai.api_base + "/openai/deployments?api-version=2022-12-01" 
    r = requests.get(url, headers={"api-key": config.OPENAIDOCS_OPENAI_APIKEY})
    print(r.text)

@app.route("/api/docs/index-video-transcripts", methods=["GET"])
def video_list_test():
    helper = VideoIndexer()
    file = request.files["file"]
    return helper.index_video(file)

@app.route("/api/docs/index-video-callback", methods=["POST"])
def video_index_callback_handler():
    helper = VideoIndexer()
    filepath =f"https://{config.OPENAIDOCS_STORAGE_ACCOUNT}.blob.core.windows.net/"+config.OPENAIDOCS_STORAGE_CONTAINER+"/"+str(request.args.get("mediaName"))
    print(filepath)
    helper.indexer_callback_handler(str(request.args.get("id")), str(request.args.get("mediaName")), filepath)
    return "Indexing Callback Successfull."

@app.route('/extractwebpage')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Web Content Extractor</title>
    </head>
    <body>
        <h1>Web Content Extractor</h1>
        <form action="/extractprocess" method="post">
            <label for="url">Enter URL:</label>
            <input type="url" id="url" name="url" required>
            <button type="submit">Extract Content</button>
        </form>
    </body>
    </html>
    '''

@app.route('/extractprocess', methods=['POST'])
def extract_content():
    try:
        url = request.form['url']
        
        # Fetch the web page content
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
        
        # Extract text from the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        extracted_content = soup.get_text()
        
        return jsonify({'extracted_content': extracted_content})
    except Exception as e:
        return str(e), 400

# Log the request information before each request
@app.before_request
def log_request_info():
    app.logger.info("Received request: %s %s", request.method, request.path)

def mp3_to_bytes(file_path):
    with open(file_path, 'rb') as mp3_file:
        mp3_bytes = mp3_file.read()
    return mp3_bytes

def mp3_to_base64(file_path):
    mp3_bytes = mp3_to_bytes(file_path)
    base64_encoded = base64.b64encode(mp3_bytes)
    return base64_encoded


# Run the Flask application
# if __name__ == "__main__":
#     # app.run(debug=True)