import os
import json
import base64
import re
import logging
from urllib.parse import urlparse

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import openai
import httpx

# ---------- Config ----------
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

DFS_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DFS_PASS = os.getenv("DATAFORSEO_PASSWORD")
DFS_AUTH = {
    "Authorization": "Basic " + base64.b64encode(
        f"{DFS_LOGIN}:{DFS_PASS}".encode()
    ).decode()
}

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Competitor + SEO POC",
    description="Returns competitor domains and their ranked keywords",
)

# ---------- Utils ----------
def clean_domain(url: str) -> str:
    """
    Extracts a clean domain name from a full URL.
    e.g. https://www.example.com → example.com
    """
    parsed = urlparse(url.strip())
    hostname = parsed.hostname or url.strip()
    return re.sub(r"^www\.", "", hostname)


# ---------- DataForSEO helper ----------
async def fetch_ranked_keywords(domain: str):
    payload = [{
        "target": domain,
        "language_name": "English",
        "location_name": "United States",
        "load_rank_absolute": True,
        "limit": 10
    }]
    headers = DFS_AUTH.copy()
    headers["Content-Type"] = "application/json"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live",
                headers=headers,
                json=payload
            )
            logging.info(f"DFS status: {resp.status_code}")
            js = resp.json()
            logging.info(f"DFS response: {json.dumps(js, indent=2)}")
            items = js["tasks"][0]["result"][0]["items"]
async def fetch_ranked_keywords(domain: str):
    payload = [{
        "target": domain,
        "language_name": "English",
        "location_name": "United States",
        "load_rank_absolute": True,
        "limit": 10
    }]
    headers = DFS_AUTH.copy()
    headers["Content-Type"] = "application/json"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live",
                headers=headers,
                json=payload
            )
            logging.info(f"DFS status: {resp.status_code}")
            js = resp.json()
            logging.info(f"DFS response: {json.dumps(js, indent=2)}")
            items = js["tasks"][0]["result"][0]["items"]
            # FIX: Extract keyword from keyword_data
            return [kw["keyword_data"]["keyword"] for kw in items if "keyword_data" in kw and "keyword" in kw["keyword_data"]]
        except Exception as e:
            logging.error(f"DFS response error: {e}, response: {resp.text if 'resp' in locals() else 'No response'}")
            return []
        except Exception as e:
            logging.error(f"DFS response error: {e}, response: {resp.text if 'resp' in locals() else 'No response'}")
            return []


# ---------- Main endpoint ----------
@app.get("/competitors")
async def get_competitors(
    appDescription: str = Query(..., description="Short description of the app")
):
    # 1. Prompt OpenAI for 3 competitor domains
    prompt = (
        "You are market research expert.\n\n"
        "Your task is to analyse the competition for the app described by the user.\n\n"
        "Step-by-step task:\n"
        "1. Analyse the app description thoroughly\n"
        "2. Answer two competitor URLs\n\n"
        "Answer in JSON format. Only include URLs. Don’t add any comments in your answer."
    )

    try:
        rsp = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": appDescription}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        parsed = json.loads(rsp.choices[0].message.content)
        competitor_urls = parsed.get("competitors") or list(parsed.values())[0]
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        raise HTTPException(502, f"OpenAI error: {e}")

    # 2. Clean domains + fetch ranked keywords
    results = []
    try:
        for raw_url in competitor_urls:
            domain = clean_domain(raw_url)
            keywords = await fetch_ranked_keywords(domain)
            results.append({
                "domain": domain,
                "keywords": keywords
            })
    except Exception as e:
        logging.error(f"DataForSEO error: {e}")
        raise HTTPException(502, f"DataForSEO error: {e}")

    return JSONResponse(content={"competitors": results})

