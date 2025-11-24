from mcp.server.fastmcp import FastMCP
from supabase_client import get_supabase_client
from embedding_model import embed_text
import time

app = FastMCP("ai-notes")
supabase = get_supabase_client()

@app.tool()
def log(source: str, prompt: str, response: str, embedding: list = None):
    ts = int(time.time())
    final_embedding = embedding or embed_text(prompt + " " + response)

    supabase.table("notes").insert({
        "source": source,
        "prompt": prompt,
        "response": response,
        "ts": ts,
        "embedding": final_embedding
    }).execute()

    return {"status": "ok"}


@app.tool()
def recent(hours: int = 6):
    now = int(time.time())
    cutoff = now - hours * 3600
    rows = supabase.table("notes").select("*").gte("ts", cutoff).execute().data
    return rows


if __name__ == "__main__":
    app.run()
