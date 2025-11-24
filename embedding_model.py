print("embedding_model.py 開始載入")
from sentence_transformers import SentenceTransformer

# 使用 MiniLM，輕量＋高品質
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def embed_text(text: str):
    emb = model.encode(text, convert_to_numpy=True)
    return emb.tolist()