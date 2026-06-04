import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from schemas.auth import Signup
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from models.user import User
from db import get_db


auth = APIRouter(tags=["auth"], prefix="/api")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    token_data = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=1))
    token_data.update({"exp": expire})
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)


# WHY SECRET KEY WAS INCLUDED WHEN WE ENCODE JWT? 
# TO SIGN THE RESPONSE (TOKEN DATA) --> WE NEED SECRET KEY. esa bhi  ho sakta hai ki koi hacker us token ko decode krke value change krke bhej de --> that is why signing the token is important

@auth.post('/signup')
def create_account(payload: Signup, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(detail="User is existing", status_code=400)
    ## append it in the database
    hashed_pass = pwd_context.hash(payload.password)

    new_user = User(
        email=payload.email,
        name=payload.name,
        password=hashed_pass,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message":"new user has been created"}

@auth.post('/login')
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(detail="User - Not found", status_code=400)

    if not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(detail="Invalid credentials", status_code=400)

    access_token = create_access_token({"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
    

