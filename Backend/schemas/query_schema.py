from  pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi import UploadFile, File

class QueryRequest(BaseModel):
    user_query: str
    conversation_id: Optional[str] = None

class QueryReponse(BaseModel):
    user_email: EmailStr
    query_response: str


    
