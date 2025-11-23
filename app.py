from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any
import time

from supabase_client import get_supabase_client
from embedding_model import embed_text

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

    # 如果沒有 embedding，自動生成
    final_embedding = entry.embedding or embed_text(entry.prompt + " " + entry.response)

    data = {
        "source": entry.source,
        "prompt": entry.prompt,
        "response": entry.response,
        "ts": ts,
        "embedding": final_embedding,
    }

    try:
        result = supabase.table("notes").insert(data).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not result.data:
        raise HTTPException(status_code=500, detail="Supabase insert returned no data")

    return {"status": "success", "id": result.data[0]["id"]}

@app.get("/recent")
def get_recent(hours: int = Query(6, ge=1)):
    now_ts = int(time.time())
    cutoff_ts = now_ts - hours * 3600

    try:
        result = (
            supabase.table("notes")
            .select("*")
            .gte("ts", cutoff_ts)
            .order("ts", desc=False)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result.data
