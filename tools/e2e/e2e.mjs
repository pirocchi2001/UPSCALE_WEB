// 使い方: node e2e.mjs <画像> <モデルファイル名> <2|4|a3> <png|jpg>
import { chromium } from 'playwright-core';
import fs from 'fs';
const [img, model, scale, fmt] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--enable-unsafe-webgpu'] });
const p = await b.newPage({ acceptDownloads: true });
if (process.env.NOGPU) await p.addInitScript(() => { Object.defineProperty(navigator, 'gpu', { value: undefined }); });
p.on('pageerror', e => console.log('PAGEERR', e.message));
await p.goto((process.env.URL || 'http://localhost:8765/index.html'));
console.log('webgpu:', await p.evaluate(() => !!navigator.gpu));
await p.setInputFiles('#file', img);
await p.waitForFunction(() => !document.getElementById('run').disabled);
console.log(await p.textContent('#info'));
await p.selectOption('#model', `models/${model}.onnx`);
await p.check(`input[name=scale][value="${scale}"]`);
const t0 = Date.now();
await p.click('#run');
await p.waitForFunction(() => /^(完了|エラー)/.test(document.getElementById('status').textContent), null, { timeout: 0 });
console.log(await p.textContent('#status'), `(${((Date.now() - t0) / 1000).toFixed(0)}s)`);
if (process.env.SHARP) { await p.evaluate(() => { const a = document.getElementById('amount'); a.value = 1; a.dispatchEvent(new Event('input')); a.dispatchEvent(new Event('change')); }); await p.waitForTimeout(3000); await p.evaluate(() => { const s = document.getElementById('split'); s.value = 30; s.dispatchEvent(new Event('input')); }); console.log('split width', await p.evaluate(() => document.getElementById('before').style.width)); }
await p.selectOption('#fmt', fmt);
const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 120000 }), p.click('#save')]);
const out = `/tmp/none`; const path = await dl.path(); const buf = fs.readFileSync(path);
const dest = `out_${model}_${scale}.${fmt}`; fs.copyFileSync(path, dest);
console.log('saved', dl.suggestedFilename(), buf.length, 'bytes ->', dest);
if (fmt === 'png') { let o = 8; while (o < buf.length) { const len = buf.readUInt32BE(o), t = buf.toString('latin1', o + 4, o + 8); if (t === 'IHDR') console.log('PNG', buf.readUInt32BE(o + 8), 'x', buf.readUInt32BE(o + 12)); if (t === 'pHYs') console.log('pHYs ppm', buf.readUInt32BE(o + 8), '=> dpi', (buf.readUInt32BE(o + 8) * 0.0254).toFixed(2)); o += 12 + len; } }
else console.log('JFIF units', buf[13], 'dpi', buf.readUInt16BE(14), buf.readUInt16BE(16));
await b.close();
