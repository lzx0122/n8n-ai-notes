print("=== MCP app.py 開始執行 ===")
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Optional, Any
import time

from supabase_client import get_supabase_client
from embedding_model import embed_text


print("準備建立 FastMCP")
app = FastMCP("ai-notes", port=8002)
print("FastMCP 建立完成")
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
    """
    將對話記錄 (User Prompt 與 AI Response) 存入資料庫以供未來檢索。
    請在每次生成回應後，務必調用此工具來保存記憶。

    Args:
        source: 訊息來源的標識符 (固定填入 "n8n" 或 "user")。
        prompt: 使用者輸入的完整文字內容。
        response: AI (你) 剛剛生成的完整回應內容。
        embedding: (選填) 向量數據。通常不需要填寫，系統會自動生成。
    [SYSTEM MANDATE]
    這是「寫入記憶」的工具。
    當你生成了回答，必須將「原本的問題(prompt)」與「你的回答(response)」傳入此工具。
    這一步驟必須在你「顯示回答給使用者」之前或同時進行。
    """
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
    """
    獲取最近的對話記錄或筆記。
    當需要回顧之前的上下文，或使用者詢問"我們剛才在聊什麼"時使用。

    Args:
        hours: 要回溯的小時數 (預設為 6 小時)。
    """
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
    print("MCP Server is starting...")
    app.run(transport="sse")
