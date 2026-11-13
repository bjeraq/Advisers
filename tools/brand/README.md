# شعار الحساب — majlis.stocks

شموع ترسم علامة صح (أخضر، أحمر نازل، أخضرين صاعدين) داخل دائرة جاهزة لصورة انستغرام.
الملفات النهائية (1080×1080): `site/brand/majlis_stocks_{dark,teal,light}.png`.

إعادة التوليد (رسم متجهي يُصوَّر بكروميوم):

```bash
mkdir -p /tmp/logo && cd /tmp/logo
npm pack @fontsource/ibm-plex-sans@5.1.0 && mkdir fontpkg2 && tar xzf fontsource-ibm-plex-sans-5.1.0.tgz -C fontpkg2
npm pack @fontsource/ibm-plex-sans-arabic@5.1.0 && mkdir fontpkg && tar xzf fontsource-ibm-plex-sans-arabic-5.1.0.tgz -C fontpkg
cp <repo>/tools/brand/ig_logo.py <repo>/tools/brand/clip.js .
python3 ig_logo.py
for v in dark teal light; do node clip.js ig_$v.html majlis_stocks_$v.png 0 0 1080 1080 1; done
```
