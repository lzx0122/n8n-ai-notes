from sentence_transformers import SentenceTransformer

# 全局載入模型（只會 load 一次）
model = SentenceTransformer("BAAI/bge-m3")

def embed_text(text: str):
    return model.encode(text).tolist()
