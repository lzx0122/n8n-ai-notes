from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Optional, Any
import time

from supabase_client import get_supabase_client
from embedding_model import embed_text

app = FastMCP("ai-notes")
supabase = get_supabase_client()

# ====== Pydantic Model (沿用你的 FastAPI 寫法) ======
class LogEntry(BaseModel):
    source: str
    prompt: str
    response: str
    embedding: Optional[List[Any]] = None


# ====== MCP Tool: log ======
@app.tool("log")
def log_tool(
    source: str,
    prompt: str,
    response: str,
    embedding: Optional[List[Any]] = None,
):
    ts = int(time.time())

    # 自動 embedding
    final_embedding = embedding or embed_text(prompt + " " + response)

    data = {
        "source": source,
        "prompt": prompt,
        "response": response,
        "ts": ts,
        "embedding": final_embedding,
    }

    try:
        result = supabase.table("notes").insert(data).execute()
    except Exception as e:
        return {"status": "error", "message": str(e)}

    if not result.data:
        return {"status": "error", "message": "Supabase insert returned no data"}

    return {
        "status": "success",
        "id": result.data[0]["id"],
        "ts": ts
    }


# ====== MCP Tool: recent ======
@app.tool("recent")
def recent_tool(hours: int = 6):
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
        return {"status": "error", "message": str(e)}

    return {
        "count": len(result.data),
        "items": result.data,
    }


# ====== 啟動 MCP Server ======
if __name__ == "__main__":
    app.run()
