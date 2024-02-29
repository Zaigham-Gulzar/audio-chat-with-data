from decouple import Config, RepositoryEnv


# The ExternalConfiguration class is used to manage the external configuration of the application.
class ExternalConfiguration:
    # The constructor for the ExternalConfiguration class.
    # It initializes the configuration from an environment file.
    def __init__(self):
        # Load the configuration from the environment file.
        config = Config(RepositoryEnv("config/settings.env"))

        # # The Configuration for the OPENAI Doc Search
        # Load the Azure Cognitive Search configurations
        self.OPENAIDOCS_SEARCH_INDEX = config("OPENAIDOCS_SEARCH_INDEX")
        self.OPENAIDOCS_SEARCH_SERVICE = config("OPENAIDOCS_SEARCH_SERVICE")
        self.OPENAIDOCS_SEARCH_SERVICE_KEY = config("OPENAIDOCS_SEARCH_SERVICE_KEY")

        # Load the Azure OpenAI Configurations
        self.OPENAIDOCS_CHATGPT_DEPLOYMENT = config(
            "OPENAIDOCS_OPENAI_CHATGPT_DEPLOYMENT"
        )
        self.OPENAIDOCS_OPENAI_GPT_DEPLOYMENT = config(
            "OPENAIDOCS_OPENAI_GPT_DEPLOYMENT"
        )
        self.OPENAIDOCS_OPENAI_EMBEDDINGS_DEPLOYMENT = config("OPENAIDOCS_OPENAI_EMBEDDINGS_DEPLOYMENT")
        self.OPENAIDOCS_OPENAI_WHISPER_DEPLOYMENT = config("OPENAIDOCS_OPENAI_WHISPER_DEPLOYMENT")
        self.OPENAIDOCS_OPENAI_WHISPER_API_VERSION = config("OPENAIDOCS_OPENAI_WHISPER_API_VERSION")
        self.OPENAIDOCS_OPENAI_APITYPE = config("OPENAIDOCS_OPENAI_APITYPE")
        self.OPENAIDOCS_OPENAI_APIKEY = config("OPENAIDOCS_OPENAI_APIKEY")
        self.OPENAIDOCS_OPENAI_BASEURL = config("OPENAIDOCS_OPENAI_BASEURL")
        self.OPENAIDOCS_OPENAI_VERSION = config("OPENAIDOCS_OPENAI_VERSION")

        # Load the Azure Blob Storage COnfigurations
        self.OPENAIDOCS_STORAGE_ACCOUNT = config("OPENAIDOCS_STORAGE_ACCOUNT")
        self.OPENAIDOCS_STORAGE_ACCOUNT_KEY = config("OPENAIDOCS_STORAGE_ACCOUNT_KEY")
        self.OPENAIDOCS_STORAGE_CONTAINER = config("OPENAIDOCS_STORAGE_CONTAINER")
        self.OPENAIDOCS_STORAGE_CONNECTION = config("OPENAIDOCS_STORAGE_CONNECTION")

        self.AZURE_VIDEO_INDEXER_ACCOUNT_ID = config("AZURE_VIDEO_INDEXER_ACCOUNT_ID")
        self.AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY = config("AZURE_VIDEO_INDEXER_SUBSCRIPTION_KEY")

        self.AZURE_SPEECH_SERVICE_ENDPOINT = config("AZURE_SPEECH_SERVICE_ENDPOINT")
        self.AZURE_SPEECH_SERVICE_KEY = config("AZURE_SPEECH_SERVICE_KEY")
        self.AZURE_SPEECH_SERVICE_REGION = config("AZURE_SPEECH_SERVICE_REGION")
        self.AZURE_SPEECH_SYNTHESIS_VOICE = config("AZURE_SPEECH_SYNTHESIS_VOICE")
        
        self.APPLICATION_HOSTING_BASE_PATH = config("APPLICATION_HOSTING_BASE_PATH")
