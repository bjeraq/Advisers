"""بطاقات الشاشة الثابتة (PNG بحجم الكادر الكامل، شفافة): العنوان، بطاقات الأرقام، الختام، شريط الإخلاء.

الرسم بتنعيم فائق SS = 2×S ثم تصغير LANCZOS. النص العربي يُمرَّر خاماً مع direction='rtl'
(بيلو فيه raqm — لا تستخدم arabic_reshaper/bidi معه وإلا ينقلب النص مرتين).

أنواع البطاقات (kind):
  title       title, subtitle, pills[[text, color, x_frac]], date_pill, label — عنوان الحلقة الكبير
              بشريط 16%–34% من الارتفاع (فوق رؤوس اللقطة الواسعة)، والسطر الصغير label فوقه
  card        lines[[text, size, weight(bold|med), color]], accent, y (مركز البطاقة، افتراضي 0.56),
              x (اختياري: مركز أفقي كنسبة من العرض — لإبعاد البطاقة عن وجه/آذان المتكلم)
  timeline    items[[title, sub], ...], n — جدول مربعات مرقّمة (أول n يبينون) على لوحة بيضاء
              بين top و bottom (افتراضي 205–805) — يبني نفسه مربع مربع بعدة بطاقات تراكمية (حلقة 13)
  image       file — طبقة PNG جاهزة بحجم الكادر (720×1280) تنعاد بمقاس الدقة (مثل إبراز سطر على السبورة، حلقة 13)
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

    def card(self, path, lines, accent='teal', y=0.56, x=None, pad=40, bottom=None):
        """بطاقة أرقام على الصدر/الطاولة. y = مركزها، لكن حافتها السفلى ما تنزل تحت SAFE.card_bottom،
        وحافتها اليمنى ≤ SAFE.right_x (أزرار إنستغرام)، وتصغر الخطوط لو العرض ما يكفي."""
        SS = self.SS
        img, d = self.canvas()
        acc = COLORS[accent]
        gaps, pad = 18 * SS, pad * SS
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
        # bottom: يسمح ببطاقة أوطى من card_bottom (مكان الترانسكريبت) لما المشهد يخفي الترانسكريبت (captions_until_cue)
        cy = min(self.H * y, min(bottom or SAFE['card_bottom'], SAFE['disc_bottom'] - 80) * SS - bh / 2)
        cy = max(cy, SAFE['top'] * SS + bh / 2)
        cx = min(self.W / 2 if x is None else self.W * x, SAFE['right_x'] * SS - bw / 2)
        cx = max(cx, SAFE['left_x'] * SS + bw / 2)
        x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=min(28 * SS, bh / 2), fill=BG, outline=acc, width=4)
        d.rounded_rectangle([x1 - 12 * SS, y0, x1, y1], radius=6 * SS, fill=acc)
        yy = cy - tot_h / 2
        for (t, f, c), (w, h, bb) in zip(items, sizes):
            d.text((cx - w / 2 - bb[0], yy - bb[1]), t, font=f, fill=c, direction='rtl')
            yy += h + gaps
        self.save(img, path)

    def photo(self, path, image, lines=(), accent='teal', y=0.56, x=None, size=300):
        """بطاقة صورة (موديل/منتج) مع سطر أو سطرين تحتها. size = عرض الصورة بإحداثيات 720.
        نفس قيود SAFE مثل card: الحافة السفلى ≤ card_bottom واليمنى ≤ right_x."""
        SS = self.SS
        img, d = self.canvas()
        acc = COLORS[accent]
        pad, gap = 22 * SS, 14 * SS
        ph = Image.open(image).convert('RGBA')
        pw = round(size * SS)
        ph = ph.resize((pw, round(pw * ph.height / ph.width)), Image.LANCZOS)
        mask = Image.new('L', ph.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.width, ph.height], radius=20 * SS, fill=255)
        items = [(t, self.font(wt, sz), COLORS[c]) for t, sz, wt, c in lines]
        sizes = [self.measure(d, t, f) for t, f, _ in items]
        txt_h = sum(h for _, h, _ in sizes) + gap * len(items)
        bw = max([ph.width] + [w for w, _, _ in sizes]) + 2 * pad
        bh = ph.height + txt_h + 2 * pad
        cy = min(self.H * y, SAFE['card_bottom'] * SS - bh / 2)
        cy = max(cy, SAFE['top'] * SS + bh / 2)
        cx = min(self.W / 2 if x is None else self.W * x, SAFE['right_x'] * SS - bw / 2)
        cx = max(cx, SAFE['left_x'] * SS + bw / 2)
        x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=28 * SS, fill=BG, outline=acc, width=4)
        img.paste(ph, (round(cx - ph.width / 2), round(y0 + pad)), mask)
        yy = y0 + pad + ph.height + gap
        for (t, f, c), (w, h, bb) in zip(items, sizes):
            d.text((cx - w / 2 - bb[0], yy - bb[1]), t, font=f, fill=c, direction='rtl')
            yy += h + gap
        self.save(img, path)

    def timeline(self, path, items, n, top=205, bottom=805, left=28, right=596):
        """لوحة بيضاء فيها مربعات مرقّمة ملوّنة متتالية بأسهم. n = كم مربع يبين (للبناء التدريجي)."""
        SS = self.SS
        img, d = self.canvas()
        cols = [(230, 160, 20, 255), (200, 60, 50, 255), (30, 110, 190, 255), (30, 150, 90, 255)]
        x0, x1, y0, y1 = left * SS, right * SS, top * SS, bottom * SS
        d.rounded_rectangle([x0, y0, x1, y1], radius=22 * SS, fill=(250, 250, 247, 246),
                            outline=(200, 170, 120, 255), width=5 * SS)
        k = len(items)
        pad, gap = 22 * SS, 30 * SS
        bh = ((y1 - y0) - 2 * pad - gap * (k - 1)) / k
        fb, fs, fn = self.font('bold', 38), self.font('med', 24), self.font('bold', 36)
        for i, (t, sub) in enumerate(items[:n]):
            c = cols[i % 4]
            by0 = y0 + pad + i * (bh + gap)
            bx0, bx1 = x0 + 18 * SS, x1 - 18 * SS
            d.rounded_rectangle([bx0, by0, bx1, by0 + bh], radius=18 * SS, fill=(255, 255, 255, 255), outline=c, width=6 * SS)
            r = 36 * SS
            cxn, cyn = bx1 - 16 * SS - r, by0 + bh / 2
            d.ellipse([cxn - r, cyn - r, cxn + r, cyn + r], fill=c)
            w, h, bb = self.measure(d, str(i + 1), fn)
            d.text((cxn - w / 2 - bb[0], cyn - h / 2 - bb[1]), str(i + 1), font=fn, fill=(255, 255, 255, 255))
            tx = cxn - r - 20 * SS
            maxw = tx - bx0 - 16 * SS
            f1 = fb
            while self.measure(d, t, f1)[0] > maxw and f1.size > 20 * SS:
                f1 = ImageFont.truetype(self.bold, f1.size - 2 * SS)
            w1, h1, b1 = self.measure(d, t, f1)
            w2, h2, b2 = self.measure(d, sub, fs)
            ty = cyn - (h1 + 10 * SS + h2) / 2
            d.text((tx - w1 - b1[0], ty - b1[1]), t, font=f1, fill=(25, 25, 30, 255), direction='rtl')
            d.text((tx - w2 - b2[0], ty + h1 + 10 * SS - b2[1]), sub, font=fs, fill=(90, 90, 95, 255), direction='rtl')
            if i < k - 1:
                ax, ay = (x0 + x1) / 2, by0 + bh + 4 * SS
                d.polygon([(ax - 14 * SS, ay), (ax + 14 * SS, ay), (ax, ay + gap - 8 * SS)], fill=(70, 70, 70, 255))
        self.save(img, path)

    def image(self, path, file):
        Image.open(file).convert('RGBA').resize((self.OW, self.OH), Image.LANCZOS).save(path)

    def disclaimer(self, path, text):
        """شريط الإخلاء: ينتهي فوق SAFE.disc_bottom (قبل منطقة الكابشن)، ومزاح لليسار عن أزرار
        إنستغرام. لو النص أعرض من المساحة ينقسم سطرين عند أول « — » (أو «•»، أو بالنص)."""
        SS = self.SS
        img, d = self.canvas()
        if not text:                      # بدون شريط إخلاء (قرار بدر للحلقة 9) — صورة شفافة
            self.save(img, path)
            return
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
