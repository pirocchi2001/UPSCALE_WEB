"""ONNX 出力が PyTorch と一致し、可変サイズで4倍になることを確認する。"""
import sys, numpy as np, torch, onnxruntime as ort
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from convert_to_onnx import MODELS, ROOT
for name, (pth, build) in MODELS.items():
    net = build()
    sd = torch.load(ROOT / "weights" / pth, map_location="cpu", weights_only=True)
    net.load_state_dict(sd.get("params_ema", sd.get("params", sd))); net.eval()
    s = ort.InferenceSession(str(ROOT / "models" / f"{name}.onnx"), providers=["CPUExecutionProvider"])
    for h, w in [(40, 56), (144, 144), (17, 33)]:
        x = np.random.rand(1, 3, h, w).astype(np.float32)
        o = s.run(None, {"input": x})[0]
        with torch.no_grad(): t = net(torch.from_numpy(x)).numpy()
        assert o.shape == (1, 3, h * 4, w * 4), o.shape
        print(name, (h, w), "maxdiff", float(np.abs(o - t).max()))
