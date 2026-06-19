from langchain_groq import ChatGroq
from langchain_apify import ApifyActorsTool
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from fastapi import APIRouter
import os
import json
import re

load_dotenv()

behaviour = APIRouter(tags=["customer_behaviour_analyser"], prefix="/behaviour")

apify_api_key = os.getenv("APIFY_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

import re

def minify_markdown(md_text: str, max_lines_per_site: int = 25) -> str:
    """
    Aggressively cleans Markdown and strictly limits the output size per website.
    """
    if not md_text:
        return ""
    
    # 1. Remove Images
    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    # 2. Extract Text from Links
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    
    # 3. Remove stray HTML tags
    md_text = re.sub(r'<[^>]+>', '', md_text)
    
    # 4. Filter and collect lines
    lines = md_text.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        # Only keep lines that look like actual informative sentences (e.g., > 40 chars)
        # This completely drops menus, navbars, names, and short FAQs
        if len(line) > 40: 
            clean_lines.append(line)
            
    # 5. HARD CAP: Take only the top N most important lines from this website
    clean_lines = clean_lines[:max_lines_per_site]
            
    return " ".join(clean_lines)


def _clean_text(text: str, max_len: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text[:max_len]


def _dedupe_keep_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.get("url") or item.get("link") or item.get("title") or json.dumps(item, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def compress_apify_output(raw_result, max_items: int = 3) -> str:
    """
    Extractive compression: keeps the most useful fields only.
    """
    items = []

    if isinstance(raw_result, list):
        items = raw_result
    elif isinstance(raw_result, dict):
        for key in ("items", "results", "data", "documents"):
            if key in raw_result and isinstance(raw_result[key], list):
                items = raw_result[key]
                break
        if not items:
            items = [raw_result]
    else:
        return _clean_text(raw_result, 3000)

    items = _dedupe_keep_order(items)[:max_items]

    blocks = []
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict):
            blocks.append(f"[{idx}] {_clean_text(item, 1000)}")
            continue

        title = _clean_text(item.get("title") or item.get("name") or item.get("heading") or "Untitled", 140)
        url = _clean_text(item.get("url") or item.get("link") or "", 300)
        snippet = _clean_text(
            item.get("text")
            or item.get("content")
            or item.get("description")
            or item.get("snippet")
            or item.get("body")
            or "",
            700
        )

        extra_bits = []
        for k in ("source", "date", "author", "siteName", "domain"):
            if item.get(k):
                extra_bits.append(f"{k}={_clean_text(item.get(k), 80)}")

        extra = f" | {'; '.join(extra_bits)}" if extra_bits else ""
        blocks.append(f"[{idx}] TITLE: {title}\nURL: {url}\nSNIPPET: {snippet}{extra}")

    return "\n\n".join(blocks)


def get_customer_behaviour_fn(context: str) -> str:
    print(f"\n🟢 [STEP 1] Starting execution for context: '{context}'")
    
    # 1. Fast, cheap model for Data Extraction (The Broom)
    extractor_llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=groq_api_key,
        temperature=0.0, # 0.0 so it only copies facts, no hallucinating
    )

    # 2. Premium model for Behavioral Analysis (The Brain)
    critic_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=groq_api_key,
        temperature=0.2,
    )

    print("🟢 [STEP 2] Initializing Apify Browser Tool...")
    browser = ApifyActorsTool(
        "apify/rag-web-browser",
        apify_api_token=apify_api_key
    )

    print(f"\n🚀 [STEP 3] Triggering Apify Direct Search for: '{context}'")
    raw_apify_data = browser.invoke({"run_input": {"query": context}}) 
    
    print("🟢 [STEP 4] Parsing and Minifying Apify JSON...")
    raw_markdowns = []
    
    if isinstance(raw_apify_data, list):
        for item in raw_apify_data:
            if isinstance(item, dict) and item.get("markdown"):
                # Clean the markdown before appending it
                cleaned_text = minify_markdown(item["markdown"])
                raw_markdowns.append(cleaned_text)
    
    # Combine the cleaned text. 
    # Because it is so clean now, 18000 chars will hold WAY more actual knowledge.
    giant_text = "\n\n---\n\n".join(raw_markdowns)[:18000]
    
    print(f"📉 Raw Markdown size: {len(giant_text)} characters. Sending to 8B for extraction...")

    # ---------------------------------------------------------
    # NEW STEP: LLM Extraction (Filtering the noise)
    # ---------------------------------------------------------
    extraction_prompt = (
        f"You are a strict data extraction tool.\n"
        f"Scan the following raw website text and extract ONLY the facts, statistics, "
        f"and statements relevant to this topic: '{context}'.\n"
        f"Do not write an introduction. Do not analyze. Just return the relevant raw information.\n\n"
        f"RAW TEXT:\n{giant_text}"
    )
    
    filtered_data = extractor_llm.invoke(extraction_prompt).content
    print(f"✅ [FILTER FINISHED] 8B Model reduced data to {len(filtered_data)} characters of pure signal.")

    print("\n🧠 [STEP 5] Sending refined signal to Llama-3.3-70B for final synthesis...")
    # Synthesis loop with the 70B model
    final_synthesis = critic_llm.invoke(
        f"You are an expert consumer psychologist and data analyst.\n"
        f"Analyze customer behavior insights based strictly on the following curated research data. "
        f"Focus on how users interact with or feel about the topic: '{context}'.\n"
        f"Do not hallucinate or guess beyond the provided facts:\n\n"
        f"{filtered_data}"
    )

    print("🟢 [STEP 6] Synthesis complete! Returning response to client.\n")
    return final_synthesis.content

@behaviour.post("/")
async def get_behaviour_customer(context: str):
    return get_customer_behaviour_fn(context)