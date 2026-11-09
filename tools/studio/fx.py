"""مكتبة الرسومات التفاعلية: لوحات متحركة شفافة (qtrle .mov) تنطلق على توقيت كلمة بالكلام.

كل لوحة مرسومة بإحداثيات أساس 620×430 (دقة 720) وتتضاعف بـ S (1.5 لدقة 1080).
موضع اللوحة بالمشهد يحدده ملف الحلقة (box) — وقاعدتها: **الوجه ما ينغطى**؛ اللوحة
بالزاوية فوق النافذة أو على الصدر تحت الذقن أو فوق الرأس على الشاشة الخلفية.

الأنواع (kind) ومعاملاتها:
  cash_bars     value, label, dur        أعمدة تتراكم + عداد نسبة يصعد
  support_break label, dur               سعر أحمر يكسر خط دعم متقطع وينزل نحو «؟»
  donut         value, lines[3], dur     حلقة تمتلئ إلى نسبة + ثلاث تسميات
  verdict_meter score, scale_max, votes[[label, n, color]], title, dur   ميزان المجلس
"""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

BASE_W, BASE_H, FPS = 620, 430, 30
COLORS = {
    'teal': (45, 212, 187, 255), 'gold': (212, 167, 71, 255), 'red': (239, 68, 68, 255),
    'white': (255, 255, 255, 255),
}
TEAL, GOLD, RED, WHITE = (COLORS[k] for k in ('teal', 'gold', 'red', 'white'))
BG = (8, 20, 24, 170)
TRACK = (70, 90, 96, 255)
MUTED = (120, 140, 150, 200)


class Pen:
    """ImageDraw بإحداثيات الأساس: يضرب الإحداثيات والخطوط بـ S."""

    def __init__(self, d, s, bold):
        self.d, self.s, self.bold, self._fonts = d, s, bold, {}

    def _b(self, b):
        return [v * self.s for v in b]

    def _w(self, w):
        return max(1, round(w * self.s))

    def font(self, size):
        if size not in self._fonts:
            self._fonts[size] = ImageFont.truetype(self.bold, round(size * self.s))
        return self._fonts[size]

    def rrect(self, b, r, **kw):
        if 'width' in kw:
            kw['width'] = self._w(kw['width'])
        self.d.rounded_rectangle(self._b(b), radius=r * self.s, **kw)

    def line(self, pts, width, **kw):
        self.d.line([(x * self.s, y * self.s) for x, y in pts], width=self._w(width), **kw)

    def ellipse(self, b, **kw):
        self.d.ellipse(self._b(b), **kw)

    def arc(self, b, a0, a1, width, **kw):
        self.d.arc(self._b(b), a0, a1, width=self._w(width), **kw)

    def text(self, xy, t, size, **kw):
        self.d.text((xy[0] * self.s, xy[1] * self.s), t, font=self.font(size), **kw)


def ease(t):
    return 1 - (1 - t) ** 3


class Panel:
    def __init__(self, s, bold):
        self.s, self.bold = s, bold
        self.W, self.H = round(BASE_W * s), round(BASE_H * s)

    def frame(self):
        img = Image.new('RGBA', (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, self.W - 1, self.H - 1], radius=26 * self.s, fill=BG,
                            outline=TEAL, width=max(1, round(3 * self.s)))
        return img, Pen(d, self.s, self.bold)


def cash_bars(P, value=76, label='التدفق الحر ينمو', dur=3.0):
    N = int(dur * FPS); W = BASE_W
    for i in range(N):
        t = i / (N - 1); img, p = P.frame()
        for b in range(5):
            bt = min(1, max(0, (t * 1.4 - b * 0.12)))
            h = ease(bt) * (120 + b * 42)
            x0 = 60 + b * 95
            if h > 2:
                p.rrect([x0, 330 - h, x0 + 66, 330], 10, fill=GOLD if b < 4 else TEAL)
        pct = int(ease(min(1, t * 1.2)) * value)
        p.text((W - 40, 360), f"%{pct}+", 80, fill=TEAL, anchor='rm', direction='rtl')
        p.text((40, 372), label, 40, fill=WHITE, anchor='lm', direction='rtl')
        yield img


def support_break(P, label='الدعم', dur=4.0):
    N = int(dur * FPS); W = BASE_W
    sup_y = 215
    pts = [(20, 70), (90, 110), (150, 88), (210, 140), (265, 120), (320, 170), (370, 150),
           (420, 205), (470, sup_y - 6), (520, 268), (570, 330), (600, 368)]
    for i in range(N):
        t = i / (N - 1); img, p = P.frame()
        for x in range(20, W - 20, 26):
            p.line([(x, sup_y), (x + 13, sup_y)], 3, fill=TEAL)
        p.text((30, sup_y - 22), label, 40, fill=TEAL, anchor='lm', direction='rtl')
        prog = ease(t) * (len(pts) - 1)
        full = int(prog)
        seg = pts[:full + 1]
        if full < len(pts) - 1:
            fr = prog - full
            a, b = pts[full], pts[full + 1]
            seg.append((a[0] + (b[0] - a[0]) * fr, a[1] + (b[1] - a[1]) * fr))
        if len(seg) > 1:
            p.line(seg, 7, fill=RED, joint='curve')
        tip = seg[-1]
        p.ellipse([tip[0] - 8, tip[1] - 8, tip[0] + 8, tip[1] + 8], fill=RED)
        for k, (x, _) in enumerate(pts[:max(1, full)]):
            vh = 14 + (k * 7 % 34) + (26 if k >= 8 else 0)
            p.rrect([x - 7, 408 - vh, x + 7, 408], 3, fill=(RED if k >= 8 else MUTED))
        if t > 0.86:
            p.text((tip[0] - 36, min(tip[1] + 16, 330)), "؟", 96, fill=RED, direction='rtl')
        yield img


def donut(P, value=66, lines=('من الأرباح', 'تصير كاش', 'حقيقي'), dur=2.6):
    N = int(dur * FPS); W = BASE_W
    cx, cy, r = 200, 215, 130
    l1, l2, l3 = lines
    for i in range(N):
        t = ease(i / (N - 1)); img, p = P.frame()
        p.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, 26, fill=TRACK)
        p.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * value / 100 * t, 26, fill=GOLD)
        p.text((cx, cy), f"%{int(value * t)}", 88, fill=WHITE, anchor='mm', direction='rtl')
        p.text((W - 40, 148), l1, 40, fill=WHITE, anchor='rm', direction='rtl')
        p.text((W - 40, 215), l2, 40, fill=GOLD, anchor='rm', direction='rtl')
        p.text((W - 40, 282), l3, 40, fill=GOLD, anchor='rm', direction='rtl')
        yield img


def verdict_meter(P, score=24, scale_max=30, votes=(('شراء', 6, 'teal'), ('انتظار', 9, 'gold'), ('بيع', 0, 'red')),
                  title='ميزان المجلس', dur=4.5):
    N = int(dur * FPS); W = BASE_W
    for i in range(N):
        t = i / (N - 1); img, p = P.frame()
        p.rrect([50, 120, W - 50, 156], 18, fill=TRACK)
        val = score * ease(min(1, t * 1.3))
        half = (W - 100) / 2
        if val >= 0:
            p.rrect([W / 2, 120, W / 2 + half * (val / scale_max), 156], 18, fill=TEAL)
        else:
            p.rrect([W / 2 + half * (val / scale_max), 120, W / 2, 156], 18, fill=RED)
        p.line([(W / 2, 108), (W / 2, 168)], 3, fill=WHITE)
        p.text((W / 2, 70), f"{int(val)}+" if val >= 0 else f"{int(-val)}-", 58,
               fill=TEAL if val >= 0 else RED, anchor='mm', direction='rtl')
        c = ease(min(1, max(0, (t - 0.35) / 0.5)))
        for k, (lab, n, col) in enumerate(votes):
            x = W - 90 - k * 180
            p.text((x, 250), str(int(n * c)), 34, fill=COLORS[col], anchor='mm')
            p.text((x, 300), lab, 30, fill=WHITE, anchor='mm', direction='rtl')
        p.text((W / 2, 375), title, 30, fill=WHITE, anchor='mm', direction='rtl')
        yield img


KINDS = {'cash_bars': cash_bars, 'support_break': support_break, 'donut': donut,
         'verdict_meter': verdict_meter}


def render(name, spec, out_dir, s=1.0, bold='fonts/PlexArabic-Bold.ttf'):
    """يرسم لوحة واحدة إلى <out_dir>/<name>.mov ويرجع مسارها."""
    spec = dict(spec)
    kind = spec.pop('kind')
    frames_dir = os.path.join(out_dir, name)
    os.makedirs(frames_dir, exist_ok=True)
    n = 0
    for n, img in enumerate(KINDS[kind](Panel(s, bold), **spec)):
        img.save(os.path.join(frames_dir, f'f{n:03d}.png'))
    mov = os.path.join(out_dir, f'{name}.mov')
    subprocess.run(f"ffmpeg -v error -y -framerate {FPS} -i {frames_dir}/f%03d.png -c:v qtrle {mov}",
                   shell=True, check=True)
    print(f'fx {name} ({kind}) {n + 1} frames')
    return mov
