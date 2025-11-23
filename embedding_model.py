import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download

# 使用 bge-micro 單文件模型（不會碎片）
repo_id = "BAAI/bge-micro"
model_file = "onnx/model.onnx"

# 下載 ONNX 模型
model_path = hf_hub_download(repo_id=repo_id, filename=model_file)

# 建立 ONNX Runtime Session
session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

def embed_text(text: str):
    # 模型要求輸入為字串陣列
    inputs = {"input_text": np.array([text])}
    outputs = session.run(None, inputs)

    # 第一個 output 是 embedding，[0]取 batch 裡第一筆
    return outputs[0][0].tolist()
