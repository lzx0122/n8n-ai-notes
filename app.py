from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any
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
        "embedding": entry.embedding,
    }

    result = supabase.table("notes").insert(data).execute()

    # NEW SUPABASE SDK: Check result.error
    if result.error:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase insert error: {result.error}",
        )

    return {"status": "success", "id": result.data[0]["id"]}


@app.get("/recent")
def get_recent(hours: int = Query(6, ge=1)):
    now_ts = int(time.time())
    cutoff_ts = now_ts - hours * 3600

    result = (
        supabase.table("notes")
        .select("*")
        .gte("ts", cutoff_ts)
        .order("ts", desc=False)
        .execute()
    )

    # New API: only check result.error
    if result.error:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase query error: {result.error}",
        )

    return result.data
