from pydantic import BaseModel, Field
from typing import List


class LLMResponse(BaseModel):
    """Defines schema for LLM Chat response"""
    answer: str = Field(default="", description="Text response by the LLM for given query")
    images: List[str] = Field(default=[], description="Images related to text response")
    was_context_valid: bool = Field(default=True, description="Indicates whether context completely generated the response")
    is_follow_up: bool = Field(default=False, description="Indicates about continuity of response on basis of current chat session")


class ChatMessage(BaseModel):
    """Defines schema for LLM chat messages (including history)"""
    role: str = Field(description="The current actor providing content")
    content: str = Field(description="Message by the current actor")