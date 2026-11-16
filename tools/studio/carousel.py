#!/usr/bin/env python3
"""كاروسيل إنستغرام لكل حلقة (طلب بدر 2026-11-15): بوست يدعم الريلز ويعرض للناس كل المعلومات
اللي كانت قدام القاضي ورأي كل مستشار، عشان كل واحد ياخذ قراره حسب شخصيته (متحفظ / متوازن / مغامر).

الاستخدام:
    ~/studio-venv/bin/python tools/studio/carousel.py tools/studio/episodes/<slug>/carousel.json --out <dir>
يطلع PNG بحجم 1080×1350 (4:5) لكل شريحة + صورة مراجعة contact.jpg.

المحتوى يكتبه كاتب الحلقة بملف carousel.json (نصوص قصيرة كويتية بسيطة)، والأداة ترسم بس.
أنواع الشرائح (type):
  cover    name, ticker, date, sub                                 — الشريحة الأولى دايماً: اسم السهم والتاريخ
           (قاعدة بدر 2026-11-16: عشان اللي يتصفح يلقى سهمه على طول). لو ما انكتبت، الأداة تبنيها
           تلقائياً من meta.brand و episode.json (ticker/data_date) اللي جنب carousel.json.
  hook     kicker, headline, big, big_sub, faces[ids], swipe      — الغلاف اللي يشد
  facts    title, rows[[label, value, tone]], note                 — الأرقام اللي كانت قدام القاضي
  duel     title, left{id,name,vote,score,points[]}, right{...}    — الضب ضد الثعلب (أو أي اثنين)
  voices   title, items[{id,name,vote,score,line}] (≤4)            — مستشارين بسطر لكل واحد
  board    title, items[{id,name,vote,score}] (≤15), total         — لوحة الأصوات كلها
  profiles title, items[{who,id,line}] (3)                         — أنت أي نوع مستثمر؟
  verdict  meter, votes{buy,wait,sell}, option, confidence, why[]  — حكم القاضي وعلى أي أساس
  decide   title, questions[], cta, disclaimer                     — القرار قرارك
tone: pos / neg / mid. vote: شراء / انتظار / بيع (اللون يتبعها).
"""
import argparse, json, os, re, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
S = 2                       # تنعيم فائق
W, H = 1080 * S, 1350 * S
PAD = 72 * S

C = {
    'bg': (15, 26, 28), 'bg2': (21, 36, 38), 'card': (24, 42, 44), 'line': (40, 62, 64),
    'ink': (233, 239, 237), 'muted': (159, 176, 173), 'teal': (60, 194, 176), 'gold': (216, 178, 94),
    'pos': (26, 166, 150), 'neg': (224, 106, 69), 'mid': (216, 178, 94),
}
# دور كل مستشار (يطلع جنب اسم الحيوان بلوحة الأصوات)
ROLE = {
    'thawr': 'محامي الشراء', 'dubb': 'محامي الحذر', 'asasi': 'محلل الأساسيات', 'fanni': 'المحلل الفني',
    'macro': 'الاستراتيجية الكلية', 'mudharib': 'المضاربة السريعة', 'suyula': 'قارئة السيولة',
    'congress': 'متتبع السياسيين', 'whales': 'متتبع الحيتان', 'rassad': 'رصّاد الأخبار',
    'mazloum': 'صائد المظلومات', 'saboor': 'المستثمر الصبور', 'qita': 'محلل القطاع',
    'haris': 'حارس المحفظة', 'qadhi': 'القاضي', 'raqib': 'الرقيب الشرعي',
}
VOTE = {'شراء': 'pos', 'انتظار': 'mid', 'بيع': 'neg'}

# أوراق الشخصيات المعتمدة (turnaround) وقص الوجه المربع (cx, cy, side) على ورقة 1344×752
SHEETS = 'https://d8j0ntlcm91z4.cloudfront.net/user_3KJGwRtEbfJGNmiXOrf7RVSlYxf/'
CAST = {
    'asasi':    ('hf_20261110_195216_bcfcb70f-0ae8-429a-83ed-800fb148b753.png', (1250, 240, 380)),
    'congress': ('hf_20261110_195217_2acdd5c9-e4dd-4438-bbac-23bbc85c04ab.png', (1230, 250, 400)),
    'dubb':     ('hf_20261110_145843_4708d2a3-50b3-4f1f-8075-ffd868ec26bd.png', (810, 230, 380)),
    'fanni':    ('hf_20261110_195216_25954d98-5661-4eb9-a7c1-5fb6747e8719.png', (1250, 200, 330)),
    'macro':    ('hf_20261110_195214_361ebe62-cbf8-42a1-9c56-59f31a6646d7.png', (1230, 230, 360)),
    'mazloum':  ('hf_20261110_195214_3e6fb5ec-9dee-4176-bb81-13b92e9ff1fe.png', (1210, 250, 360)),
    'mudharib': ('hf_20261110_195213_5d9f02db-d73c-4d74-9d8c-60f0096ea29c.png', (1230, 230, 360)),
    'qadhi':    ('hf_20261110_195216_25c7f704-f5ab-4992-8bf8-8b72c64c51a4.png', (1220, 235, 370)),
    'rassad':   ('hf_20261110_195213_1b4f7293-aa7e-4f51-87cd-45ba07c3c943.png', (1230, 250, 330)),
    'saboor':   ('hf_20261110_195212_39d7d94a-e572-47ec-a6a8-d6670266dcd9.png', (1210, 250, 380)),
    'suyula':   ('hf_20261110_195212_65d85815-d335-454a-9a9e-318b580551ea.png', (1220, 230, 360)),
    'thawr':    ('hf_20261110_144751_7d46c827-8028-429d-9d9c-8addc2aa9f24.png', (1170, 240, 420)),
    'whales':   ('hf_20261110_120717_68f65514-c6cc-47d2-85db-af36de1b93a4.png', (1120, 180, 340)),
}
CACHE = os.path.expanduser('~/.cache/majlis_avatars')
# بورتريه مربع 1024 بدل الورقة (cx, cy, side): يغلب CAST — السلحفاة الشايب + وجوه الأدوار الجديدة
PORTRAITS = {
    'asasi': ('https://d8j0ntlcm91z4.cloudfront.net/user_3KJGwRtEbfJGNmiXOrf7RVSlYxf/hf_20261115_064326_953f1d70-fe2c-4fdb-a989-095c828747f3.png', (525, 310, 560)),
    'haris': ('https://d8j0ntlcm91z4.cloudfront.net/user_3KJGwRtEbfJGNmiXOrf7RVSlYxf/hf_20261116_063623_39bd67df-05cd-4cd1-b5e4-8e630b8eb200.png', (515, 290, 600)),   # الحصان القوي بالشماغ الأحمر (اختيار بدر)
    'qita':  ('https://d8j0ntlcm91z4.cloudfront.net/user_3KJGwRtEbfJGNmiXOrf7RVSlYxf/hf_20261116_062146_93f79712-b73b-417f-b66e-f5f0c7946202.png', (530, 330, 540)),   # المها (مقترح)
}


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f'PlexArabic-{"Bold" if weight == "bold" else "Medium"}.ttf'), size * S)


ARABIC = re.compile('[\u0600-\u06FF]')
PUNCT_END = ':،؛؟!.,'


def _is_ar(t):
    return bool(ARABIC.search(t))


def _ltr_token(tok):
    """كلمة أرقام/لاتيني داخل سطر عربي: نرسمها يسار→يمين، ونعكس الأقواس وننقل علامة الوقف لطرفها اليسار
    (لأن السطر يُقرأ من اليمين). هذا بدل محرك الاتجاهات اللي كان يقلب 390$ إلى $390."""
    pre = ''
    while tok and tok[-1] in PUNCT_END:
        pre = tok[-1] + pre; tok = tok[:-1]
    if tok.startswith('(') and not tok.endswith(')'):
        tok = tok[1:] + ')'
    elif tok.endswith(')') and not tok.startswith('('):
        tok = '(' + tok[:-1]
    return pre + tok


def _tok_w(d, tok, f):
    if _is_ar(tok):
        return d.textlength(tok, font=f, direction='rtl', language='ar')
    return d.textlength(_ltr_token(tok), font=f, direction='ltr')


def tw(d, t, f):
    if not _is_ar(t):
        return d.textlength(t, font=f, direction='ltr')
    sp = d.textlength(' ', font=f)
    toks = t.split(' ')
    return sum(_tok_w(d, k, f) for k in toks) + sp * (len(toks) - 1)


def rtext(d, x_right, y, t, f, fill):
    """سطر محاذى يمين عند x_right. العربي يُرسم كلمة كلمة من اليمين، والأرقام كل وحدة باتجاهها."""
    if not _is_ar(t):
        d.text((x_right - tw(d, t, f), y), t, font=f, fill=fill, direction='ltr')
        return
    sp = d.textlength(' ', font=f)
    x = x_right
    for tok in t.split(' '):
        w = _tok_w(d, tok, f)
        if _is_ar(tok):
            d.text((x - w, y), tok, font=f, fill=fill, direction='rtl', language='ar')
        else:
            d.text((x - w, y), _ltr_token(tok), font=f, fill=fill, direction='ltr')
        x -= w + sp


def ctext(d, cx, y, t, f, fill):
    rtext(d, cx + tw(d, t, f) / 2, y, t, f, fill)


def ltext(d, x_left, y, t, f, fill):
    rtext(d, x_left + tw(d, t, f), y, t, f, fill)


def wrap(d, t, f, maxw):
    words, lines, cur = t.split(), [], ''
    for w in words:
        cand = (cur + ' ' + w).strip()
        if cur and tw(d, cand, f) > maxw:
            lines.append(cur); cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def para(d, x_right, y, t, f, fill, maxw, gap=1.35, center=None):
    lh = f.size * gap
    for ln in wrap(d, t, f, maxw):
        if center is not None:
            ctext(d, center, y, ln, f, fill)
        else:
            rtext(d, x_right, y, ln, f, fill)
        y += lh
    return y


def avatar(key, size):
    size = int(size)
    os.makedirs(CACHE, exist_ok=True)
    mask = Image.new('L', (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    if key in PORTRAITS or key in CAST:
        if key in PORTRAITS:
            url, (cx, cy, s) = PORTRAITS[key]
        else:
            name, (cx, cy, s) = CAST[key]
            url = SHEETS + name
        p = os.path.join(CACHE, url.rsplit('/', 1)[1])
        if not os.path.exists(p):
            urllib.request.urlretrieve(url, p)
        im = Image.open(p).convert('RGB')
        x0 = max(0, min(im.width - s, cx - s // 2)); y0 = max(0, min(im.height - s, cy - s // 2))
        face = im.crop((x0, y0, x0 + s, y0 + s)).resize((size, size), Image.LANCZOS)
    else:   # مستشار بلا شخصية (محلل القطاع، حارس المحفظة): دائرة بلون الهوية
        face = Image.new('RGB', (size, size), C['line'])
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(face, (0, 0), mask)
    return out


NO_FACE = {'qita': 'ق', 'haris': 'ح', 'raqib': 'ر'}   # أدوار بلا شخصية: حرف بدل الوجه


def ring(img, key, cx, cy, size, color):
    d = ImageDraw.Draw(img)
    r = size / 2 + 5 * S
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    a = avatar(key, size)
    img.alpha_composite(a, (int(cx - size / 2), int(cy - size / 2)))
    if key == 'raqib':   # دور مخفي: لا يظهر كشخصية — شارة ✓ «متوافق» بدل الوجه
        r2 = size / 2
        d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), fill=C['pos'])
        w = max(3, int(size * 0.07))
        d.line([(cx - r2 * 0.42, cy + r2 * 0.02), (cx - r2 * 0.1, cy + r2 * 0.34), (cx + r2 * 0.46, cy - r2 * 0.3)],
               fill=C['ink'], width=w, joint='curve')
    elif key not in CAST and key not in PORTRAITS:
        f = font('bold', max(20, int(size / S * 0.42)))
        ctext(d, cx, cy - f.size * 0.62, NO_FACE.get(key, '•'), f, C['muted'])


def sc(n):
    return f'{n:+d}' if n else '0'


def badge(d, x_left, y, text, color, f):
    w = tw(d, text, f) + 36 * S
    h = f.size + 22 * S
    d.rounded_rectangle((x_left, y, x_left + w, y + h), radius=h / 2, fill=color)
    ctext(d, x_left + w / 2, y + 7 * S, text, f, C['bg'])
    return w


def base(n, total, meta):
    img = Image.new('RGBA', (W, H), C['bg'] + (255,))
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-W * 0.3, -H * 0.25, W * 0.9, H * 0.45), fill=C['teal'] + (40,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160 * S)))
    d = ImageDraw.Draw(img)
    f = font('med', 26)
    rtext(d, W - PAD, 46 * S, meta.get('brand', 'مجلس المستشارين'), f, C['gold'])
    d.text((PAD, 46 * S), f'{n}/{total}', font=f, fill=C['muted'])
    fb = font('med', 24)
    rtext(d, W - PAD, H - 70 * S, meta.get('footer', ''), fb, C['muted'])
    if meta.get('handle'):
        d.text((PAD, H - 70 * S), meta['handle'], font=fb, fill=C['teal'])
    return img, d


def title(d, t, y=120):
    f = font('bold', 52)
    return para(d, W - PAD, y * S, t, f, C['ink'], W - 2 * PAD) + 18 * S


AR_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر',
             'أكتوبر', 'نوفمبر', 'ديسمبر']
AR_DAYS = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']


def auto_cover(spec_path, meta):
    """يبني شريحة الغلاف (اسم السهم + التاريخ) من meta و episode.json اللي جنب الملف."""
    import datetime
    ep = {}
    ep_path = os.path.join(os.path.dirname(os.path.abspath(spec_path)), 'episode.json')
    if os.path.exists(ep_path):
        ep = json.load(open(ep_path, encoding='utf-8'))
    name = meta.get('name') or meta.get('brand', '').split('•')[-1].strip()
    ticker = meta.get('ticker') or ep.get('ticker', '')
    date = meta.get('date', '')
    if not date and ep.get('data_date'):
        dt = datetime.date.fromisoformat(ep['data_date'])
        date = f'{AR_DAYS[dt.weekday()]} {dt.day} {AR_MONTHS[dt.month - 1]} {dt.year}'
    return {'type': 'cover', 'name': name, 'ticker': ticker, 'date': date}


def s_cover(img, d, sl, meta):
    cx = W / 2
    name, ticker = sl.get('name', ''), sl.get('ticker', '')
    fs = 170
    while fs > 90 and tw(d, name, font('bold', fs)) > W - 2 * PAD:
        fs -= 10
    y = 380 * S
    if name:
        ctext(d, cx, y, name, font('bold', fs), C['ink'])
        y += fs * 1.55 * S
    if ticker and ticker.upper() != name.upper():
        f = font('bold', 96)
        w = tw(d, ticker, f) + 80 * S
        h = 150 * S
        d.rounded_rectangle((cx - w / 2, y, cx + w / 2, y + h), radius=28 * S, outline=C['teal'], width=5 * S)
        ctext(d, cx, y + 8 * S, ticker, f, C['teal'])
        y += h + 70 * S
    else:
        y += 20 * S
    d.line((cx - 160 * S, y, cx + 160 * S, y), fill=C['gold'], width=4 * S)
    y += 50 * S
    if sl.get('date'):
        ctext(d, cx, y, sl['date'], font('bold', 56), C['gold'])
        y += 100 * S
    if sl.get('sub'):
        para(d, W - PAD, y, sl['sub'], font('med', 40), C['muted'], W - 2 * PAD, center=cx)
    ctext(d, cx, H - 200 * S, sl.get('swipe', 'اسحب ←'), font('bold', 38), C['muted'])


def s_hook(img, d, sl, meta):
    f = font('med', 30)
    k = sl.get('kicker', '')
    if k:
        badge(d, W - PAD - tw(d, k, f) - 36 * S, 130 * S, k, C['gold'], f)
    y = para(d, W - PAD, 230 * S, sl['headline'], font('bold', 88), C['ink'], W - 2 * PAD, gap=1.25)
    y += 30 * S
    if sl.get('big'):
        fb = font('bold', 170)
        rtext(d, W - PAD, y, sl['big'], fb, C['teal'])
        y += 210 * S
    if sl.get('big_sub'):
        y = para(d, W - PAD, y, sl['big_sub'], font('med', 40), C['muted'], W - 2 * PAD) + 30 * S
    faces = sl.get('faces', [])
    if faces:
        size = 200 * S
        n = len(faces)
        gapx = 40 * S
        total = n * size + (n - 1) * gapx
        x = W / 2 + total / 2 - size / 2
        cy = max(y + size / 2 + 20 * S, H - 380 * S)
        for key in faces:
            ring(img, key, x, cy, size, C['teal'])
            x -= size + gapx
    if sl.get('swipe'):
        ctext(d, W / 2, H - 160 * S, sl['swipe'], font('bold', 38), C['gold'])


def s_facts(img, d, sl, meta):
    y = title(d, sl['title'])
    rows = sl['rows']
    rh = 128 * S
    for label, value, tone in rows:
        d.rounded_rectangle((PAD, y, W - PAD, y + rh - 18 * S), radius=28 * S, fill=C['card'])
        rtext(d, W - PAD - 34 * S, y + 32 * S, label, font('med', 36), C['muted'])
        lw = tw(d, label, font('med', 36))
        room = W - 2 * PAD - 68 * S - lw - 30 * S
        size = 46
        while size > 26 and tw(d, value, font('bold', size)) > room:
            size -= 2
        fv = font('bold', size)
        ltext(d, PAD + 34 * S, y + 26 * S + (46 - size) * S / 2, value, fv, C[tone] if tone in C else C['ink'])
        y += rh
    if sl.get('note'):
        para(d, W - PAD, y + 10 * S, sl['note'], font('med', 30), C['muted'], W - 2 * PAD)


def _side(img, d, x0, x1, y, side):
    cx = (x0 + x1) / 2
    col = C[VOTE.get(side['vote'], 'mid')]
    ring(img, side['id'], cx, y + 130 * S, 230 * S, col)
    y += 280 * S
    ctext(d, cx, y, side['name'], font('bold', 40), C['ink'])
    y += 64 * S
    fv = font('bold', 32)
    lbl = f"{side['vote']}  {sc(side['score'])}"
    bw = tw(d, lbl, fv) + 36 * S
    badge(d, cx - bw / 2, y, lbl, col, fv)
    y += 84 * S
    fp = font('med', 32)
    for p in side['points']:
        y = para(d, x1 - 12 * S, y, '• ' + p, fp, C['ink'], x1 - x0 - 24 * S, gap=1.3) + 14 * S


def s_duel(img, d, sl, meta):
    y = title(d, sl['title'])
    mid = W / 2
    _side(img, d, mid + 16 * S, W - PAD, y + 10 * S, sl['right'])
    _side(img, d, PAD, mid - 16 * S, y + 10 * S, sl['left'])
    d.line((mid, y + 40 * S, mid, H - 160 * S), fill=C['line'], width=3 * S)
    ctext(d, mid, y + 110 * S, 'ضد', font('bold', 34), C['gold'])


def s_voices(img, d, sl, meta):
    y = title(d, sl['title'])
    items = sl['items']
    ch = (H - y - 150 * S) / max(1, len(items))
    for it in items:
        col = C[VOTE.get(it['vote'], 'mid')]
        d.rounded_rectangle((PAD, y, W - PAD, y + ch - 20 * S), radius=30 * S, fill=C['card'])
        size = 150 * S
        ring(img, it['id'], W - PAD - 30 * S - size / 2, y + 30 * S + size / 2, size, col)
        xr = W - PAD - 60 * S - size
        rtext(d, xr, y + 30 * S, it['name'], font('bold', 38), C['ink'])
        fv = font('bold', 28)
        lbl = f"{it['vote']} {sc(it['score'])}"
        badge(d, PAD + 30 * S, y + 32 * S, lbl, col, fv)
        para(d, xr, y + 96 * S, it['line'], font('med', 31), C['ink'], xr - PAD - 30 * S, gap=1.3)
        y += ch


def lean(vote, score):
    """شرح الدرجة بالكلام (بدر: «انتظار +2» و«انتظار -3» مو مفهومة)."""
    if vote == 'انتظار':
        return 'محايد' if not score else f"يميل للشراء {sc(score)}" if score > 0 else f"يميل للبيع {sc(score)}"
    return f"الدرجة {sc(score)}"


def s_board(img, d, sl, meta):
    """لوحة الأصوات كقائمة بعمودين: وجه + اسم + الرأي وميله بالكلام."""
    y = title(d, sl['title'])
    if sl.get('sub'):
        y = para(d, W - PAD, y - 6 * S, sl['sub'], font('med', 28), C['muted'], W - 2 * PAD) + 22 * S
    items = sl['items']
    cols = 2
    rows = (len(items) + cols - 1) // cols
    gap = 20 * S
    cw = (W - 2 * PAD - gap) / cols
    rh = min(124 * S, (H - y - 230 * S) / rows)
    av = rh - 26 * S
    for i, it in enumerate(items):
        c, r = divmod(i, rows)                     # العمود اليمين أول (من اليمين لليسار)
        x1 = W - PAD - c * (cw + gap)
        y0 = y + r * rh
        col = C[VOTE.get(it['vote'], 'mid')]
        d.rounded_rectangle((x1 - cw, y0, x1, y0 + rh - 10 * S), radius=22 * S, fill=C['card'])
        ring(img, it['id'], x1 - 16 * S - av / 2, y0 + (rh - 10 * S) / 2, av - 8 * S, col)
        xr = x1 - 34 * S - av
        fn = font('bold', 26)
        rtext(d, xr, y0 + 10 * S, it['name'], fn, C['ink'])
        role = it.get('role', ROLE.get(it['id']))
        if role and role != it['name']:                 # الحيوان أول، وبعده دوره بالمجلس
            xr2 = xr - tw(d, it['name'], fn) - 12 * S
            room = xr2 - (x1 - cw) - 18 * S
            sz = 21
            while sz > 15 and tw(d, '• ' + role, font('med', sz)) > room:
                sz -= 1
            rtext(d, xr2, y0 + 16 * S, '• ' + role, font('med', sz), C['muted'])
        rtext(d, xr, y0 + 52 * S, f"{it['vote']} • {lean(it['vote'], it['score'])}", font('med', 22), col)
    if sl.get('total'):
        ctext(d, W / 2, H - 168 * S, sl['total'], font('bold', 40), C['gold'])


def s_profiles(img, d, sl, meta):
    y = title(d, sl['title'])
    if sl.get('sub'):
        y = para(d, W - PAD, y, sl['sub'], font('med', 32), C['muted'], W - 2 * PAD) + 20 * S
    items = sl['items']
    ch = min(330 * S, (H - y - 150 * S) / len(items))
    for it in items:
        d.rounded_rectangle((PAD, y, W - PAD, y + ch - 22 * S), radius=30 * S, fill=C['card'])
        size = 160 * S
        ring(img, it['id'], W - PAD - 30 * S - size / 2, y + ch / 2 - 11 * S, size, C['gold'])
        xr = W - PAD - 64 * S - size
        rtext(d, xr, y + 34 * S, it['who'], font('bold', 40), C['gold'])
        para(d, xr, y + 100 * S, it['line'], font('med', 32), C['ink'], xr - PAD - 30 * S, gap=1.3)
        y += ch


def s_verdict(img, d, sl, meta):
    y = title(d, sl.get('title', 'حكم القاضي'))
    size = 210 * S
    ring(img, 'qadhi', W - PAD - size / 2, y + size / 2 + 10 * S, size, C['gold'])
    m = sl['meter']
    col = C['pos'] if m > 0 else C['neg'] if m < 0 else C['mid']
    rtext(d, W - PAD - size - 50 * S, y + 6 * S, 'ميزان الاستثمار', font('med', 34), C['muted'])
    rtext(d, W - PAD - size - 50 * S, y + 50 * S, sc(m), font('bold', 120), col)
    y += size + 50 * S
    v = sl['votes']; tot = v['buy'] + v['wait'] + v['sell']
    bx0, bx1, bh = PAD, W - PAD, 46 * S
    x = bx1
    for key, n, label in (('pos', v['buy'], 'شراء'), ('mid', v['wait'], 'انتظار'), ('neg', v['sell'], 'بيع')):
        if not n:
            continue
        w = (bx1 - bx0) * n / tot
        d.rectangle((x - w, y, x, y + bh), fill=C[key])
        if w > 120 * S:
            ctext(d, x - w / 2, y + 4 * S, f'{label} {n}', font('bold', 26), C['bg'])
        x -= w
    y += bh + 40 * S
    d.rounded_rectangle((PAD, y, W - PAD, y + 230 * S), radius=30 * S, fill=C['card'])
    rtext(d, W - PAD - 30 * S, y + 22 * S, 'الخيار الأول', font('med', 30), C['gold'])
    para(d, W - PAD - 30 * S, y + 70 * S, sl['option'], font('bold', 36), C['ink'], W - 2 * PAD - 60 * S, gap=1.3)
    ltext(d, PAD + 30 * S, y + 22 * S, f"الثقة {sl['confidence']}", font('bold', 30), C['teal'])
    y += 260 * S
    rtext(d, W - PAD, y, 'على أي أساس حكم؟', font('bold', 36), C['ink'])
    y += 64 * S
    for w_ in sl['why']:
        y = para(d, W - PAD, y, '• ' + w_, font('med', 31), C['ink'], W - 2 * PAD, gap=1.3) + 10 * S


def s_decide(img, d, sl, meta):
    y = title(d, sl.get('title', 'القرار قرارك'))
    for i, q in enumerate(sl['questions'], 1):
        d.rounded_rectangle((PAD, y, W - PAD, y + 120 * S), radius=26 * S, fill=C['card'])
        ctext(d, W - PAD - 52 * S, y + 30 * S, str(i), font('bold', 40), C['gold'])
        para(d, W - PAD - 100 * S, y + 30 * S, q, font('med', 32), C['ink'], W - 2 * PAD - 140 * S, gap=1.25)
        y += 140 * S
    y += 20 * S
    if sl.get('cta'):
        y = para(d, W - PAD, y, sl['cta'], font('bold', 40), C['teal'], W - 2 * PAD, center=W / 2) + 20 * S
    if sl.get('disclaimer'):
        para(d, W - PAD, H - 200 * S, sl['disclaimer'], font('med', 26), C['muted'], W - 2 * PAD, center=W / 2)


RENDER = {'cover': s_cover, 'hook': s_hook, 'facts': s_facts, 'duel': s_duel, 'voices': s_voices, 'board': s_board,
          'profiles': s_profiles, 'verdict': s_verdict, 'decide': s_decide}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    spec = json.load(open(a.spec, encoding='utf-8'))
    os.makedirs(a.out, exist_ok=True)
    slides = spec['slides']; meta = spec.get('meta', {})
    if not slides or slides[0].get('type') != 'cover':
        slides = [auto_cover(a.spec, meta)] + slides
    paths = []
    for i, sl in enumerate(slides, 1):
        img, d = base(i, len(slides), meta)
        RENDER[sl['type']](img, d, sl, meta)
        p = os.path.join(a.out, f'{i:02d}_{sl["type"]}.png')
        img.convert('RGB').resize((W // S, H // S), Image.LANCZOS).save(p)
        paths.append(p)
    # صورة مراجعة وحدة
    th = [Image.open(p).resize((270, 338)) for p in paths]
    cols = 4
    sheet = Image.new('RGB', (cols * 274, ((len(th) + cols - 1) // cols) * 342), (255, 255, 255))
    for i, t in enumerate(th):
        sheet.paste(t, ((cols - 1 - i % cols) * 274 + 2, (i // cols) * 342 + 2))   # من اليمين لليسار
    sheet.save(os.path.join(a.out, 'contact.jpg'), quality=88)
    print('\n'.join(paths))


if __name__ == '__main__':
    sys.exit(main())
