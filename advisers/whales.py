"""Track famous investors' quarterly 13F filings from official SEC EDGAR.

The SEC requires automated clients to identify themselves with a contact in
the User-Agent header, so requests read it from the SEC_CONTACT_UA
environment variable (e.g. "Name email@example.com"); nothing is sent until
the user sets it. Values in 13F filings are whole US dollars.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}"
WHALES_CONFIG = "config/whales.json"
OUT_PATH = "data/whales_13f.json"

NAME_STOPWORDS = {
    "CORP", "CORPORATION", "INC", "INCORPORATED", "CO", "COMPANY", "PLC",
    "LTD", "LIMITED", "HOLDINGS", "HLDGS", "GROUP", "CL", "CLASS", "COM",
    "NEW", "DEL", "THE", "&", "A", "B", "C",
}


class WhalesError(RuntimeError):
    pass


def _ua() -> str:
    ua = os.environ.get("SEC_CONTACT_UA", "").strip()
    if not ua:
        raise WhalesError(
            "متغير البيئة SEC_CONTACT_UA غير مضبوط — الهيئة الأمريكية تشترط "
            "تعريف الأداة بجهة تواصل (مثال: Name email@example.com). "
            "أضفه من إعدادات البيئة ثم أعد المحاولة."
        )
    return ua


def _get(url: str, timeout: float = 30.0, retries: int = 2) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": _ua(),
        "Accept-Encoding": "identity",
    })
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            time.sleep(0.25)  # stay well under SEC's 10 req/s fair-use cap
            return data
        except Exception:
            if attempt == retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise WhalesError("unreachable")


def _get_json(url: str):
    return json.loads(_get(url).decode())


def latest_13f(subs: dict, count: int = 2) -> list[dict]:
    """Newest 13F-HR filings, one per report period (amendments win)."""
    r = subs.get("filings", {}).get("recent", {})
    seen: dict[str, dict] = {}
    for form, acc, fdate, period in zip(
        r.get("form", []), r.get("accessionNumber", []),
        r.get("filingDate", []), r.get("reportDate", []),
    ):
        if form in ("13F-HR", "13F-HR/A") and period not in seen:
            seen[period] = {"accession": acc, "filed": fdate, "period": period}
    return sorted(seen.values(), key=lambda f: f["period"], reverse=True)[:count]


def holdings_for(cik: int, accession: str) -> dict[str, dict]:
    """Parse one filing's information table into {cusip: holding}."""
    acc = accession.replace("-", "")
    index = _get_json(ARCHIVE.format(cik=cik, acc=acc) + "/index.json")
    candidates = [
        it for it in index["directory"]["item"]
        if it["name"].lower().endswith(".xml")
        and "primary_doc" not in it["name"].lower()
    ]
    if not candidates:
        raise WhalesError(f"لا يوجد جدول مراكز في الملف {accession}")
    name = max(candidates, key=lambda it: int(it.get("size") or 0))["name"]
    root = ET.fromstring(_get(ARCHIVE.format(cik=cik, acc=acc) + f"/{name}"))

    out: dict[str, dict] = {}
    for el in root.iter():
        if not el.tag.endswith("infoTable"):
            continue
        row = {"name": "", "cusip": "", "value": 0.0, "shares": 0.0}
        for child in el.iter():
            tag = child.tag.rsplit("}", 1)[-1]
            text = (child.text or "").strip()
            if tag == "nameOfIssuer":
                row["name"] = text
            elif tag == "cusip":
                row["cusip"] = text
            elif tag == "value" and text:
                row["value"] = float(text)
            elif tag == "sshPrnamt" and text:
                row["shares"] += float(text)
        if row["cusip"]:
            cur = out.setdefault(row["cusip"], {**row, "value": 0.0, "shares": 0.0})
            cur["value"] += row["value"]
            cur["shares"] += row["shares"]
            cur["name"] = cur["name"] or row["name"]
    return out


def diff_holdings(prev: dict[str, dict], cur: dict[str, dict],
                  threshold: float = 0.25) -> dict[str, list[dict]]:
    changes: dict[str, list[dict]] = {
        "new": [], "exited": [], "increased": [], "decreased": [],
    }
    for cusip, h in cur.items():
        if cusip not in prev:
            changes["new"].append(h)
        else:
            old = prev[cusip].get("shares") or 0
            if old:
                pct = (h.get("shares", 0) - old) / old
                if pct >= threshold:
                    changes["increased"].append({**h, "change_pct": pct * 100})
                elif pct <= -threshold:
                    changes["decreased"].append({**h, "change_pct": pct * 100})
    for cusip, h in prev.items():
        if cusip not in cur:
            changes["exited"].append(h)
    for key in changes:
        changes[key].sort(key=lambda h: -(h.get("value") or 0))
        changes[key] = changes[key][:10]
    return changes


def normalize_name(name: str) -> str:
    tokens = re.sub(r"[^A-Za-z0-9 ]", " ", name.upper()).split()
    kept = [t for t in tokens if t not in NAME_STOPWORDS]
    return " ".join(kept or tokens)


def names_match(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = sorted((na, nb), key=len)
    return len(shorter) >= 5 and longer.startswith(shorter)


def refresh(config_path: str = WHALES_CONFIG, out_path: str = OUT_PATH,
            top: int = 15, limit: Optional[int] = None) -> dict:
    with open(config_path) as f:
        whales = json.load(f)["whales"]
    if limit:
        whales = whales[:limit]
    result = {"asof": date.today().isoformat(), "whales": [], "errors": []}
    for w in whales:
        try:
            subs = _get_json(SUBMISSIONS.format(cik=w["cik"]))
            filings = latest_13f(subs)
            if not filings:
                raise WhalesError("لا ملفات 13F حديثة")
            cur = holdings_for(w["cik"], filings[0]["accession"])
            prev = (
                holdings_for(w["cik"], filings[1]["accession"])
                if len(filings) > 1 else {}
            )
            total = sum(h["value"] for h in cur.values()) or 1.0
            ranked = sorted(cur.values(), key=lambda h: -h["value"])
            result["whales"].append({
                "name": w["name"],
                "cik": w["cik"],
                "filed": filings[0]["filed"],
                "period": filings[0]["period"],
                "portfolio_value": total,
                "top": [
                    {**h, "pct": h["value"] / total * 100}
                    for h in ranked[:top]
                ],
                "changes": diff_holdings(prev, cur) if prev else {},
            })
            print(f"✓ {w['name']}: {len(cur)} مركز، آخر ملف {filings[0]['filed']}")
        except Exception as e:
            result["errors"].append({"name": w.get("name", "?"), "error": str(e)})
            print(f"✗ {w.get('name', '?')}: {e}", file=sys.stderr)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="تحديث محافظ كبار المستثمرين من ملفات 13F")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--config", default=WHALES_CONFIG)
    p.add_argument("--out", default=OUT_PATH)
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--limit", type=int, default=None, help="أول N حيتان فقط (للتجارب)")
    args = p.parse_args(argv)
    if not args.refresh:
        p.error("استخدم --refresh")
    result = refresh(args.config, args.out, args.top, args.limit)
    ok, bad = len(result["whales"]), len(result["errors"])
    print(f"اكتمل: {ok} حوت بنجاح، {bad} أخطاء — حُفظ في {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
