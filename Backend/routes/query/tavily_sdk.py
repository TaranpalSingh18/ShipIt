from tavily import TavilyClient
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

tavily_api_key = os.getenv("TAVILY_API_KEY")

client = TavilyClient(api_key=tavily_api_key)

result = client.search( query="Spotify competitors",
    max_results=5)

print(result)