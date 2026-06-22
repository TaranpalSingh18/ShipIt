from pydantic import BaseModel
from typing import Optional, Any


class QueryRequest(BaseModel):
    project_id: int
    user_query: str
    conversation_id: Optional[str] = None


class QueryReponse(BaseModel):
    user_email: str
    query_response: Any


class ProjectCreateRequest(BaseModel):
    project_name: Optional[str] = None


class ProjectCreateResponse(BaseModel):
    project_id: int
    project_name: Optional[str] = None

