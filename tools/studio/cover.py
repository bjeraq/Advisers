#!/usr/bin/env python3
"""غلاف الريل (وأول شريحة بالكاروسيل) بالشكل اليديد: عنوان عريض كبير، والرقم المهم ملوّن، وسؤال واضح.

قرار بدر (18 نوفمبر 2026) بعد ما شاف حسابات المالية الكبيرة: الغلاف يشد من أول نظرة.
الاستخدام:
    ~/studio-venv/bin/python tools/studio/cover.py <cover.json> --out <dir>

يطلع ثلاث صور:
    cover_reel.png  1080×1920  (غلاف الريل؛ كل الكلام داخل الوسط 1080×1440 اللي يطلع بشبكة الحساب)
    cover_grid.png  1080×1440  (معاينة: شلون يبين بشبكة الحساب)
    cover_post.png  1080×1350  (نفس التصميم لأول شريحة بالكاروسيل أو بوست بروحه)

cover.json:
{
  "bg": {"video": "<mp4 path or https url>", "t": 12.5}   أو {"image": "<png/jpg path or url>"}   (اختياري)
  "tag": "ميزان الاستثمار • الحلقة 7",
  "lines": [
    {"text": "بعد النتايج", "size": 54, "box": "red"},
    {"text": "إنفيديا: مبيعات [[+103%]]", "size": 104},
    {"text": "والسهم نازل {{28%}}!", "size": 104},
    {"text": "فرصة ولا فخ؟", "size": 120, "box": "yellow"}
  ],
  "faces": ["thawr", "dubb"],                      (اختياري: وجوه من الطاقم)
  "footer": "15 مستشار يتناظرون • القرار عندك",
  "date": "أسعار الثلاثاء 17 نوفمبر 2026",
  "disclaimer": "تحليل لا توصية"
}
تلوين داخل السطر: [[...]] أصفر، {{...}} أحمر، ((...)) تيل. «box» يحط السطر كله داخل مستطيل أصفر أو أحمر.
«size» بالبكسل على عرض 1080، ويصغر بروحه إذا السطر أعرض من الشاشة.
"""
import argparse, hashlib, json, os, re, subprocess, sys, urllib.request
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from carousel import C, S, font, _is_ar, _ltr_token, _tok_w, ring, ctext   # noqa: E402

YELLOW = (255, 204, 51)
RED = (226, 58, 46)
WHITE = (255, 255, 255)
INK_DARK = (16, 20, 22)
COLORS = {'yellow': YELLOW, 'red': RED, 'teal': C['teal'], 'white': WHITE, 'gold': C['gold']}
MARK = {'[[': ('yellow', ']]'), '{{': ('red', '}}'), '((': ('teal', '))')}
CACHE = os.path.expanduser('~/.cache/majlis_covers')


# ---------- الخلفية ----------
def _fetch(src):
    if not re.match(r'^https?://', src):
        return src
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, hashlib.md5(src.encode()).hexdigest()[:12] + os.path.splitext(src.split('?')[0])[1])
    if not os.path.exists(p):
        urllib.request.urlretrieve(src, p)
    return p


def load_bg(bg, base_dir):
    if not bg:
        return None
    if bg.get('image'):
        p = bg['image'] if re.match(r'^https?://', bg['image']) else os.path.join(base_dir, bg['image'])
        return Image.open(_fetch(p)).convert('RGB')
    if bg.get('video'):
        v = bg['video'] if re.match(r'^https?://', bg['video']) else os.path.join(base_dir, bg['video'])
        v = _fetch(v)
        os.makedirs(CACHE, exist_ok=True)
        out = os.path.join(CACHE, f'frame_{hashlib.md5((v + str(bg.get("t", 1))).encode()).hexdigest()[:10]}.png')
        if not os.path.exists(out):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(bg.get('t', 1)), '-i', v,
                            '-frames:v', '1', out], check=True)
        return Image.open(out).convert('RGB')
    return None


def cover_fill(im, w, h, focus_y=0.35):
    """يملى الإطار بدون تشويه، ويقص حول نقطة focus_y (0 فوق، 1 تحت) عشان الوجوه تبقى ظاهرة."""
    k = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * k + 0.5), int(im.height * k + 0.5)), Image.LANCZOS)
    x0 = (im.width - w) // 2
    y0 = int(max(0, min(im.height - h, im.height * focus_y - h * focus_y)))
    return im.crop((x0, y0, x0 + w, y0 + h))


def backdrop(w, h, bg_img, focus_y):
    if bg_img is None:
        img = Image.new('RGBA', (w, h), C['bg'] + (255,))
        glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((-w * 0.3, -h * 0.2, w * 0.9, h * 0.4), fill=C['teal'] + (55,))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160 * S)))
        return img
    img = cover_fill(bg_img, w, h, focus_y).convert('RGBA')
    # تدرج: فوق خفيف (الوجوه تبين)، تحت غامق (الكلام يقرا)
    shade = Image.new('L', (1, 256))
    for i in range(256):
        t = i / 255
        a = 70 + 185 * max(0.0, (t - 0.25) / 0.75) ** 1.2 if t > 0.25 else 70
        shade.putpixel((0, i), int(min(235, a)))
    shade = shade.resize((w, h))
    dark = Image.new('RGBA', (w, h), (6, 10, 12, 255))
    dark.putalpha(shade)
    img.alpha_composite(dark)
    return img


# ---------- الكلام ----------
def parse(text):
    """يرجع [(كلمة, لون)] — التلوين ممكن يمتد على أكثر من كلمة."""
    out, state, close = [], None, None
    for raw in text.split(' '):
        tok, color = raw, state
        for opn, (col, cls) in MARK.items():
            if opn in tok:
                tok = tok.replace(opn, ''); color = col; state, close = col, cls
        if close and close in tok:
            tok = tok.replace(close, ''); state, close = None, None
        if tok:
            out.append((tok, color))
    return out


def line_width(d, toks, f):
    sp = d.textlength(' ', font=f)
    return sum(_tok_w(d, t, f) for t, _ in toks) + sp * (len(toks) - 1)


def draw_line(d, cx, y, toks, f, base_fill, stroke):
    """سطر بالوسط عند cx: الكلمات من اليمين لليسار، وكل كلمة بلونها."""
    sp = d.textlength(' ', font=f)
    x = cx + line_width(d, toks, f) / 2
    sw = int(f.size * 0.07) if stroke else 0
    for tok, col in toks:
        w = _tok_w(d, tok, f)
        fill = COLORS.get(col, base_fill) if col else base_fill
        if _is_ar(tok):
            d.text((x - w, y), tok, font=f, fill=fill, direction='rtl', language='ar',
                   stroke_width=sw, stroke_fill=(0, 0, 0))
        else:
            d.text((x - w, y), _ltr_token(tok), font=f, fill=fill, direction='ltr',
                   stroke_width=sw, stroke_fill=(0, 0, 0))
        x -= w + sp


def line_bbox(d, cx, y, toks, f):
    """حدود السطر الفعلية (للمستطيل الملوّن خلفه)."""
    sp = d.textlength(' ', font=f)
    x = cx + line_width(d, toks, f) / 2
    top, bot = 1e9, -1e9
    for tok, _ in toks:
        w = _tok_w(d, tok, f)
        if _is_ar(tok):
            b = d.textbbox((x - w, y), tok, font=f, direction='rtl', language='ar')
        else:
            b = d.textbbox((x - w, y), _ltr_token(tok), font=f, direction='ltr')
        top, bot = min(top, b[1]), max(bot, b[3])
        x -= w + sp
    lw = line_width(d, toks, f)
    return cx - lw / 2, top, cx + lw / 2, bot


def fit(d, toks, size, maxw):
    while size > 36:
        f = font('bold', size)
        if line_width(d, toks, f) <= maxw:
            return f
        size -= 4
    return font('bold', size)


def pill(d, cx, y, text, f, fg, bg, pad=28):
    w = line_width(d, parse(text), f) + 2 * pad * S
    h = f.size * 1.55
    d.rounded_rectangle((cx - w / 2, y, cx + w / 2, y + h), radius=h / 2, fill=bg)
    draw_line(d, cx, y + h * 0.12, parse(text), f, fg, stroke=False)
    return h


# ---------- التركيب ----------
def render(spec, w_px, h_px, base_dir='.', safe=None, final=True):
    W, H = w_px * S, h_px * S
    top_safe, bot_safe = [v * S for v in (safe or (90, h_px - 90))]
    pad = 64 * S
    bg = load_bg(spec.get('bg'), base_dir)
    img = backdrop(W, H, bg, spec.get('focus_y', 0.3))
    d = ImageDraw.Draw(img)
    cx = W / 2

    # فوق: اسم البرنامج ورقم الحلقة
    if spec.get('tag'):
        pill(d, cx, top_safe + 10 * S, spec['tag'], font('bold', 34), C['gold'], (8, 14, 16, 215))

    # تحت لفوق: التاريخ والإخلاء، ثم شريط المجلس، ثم الوجوه، ثم العنوان
    y = bot_safe
    small = ' • '.join(x for x in (spec.get('date'), spec.get('disclaimer')) if x)
    if small:
        f = font('med', 30)
        y -= f.size * 1.5
        draw_line(d, cx, y, parse(small), f, (225, 232, 230), stroke=True)
        y -= 18 * S
    if spec.get('footer'):
        f = font('bold', 36)
        y -= f.size * 1.55
        pill(d, cx, y, spec['footer'], f, INK_DARK, C['teal'] + (255,))
        y -= 34 * S
    faces = spec.get('faces') or []
    if faces:
        size = 190 * S
        gap = 34 * S
        total = len(faces) * size + (len(faces) - 1) * gap
        y -= size + 10 * S
        x = cx + total / 2 - size / 2
        for k in faces:
            ring(img, k, x, y + size / 2, size, C['teal'])
            x -= size + gap
        y -= 30 * S

    # العنوان: نحسب الارتفاع أول ثم نرسم من فوق لتحت فوق الشريط
    lines = []
    for ln in spec.get('lines', []):
        toks = parse(ln['text'])
        box = ln.get('box')
        maxw = W - 2 * pad - (2 * 0.32 * ln.get('size', 100) * S if box else 0)
        f = fit(d, toks, ln.get('size', 100), maxw)
        lines.append((toks, f, box, ln.get('color')))
    heights = [f.size * (1.42 if box else 1.22) for _, f, box, _ in lines]
    y0 = max(top_safe + 110 * S, y - sum(heights))
    yy = y0
    for (toks, f, box, col), lh in zip(lines, heights):
        ty = yy + (f.size * 0.16 if box else 0)
        if box:
            x0, t, x1, b = line_bbox(d, cx, ty, toks, f)
            px, py = f.size * 0.30, f.size * 0.16
            d.rounded_rectangle((x0 - px, t - py, x1 + px, b + py), radius=f.size * 0.18,
                                fill=COLORS.get(box, YELLOW))
            draw_line(d, cx, ty, toks, f, INK_DARK if box == 'yellow' else WHITE, stroke=False)
        else:
            draw_line(d, cx, ty, toks, f, COLORS.get(col, WHITE), stroke=True)
        yy += lh
    if not final:                               # للكاروسيل: نرجعها بالحجم المضاعف ويصغّرها هو
        return img
    return img.convert('RGB').resize((w_px, h_px), Image.LANCZOS)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    spec = json.load(open(a.spec, encoding='utf-8'))
    base_dir = os.path.dirname(os.path.abspath(a.spec))
    os.makedirs(a.out, exist_ok=True)
    reel = render(spec, 1080, 1920, base_dir, safe=(280, 1640))
    reel.save(os.path.join(a.out, 'cover_reel.png'))
    reel.crop((0, 240, 1080, 1680)).save(os.path.join(a.out, 'cover_grid.png'))
    post = render(spec, 1080, 1350, base_dir, safe=(80, 1270))
    post.save(os.path.join(a.out, 'cover_post.png'))
    # معاينة وحدة: الريل + الشبكة + البوست
    th = [reel.resize((360, 640)), reel.crop((0, 240, 1080, 1680)).resize((360, 480)), post.resize((360, 450))]
    sheet = Image.new('RGB', (3 * 370 + 10, 650), (255, 255, 255))
    x = 10
    for t in th:
        sheet.paste(t, (x, 5)); x += 370
    sheet.save(os.path.join(a.out, 'cover_preview.jpg'), quality=88)
    print(os.path.join(a.out, 'cover_reel.png'))


if __name__ == '__main__':
    sys.exit(main())
