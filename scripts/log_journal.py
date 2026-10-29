#!/usr/bin/env python3
"""Bitácora diaria de logs útiles -> R2 (logs/AAAA-MM-DD/).
Solo errores/warnings y eventos clave (deploys, fallos de descarga de correo, auth anómalos).
Redacta emails, tokens, JWT, claves y URLs con credenciales. Sin dependencias externas."""
import gzip, json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

KEY_RE = re.compile(r"(deploy|crash|fail|error|exception|traceback|timeout|imap|smtp|gmail|outlook|yahoo|"
                    r"fetch|sync|unauthori[sz]ed|forbidden|401|403|invalid[ _]token|login|otp|rate.?limit|5\d\d\b)", re.I)
REDACT = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]*"), "[jwt]"),
    (re.compile(r"(?i)\b(bearer|token|apikey|api_key|key|secret|password|passwd|pwd|authorization)\b(\s*[:=]\s*|\s+)\S+"), r"\1=[redactado]"),
    (re.compile(r"\b(sk|pk|rk|re|ghp|gho|ghs|github_pat|xox[abpr])[-_][A-Za-z0-9_-]{8,}"), "[secreto]"),
    (re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@"), "[url-cred]@"),
    (re.compile(r"\b[A-Fa-f0-9]{32,}\b"), "[hex]"),
    (re.compile(r"\+?\d[\d -]{9,}\d"), "[tel]"),
]

def redact(s: str) -> str:
    s = str(s)[:2000]
    for r, rep in REDACT:
        s = r.sub(rep, s)
    return s

def useful(sev: str, msg: str) -> bool:
    sev = (sev or "").lower()
    return sev in ("error", "err", "warn", "warning", "fatal", "critical") or bool(KEY_RE.search(msg or ""))

def _post(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def railway_entries(token, since, until):
    """Logs de despliegues del día. Devuelve (entries, nota)."""
    if not token:
        return [], "sin RAILWAY_API_TOKEN: se omiten logs de Railway"
    url = "https://backboard.railway.com/graphql/v2"
    h = {"Authorization": f"Bearer {token}"}
    q = '{projects{edges{node{name services{edges{node{id name deployments(first:20){edges{node{id status createdAt}}}}}}}}}}'
    d = _post(url, {"query": q}, h)
    if d.get("errors"):
        return [], "railway: error de API (" + redact(d["errors"][0].get("message", "")) + ")"
    out = []
    for p in d["data"]["projects"]["edges"]:
        for s in p["node"]["services"]["edges"]:
            sv = s["node"]
            for dep in sv["deployments"]["edges"]:
                dn = dep["node"]
                if dn["createdAt"] >= since:
                    out.append({"src": "railway", "svc": sv["name"], "kind": "deploy", "ts": dn["createdAt"], "sev": "info" if dn["status"] == "SUCCESS" else "warn", "msg": f"deployment {dn['status']}"})
                if dn["createdAt"] > until:
                    continue
                lq = 'query($id:String!){deploymentLogs(deploymentId:$id,limit:5000){timestamp severity message}}'
                try:
                    ld = _post(url, {"query": lq, "variables": {"id": dn["id"]}}, h)
                except Exception as e:  # un despliegue sin logs no tumba la bitácora
                    out.append({"src": "railway", "svc": sv["name"], "kind": "collector", "sev": "warn", "msg": f"logs no disponibles: {type(e).__name__}"})
                    continue
                for l in (ld.get("data") or {}).get("deploymentLogs") or []:
                    ts = l.get("timestamp") or ""
                    if since <= ts < until and useful(l.get("severity"), l.get("message")):
                        out.append({"src": "railway", "svc": sv["name"], "kind": "log", "ts": ts, "sev": (l.get("severity") or "").lower(), "msg": redact(l.get("message"))})
    return out, "ok"

def github_entries(token, repo, since, until):
    if not token or not repo:
        return [], "sin GH_TOKEN"
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/runs?per_page=100&created=%3E%3D{since[:10]}",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        runs = json.load(r).get("workflow_runs", [])
    out = []
    for w in runs:
        ts = w.get("created_at", "")
        if not (since <= ts < until):
            continue
        concl = w.get("conclusion") or w.get("status")
        is_deploy = "deploy" in (w.get("name") or "").lower()
        if concl not in ("success", "skipped") or is_deploy:
            out.append({"src": "github", "svc": redact(w.get("name")), "kind": "deploy" if is_deploy else "workflow", "ts": ts,
                        "sev": "info" if concl == "success" else "error", "msg": f"{concl} run {w.get('id')} sha {str(w.get('head_sha'))[:7]}"})
    return out, "ok"

def day_window(day):
    s = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    f = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f(s), f(s + timedelta(days=1))

def expired_prefixes(prefixes, today, keep_days=90):
    cut = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    res = []
    for p in prefixes:
        m = re.fullmatch(r"logs/(\d{4}-\d{2}-\d{2})/", p)
        if m and m.group(1) < cut:
            res.append(p)
    return res

def main():
    day = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    since, until = day_window(day)
    entries, notes = [], {}
    for name, fn in (("railway", lambda: railway_entries(os.environ.get("RAILWAY_API_TOKEN"), since, until)),
                     ("github", lambda: github_entries(os.environ.get("GH_TOKEN"), os.environ.get("GH_REPO"), since, until))):
        try:
            e, n = fn()
        except Exception as ex:
            e, n = [], f"error {type(ex).__name__}"
        entries += e; notes[name] = n
    entries.sort(key=lambda x: x.get("ts", ""))
    out = os.environ.get("OUT", "journal.jsonl.gz")
    with gzip.open(out, "wt") as fh:
        fh.write(json.dumps({"day": day, "generated": datetime.now(timezone.utc).isoformat(), "fuentes": notes, "n": len(entries)}) + "\n")
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(json.dumps({"day": day, "n": len(entries), "fuentes": notes}))

if __name__ == "__main__":
    main()
