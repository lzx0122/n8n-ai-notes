from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any
import time
import json

from embedding_model import embed_text
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
    embedding = entry.embedding or embed_text(entry.prompt)

    data = {
        "source": entry.source,
        "prompt": entry.prompt,
        "response": entry.response,
        "ts": ts,
        "embedding": embedding,
    }

    result = supabase.table("notes").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to insert log entry")

    return {"status": "success", "id": result.data[0]["id"]}


@app.get("/recent")
def get_recent(hours: int = Query(6, ge=1)):
    now_ts = int(time.time())
    cutoff_ts = now_ts - hours * 3600

    result = (supabase.table("notes")
              .select("*")
              .gte("ts", cutoff_ts)
              .order("ts", asc=True)
              .execute())

    if result.data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch logs")

    return result.data


# -------------------------
#      MCP WebSocket
# -------------------------
@app.websocket("/mcp")
async def mcp_ws(ws: WebSocket):
    await ws.accept()

    try:
        raw = await ws.receive_text()
        init = json.loads(raw)

        if init.get("method") != "initialize":
            await ws.send_text(json.dumps({
                "jsonrpc": "2.0",
                "id": init.get("id"),
                "error": {"code": -32600, "message": "Invalid initialize request"}
            }))
            await ws.close()
            return

        # send proper initialize response
        await ws.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": init.get("id"),   # IMPORTANT
            "result": {
                "protocolVersion": "2024-02-01",
                "serverInfo": {
                    "name": "ai-notes",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": [
                        {"name": "log", "description": "log a note"},
                        {"name": "recent", "description": "fetch recent notes"}
                    ]
                }
            }
        }))

        # handle tool calls
        while True:
            msg = await ws.receive_text()
            req = json.loads(msg)

            method = req.get("method")
            rid = req.get("id")

            # invalid
            if "jsonrpc" not in req or method is None:
                await ws.send_text(json.dumps({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32600, "message": "Invalid request"}
                }))
                continue

            # tool: log
            if method == "tools/log":
                try:
                    p = req.get("params", {})
                    embedding = p.get("embedding") or embed_text(p["prompt"])

                    data = {
                        "source": p["source"],
                        "prompt": p["prompt"],
                        "response": p["response"],
                        "ts": int(time.time()),
                        "embedding": embedding,
                    }

                    result = supabase.table("notes").insert(data).execute()

                    await ws.send_text(json.dumps({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {"status": "success"}
                    }))

                except Exception as e:
                    await ws.send_text(json.dumps({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {"code": -32000, "message": str(e)}
                    }))

            # tool: recent
            elif method == "tools/recent":
                try:
                    hours = int(req.get("params", {}).get("hours", 6))
                    now_ts = int(time.time())
                    cutoff_ts = now_ts - hours * 3600

                    r = (supabase.table("notes")
                         .select("*")
                         .gte("ts", cutoff_ts)
                         .order("ts", asc=True)
                         .execute())

                    await ws.send_text(json.dumps({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {"notes": r.data}
                    }))

                except Exception as e:
                    await ws.send_text(json.dumps({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {"code": -32000, "message": str(e)}
                    }))

            # unknown tool
            else:
                await ws.send_text(json.dumps({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32601, "message": "Method not found"}
                }))

    except WebSocketDisconnect:
        return
