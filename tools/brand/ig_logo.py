# شعار حساب انستغرام: شموع على شكل علامة صح (أخضر، أحمر نازل، أخضرين صاعدين) + majlis.stocks — دائري
G, R = '#22C55E', '#EF4444'

def candles(x0=0, y0=0, s=1.0, outline=None):
    # (center_x, body_top, body_bot, wick_top, wick_bot, color) in a 200x200 box
    cs = [(61, 104, 130, 96, 137, G), (89, 124, 160, 117, 168, R), (117, 92, 126, 84, 133, G), (145, 42, 98, 32, 105, G)]
    out = []
    for cx, bt, bb, wt, wb, col in cs:
        sw = f' stroke="{outline}" stroke-width="2.5"' if outline else ''
        out.append(f'<line x1="{cx}" y1="{wt}" x2="{cx}" y2="{wb}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>')
        out.append(f'<rect x="{cx-10}" y="{bt}" width="20" height="{bb-bt}" rx="3.5" fill="{col}"{sw}/>')
    return f'<g transform="translate({x0} {y0}) scale({s})">' + ''.join(out) + '</g>'

V = {
 'dark':  dict(bg='#0B1C1F', ring='#C9A227', ring2='#1E3A3D', a='#F6EFE2', b='#C9A227', name='داكن'),
 'teal':  dict(bg='#0F5C55', ring='#C9A227', ring2='#0B4A44', a='#F6EFE2', b='#C9A227', name='تيل المجلس'),
 'light': dict(bg='#F6EFE2', ring='#C9A227', ring2='#E7DCC6', a='#0F5C55', b='#C9A227', name='فاتح'),
}

def badge(v, size=1080, full_square=False):
    c = V[v]
    sq = f'<rect width="1000" height="1000" fill="{c["bg"]}"/>' if full_square else ''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="{size}" height="{size}">
{sq}<circle cx="500" cy="500" r="500" fill="{c['bg']}"/>
<circle cx="500" cy="500" r="468" fill="none" stroke="{c['ring']}" stroke-width="10"/>
<circle cx="500" cy="500" r="446" fill="none" stroke="{c['ring2']}" stroke-width="3"/>
{candles(150, 62, 3.5, outline=None)}
<text x="500" y="772" text-anchor="middle" font-family="PlexLat" font-weight="700" font-size="90" letter-spacing="1">
<tspan fill="{c['a']}">majlis</tspan><tspan fill="{c['b']}">.stocks</tspan></text>
</svg>'''

css = '''@font-face{font-family:PlexLat;font-weight:700;src:url(fontpkg2/package/files/ibm-plex-sans-latin-700-normal.woff2) format('woff2');}
@font-face{font-family:PlexAr;font-weight:700;src:url(fontpkg/package/files/ibm-plex-sans-arabic-arabic-700-normal.woff2) format('woff2');}
@font-face{font-family:PlexAr;font-weight:500;src:url(fontpkg/package/files/ibm-plex-sans-arabic-arabic-500-normal.woff2) format('woff2');}
*{margin:0;padding:0;box-sizing:border-box}'''

# single exports (square canvas, Instagram crops to circle)
for v in V:
    open(f'ig_{v}.html', 'w', encoding='utf-8').write(
        f'<!doctype html><html><head><meta charset="utf-8"><style>{css} body{{width:1080px;height:1080px;background:{V[v]["bg"]}}}</style></head>'
        f'<body>{badge(v, 1080, True)}</body></html>')

cards = ''
for v, c in V.items():
    cards += f'''<div class="card"><div class="lab">{c["name"]}</div>{badge(v, 440)}
<div class="ig"><div class="pp">{badge(v, 110)}</div><div class="handle">majlis.stocks</div><div class="sub2">شكله بالبروفايل</div></div></div>'''
open('ig_sheet.html', 'w', encoding='utf-8').write(f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{css}
body{{background:#F6EFE2;font-family:PlexAr,sans-serif;width:1680px;padding:44px 56px 52px}}
h1{{font-weight:700;font-size:42px;color:#0F5C55;margin-bottom:6px}}
.sub{{font-weight:500;font-size:23px;color:#6b6b6b;margin-bottom:30px}}
.row{{display:flex;gap:36px;justify-content:space-between}}
.card{{width:510px;background:#fffdf8;border-radius:28px;box-shadow:0 10px 30px rgba(15,92,85,.08);padding:26px 24px 26px;display:flex;flex-direction:column;align-items:center;gap:18px}}
.lab{{align-self:flex-start;font-weight:700;font-size:26px;color:#123430}}
.ig{{display:flex;align-items:center;gap:16px;align-self:stretch;border-top:1px solid #eee3cf;padding-top:16px}}
.pp svg{{display:block;border-radius:50%}}
.handle{{font-family:PlexLat,sans-serif;font-weight:700;font-size:24px;color:#222;direction:ltr}}
.sub2{{font-weight:500;font-size:18px;color:#8a8a8a;margin-inline-start:auto}}
</style></head><body>
<h1>شعار الحساب — majlis.stocks</h1>
<div class="sub">الشموع ترسم علامة صح: أخضر، ثم أحمر نازل، ثم أخضرين صاعدين — بدائرة جاهزة لصورة انستغرام</div>
<div class="row">{cards}</div></body></html>''')
print('ok')
