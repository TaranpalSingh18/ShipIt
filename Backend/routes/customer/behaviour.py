import asyncio

from fastapi import APIRouter
from dotenv import load_dotenv

from routes.customer.voice_analysis import generate_customer_voice

load_dotenv()

behaviour = APIRouter(tags=["customer_behaviour_analyser"], prefix="/behaviour")


@behaviour.post("/debug")
async def debug_customer_voice(
    product_context: str,
    competitor_name: str,
):
    """
    Dev-only route to test Phase 4 customer voice for a single competitor context.
    Prefer POST /teardown/generate-pdf for the full integrated pipeline.
    """
    market_analysis = [{"comp_name": competitor_name, "competitor_because": "debug"}]
    result = await asyncio.to_thread(
        generate_customer_voice,
        product_context,
        market_analysis,
    )
    return result
