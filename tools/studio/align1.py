"""محاذاة متحدث واحد: تسجيل إلفن لابز الأصلي فوق كتلة الشفاه في مقطع تزامن الشفاه.

نموذج الشفاه يعيد توليد العربي بمحرك رديء ويمطّ الكلام (~20% عند 1080) → صوته يُكتم دائماً.
الحل المعتمد: نسرّع/نبطّئ **الفيديو** بعامل F = مدة_كلام_التسجيل / كتلة_الشفاه (0.78–1.05)
والتسجيل الأصلي يبقى بسرعته الطبيعية تقريباً (atempo بقايا 0.93–1.07 فقط، بدون تغيير طبقة).
حدود الكلام بالمقطع من التفريغ (VAD ويسبر) لا من كاشف الصمت — ضوضاء القاعة تخدعه.
كسب ثابت فقط نحو -18 ديسيبل متوسط — ممنوع أي فلتر ديناميكي (loudnorm خرّب حلقة سابقة).

    python3 align1.py <clip.mp4> <rec.mp3> <rec_words.json> <out.wav> <out_words.json> <meta.json>
مخرج meta: {"f": عامل تمطيط الفيديو (setpts=PTS*f), "dur": مدة المشهد بعد التمطيط}
"""
import os, sys, json, subprocess, re, tempfile
os.environ.setdefault('HF_HOME', '/home/user/.hfcache')


def run(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True)


def mean_vol(p):
    r = run(f"ffmpeg -hide_banner -i '{p}' -vn -af volumedetect -f null - 2>&1")
    return float(re.search(r'mean_volume: ([-\d.]+)', r.stdout + r.stderr).group(1))


def speech_bounds(p, noise='-32dB', d=0.22):
    r = run(f"ffmpeg -hide_banner -i '{p}' -vn -af silencedetect=noise={noise}:d={d} -f null - 2>&1")
    t = r.stdout + r.stderr
    ss = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', t)]
    es = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', t)]
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', t)
    dur = 3600 * int(m.group(1)) + 60 * int(m.group(2)) + float(m.group(3))
    head = es[0] if (ss and ss[0] <= 0.02 and es) else 0.0
    tail = ss[-1] if (ss and (not es or ss[-1] > max(es))) else dur
    if tail <= head:
        tail = dur
    return head, tail, dur, ss, es


_WH = None


def _whisper():
    global _WH
    if _WH is None:
        from faster_whisper import WhisperModel
        _WH = WhisperModel('small', device='cpu', compute_type='int8')
    return _WH


def clip_segments(clip):
    _, _, dur, _, _ = speech_bounds(clip, noise='-37dB', d=0.30)
    wav = tempfile.mktemp(suffix='.wav')
    run(f"ffmpeg -v error -y -i '{clip}' -vn -ac 1 -ar 16000 '{wav}'")
    segs = list(_whisper().transcribe(wav, language='ar', vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300))[0])
    return segs, dur


def main(clip, rec, words_json, out_wav, out_words, meta_out):
    segs, cdur = clip_segments(clip)
    ch = max(0.0, segs[0].start - 0.05) if segs else 0.2
    ct = min(cdur, segs[-1].end + 0.10) if segs else cdur
    rh, rt, _, _, _ = speech_bounds(rec)
    block = ct - ch
    recd = rt - rh
    f = max(0.78, min(1.05, recd / block))            # عامل تمطيط الفيديو
    tempo = max(0.93, min(1.07, recd / (block * f)))  # بقايا طفيفة على الصوت فقط
    g = max(-8, min(8, -18.0 - mean_vol(rec)))
    delay = ch * f
    out_dur = cdur * f
    fc = (f"[0:a]atrim={rh:.3f}:{rt:.3f},asetpts=PTS-STARTPTS,atempo={tempo:.4f},"
          f"afade=t=in:d=0.03,volume={g:.1f}dB,adelay={int(delay*1000)}|{int(delay*1000)},apad,"
          f"atrim=0:{out_dur:.2f},aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a]")
    r = run(f"ffmpeg -v error -y -i '{rec}' -filter_complex \"{fc}\" -map '[a]' '{out_wav}'")
    assert r.returncode == 0, r.stderr[-500:]
    ws = json.load(open(words_json))
    adj = [{'w': w['w'], 's': round((w['s'] - rh) / tempo + delay, 3),
            'e': round((w['e'] - rh) / tempo + delay, 3)} for w in ws]
    json.dump(adj, open(out_words, 'w'), ensure_ascii=False)
    json.dump({'f': round(f, 4), 'dur': round(out_dur, 2)}, open(meta_out, 'w'))
    print(f"{os.path.basename(clip)}: lips {ch:.2f}-{ct:.2f} rec {recd:.2f}s "
          f"F={f:.3f} tempo={tempo:.3f} out={out_dur:.2f}s gain {g:+.1f}")


if __name__ == '__main__':
    main(*sys.argv[1:7])
