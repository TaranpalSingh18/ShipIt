from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from db import get_db
from models.user import User
from routes.auth.auth import ALGORITHM, SECRET_KEY
from schemas.query_schema import QueryReponse, QueryRequest

query = APIRouter(prefix='/api')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/login')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail='Could not validate credentials',
		headers={'WWW-Authenticate': 'Bearer'},
	)

	try:
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		user_email = payload.get('sub')
		if user_email is None:
			raise credentials_exception
	except JWTError:
		raise credentials_exception

	user = db.query(User).filter(User.email == user_email).first()
	if user is None:
		raise credentials_exception

	return user

@query.post('/query', response_model=QueryReponse)
def get_query(payload: QueryRequest, current_user: User = Depends(get_current_user)):
	return QueryReponse(
		user_email=current_user.email,
		query_response=f'Received query: {payload.user_query}',
	)

@query.get('/query')
def get_response(current_user: User = Depends(get_current_user)):
	return {'message': 'Authorized', 'user_email': current_user.email}
