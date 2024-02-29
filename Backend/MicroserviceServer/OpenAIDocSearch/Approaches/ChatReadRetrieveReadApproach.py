import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from MicroserviceServer.OpenAIDocSearch.Approaches.Approach import Approach
from MicroserviceServer.OpenAIDocSearch.PromptHelper import PromptHelper
from config.ExternalConfiguration import ExternalConfiguration

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
# (answer) with that prompt.
class ChatReadRetrieveReadApproach(Approach):
    config = ExternalConfiguration()
    # Prompt prefix template
    # prompt_prefix = r"""<|im_start|>You are a Koenigsegg customer support agent who helps customers with accurate and concise answer to their questions based on the information based on the provided sources.
    # The sources are provided below with each source having a filename and file path at the start. Do your best to answer the question based on these sources.
    # If you cannot find an answer in the sources, just reply with 'I don't know.'

    # Please keep in mind that your responses should not include assumptions and will remain neutral. After your answer, list the sources in an HTML format for reference, like this:

    # <ul>
    #     <li><a href="FilePath">FileName</a></li>
    #     <!-- Repeat for each relevant source -->
    # </ul>

    # {follow_up_questions_prompt}
    # {injected_prompt}
    # Sources:
    # {sources}
    # <|im_end|>
    # {chat_history}
    # """

    prompt_prefix = r"""<|im_start|>You are a Koenigsegg customer support agent who helps customers with accurate and simple answer to their questions based on the information based on the provided sources.
    The sources are provided below with each source having a filename and file path at the start. Do your best to answer the question based on these sources.
    If you cannot find an answer in the sources, just reply with 'Sorry, I am not able to answer your question.'

    Please keep in mind that your responses should not include assumptions and will remain neutral. After your answer, list the sources in an HTML format for reference, like this:

    <ul>
        <li><a href="FilePath">FileName</a></li>
        <!-- Repeat for each relevant source -->
    </ul>

    {follow_up_questions_prompt}
    {injected_prompt}
    Sources:
    {sources}
    <|im_end|>
    {chat_history}
    """

    prompt_prefix_no_reference = r"""<|im_start|>You are a Koenigsegg customer support agent who helps customers with accurate and simple answer to their questions based on the information based on the provided sources.
    Your answer should be simple, short and should only answer the question asked.The sources are provided below with each source having a filename and file path at the start. Do your best to answer the question based on these sources.
    If you cannot find an answer in the sources, just reply with 'Sorry, I am not able to answer your question.'

    Please keep in mind that your responses should not include assumptions and will remain neutral.

    {follow_up_questions_prompt}
    {injected_prompt}
    Sources:
    {sources}
    <|im_end|>
    {chat_history}
    """

    confirmation_prompt = r"""<|im_start|>See the answer below. 
    Rephrase the answer if the answer mentions something like 'the provided sources', 'the sources', etc by removing the word source. Do not remove anything from the answer.
    If the contains any sources, make sure they are listed as HTML list tag at the end of the answer else rewrite them as below:
    <ul>
        <li><a href="FilePath">FileName</a></li>
        <!-- Repeat for each relevant source -->
    </ul>
    Answer:
    {answer}
    <|im_end|>
    """

    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next. 
    Use double angle brackets to reference the questions, e.g. <<what is the principle of air bending?>>.
    Try not to repeat questions that have already been asked.
    Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    chat_history_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.

Chat History:
{chat_history}

Question:
{question}

Search query:
"""

    def __init__(
        self,
        search_client: SearchClient,
        chatgpt_deployment: str,
        gpt_deployment: str,
        content_field: str,
    ):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.content_field = content_field

        self.config = ExternalConfiguration()

    def run(self, history, overrides: dict) -> any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 10
        exclude_category = overrides.get("exclude_category") or None
        filter = (
            "category ne '{}'".format(exclude_category.replace("'", "''"))
            if exclude_category
            else None
        )

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        prompt = self.chat_history_prompt_template.format(
            chat_history=self.get_chat_history_as_text(
                history, include_last_turn=False
            ),
            question=history[-1].user_message,
        )
        completion = openai.Completion.create(
            api_base=self.config.OPENAIDOCS_OPENAI_BASEURL,
            api_key=self.config.OPENAIDOCS_OPENAI_APIKEY,
            api_type="azure",
            api_version="2023-05-15",
            engine=self.gpt_deployment,
            prompt=prompt,
            temperature=0.4,
            max_tokens=1024,
            n=1,
            stop=["\n"],
        )
        q = completion.choices[0].text

        #Extract Vectors
        embedding_args = {"deployment_id": self.config.OPENAIDOCS_OPENAI_EMBEDDINGS_DEPLOYMENT}
        openai.api_type = "azure"
        openai.api_key = self.config.OPENAIDOCS_OPENAI_APIKEY
        openai.api_base = self.config.OPENAIDOCS_OPENAI_BASEURL
        openai.api_version = "2022-12-01"
        embedding = openai.Embedding.create(**embedding_args, model=self.config.OPENAIDOCS_OPENAI_EMBEDDINGS_DEPLOYMENT, input=history[-1].user_message)
        query_vector = embedding["data"][0]["embedding"]

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
        # if True:#overrides.get("semantic_ranker"):
        #     r = self.search_client.search(
        #         q,
        #         filter=filter,
        #         query_type=QueryType.SEMANTIC,
        #         query_language="en-us",
        #         query_speller="lexicon",
        #         semantic_configuration_name="default",
        #         top=top,
        #         query_caption="extractive|highlight-false"
        #         if use_semantic_captions
        #         else None,
        #         vector=query_vector,
        #         top_k=50,
        #         vector_fields="embedding"
        #     )
        #else:
        r = self.search_client.search(q,
            filter=filter,
            #query_type=QueryType.SEMANTIC,              #For Semantic Search
            #semantic_configuration_name="default",      #For Semantic Search
            #query_caption="extractive|highlight-false", #For Semantic Search
            top=top,
            vector=query_vector,
            top_k=50,
            vector_fields="embedding"
        )
        authorizedDocs = []
        references = []

        for doc in r:
            authorizedDocs.append(doc)
            references.append({
                            "filename":doc["filename"],
                            "filepath":"https://"+self.config.OPENAIDOCS_STORAGE_ACCOUNT+".blob.core.windows.net/"+self.config.OPENAIDOCS_STORAGE_CONTAINER+"/"+doc["filename"]
                        })
            
        if len(authorizedDocs) == 0:
            return {"answer": "I dont know."}        
      
        if use_semantic_captions:
            results = [doc["filename"] + ": " + 
                PromptHelper().NoNewLines(
                    " . ".join([c.text for c in doc["@search.captions"]])
                )
                for doc in authorizedDocs
            ]
        else:
            results = [doc["filename"] + "(" + doc["filepath"] + "): " +
                PromptHelper().NoNewLines(doc[self.content_field]) + "."
                for doc in authorizedDocs
            ]
        content = "\n".join(results)

        follow_up_questions_prompt = (
            self.follow_up_questions_prompt_content
            if overrides.get("suggest_followup_questions")
            else ""
        )

        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None:
            allow_references = overrides.get("references")
            print(type(allow_references))
            if allow_references is not None and allow_references == False:
                print("WITHOUT REFERENCES")
                prompt = self.prompt_prefix_no_reference.format(
                    injected_prompt="",
                    sources=content,
                    chat_history=self.get_chat_history_as_text(history),
                    follow_up_questions_prompt=follow_up_questions_prompt,
                )
            else:
                prompt = self.prompt_prefix.format(
                    injected_prompt="",
                    sources=content,
                    chat_history=self.get_chat_history_as_text(history),
                    follow_up_questions_prompt=follow_up_questions_prompt,
                )
        else:
            prompt = prompt_override.format(
                sources=content,
                chat_history=self.get_chat_history_as_text(history),
                follow_up_questions_prompt=follow_up_questions_prompt,
            )
        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        completion = openai.Completion.create(
            api_base=self.config.OPENAIDOCS_OPENAI_BASEURL,
            api_key=self.config.OPENAIDOCS_OPENAI_APIKEY,
            api_type="azure",
            api_version="2023-05-15",
            engine=self.chatgpt_deployment,
            prompt=prompt,
            temperature=overrides.get("temperature") or 0.7,
            max_tokens=2048,
            n=1,
            stop=["<|im_end|>", "<|im_start|>"],
        )

        prompt1 = self.confirmation_prompt.format(
                answer=completion.choices[0].text,
            )
        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        completion1 = openai.Completion.create(
            api_base=self.config.OPENAIDOCS_OPENAI_BASEURL,
            api_key=self.config.OPENAIDOCS_OPENAI_APIKEY,
            api_type="azure",
            api_version="2023-05-15",
            engine=self.chatgpt_deployment,
            prompt=prompt1,
            temperature=overrides.get("temperature") or 0.7,
            max_tokens=2048,
            n=1,
            stop=["<|im_end|>", "<|im_start|>"],
        )

        #print("Answer: " + completion.choices[0].text)
        #print("Updated Answer: " + completion1.choices[0].text)
        response = {"answer": completion.choices[0].text}

        #if overrides.get("data_points"):
        response["data_points"] = results
        response["references"] = self.get_unique_references(references)
        if overrides.get("thoughts"):
            response[
                "thoughts"
            ] = f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace("\n", "<br>")
        return response
    
    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=2000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = (
                """<|im_start|>"""
                + "\n"
                + str(h.user_message)
                + "\n"
                + """<|im_end|>"""
                + "\n"
                + """<|im_start|>assistant"""
                + "\n"
                + (h.bot_message if h.bot_message is not None else "")
                + "\n"
                # + """<|im_end|>"""
                + history_text
            )
            if len(history_text) > approx_max_tokens * 4:
                break
        return history_text
    
    def get_unique_references(self, references):
        result = [] 
        for i in references: 
            if i not in result: 
                result.append(i)
        return result