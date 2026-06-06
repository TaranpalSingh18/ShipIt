from fastapi import APIRouter, Depends, HTTPException, status
import json
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import TypedDict
from db import get_db
from models.user import User
from routes.auth.auth import ALGORITHM, SECRET_KEY
from schemas.query_schema import QueryReponse, QueryRequest
from langchain_groq.chat_models import ChatGroq
import os 
from dotenv import load_dotenv
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model="llama-3.1-8b-instant", api_key=groq_api_key)


query = APIRouter(prefix='/api')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/login')


class ProductRequirements(TypedDict):
    user_query: str

    fully_answered: bool
    follow_up_questions: list[str]

    problem_and_customer: str
    product_and_value_prop: str
    business_and_revenue_model: str
    traction_and_metrics: str
    strategy_priorities: str


class ProductQuestions(TypedDict):
      user_query: str
      fully_answered: bool
      follow_up_questions: list[str]
      question_mapping: dict

QUESTIONS = {
    "customer_segment": "Which customer segment are you specifically targeting?",
    "pain_point": "What is the biggest pain point for these customers?",
    "frequency": "How frequently does this problem occur?",
    "current_solution": "How are customers currently solving this problem?",
    "advantage": "How is your solution better than existing alternatives?",
    "validation": "Have you conducted customer interviews or validated the problem?"
}


def get_answer(state: ProductQuestions):
      
      query = state["user_query"]
      prompt = f"""
        You are a senior product manager.

        Analyze the user response and determine which product discovery
        questions have already been answered.

        Questions:

        1. customer_segment:
        {QUESTIONS["customer_segment"]}

        2. pain_point:
        {QUESTIONS["pain_point"]}

        3. frequency:
        {QUESTIONS["frequency"]}

        4. current_solution:
        {QUESTIONS["current_solution"]}

        5. advantage:
        {QUESTIONS["advantage"]}

        6. validation:
        {QUESTIONS["validation"]}

        User Response:
        {query}

        Return ONLY valid JSON.

        Example:

        {{
            "customer_segment": {{
                "answered": true,
                "answer": "College students"
            }},
            "pain_point": {{
                "answered": true,
                "answer": "Need interview practice"
            }},
            "frequency": {{
                "answered": false,
                "answer": ""
            }},
            "current_solution": {{
                "answered": false,
                "answer": ""
            }},
            "advantage": {{
                "answered": false,
                "answer": ""
            }},
            "validation": {{
                "answered": false,
                "answer": ""
            }}
        }}

        Return JSON only.
    """
      
      llm_answer = llm.invoke(prompt)

      try:
            llm_content = llm_answer.content.strip()

            if llm_content.startswith("```json"):
                  llm_content = llm_content.replace("```json", "")
                  llm_content = llm_content.replace("```", "").strip()

            result = json.loads(llm_content)

            follow_up_questions = []

            for key, value in result.items():

                if not value["answered"]:
                    follow_up_questions.append(
                        QUESTIONS[key]
                    )

            state["question_mapping"] = result

            state["follow_up_questions"] = follow_up_questions

            state["fully_answered"] = len(follow_up_questions) == 0

            return state


      except Exception as e:

            state["fully_answered"] = False

            state["question_mapping"] = {}

            state["follow_up_questions"] = [
                f"Could not parse LLM response: {str(e)}"
            ]

            return state


def get_prob(state: ProductRequirements):

    query = state["user_query"]

    prompt = f"""
    You are a senior product assistant.

    Goal: Understand what problem is being solved and for whom.

    Questions to verify:

    1. Which customer segment are you specifically targeting?
    2. What is the biggest pain point for these customers?
    3. How frequently does this problem occur?
    4. How are customers currently solving this problem?
    5. How is your solution better than existing alternatives?
    6. Have you conducted customer interviews or validated the problem?

    Be honest with everything and ask everything that should be meant to be asked by the user. Be honest

    User Response:
    {query}

    Determine whether all required information is present.

    Return ONLY valid JSON in this format:

    {{
        "fully_answered": true,
        "follow_up_questions": []
    }}

    OR

    {{
        "fully_answered": false,
        "follow_up_questions": [
            "question 1",
            "question 2"
        ]
    }}

    Return JSON only.
    """

    llm_response = llm.invoke(prompt)

    try:
        content = llm_response.content.strip()

        if content.startswith("```json"):
            content = content.replace("```json", "")
            content = content.replace("```", "").strip()

        result = json.loads(content)

        state["fully_answered"] = result["fully_answered"]
        state["follow_up_questions"] = result["follow_up_questions"]

        return state

    except Exception as e:
        state["fully_answered"] = False
        state["follow_up_questions"] = [
            f"Could not parse LLM response: {str(e)}"
        ]

        return state

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
def get_query(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user)
):

    state: ProductQuestions = {
        "user_query": payload.user_query,
        "fully_answered": False,
        "follow_up_questions": [],
        "question_mapping": {}
    }

    result = get_answer(state)

    return QueryReponse(
        user_email=current_user.email,
        query_response=result
    )


@query.get('/query')
def get_response(current_user: User = Depends(get_current_user)):
	return {'message': 'Authorized', 'user_email': current_user.email}
