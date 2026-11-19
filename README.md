# UPSCALE_WEB

サーバー不要の画像高画質化ウェブアプリ。Real-ESRGAN(ONNX)をブラウザ内で実行します(画像は外部に送信されません)。

- WebGPU が使えればGPUで、使えなければ WASM(CPU)で自動的に動作
- 倍率: 2倍 / 4倍 / A3・300dpi(いずれも4倍で推論 → 高品質縮小)
- 輪郭強調(アンシャープマスク)、拡大前後の比較スライダー
- PNG / JPEG 保存(既定はJPEG品質0.98。dpi情報を埋め込み)

## 使い方(公開)
`index.html` と `models/` を GitHub Pages で公開するだけです。ローカルでは `python3 -m http.server` で配信して開きます(`file://` ではモデルを読み込めません)。

## モデル(`models/`)
| ファイル | 元の重み | 用途 | サイズ |
|---|---|---|---|
| `realesrgan-x4plus.onnx` | RealESRGAN_x4plus.pth | 写真 | 67 MB |
| `realesrgan-x4plus-anime.onnx` | RealESRGAN_x4plus_anime_6B.pth | イラスト・文字 | 18 MB |
| `realesr-general-x4v3.onnx` | realesr-general-x4v3.pth | 軽量・高速 | 5 MB |

入力 `input`: 1×3×H×W(0〜1のRGB、H・W可変)/ 出力 `output`: 1×3×4H×4W。

### 再生成
```
python3 -m venv .venv && .venv/bin/pip install torch onnx onnxruntime onnxscript numpy pillow
# weights/ に公式リリースの .pth を置く
#   https://github.com/xinntao/Real-ESRGAN/releases (v0.1.0 / v0.2.2.4 / v0.2.5.0)
.venv/bin/python tools/convert_to_onnx.py
.venv/bin/python tools/verify_onnx.py     # PyTorch との一致確認
```
`tools/e2e/` にはPlaywright(システムのChrome使用)による動作確認スクリプトがあります。

## 動作確認の結果(Chrome / Apple Silicon Mac)
- ONNX と PyTorch の出力差: 約 1e-6(可変サイズ・4倍出力を確認)
- 1400×2000px: 2倍 / 4倍(5600×8000) / A3 300dpi がいずれも完了。保存したPNG(pHYs)・JPEG(JFIF)のdpiが正しく読めることを確認
- タイル継ぎ目: タイル無し推論との差は継ぎ目付近で平均 約2/255(継ぎ目以外は約1/255)
- WebGPU 無効(WASM)時の速度: 軽量モデルは約 0.7秒/タイル、x4plus は約 9秒/タイル。
  1400×2000px(176タイル)では軽量で約2分、x4plus は約25分の見込み。WASM では「軽量・高速」の使用を推奨

## ライセンス
本リポジトリのコードは [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)(Copyright (c) 2021, Xintao Wang、BSD-3-Clause)の学習済みモデルを変換して利用しています。

```
BSD 3-Clause License
Copyright (c) 2021, Xintao Wang
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
