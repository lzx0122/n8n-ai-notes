from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta
import time

from supabase_client import get_supabase_client

app = FastAPI()
supabase = get_supabase_client()

class LogEntry(BaseModel):
    source: str
    prompt: str
    response: str
    embedding: Optional[List[Any]] = None

@app.get("/")
def root():
    return {"message": "MCP Logging Server is running"}

@app.post("/log")
def log_entry(entry: LogEntry):
    ts = int(time.time())
    data = {
        "source": entry.source,
        "prompt": entry.prompt,
        "response": entry.response,
        "ts": ts,
        "embedding": entry.embedding
    }
    response = supabase.table("notes").insert(data).execute()
    if response.response.status_code != 201:
        raise HTTPException(status_code=500, detail="Failed to insert log entry")
    return {"status": "success", "id": response.data[0]["id"]}

@app.get("/recent")
def get_recent(hours: int = Query(6, ge=1)):
    now_ts = int(time.time())
    cutoff_ts = now_ts - hours * 3600
    response = supabase.table("notes").select("*").gte("ts", cutoff_ts).order("ts", asc=True).execute()
    if response.response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch recent logs")
    return response.data
