"""بطاقات الشاشة الثابتة (PNG بحجم الكادر الكامل، شفافة): العنوان، بطاقات الأرقام، الختام، شريط الإخلاء.

الرسم بتنعيم فائق SS = 2×S ثم تصغير LANCZOS. النص العربي يُمرَّر خاماً مع direction='rtl'
(بيلو فيه raqm — لا تستخدم arabic_reshaper/bidi معه وإلا ينقلب النص مرتين).

أنواع البطاقات (kind):
  title       title, subtitle, pills[[text, color, x_frac]], date_pill
  card        lines[[text, size, weight(bold|med), color]], accent, y (نسبة من الارتفاع، افتراضي 0.80)
  disclaimer  text   — شريط ثابت أسفل الشاشة بكل المشاهد (تاريخ البيانات + «تحليل لا توصية»)
قاعدة «الوجه ما ينغطى»: بطاقات card تجلس على الصدر/الطاولة (y ≥ 0.70) والعنوان فوق الرؤوس.
"""
import os
from PIL import Image, ImageDraw, ImageFont

COLORS = {
    'teal': (20, 184, 166, 255), 'red': (239, 68, 68, 255), 'gold': (212, 167, 71, 255),
    'white': (255, 255, 255, 255), 'sub': (207, 232, 229, 255), 'light_teal': (94, 234, 212, 255),
}
BG = (10, 22, 26, 214)
DARK = (8, 18, 20, 255)


class Cards:
    def __init__(self, s=1, fonts='fonts'):
        self.s = s
        self.SS = 2 * s
        self.OW, self.OH = round(720 * s), round(1280 * s)
        self.W, self.H = round(720 * self.SS), round(1280 * self.SS)
        self.bold = os.path.join(fonts, 'PlexArabic-Bold.ttf')
        self.med = os.path.join(fonts, 'PlexArabic-Medium.ttf')

    def font(self, weight, size):
        return ImageFont.truetype(self.bold if weight == 'bold' else self.med, round(size * self.SS))

    def canvas(self):
        img = Image.new('RGBA', (self.W, self.H), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    def save(self, img, path):
        img.resize((self.OW, self.OH), Image.LANCZOS).save(path)

    @staticmethod
    def measure(d, t, f):
        bb = d.textbbox((0, 0), t, font=f, direction='rtl')
        return bb[2] - bb[0], bb[3] - bb[1], bb

    def center_text(self, d, cx, y, t, f, fill, stroke=0):
        w, h, bb = self.measure(d, t, f)
        d.text((cx - w / 2 - bb[0], y - bb[1]), t, font=f, fill=fill, direction='rtl',
               stroke_width=stroke, stroke_fill=DARK)
        return h

    def pill(self, d, cx, cy, t, f, border, pad_x=44, pad_y=22):
        w, h, bb = self.measure(d, t, f)
        x0, y0, x1, y1 = cx - w / 2 - pad_x, cy - h / 2 - pad_y, cx + w / 2 + pad_x, cy + h / 2 + pad_y
        d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2, fill=BG, outline=border, width=4)
        d.text((cx - w / 2 - bb[0], cy - h / 2 - bb[1]), t, font=f, fill=COLORS['white'], direction='rtl')

    def title(self, path, title, subtitle, pills=(), date_pill=None):
        SS = self.SS
        img, d = self.canvas()
        self.center_text(d, self.W / 2, 70 * SS, title, self.font('bold', 76), COLORS['white'], stroke=3 * SS)
        self.center_text(d, self.W / 2, 168 * SS, subtitle, self.font('med', 42), COLORS['sub'], stroke=2 * SS)
        fp = self.font('bold', 30)
        default_x = {1: [0.5], 2: [0.30, 0.72], 3: [0.18, 0.5, 0.82]}.get(len(pills), [])
        for i, pl in enumerate(pills):
            text, color = pl[0], pl[1]
            x = pl[2] if len(pl) > 2 else default_x[i]
            self.pill(d, self.W * x, 250 * SS, text, fp, COLORS[color])
        if date_pill:
            self.pill(d, self.W * 0.50, 322 * SS, date_pill, self.font('med', 26), COLORS['gold'])
        self.save(img, path)

    def card(self, path, lines, accent='teal', y=0.80):
        SS = self.SS
        img, d = self.canvas()
        acc = COLORS[accent]
        items = [(t, self.font(wt, size), COLORS[c]) for t, size, wt, c in lines]
        gaps = 18 * SS
        sizes = [self.measure(d, t, f) for t, f, _ in items]
        tot_h = sum(h for _, h, _ in sizes) + gaps * (len(items) - 1)
        max_w = max(w for w, _, _ in sizes)
        pad = 40 * SS
        cx, cy = self.W / 2, self.H * y
        x0, y0, x1, y1 = cx - max_w / 2 - pad, cy - tot_h / 2 - pad, cx + max_w / 2 + pad, cy + tot_h / 2 + pad
        d.rounded_rectangle([x0, y0, x1, y1], radius=28 * SS, fill=BG, outline=acc, width=4)
        d.rounded_rectangle([x1 - 12 * SS, y0, x1, y1], radius=6 * SS, fill=acc)
        yy = cy - tot_h / 2
        for (t, f, c), (w, h, bb) in zip(items, sizes):
            d.text((cx - w / 2 - bb[0], yy - bb[1]), t, font=f, fill=c, direction='rtl')
            yy += h + gaps
        self.save(img, path)

    def disclaimer(self, path, text):
        SS = self.SS
        img, d = self.canvas()
        f = self.font('med', 21)
        w, h, bb = self.measure(d, text, f)
        cy = self.H - 72 * SS
        d.rounded_rectangle([self.W / 2 - w / 2 - 26 * SS, cy - h / 2 - 14 * SS,
                             self.W / 2 + w / 2 + 26 * SS, cy + h / 2 + 14 * SS],
                            radius=20 * SS, fill=(8, 18, 20, 165))
        d.text((self.W / 2 - w / 2 - bb[0], cy - h / 2 - bb[1]), text, font=f,
               fill=(226, 240, 238, 235), direction='rtl')
        self.save(img, path)


def render_all(specs, out_dir, s=1, fonts='fonts'):
    os.makedirs(out_dir, exist_ok=True)
    C = Cards(s, fonts)
    for name, spec in specs.items():
        spec = dict(spec)
        kind = spec.pop('kind')
        getattr(C, kind)(os.path.join(out_dir, f'{name}.png'), **spec)
    print(f'cards: {len(specs)} → {out_dir}')
