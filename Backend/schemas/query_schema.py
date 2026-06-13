from  pydantic import BaseModel, EmailStr
from typing import Optional, Any
from fastapi import UploadFile, File

class QueryRequest(BaseModel):
    project_id: int
    user_query: str
    conversation_id: Optional[str] = None

class QueryReponse(BaseModel):
    user_email: str
    query_response: Any
    
