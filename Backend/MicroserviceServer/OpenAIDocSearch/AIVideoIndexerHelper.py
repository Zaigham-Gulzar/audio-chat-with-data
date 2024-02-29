import os
import requests
from config.ExternalConfiguration import ExternalConfiguration
from MicroserviceServer.OpenAIDocSearch.AIEnrichmentHelper import AIEnrichmentHelper

config = ExternalConfiguration()

class VideoIndexer:

    def __init__(self) -> None:
        self.access_token = self.get_access_token_by_account_id()

    access_token = ""

    def get_access_token_by_account_id(self):
        try:
            url = "https://api.videoindexer.ai/Auth/trial/Accounts/"+ config.AZURE_VIDEO_INDEXER_ACCOUNT_ID +"/AccessToken?allowEdit=true"

            headers ={
            # Request headers
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': config.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY,
            }

            response = requests.get(url, headers=headers)
            return response.json()
        except Exception as e:
            print(e)
            return e

    def get_video_index_by_id(self, video_id: str):
        try:
            url = "https://api.videoindexer.ai/trial/Accounts/"+ config.AZURE_VIDEO_INDEXER_ACCOUNT_ID + "/Videos/"+ video_id +"/Index?language=en-US&reTranslate=false&includeStreamingUrls=false&includedInsights=Labels,%20Topics,%20Keywords,%20OCR,%20Transcript&includeSummarizedInsights=false&accessToken=" + self.access_token

            headers ={
                # Request headers
                'x-ms-client-request-id': '123',
                'Cache-Control': 'no-cache',
                'Ocp-Apim-Subscription-Key': config.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY,
            }

            response = requests.get(url, headers=headers)
            response.json()
            return response.json()
        except Exception as e:
            print(e)
            return e
        
    def get_videos_list(self):
        try:
            url = "https://api.videoindexer.ai/trial/Accounts/"+ config.AZURE_VIDEO_INDEXER_ACCOUNT_ID +"/Videos?pageSize=25&skip=0&accessToken="+ self.access_token

            haders ={
                # Request headers
                'Cache-Control': 'no-cache',
                'Ocp-Apim-Subscription-Key': config.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY,
            }

            response = requests.get(url, headers=haders)
            return response.json()["results"]
        except Exception as e:
            print(e)
            return e

    def index_video(self, file):
        enrichment_helper = AIEnrichmentHelper()
        uploaded_blob_client = enrichment_helper.upload_blobs(file)
        uploaded_video_response = self.upload_video_to_indexer(str(uploaded_blob_client.blob_name), str(uploaded_blob_client.url))
        return uploaded_blob_client.blob_name + " will be indexed in a few minutes."

    def upload_video_to_indexer(self, media_name: str, media_url: str):
        try:
            print("Media URL: " + str(media_url))
            print(config.APPLICATION_HOSTING_BASE_PATH)
            callback_url = config.APPLICATION_HOSTING_BASE_PATH + "/api/docs/index-video-callback?mediaName=" + media_name
            url = "https://api.videoindexer.ai/trial/Accounts/"+ config.AZURE_VIDEO_INDEXER_ACCOUNT_ID +"/Videos?name="+ media_name +"&privacy=Private&callbackUrl="+ callback_url +"&language=en-US&videoUrl="+ media_url +"&fileName="+ media_name + "&streamingPreset=Default&useManagedIdentityToDownloadVideo=false&accessToken=" + self.access_token

            header ={
            # Request headers
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': config.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY,
            }

            response = requests.post(url, headers=header)
            return response.json()
        except Exception as e:
            print(e)
    
    def get_video_id_by_external_id(self, external_id: str):
        try:
            url = "https://api.videoindexer.ai/trial/Accounts/"+ config.AZURE_VIDEO_INDEXER_ACCOUNT_ID +"/Videos/GetIdByExternalId?externalId="+ external_id +"&accessToken=" + self.access_token

            headers ={
            # Request headers
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': config.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY,
            }

            response = requests.get(url, headers=headers)
            return response.json()
        except Exception as e:
            print(e)
            return e

    def indexer_callback_handler(self, video_id: str, filename: str, filepath: str):
        video_insights = self.get_video_index_by_id(video_id)["videos"][0]["insights"]["transcript"]
        complete_transcript = ""
        for item in video_insights:
            complete_transcript = complete_transcript + " " + str(item["text"])
        enrichment_helper = AIEnrichmentHelper()
        transcript_section = enrichment_helper.create_section_from_transcript(filename, complete_transcript, filepath)
        enrichment_helper.create_search_index()
        enrichment_helper.index_sections(filename, transcript_section)

    def get_blob_download_url(self, video_id: str):
        try:
            url = "https://api.videoindexer.ai/trial/Accounts/"+ config.AZURE_VIDEO_INDEXER_ACCOUNT_ID +"/Videos/"+ video_id +"/SourceFile/DownloadUrl?accessToken=" + self.access_token

            headers ={
                'x-ms-client-request-id': '123',
                'Cache-Control': 'no-cache',
                'Ocp-Apim-Subscription-Key': config.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY,
            }

            response = requests.get(url, headers=headers)
            return response.json()
        except Exception as e:
            print(e)