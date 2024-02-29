import os
import io
import openai
import requests
import json
import re
import base64

from pypdf import PdfReader, PdfWriter

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.storage.blob import BlobServiceClient
from config.ExternalConfiguration import ExternalConfiguration

config = ExternalConfiguration()

# Set up clients for Cognitive Search and Storage
searchCredentialKey = AzureKeyCredential(config.OPENAIDOCS_SEARCH_SERVICE_KEY)

MAX_SECTION_LENGTH = 1000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100


class AIEnrichmentHelper:
    def ai_enrichment_pipeline(self):
        #Create and Index
        self.create_search_index()

    def create_search_index(self):
        print(f"Ensuring search index {config.OPENAIDOCS_SEARCH_INDEX} exists")
        index_client = SearchIndexClient(
            endpoint=f"https://{config.OPENAIDOCS_SEARCH_SERVICE}.search.windows.net/", credential=AzureKeyCredential(config.OPENAIDOCS_SEARCH_SERVICE_KEY)
        )
        if config.OPENAIDOCS_SEARCH_INDEX not in index_client.list_index_names():
            index = SearchIndex(
                name=config.OPENAIDOCS_SEARCH_INDEX,
                fields=[
                    SimpleField(name="id", type="Edm.String", key=True),
                    SimpleField(name="filename", type="Edm.String"),
                    SimpleField(name="filepath", type="Edm.String"),
                    SearchableField(name="content", type="Edm.String", analyzer_name="en.microsoft"),
                    SearchField(
                        name="embedding",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        hidden=False,
                        searchable=True,
                        filterable=False,
                        sortable=False,
                        facetable=False,
                        vector_search_dimensions=1536,
                        vector_search_configuration="default",
                    ),
                ],
                semantic_settings=SemanticSettings(
                    configurations=[
                        SemanticConfiguration(
                            name="default",
                            prioritized_fields=PrioritizedFields(
                                title_field=None, prioritized_content_fields=[SemanticField(field_name="content")]
                            ),
                        )
                    ]
                ),
                vector_search=VectorSearch(
                    algorithm_configurations=[
                        VectorSearchAlgorithmConfiguration(
                            name="default", kind="hnsw", hnsw_parameters=HnswParameters(metric="cosine")
                        )
                    ]
                ),
            )
            print(f"Creating {config.OPENAIDOCS_SEARCH_INDEX} search index")
            index_client.create_index(index)
        else:
            print(f"Search index {config.OPENAIDOCS_SEARCH_INDEX} already exists")

    def upload_blobs(self, file):
        blob_service = BlobServiceClient(
            account_url=f"https://{config.OPENAIDOCS_STORAGE_ACCOUNT}.blob.core.windows.net",
            credential=config.OPENAIDOCS_STORAGE_ACCOUNT_KEY,
        )
        blob_container = blob_service.get_container_client(
            config.OPENAIDOCS_STORAGE_CONTAINER
        )
        if not blob_container.exists():
            blob_container.create_container()

        # if file is PDF split into pages and upload each page as a separate blob
        if os.path.splitext(file.filename)[1].lower() == ".pdf":
            # Upload Complete file for references:
            uploaded_blob = blob_container.upload_blob(file.filename, file, overwrite=True)
            reader = PdfReader(file)
            pages = reader.pages

            for i in range(len(pages)):
                # blob_name = self.blob_name_from_file_page(file.filename, i)
                blob_name = (
                    os.path.splitext(os.path.basename(file.filename))[0]
                    + f"-{i}"
                    + ".pdf"
                )
                f = io.BytesIO()
                writer = PdfWriter()
                writer.add_page(pages[i])
                writer.write(f)
                f.seek(0)
                uploaded_blobs = blob_container.upload_blob(blob_name, f, overwrite=True)
        else:
            blob_name = os.path.basename(file.filename)
            uploaded_blob = blob_container.upload_blob(
                blob_name, file, overwrite=True
            )
            print(
                uploaded_blob.account_name
                + "### "
                + uploaded_blob.container_name
                + " "
                + uploaded_blob.blob_name
            )
        return uploaded_blob

    def index_sections(self, filename, sections):
        print("...................START INDEXING..........................")
        search_client = SearchClient(
            endpoint=f"https://{config.OPENAIDOCS_SEARCH_SERVICE}.search.windows.net/", index_name=config.OPENAIDOCS_SEARCH_INDEX, credential=AzureKeyCredential(config.OPENAIDOCS_SEARCH_SERVICE_KEY)
        )
        i = 0
        batch = []
        for s in sections:
            batch.append(s)
            i += 1
            if i % 1000 == 0:
                results = search_client.upload_documents(documents=batch)
                succeeded = sum([1 for r in results if r.succeeded])
                print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
                batch = []
        print("...................INDEXING..........................")
        if len(batch) > 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")

    def upload_file(self, file):
        filepath = self.upload_blobs(file).url
        page_map = self.get_document_text(file)
        sections = self.create_sections(file.filename,
                    filepath,
                    page_map,
                    #embedding_deployment,
                    #embedding_model,
                )
        #if use_vectors and vectors_batch_support:
        #sections = update_embeddings_in_batch(sections)
        self.create_search_index()
        self.index_sections(file.filename, sections)

    def upload_media(self, media_buffer):
        media_transcript = self.get_video_transcript(media_buffer)
        print(media_transcript)
        trasncript_section = self.create_section_from_transcript(media_buffer.name, media_transcript)
        print(trasncript_section)
        self.index_sections(trasncript_section)

    def get_document_text(self, file):
        offset = 0
        page_map = []
        reader = PdfReader(file)
        pages = reader.pages
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)

        return page_map
    
    #def create_sections(filename, page_map, use_vectors, embedding_deployment: str = None, embedding_model: str = None):
    def create_sections(self, filename, filepath, page_map, embedding_deployment: str = None, embedding_model: str = None):
        file_id = self.filename_to_id(filename)
        for i, (content, pagenum) in enumerate(self.split_text(page_map, filename)):
            section = {
                "id": f"{file_id}-page-{i}",
                "content": content,
                "filename": filename,
                "filepath": filepath,
                "embedding": self.compute_embedding(content)
            }
            yield section

    def create_section_from_transcript(self, filename, sentences, fileurl):
        yield {
            "id": self.filename_to_id(filename),
            "content": sentences,
            "filename": filename,
            "filepath": fileurl,
            "embedding": self.compute_embedding(sentences)
        }

    def filename_to_id(self, filename):
        if(len(filename.split("."))>1):
            filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", filename)
            return f"file-{filename_ascii}"

    def split_text(self, page_map, filename):
        SENTENCE_ENDINGS = [".", "!", "?"]
        WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

        def find_page(offset):
            num_pages = len(page_map)
            for i in range(num_pages - 1):
                if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                    return i
            return num_pages - 1

        all_text = "".join(p[2] for p in page_map)
        length = len(all_text)
        start = 0
        end = length
        while start + SECTION_OVERLAP < length:
            last_word = -1
            end = start + MAX_SECTION_LENGTH

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while (
                    end < length
                    and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT
                    and all_text[end] not in SENTENCE_ENDINGS
                ):
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                    end = last_word  # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while (
                start > 0
                and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT
                and all_text[start] not in SENTENCE_ENDINGS
            ):
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield (section_text, find_page(start))

            last_table_start = section_text.rfind("<table")
            if last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start > section_text.rfind("</table"):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
                # If last table starts inside SECTION_OVERLAP, keep overlapping
                start = min(end - SECTION_OVERLAP, start + last_table_start)
            else:
                start = end - SECTION_OVERLAP

        if start + SECTION_OVERLAP < end:
            yield (all_text[start:end], find_page(start))

    def compute_embedding(self, text):
        embedding_args = {"deployment_id": config.OPENAIDOCS_OPENAI_EMBEDDINGS_DEPLOYMENT}
        openai.api_type = "azure"
        openai.api_key = config.OPENAIDOCS_OPENAI_APIKEY
        openai.api_base = config.OPENAIDOCS_OPENAI_BASEURL
        openai.api_version = "2022-12-01"
        return openai.Embedding.create(**embedding_args, model=config.OPENAIDOCS_OPENAI_EMBEDDINGS_DEPLOYMENT, input=text)["data"][0]["embedding"]