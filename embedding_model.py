from huggingface_hub import hf_hub_download
import onnxruntime as ort
import numpy as np

repo_id = "BAAI/bge-m3"
model_file = "onnx/model.onnx"

model_path = hf_hub_download(repo_id=repo_id, filename=model_file)

session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

def embed_text(text: str):
    inputs = {"input_text": np.array([text])}
    outputs = session.run(None, inputs)
    return outputs[0][0].tolist()
