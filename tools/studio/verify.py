#!/usr/bin/env python3
"""بوابة التسليم الإلزامية: تفريغ الحلقة المجمعة مشهداً مشهداً ومطابقته مع النص المؤلف.

ما تنرفع ولا تنعرض أي نسخة قبل ما تمر هذي البوابة وتقرأ النتيجة بنفسك.
نسبة التشابه تقريبية (ويسبر يكتب اللهجة بحروف مختلفة: قاعدة→جاعدة، والأرقام المنطوقة كأرقام)،
فالنسبة تنبيه للمراجعة لا حكم آلي: أي مشهد «⚠️» اسمعه واقرأ تفريغه كلمة كلمة.

    python3 tools/studio/verify.py <episode.json> build/draft720/manifest.json
"""
import os, sys, json, re, subprocess, difflib
os.environ.setdefault('HF_HOME', '/home/user/.hfcache')
from faster_whisper import WhisperModel

TASHKEEL = re.compile(r'[ً-ْٰـ]')


def norm(t):
    t = TASHKEEL.sub('', t)
    t = re.sub(r'[إأآٱ]', 'ا', t).replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    return ' '.join(re.sub(r'[^ء-ي0-9 ]', ' ', t).split())


def main(ep_path, manifest_path, threshold=0.72):
    ep = json.load(open(ep_path))
    man = json.load(open(manifest_path))
    m = WhisperModel('small', device='cpu', compute_type='int8')
    os.makedirs('build/probe', exist_ok=True)
    t, worst = 0.0, 1.0
    for sc in man['scenes']:
        wav = f"build/probe/{sc['id']}.wav"
        subprocess.run(f"ffmpeg -v error -y -ss {t} -t {sc['dur']} -i {man['output']} -vn -ac 1 -ar 16000 {wav}",
                       shell=True, check=True)
        heard = ' '.join(s.text.strip() for s in m.transcribe(wav, language='ar')[0])
        authored = ' '.join(ep['lines'][ln]['text'] for ln in sc['lines'])
        r = difflib.SequenceMatcher(None, norm(authored), norm(heard)).ratio()
        worst = min(worst, r)
        flag = '✅' if r >= threshold else '⚠️ راجع'
        print(f"{flag} {sc['id']} ({t:.1f}-{t + sc['dur']:.1f}s) تشابه {r:.2f}\n   النص: {authored}\n   المسموع: {heard}")
        t += sc['dur']
    print(f"أقل تشابه: {worst:.2f}")


if __name__ == '__main__':
    main(*sys.argv[1:3])
