"""ترانسكريبت كلمة-كلمة (ASS): الكلمة المنطوقة تيل والباقي أبيض، بخط IBM Plex Sans Arabic.

حدث مستقل لكل حالة كلمة بدل كاريوكي \\k — يتفادى مشاكل الاتجاه من اليمين لليسار.
خط 58 بمسودة 720 و88 بنهائي 1080 (طلب بدر 10 نوفمبر: «الخط صغير كبّره»).
التجميع ديناميكي: حتى 3 كلمات وبسقف 16 حرفاً → سطر واحد قصير، ما يصعد نحو الوجه.
مناطق إنستغرام الآمنة (قاعدة ig_safe_zones، 14 نوفمبر): أسفل ~78% يغطيه اسم الحساب والكابشن،
وأزرار اللايك/الكومنت على يمين الشاشة (x ≥ 85%) من نص الارتفاع وتحت → السطر قاعدته عند ~71%
من الارتفاع (MarginV ≈ 29%) ومزاح لليسار بهامش يمين أكبر.

    python3 captions.py <out.ass> <words.json>:<offset> [--res 720|1080]
"""
import sys, json

STYLE = {  # fontsize, outline, shadow, margin_l, margin_r, margin_v
    720: (58, 3, 1, 24, 136, 372),
    1080: (88, 4, 2, 36, 204, 558),
}
TEAL = r'{\c&HBBD42D&}'
WHITE = r'{\c&HFFFFFF&}'


def head(res):
    fs, ol, sh, ml, mr, mv = STYLE[res]
    w, h = (720, 1280) if res == 720 else (1080, 1920)
    return f"""[Script Info]
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: W, IBM Plex Sans Arabic, {fs}, &H00FFFFFF, &H00141208, &H96141208, 1, {ol}, {sh}, 2, {ml}, {mr}, {mv}, 1

[Events]
Format: Layer, Start, End, Style, Text
"""


def ts(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def groups(words, maxw=3, maxc=16):
    out, cur, c = [], [], 0
    for w in words:
        wl = len(w['w'])
        if cur and (len(cur) >= maxw or c + wl > maxc):
            out.append(cur); cur, c = [], 0
        cur.append(w); c += wl
    if cur:
        out.append(cur)
    return out


def events(words, offset=0.0):
    ev = []
    gs = groups(words)
    for gi, g in enumerate(gs):
        nxt = gs[gi + 1][0]['s'] - 0.02 if gi + 1 < len(gs) else g[-1]['e'] + 0.25
        for k in range(len(g)):
            s = g[k]['s'] + offset
            e = (g[k + 1]['s'] if k + 1 < len(g) else min(g[-1]['e'] + 0.25, nxt)) + offset
            txt = ' '.join((TEAL if j == k else WHITE) + w['w'] for j, w in enumerate(g))
            ev.append(f"Dialogue: 0,{ts(s)},{ts(e)},W,{txt}")
    return ev


def write(out, specs, res=720):
    """specs: [(words_list, offset), ...]"""
    lines = [head(res)]
    for words, off in specs:
        lines += events(words, off)
    open(out, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    args = sys.argv[1:]
    res = 720
    if '--res' in args:
        i = args.index('--res'); res = int(args[i + 1]); del args[i:i + 2]
    out, specs = args[0], []
    for spec in args[1:]:
        path, off = spec.rsplit(':', 1)
        specs.append((json.load(open(path)), float(off)))
    write(out, specs, res)
    print(out, 'ok')
