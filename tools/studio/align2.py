"""محاذاة مقطع المواجهة (متحدثان بمقطع واحد): تمطيط فيديو موحد + كتلتا شفاه.

الكتلتان = أطول وقفة بين مقاطع التفريغ تفصل الأول عن الثاني. كل تسجيل أصلي يوضع على كتلته.

    python3 align2.py <clip.mp4> <recA.mp3> <wordsA.json> <recB.mp3> <wordsB.json> <out.wav> <out_words.json> <meta.json>
"""
import os, sys, json
os.environ.setdefault('HF_HOME', '/home/user/.hfcache')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align1 import speech_bounds, mean_vol, run, clip_segments


def main(clip, rec1, w1, rec2, w2, out_wav, out_words, meta_out):
    segs, cdur = clip_segments(clip)
    if len(segs) >= 2:
        gaps = [(segs[i + 1].start - segs[i].end, i) for i in range(len(segs) - 1)]
        _, gi = max(gaps)
        blocks = [(max(0, segs[0].start - 0.05), segs[gi].end + 0.05),
                  (segs[gi + 1].start - 0.05, min(cdur, segs[-1].end + 0.10))]
    else:
        blocks = [(0.2, cdur / 2 - 0.2), (cdur / 2 + 0.2, cdur - 0.2)]
    recs = []
    for rec in (rec1, rec2):
        rh, rt, _, _, _ = speech_bounds(rec)
        recs.append((rh, rt, rt - rh))
    lips_total = sum(b1 - b0 for b0, b1 in blocks)
    f = max(0.78, min(1.05, (recs[0][2] + recs[1][2]) / lips_total))
    out_dur = cdur * f
    fcs, allw = [], []
    for i, (rec, wj) in enumerate([(rec1, w1), (rec2, w2)]):
        rh, rt, recd = recs[i]
        b0, b1 = blocks[i][0] * f, blocks[i][1] * f
        tempo = max(0.90, min(1.12, recd / (b1 - b0)))
        g = max(-8, min(8, -18.0 - mean_vol(rec)))
        fcs.append(f"[{i}:a]atrim={rh:.3f}:{rt:.3f},asetpts=PTS-STARTPTS,atempo={tempo:.4f},"
                   f"afade=t=in:d=0.03,volume={g:.1f}dB,adelay={int(b0*1000)}|{int(b0*1000)},apad[x{i}]")
        for w in json.load(open(wj)):
            allw.append({'w': w['w'], 's': round((w['s'] - rh) / tempo + b0, 3),
                         'e': round((w['e'] - rh) / tempo + b0, 3)})
        print(f"clash rec{i}: lips*F {b0:.2f}-{b1:.2f} tempo {tempo:.3f}")
    fc = ';'.join(fcs) + (f";[x0][x1]amix=inputs=2:normalize=0:duration=first[m];"
                          f"[m]atrim=0:{out_dur:.2f},aresample=44100,"
                          f"aformat=sample_fmts=fltp:channel_layouts=stereo[a]")
    r = run(f"ffmpeg -v error -y -i '{rec1}' -i '{rec2}' -filter_complex \"{fc}\" -map '[a]' '{out_wav}'")
    assert r.returncode == 0, r.stderr[-500:]
    json.dump(sorted(allw, key=lambda x: x['s']), open(out_words, 'w'), ensure_ascii=False)
    json.dump({'f': round(f, 4), 'dur': round(out_dur, 2)}, open(meta_out, 'w'))
    print(f"clash: F={f:.3f} out={out_dur:.2f}s")


if __name__ == '__main__':
    main(*sys.argv[1:9])
