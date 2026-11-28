const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [, , html, out, x, y, w, h, scale] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1680, height: 900 }, deviceScaleFactor: Number(scale || 2) });
  await p.goto('file://' + path.join(__dirname, html));
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: path.join(__dirname, out), clip: { x: +x, y: +y, width: +w, height: +h }, fullPage: true });
  await b.close();
})();
