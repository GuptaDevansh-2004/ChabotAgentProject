from typing import List
from pydantic import BaseModel, Field
from llm_service.schemas import ChatMessage


class ResponseImage(BaseModel):
    """Defines schema for images to be included along with response text"""
    path: str = Field(default="", description="Path of image to be include in response")
    data: str = Field(default="", description="Image data in base64 embedding form")


class SearchRequest(BaseModel):
    """Defines schema for search service request"""
    prev_context: str = Field(default="", description="Context fetched for responding to previous query")
    message_history: List[ChatMessage] = Field(default=[], description="List of past conversation of user")
    query: str = Field(description="user's current query")
    was_context_valid_old: bool = Field(default=False, description="Indicates whether the context is valid in accordance to query")
    is_follow_up_old: bool = Field(default=False, description="Indicates if follow query was asked or not")
    related_images: List[str] = Field(default=[], description="List of supporting images along with user query")


class SearchResponse(BaseModel):
    """Defines schema for search service response"""
    context: str = Field(default="", description="Context fetched corresponding to gievn query from search index")
    answer: str = Field(default="", description="Answer generated corresponding to query")
    images: List[ResponseImage] = Field(default=[], description="List of supporting images along with text response")
    was_context_valid: bool = Field(default=True, description="Indicates whether the context is valid in accordance to query")
    is_follow_up: bool = Field(default=False, description="Indicates if follow query was asked or not")