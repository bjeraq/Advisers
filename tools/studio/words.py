"""توقيت الكلمات: تفريغ ويسبر بطوابع زمنية لكل كلمة، مربوطاً بالنص المؤلَّف المعتمد.

لو عدد كلمات التفريغ يساوي عدد كلمات النص → كل كلمة مؤلفة تاخذ توقيت نظيرتها.
لو اختلف (وهذا الغالب مع اللهجة) → توزيع تناسبي بعدد الحروف بين أول وآخر كلمة مسموعة.
الترانسكريبت على الشاشة يعرض دائماً النص المؤلف، مو تخمين ويسبر.

    python3 words.py <audio> "<authored text>" <out.json>
"""
import os, sys, json
os.environ.setdefault('HF_HOME', '/home/user/.hfcache')
from faster_whisper import WhisperModel

_m = None


def model():
    global _m
    if _m is None:
        _m = WhisperModel('small', device='cpu', compute_type='int8')
    return _m


def word_times(audio, authored_text):
    segs, _ = model().transcribe(audio, language='ar', word_timestamps=True)
    ws = [{'w': w.word.strip(), 's': w.start, 'e': w.end} for s in segs for w in s.words]
    A = authored_text.split()
    if not ws:
        return []
    if len(ws) == len(A):
        return [{'w': a, 's': w['s'], 'e': w['e']} for a, w in zip(A, ws)]
    t0, t1 = ws[0]['s'], ws[-1]['e']
    total = sum(len(a) for a in A) or 1
    out, acc = [], 0
    for a in A:
        s = t0 + (t1 - t0) * acc / total
        acc += len(a)
        e = t0 + (t1 - t0) * acc / total
        out.append({'w': a, 's': round(s, 3), 'e': round(e, 3)})
    return out


if __name__ == '__main__':
    audio, text, out = sys.argv[1], sys.argv[2], sys.argv[3]
    json.dump(word_times(audio, text), open(out, 'w'), ensure_ascii=False)
    print(out, 'ok')
