# v2: كتابة كبيرة على سطرين تنقرا بالتلفون + شموع أصغر وأكثر (6) ترسم علامة صح
G, R = '#22C55E', '#EF4444'
# (cx, body_top, body_bot, wick_top, wick_bot, color) — box ~310x180
CS = [(15, 80, 110, 70, 118, G), (71, 98, 140, 90, 148, R), (127, 128, 168, 120, 178, R),
      (183, 102, 150, 92, 158, G), (239, 62, 112, 52, 120, G), (295, 18, 74, 6, 84, G)]

def candles(x0, y0, s):
    o = []
    for cx, bt, bb, wt, wb, col in CS:
        o.append(f'<line x1="{cx}" y1="{wt}" x2="{cx}" y2="{wb}" stroke="{col}" stroke-width="6" stroke-linecap="round"/>')
        o.append(f'<rect x="{cx-15}" y="{bt}" width="30" height="{bb-bt}" rx="5" fill="{col}"/>')
    return f'<g transform="translate({x0} {y0}) scale({s})">' + ''.join(o) + '</g>'

V = {
 'dark':  dict(bg='#0B1C1F', ring='#C9A227', a='#F6EFE2', b='#C9A227', name='داكن'),
 'teal':  dict(bg='#0F5C55', ring='#C9A227', a='#F6EFE2', b='#E2BE45', name='تيل المجلس'),
 'light': dict(bg='#F6EFE2', ring='#C9A227', a='#0F5C55', b='#B8901A', name='فاتح'),
}

def badge(v, size, full_square=False):
    c = V[v]
    sq = f'<rect width="1000" height="1000" fill="{c["bg"]}"/>' if full_square else ''
    w = 310 * 1.15
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="{size}" height="{size}">
{sq}<circle cx="500" cy="500" r="500" fill="{c['bg']}"/>
<circle cx="500" cy="500" r="472" fill="none" stroke="{c['ring']}" stroke-width="14"/>
{candles(500 - w / 2, 150, 1.15)}
<text direction="ltr" style="unicode-bidi:isolate" x="500" y="598" text-anchor="middle" font-family="PlexLat" font-weight="700" font-size="188" letter-spacing="-2" fill="{c['a']}">majlis</text>
<text direction="ltr" style="unicode-bidi:isolate" x="500" y="790" text-anchor="middle" font-family="PlexLat" font-weight="700" font-size="188" letter-spacing="-2" fill="{c['b']}">.stocks</text>
</svg>'''

css = '''@font-face{font-family:PlexLat;font-weight:700;src:url(fontpkg2/package/files/ibm-plex-sans-latin-700-normal.woff2) format('woff2');}
@font-face{font-family:PlexAr;font-weight:700;src:url(fontpkg/package/files/ibm-plex-sans-arabic-arabic-700-normal.woff2) format('woff2');}
@font-face{font-family:PlexAr;font-weight:500;src:url(fontpkg/package/files/ibm-plex-sans-arabic-arabic-500-normal.woff2) format('woff2');}
*{margin:0;padding:0;box-sizing:border-box} svg{direction:ltr}'''

for v in V:
    open(f'ig2_{v}.html', 'w', encoding='utf-8').write(
        f'<!doctype html><html><head><meta charset="utf-8"><style>{css} body{{width:1080px;height:1080px;background:{V[v]["bg"]}}}</style></head>'
        f'<body>{badge(v, 1080, True)}</body></html>')

cards = ''
for v, c in V.items():
    cards += f'''<div class="card"><div class="lab">{c["name"]}</div>{badge(v, 400)}
<div class="ig"><div class="pp">{badge(v, 96)}</div><div class="pp">{badge(v, 56)}</div><div class="pp">{badge(v, 36)}</div>
<div class="sub2">بحجم صورة البروفايل على التلفون</div></div></div>'''
open('ig2_sheet.html', 'w', encoding='utf-8').write(f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{css}
body{{background:#F6EFE2;font-family:PlexAr,sans-serif;width:1680px;padding:44px 56px 52px}}
h1{{font-weight:700;font-size:42px;color:#0F5C55;margin-bottom:6px}}
.sub{{font-weight:500;font-size:23px;color:#6b6b6b;margin-bottom:30px}}
.row{{display:flex;gap:36px;justify-content:space-between}}
.card{{width:510px;background:#fffdf8;border-radius:28px;box-shadow:0 10px 30px rgba(15,92,85,.08);padding:26px 24px 26px;display:flex;flex-direction:column;align-items:center;gap:18px}}
.lab{{align-self:flex-start;font-weight:700;font-size:26px;color:#123430}}
.ig{{display:flex;align-items:center;gap:18px;align-self:stretch;border-top:1px solid #eee3cf;padding-top:16px}}
.pp svg{{display:block;border-radius:50%}}
.sub2{{font-weight:500;font-size:18px;color:#8a8a8a;margin-inline-start:auto}}
</style></head><body>
<h1>شعار الحساب — النسخة الثانية</h1>
<div class="sub">الكتابة أكبر على سطرين حتى تنقرا بالتلفون، والشموع أصغر وصارت ست شموع ترسم علامة صح</div>
<div class="row">{cards}</div></body></html>''')
print('ok')
