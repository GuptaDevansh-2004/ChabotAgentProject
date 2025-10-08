import os
from dotenv import load_dotenv
load_dotenv()
#---------------Libraries for models utilized in vector index service----------------
import clip
import torch
import easyocr
from sentence_transformers import CrossEncoder
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.bedrock_converse import BedrockConverse
from transformers import BlipProcessor, BlipForConditionalGeneration

from llama_index.core import Settings


class IndexConfig:
    """Provide required parameters to configure the services utilized by search index"""

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    #------------Configure Models utilized in index service--------------
    CLIP_MODEL, CLIP_PREPROCESSOR = clip.load("RN50", device=DEVICE)
    CLIP_TOP_K = 20

    CAPTION_PROCESSOR = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    CAPTION_MODEL = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(DEVICE)
    OCR_READER = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

    EMBEDDING_MODEL = GoogleGenAIEmbedding(model="models/embedding-001")

    RERANKER = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

    #---------Configure LLM clients for querying-------------------
    LLM = GoogleGenAI(model="gemini-2.0-flash")
    LLM_AWS = BedrockConverse(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0", 
        region_name='us-east-1',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_ID")
    ) 

    #------Configure llamaindex vector store index----------------
    Settings.llm = LLM
    Settings.embed_model = EMBEDDING_MODEL # embedding model used by llamaindex
    Settings.num_output = 512
    Settings.context_window = 3900

    # Nodes to be retrieved from search index
    TOP_K = 7