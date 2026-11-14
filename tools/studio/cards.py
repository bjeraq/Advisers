"""بطاقات الشاشة الثابتة (PNG بحجم الكادر الكامل، شفافة): العنوان، بطاقات الأرقام، الختام، شريط الإخلاء.

الرسم بتنعيم فائق SS = 2×S ثم تصغير LANCZOS. النص العربي يُمرَّر خاماً مع direction='rtl'
(بيلو فيه raqm — لا تستخدم arabic_reshaper/bidi معه وإلا ينقلب النص مرتين).

أنواع البطاقات (kind):
  title       title, subtitle, pills[[text, color, x_frac]], date_pill, label — عنوان الحلقة الكبير
              بشريط 16%–34% من الارتفاع (فوق رؤوس اللقطة الواسعة)، والسطر الصغير label فوقه
  card        lines[[text, size, weight(bold|med), color]], accent, y (مركز البطاقة، افتراضي 0.56)
  disclaimer  text   — شريط ثابت بكل المشاهد (تاريخ البيانات + «تحليل لا توصية»)، سطرين لو طال
قاعدة «الوجه ما ينغطى»: بطاقات card على الصدر/الطاولة تحت الوجه، والعنوان فوق الرؤوس.
قاعدة ig_safe_zones (بدر 14 نوفمبر، كادر 720×1280): أعلى 12% تحت ترويسة إنستغرام، وأسفل ~78%
يغطيه اسم الحساب والكابشن، وأزرار اللايك/الكومنت/الشير تغطي يمين الشاشة (x ≥ 612) من y ≥ 576.
فكل شي هنا يتقيد بـ SAFE: البطاقات تنتهي فوق الترانسكريبت (≤ CARD_BOTTOM) وتنزاح لليسار
بحيث حافتها اليمنى ≤ RIGHT_X، وشريط الإخلاء ينتهي فوق 77%.
"""
import os
from PIL import Image, ImageDraw, ImageFont

COLORS = {
    'teal': (20, 184, 166, 255), 'red': (239, 68, 68, 255), 'gold': (212, 167, 71, 255),
    'white': (255, 255, 255, 255), 'sub': (207, 232, 229, 255), 'light_teal': (94, 234, 212, 255),
}
BG = (10, 22, 26, 214)

# مناطق إنستغرام الآمنة بإحداثيات 720×1280 (تتضاعف تلقائياً مع s)
SAFE = {
    'top': 192,            # 15% — لا رسومات فوقه (ترويسة إنستغرام)
    'title_band': (205, 470),
    'right_x': 596,        # حافة يمنى قصوى لأي شي تحت y=576 (أزرار التفاعل من x≈612)
    'right_from_y': 576,
    'left_x': 16,
    'card_bottom': 812,    # فوق سطر الترانسكريبت (≈ 830–905)
    'disc_bottom': 984,    # شريط الإخلاء ينتهي قبل 77%
    'bottom': 1000,        # 78% — لا شي تحته أبداً
}
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

    def title(self, path, title, subtitle, pills=(), date_pill=None, label=None):
        """عنوان الحلقة الكبير بشريط 16%–34% (y≈205–470): سطر صغير ذهبي ← العنوان ← سطر فرعي
        ← شارات ← شارة التاريخ. يطلع بس على اللقطة الواسعة (فوق رؤوس الطاولة، ما يغطي وجه)."""
        SS = self.SS
        img, d = self.canvas()
        cx = self.W / 2
        if label:
            self.pill(d, cx, 222 * SS, label, self.font('med', 24), COLORS['gold'], pad_x=26, pad_y=10)
        self.center_text(d, cx, 252 * SS, title, self.fit(d, title, 'bold', 66, 640), COLORS['white'], stroke=3 * SS)
        if subtitle:
            self.center_text(d, cx, 330 * SS, subtitle, self.fit(d, subtitle, 'bold', 40, 640),
                             COLORS['light_teal'], stroke=2 * SS)
        fp = self.font('bold', 24)
        default_x = {1: [0.5], 2: [0.30, 0.70], 3: [0.19, 0.5, 0.81]}.get(len(pills), [])
        for i, pl in enumerate(pills):
            text, color = pl[0], pl[1]
            x = pl[2] if len(pl) > 2 else default_x[i]
            self.pill(d, self.W * x, 400 * SS, text, fp, COLORS[color], pad_x=22, pad_y=12)
        if date_pill:
            self.pill(d, cx, 452 * SS, date_pill, self.font('med', 20), COLORS['gold'], pad_x=22, pad_y=9)
        self.save(img, path)

    def fit(self, d, text, weight, size, max_w):
        """أكبر خط ≤ size يخلي النص بعرض ≤ max_w (بإحداثيات 720)."""
        while size > 16:
            f = self.font(weight, size)
            if self.measure(d, text, f)[0] <= max_w * self.SS:
                return f
            size -= 2
        return self.font(weight, size)

    def card(self, path, lines, accent='teal', y=0.56):
        """بطاقة أرقام على الصدر/الطاولة. y = مركزها، لكن حافتها السفلى ما تنزل تحت SAFE.card_bottom،
        وحافتها اليمنى ≤ SAFE.right_x (أزرار إنستغرام)، وتصغر الخطوط لو العرض ما يكفي."""
        SS = self.SS
        img, d = self.canvas()
        acc = COLORS[accent]
        gaps, pad = 18 * SS, 40 * SS
        avail = (SAFE['right_x'] - SAFE['left_x']) * SS
        scale = 1.0
        while True:
            items = [(t, self.font(wt, size * scale), COLORS[c]) for t, size, wt, c in lines]
            sizes = [self.measure(d, t, f) for t, f, _ in items]
            max_w = max(w for w, _, _ in sizes)
            if max_w + 2 * pad <= avail or scale < 0.55:
                break
            scale -= 0.04
        tot_h = sum(h for _, h, _ in sizes) + gaps * (len(items) - 1)
        bw, bh = max_w + 2 * pad, tot_h + 2 * pad
        cy = min(self.H * y, SAFE['card_bottom'] * SS - bh / 2)
        cy = max(cy, SAFE['top'] * SS + bh / 2)
        cx = min(self.W / 2, SAFE['right_x'] * SS - bw / 2)
        x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=28 * SS, fill=BG, outline=acc, width=4)
        d.rounded_rectangle([x1 - 12 * SS, y0, x1, y1], radius=6 * SS, fill=acc)
        yy = cy - tot_h / 2
        for (t, f, c), (w, h, bb) in zip(items, sizes):
            d.text((cx - w / 2 - bb[0], yy - bb[1]), t, font=f, fill=c, direction='rtl')
            yy += h + gaps
        self.save(img, path)

    def disclaimer(self, path, text):
        """شريط الإخلاء: ينتهي فوق SAFE.disc_bottom (قبل منطقة الكابشن)، ومزاح لليسار عن أزرار
        إنستغرام. لو النص أعرض من المساحة ينقسم سطرين عند أول « — » (أو «•»، أو بالنص)."""
        SS = self.SS
        img, d = self.canvas()
        f = self.font('med', 19)
        avail = (SAFE['right_x'] - SAFE['left_x'] - 40) * SS
        rows = [text]
        if self.measure(d, text, f)[0] > avail:
            sep = next((x for x in (' — ', ' • ') if x in text), ' ')
            if sep == ' ':
                ws = text.split(' '); k = len(ws) // 2
                rows = [' '.join(ws[:k]), ' '.join(ws[k:])]
            else:
                head, _, tail = text.partition(sep)
                rows = [head, tail]
        ms = [self.measure(d, r, f) for r in rows]
        lh = max(h for _, h, _ in ms)
        gap = 7 * SS
        w = max(m[0] for m in ms)
        bh = lh * len(rows) + gap * (len(rows) - 1) + 24 * SS
        bw = w + 44 * SS
        y1 = SAFE['disc_bottom'] * SS
        y0 = y1 - bh
        cx = min(self.W / 2, SAFE['right_x'] * SS - bw / 2)
        d.rounded_rectangle([cx - bw / 2, y0, cx + bw / 2, y1], radius=18 * SS, fill=(8, 18, 20, 175))
        yy = y0 + 12 * SS
        for r, (rw, rh, bb) in zip(rows, ms):
            d.text((cx - rw / 2 - bb[0], yy + (lh - rh) / 2 - bb[1]), r, font=f,
                   fill=(226, 240, 238, 240), direction='rtl')
            yy += lh + gap
        self.save(img, path)


def render_all(specs, out_dir, s=1, fonts='fonts'):
    os.makedirs(out_dir, exist_ok=True)
    C = Cards(s, fonts)
    for name, spec in specs.items():
        spec = dict(spec)
        kind = spec.pop('kind')
        getattr(C, kind)(os.path.join(out_dir, f'{name}.png'), **spec)
    print(f'cards: {len(specs)} → {out_dir}')
