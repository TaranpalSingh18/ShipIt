from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import TypedDict, Any, NotRequired
import json
import os
from dotenv import load_dotenv
from tavily import TavilyClient
from db import get_db
from models.user import User, Project
from routes.auth.auth import ALGORITHM, SECRET_KEY
from routes.customer.voice_analysis import generate_customer_voice
from schemas.query_schema import QueryReponse, QueryRequest
from langchain_groq.chat_models import ChatGroq
from timing import PipelineTimer

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

llm = ChatGroq(model="llama-3.1-8b-instant", api_key=groq_api_key)

query = APIRouter(prefix="/api")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


class ProductQuestions(TypedDict):
    user_query: str
    fully_answered: bool
    follow_up_questions: list[str]
    question_mapping: dict[str, Any]
    product_context: str
    market_search_query: str
    market_analysis: list[dict[str, str]]
    customer_voice: dict[str, Any]
    pipeline_timing: NotRequired[dict[str, Any]]


QUESTIONS = {
    "customer_segment": "Which customer segment are you specifically targeting?",
    "pain_point": "What is the biggest pain point for these customers?",
    "frequency": "How frequently does this problem occur?",
    "current_solution": "How are customers currently solving this problem?",
    "advantage": "How is your solution better than existing alternatives?",
    "validation": "Have you conducted customer interviews or validated the problem?",
}


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()
    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def parse_llm_json(content: str) -> dict[str, Any]:
    cleaned = strip_code_fences(content)
    return json.loads(cleaned)


def build_follow_up_questions(result: dict[str, Any]) -> list[str]:
    follow_up_questions: list[str] = []

    for key in QUESTIONS:
        value = result.get(key, {})
        if not isinstance(value, dict):
            follow_up_questions.append(QUESTIONS[key])
            continue

        answered = value.get("answered", False)
        if not answered:
            follow_up_questions.append(QUESTIONS[key])

    return follow_up_questions


def build_context_prompt(result: dict[str, Any]) -> str:
    return f"""
You are a senior product strategist.

Based on the product discovery answers below, create a detailed
product context document.

Answers:
{json.dumps(result, indent=2)}

Return a structured summary covering:

1. Product Overview
2. Target Customers
3. Core Pain Point
4. Current Alternatives
5. Unique Value Proposition
6. Validation Status
7. Key Risks
8. Product Vision

Write concise but detailed paragraphs.
""".strip()


def build_market_prompt(product_context: str, tavily_results: dict[str, Any]) -> str:
    return f"""
You have the whole context of the market analysis now, You have to make a JSON now.

Return ONLY this JSON shape:

{{
  "competitors": [
    {{
      "comp_name": "Apple Music",
      "competitor_because": "Reason why it is considered as a competitor"
    }}
  ]
}}

Rules:
- Return JSON only, nothing more.
- Only include real competitors.
- Keep reasons short and specific.

Product Context:
{product_context}

Search Results:
{json.dumps(tavily_results, indent=2)}
""".strip()


def analyze_product_answers(state: ProductQuestions) -> ProductQuestions:
    query_text = state["user_query"]

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
{query_text}

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
""".strip()

    try:
        llm_answer = llm.invoke(prompt)
        print("LLM raw response for analyze_product_answers:", llm_answer.content)
        result = parse_llm_json(llm_answer.content)
    except Exception as e:
        print("LLM parse/invoke failed:", repr(e))
        # Fallback: try simple heuristics to extract obvious answers from the user's text
        def heuristic_parse_from_text(text: str) -> dict[str, Any]:
            t = text.lower()
            parsed: dict[str, Any] = {}
            # frequency
            if "every" in t or "season" in t or "placement season" in t:
                parsed["frequency"] = {"answered": True, "answer": "Every placement season"}
            # current solution
            current = []
            for token in ("youtube", "leetcode", "friends", "mock interview", "mock interviews"):
                if token in t:
                    current.append(token)
            if current:
                parsed["current_solution"] = {"answered": True, "answer": ", ".join(current)}
            return parsed

        result = heuristic_parse_from_text(query_text)

    # Ensure mapping has required keys in a consistent shape
    def normalize_question_mapping(res: dict[str, Any]) -> dict[str, Any]:
        norm: dict[str, Any] = {}
        for key in QUESTIONS:
            val = res.get(key, {})
            if isinstance(val, dict):
                answered = bool(val.get("answered", False))
                answer = str(val.get("answer", "")).strip()
            elif isinstance(val, str):
                answered = bool(val.strip())
                answer = val.strip()
            else:
                answered = False
                answer = ""
            norm[key] = {"answered": answered, "answer": answer}
        return norm

    result = normalize_question_mapping(result)

    follow_up_questions = build_follow_up_questions(result)
    fully_answered = len(follow_up_questions) == 0

    state["question_mapping"] = result
    state["follow_up_questions"] = follow_up_questions
    state["fully_answered"] = fully_answered

    return state


def generate_product_context(question_mapping: dict[str, Any]) -> str:
    context_prompt = build_context_prompt(question_mapping)
    context_response = llm.invoke(context_prompt)
    return context_response.content.strip()


def _clean_search_fragment(text: str) -> str:
    return " ".join(text.replace("\n", " ").replace("\r", " ").split()).strip(" ,;:.-")


def build_market_search_query(question_mapping: dict[str, Any]) -> str:
    fragments: list[str] = []

    def add_fragment(value: Any) -> None:
        if not isinstance(value, dict):
            return

        answer = _clean_search_fragment(str(value.get("answer", "")))
        if answer:
            fragments.append(answer)

    add_fragment(question_mapping.get("customer_segment"))
    add_fragment(question_mapping.get("pain_point"))
    add_fragment(question_mapping.get("current_solution"))
    add_fragment(question_mapping.get("advantage"))

    query_parts = [part for part in fragments if part]
    search_query = "; ".join(query_parts)

    if len(search_query) > 350:
        search_query = search_query[:347].rstrip(" ,;:-") + "..."

    return search_query


def get_tavily_results(search_query: str) -> dict[str, Any]:
    if not tavily_api_key:
        print("TAVILY_API_KEY is missing; skipping market analysis")
        return {}

    client = TavilyClient(api_key=tavily_api_key)
    try:
        return client.search(
            query=search_query,
            max_results=5,
        )
    except Exception as e:
        print("Tavily search failed:", repr(e))
        return {}


def generate_market_analysis(
    product_context: str,
    search_query: str = "",
    timer: PipelineTimer | None = None,
) -> list[dict[str, str]]:
    if not product_context:
        return []

    if timer:
        timer.start_phase("phase3_market_tavily_search")
    tavily_results = get_tavily_results(search_query or product_context)
    print(tavily_results)

    if not tavily_results:
        return []

    if timer:
        timer.start_phase("phase3_market_llm_competitors")
    prompt = build_market_prompt(product_context, tavily_results)

    try:
        llm_answer = llm.invoke(prompt)
        print(llm_answer.content)
        parsed = parse_llm_json(llm_answer.content)

        competitors = parsed.get("competitors", [])
        if not isinstance(competitors, list):
            return []

        cleaned_items: list[dict[str, str]] = []
        for item in competitors:
            if not isinstance(item, dict):
                continue

            comp_name = str(item.get("comp_name", "")).strip()
            reason = str(item.get("competitor_because", "")).strip()

            if comp_name and reason:
                cleaned_items.append(
                    {
                        "comp_name": comp_name,
                        "competitor_because": reason,
                    }
                )
        print("===== TAVILY RESULTS =====")
        print(json.dumps(tavily_results, indent=2))

        print("===== LLM RESPONSE =====")
        print(llm_answer.content)

        return cleaned_items

    except Exception:
        return []


def run_product_pipeline(
    state: ProductQuestions,
    timer: PipelineTimer | None = None,
    finalize_timer: bool = True,
) -> ProductQuestions:
    owns_timer = timer is None
    if timer is None:
        timer = PipelineTimer(label="product_pipeline")

    timer.start_phase("phase1_product_discovery")
    state = analyze_product_answers(state)

    if not state["fully_answered"]:
        state["product_context"] = ""
        state["market_search_query"] = ""
        state["market_analysis"] = []
        state["customer_voice"] = {}
        if finalize_timer or owns_timer:
            state["pipeline_timing"] = timer.finish()
        return state

    try:
        timer.start_phase("phase2_product_context")
        state["product_context"] = generate_product_context(state["question_mapping"])
    except Exception:
        state["product_context"] = ""

    timer.start_phase("phase2_build_market_query")
    state["market_search_query"] = build_market_search_query(state["question_mapping"])

    try:
        state["market_analysis"] = generate_market_analysis(
            state["product_context"],
            state["market_search_query"],
            timer=timer,
        )
    except Exception:
        state["market_analysis"] = []

    try:
        state["customer_voice"] = generate_customer_voice(
            state["product_context"],
            state["market_analysis"],
            timer=timer,
        )
    except Exception:
        state["customer_voice"] = {}

    if finalize_timer or owns_timer:
        state["pipeline_timing"] = timer.finish()
    return state


def persist_project_state(project_id: int, state: ProductQuestions, db: Session) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    project.latest_query = state["user_query"]
    project.question_mapping = state["question_mapping"]
    project.follow_up_questions = state["follow_up_questions"]
    project.product_context = state["product_context"]
    project.market_search_query = state["market_search_query"]
    project.market_analysis = state["market_analysis"]
    project.customer_voice = state.get("customer_voice") or {}
    db.commit()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        raise credentials_exception

    return user


@query.post("/query", response_model=QueryReponse)
def get_query(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state: ProductQuestions = {
        "user_query": payload.user_query,
        "fully_answered": False,
        "follow_up_questions": [],
        "question_mapping": {},
        "product_context": "",
        "market_search_query": "",
        "market_analysis": [],
        "customer_voice": {},
    }

    result = run_product_pipeline(state)
    persist_project_state(payload.project_id, result, db)

    return QueryReponse(
        user_email=current_user.email,
        query_response=result,
    )


@query.get("/query")
def get_response(current_user: User = Depends(get_current_user)):
    return {
        "message": "Authorized",
        "user_email": current_user.email,
    }