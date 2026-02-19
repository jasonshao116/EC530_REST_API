from fastapi import FastAPI, Query, HTTPException
import requests

app = FastAPI()

OPENFDA = "https://api.fda.gov/drug/shortages.json"


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/v1/shortages/current")
def current(limit: int = Query(5, ge=1, le=100)):
    # OpenFDA doesn't have "current" as a separate endpoint; this is a basic wrapper example
    r = requests.get(OPENFDA, params={"limit": limit}, timeout=10)
    r.raise_for_status()
    data = r.json()

    # Normalize a bit: give each result a shortage_id
    results = data.get("results", [])
    normalized = []
    for i, item in enumerate(results):
        shortage_id = item.get("id") or item.get("shortage_id") or f"openfda:{i}"
        normalized.append({"shortage_id": shortage_id, "raw": item})

    return {"results": normalized}


@app.get("/v1/shortages/search")
def search(q: str, status: str = "any", limit: int = Query(5, ge=1, le=100)):
    # Minimal search wrapper: you should map q to proper OpenFDA fields later
    r = requests.get(OPENFDA, params={"search": q, "limit": limit}, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = data.get("results", [])
    normalized = []
    for i, item in enumerate(results):
        shortage_id = item.get("id") or item.get("shortage_id") or f"openfda:{i}"
        normalized.append({"shortage_id": shortage_id, "raw": item})

    return {"results": normalized}


@app.get("/v1/shortages/{shortage_id}")
def get_one(shortage_id: str):
    # In a real API you'd store/cache shortage_id mappings.
    # For now, tell user it's not implemented.
    raise HTTPException(status_code=501, detail="Lookup by shortage_id not implemented in this minimal demo.")