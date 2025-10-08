import os
import json
from typing import Any, Optional, List, Dict
from dotenv import load_dotenv
load_dotenv()
#-----Libraries utilized for interacting with LLM------
from google import genai
from google.api_core import exceptions
from concurrent.futures import ThreadPoolExecutor
from google.genai.types import Content, Part, GenerateContentConfig, ContentListUnion
#------Libraries for custom functionalities-------
from llm_service.config import LLMConfig as settings
from llm_service.prompts import LLMPrompts as prompts
from llm_service.schemas import LLMResponse, ChatMessage
from llm_service.utilities import JSONDataProcessor as responseParser, TextProcessor as contentprocessor

#-----Paramters required by LLM------
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')


class LLMChatService:
    """Provides utilities to interact with LLM models i.e. Gemini"""

    def __init__(self) -> None:
        self._client = None
        self._initialize()


    def _initialize(self) -> None:
        """Initialize a LLM client for interacting with Gemini"""
        try:
            self._client = genai.Client(api_key=GOOGLE_API_KEY)
            print("[LLM Service][Chat] Intialized a LLM client for Gemini successfully....")
        except Exception as e:
            print(f"[LLM Service][Chat] LLM Client for Gemini not initialized due to following reason: {e}")


    async def generate_response(self, *, query: str, context: str, message_history: List[ChatMessage]) -> LLMResponse:
        """Generates and Returns LLM response for given query based on data from given knowledge base"""

        try:
            print("[LLM Service][Chat] Initialized request for user's query.......")
            with ThreadPoolExecutor(max_workers=1) as executor:
                llm_response = executor.submit(self._generate_llm_response, query, context, message_history).result()
            print("[LLM Service][Chat] Response for user's query generated successfully....")
            return llm_response
        
        except exceptions.GoogleAPICallError as e:
            print("[LLM Service][Chat] Response for user's query cannot be generated ......")
            raise exceptions.InternalServerError(message=e.message, errors=e.errors)
        

    def _generate_llm_response(self, query: str, context: str, message_history: List[ChatMessage]) -> LLMResponse:
        """Initialize a LLM chat session. Returns response for given query on the basis of retrieved context and message history"""

        print("[LLM Service][Chat] Initiated a chat session with LLM client.....")
        llm_contents: ContentListUnion = [] # Stores the contents to be passed to llm model

        for msg in message_history[-settings.MAX_HISTORY:]:
            if msg.role.lower() == 'user':
                llm_contents.append(Content(
                    role='user', 
                    parts=[Part(text=contentprocessor.normalize_content(msg.content))]
                ))
            elif msg.role.lower() in ['model', 'assistant']:
                llm_contents.append(Content(
                    role='model', 
                    parts=[Part(text=contentprocessor.normalize_content(msg.content))]
                ))

        # Configure parameters for LLM
        model_config = GenerateContentConfig(
            system_instruction = prompts.generate_system_prompt(query, context),
            temperature = settings.TEMPERATURE,
            top_k = settings.TOP_K,
            top_p = settings.TOP_P,
            response_mime_type = settings.RESPONSE_TYPE,
            max_output_tokens = settings.MAX_OUTPUT_TOKENS,
        )

        try:
            response = self._client.models.generate_content(
                model=settings.MODEL,
                contents=llm_contents,
                config=model_config
            )

            if response.parsed:
                response_data = response.parsed
            else:
                try:
                    response_data = json.loads(str(response.text))
                except json.JSONDecodeError:
                    response_data = responseParser.parse_json(str(response.text))
            print(f"[LLM Service][Chat] Response for chat session generated successfully: {response_data}")

            return LLMResponse(
                answer= response_data.get('answer', 'Apology cannot generate answer... Please try again'),
                images = response_data.get('images', []),
                was_context_valid = response_data.get('was_context_valid', True),
                is_follow_up = response_data.get('is_follow_up', False)
            )

        except Exception as e:
            print(f"[LLM Service][Chat] Response for chat session not created successfully due to {e}")
            raise exceptions.GoogleAPICallError(message=f"Cannot generate response for chat session", errors=(e,))