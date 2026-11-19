"""Real-ESRGAN の .pth を ONNX に変換する(入力 input: 1x3xHxW 可変、出力 output: 4倍)。

使い方:
  python tools/convert_to_onnx.py            # weights/ から models/ へ3モデルを変換
重みは公式リリースから取得する(README 参照)。basicsr に依存しないよう、
ネットワーク定義を最小限で再実装している(公式実装と同じ state_dict キー)。
"""
import sys
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent


class RDB(nn.Module):
    def __init__(s, nf=64, gc=32):
        super().__init__()
        s.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        s.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        s.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        s.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        s.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        s.act = nn.LeakyReLU(0.2, True)

    def forward(s, x):
        x1 = s.act(s.conv1(x))
        x2 = s.act(s.conv2(torch.cat((x, x1), 1)))
        x3 = s.act(s.conv3(torch.cat((x, x1, x2), 1)))
        x4 = s.act(s.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = s.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(s, nf, gc=32):
        super().__init__()
        s.rdb1, s.rdb2, s.rdb3 = RDB(nf, gc), RDB(nf, gc), RDB(nf, gc)

    def forward(s, x):
        return s.rdb3(s.rdb2(s.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):  # scale=4
    def __init__(s, nf=64, nb=23, gc=32):
        super().__init__()
        s.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        s.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        s.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        s.act = nn.LeakyReLU(0.2, True)

    def forward(s, x):
        f = s.conv_first(x)
        f = f + s.conv_body(s.body(f))
        f = s.act(s.conv_up1(F.interpolate(f, scale_factor=2, mode="nearest")))
        f = s.act(s.conv_up2(F.interpolate(f, scale_factor=2, mode="nearest")))
        return s.conv_last(s.act(s.conv_hr(f)))


class SRVGGNetCompact(nn.Module):  # upscale=4, prelu
    def __init__(s, nf=64, nc=32, up=4):
        super().__init__()
        s.up = up
        layers = [nn.Conv2d(3, nf, 3, 1, 1), nn.PReLU(nf)]
        for _ in range(nc):
            layers += [nn.Conv2d(nf, nf, 3, 1, 1), nn.PReLU(nf)]
        layers.append(nn.Conv2d(nf, 3 * up * up, 3, 1, 1))
        s.body = nn.ModuleList(layers)

    def forward(s, x):
        out = x
        for l in s.body:
            out = l(out)
        out = F.pixel_shuffle(out, s.up)
        return out + F.interpolate(x, scale_factor=s.up, mode="nearest")


MODELS = {
    "realesrgan-x4plus": ("RealESRGAN_x4plus.pth", lambda: RRDBNet(nb=23)),
    "realesrgan-x4plus-anime": ("RealESRGAN_x4plus_anime_6B.pth", lambda: RRDBNet(nb=6)),
    "realesr-general-x4v3": ("realesr-general-x4v3.pth", SRVGGNetCompact),
}


def convert(name, pth, build):
    net = build()
    sd = torch.load(ROOT / "weights" / pth, map_location="cpu", weights_only=True)
    net.load_state_dict(sd.get("params_ema", sd.get("params", sd)), strict=True)
    net.eval()
    out = ROOT / "models" / f"{name}.onnx"
    dummy = torch.rand(1, 3, 64, 64)
    torch.onnx.export(
        net, dummy, str(out), input_names=["input"], output_names=["output"],
        dynamic_axes={"input": {2: "h", 3: "w"}, "output": {2: "oh", 3: "ow"}},
        opset_version=17, dynamo=False,
    )
    print(f"{name}: {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    (ROOT / "models").mkdir(exist_ok=True)
    for n, (p, b) in MODELS.items():
        convert(n, p, b)
