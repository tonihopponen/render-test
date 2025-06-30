import os, json
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import openai

# --- OpenAI key from Render's ENV settings ---
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"          # or gpt-4o if enabled

app = FastAPI(
    title="Competitor-POC",
    summary="Returns three competitor URLs for a given app description."
)

@app.get("/competitors")
async def get_competitors(
    appDescription: str = Query(..., description="Short description of the app")
):
    """
    Example:
    /competitors?appDescription=Ride+sharing+for+pets
    """
    prompt = (
        "You are market research expert.\n\n"
        "Your task is to analyse the competition for the app described by the user.\n\n"
        "Step-by-step task:\n"
        "1. Analyse the app description thoroughly\n"
        "2. Answer three competitor URLs\n\n"
        "Answer in JSON format. Only include URLs. Don’t add any comments in your answer."
    )

    try:
       (
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": appDescription}
            ],
            # makes the model return a pure JSON object
            response_format={"type": "json_object"},
            temperature=0.3
        )
    except Exception as e:
        raise HTTPException(502, f"OpenAI error: {e}")

    # content is a JSON string like: {"competitors": ["url1","url2","url3"]}
    try:
        data = json.loads(rsp.choices[0].message.content)
    except json.JSONDecodeError:
        raise HTTPException(500, "Model did not return valid JSON")

    return JSONResponse(content=data)
