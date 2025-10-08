from pydantic import BaseModel, Field
from typing import Optional, List


class SourceMetadata(BaseModel):
    """Schema for metadata retrieved with nodes"""
    IMAGE_PATHS: Optional[List[str]] = Field(default=None, description="Paths of images referred by nodes")


class SourceNode(BaseModel):
    """Defines schema for nodes from retriever"""
    text: str = Field(description="Text content of the node")
    metadata: SourceMetadata = Field(description="Metadata attached with node")