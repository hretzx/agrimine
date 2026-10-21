"""
tools/check_cors.py
-------------------
Checks a DEPLOYED AgriMine API the way a browser does, and says what is wrong. Standard library only: run it from your own machine.

    python tools/check_cors.py https://agrimine.onrender.com
    python tools/check_cors.py https://agrimine.onrender.com --origin https://agrimine.vercel.app --wait 180

1. waits for the service to wake (a free Render service sleeps after 15 minutes and takes up to a minute to answer),
2. asks which commit is running (/api/health shows it on Render),
3. sends the OPTIONS "preflight" the browser sends, then a real GET, both with your web app's Origin header.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

PATHS = ["/api/meta", "/api/checks?limit=1"]


def call(method: str, url: str, headers: dict | None = None, timeout: float = 30):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers.items()), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read().decode("utf-8", "replace")
    except Exception as e:                                  # no answer at all (DNS, refused, timeout)
        return None, {}, f"{type(e).__name__}: {e}"


def lower(h: dict) -> dict:
    return {k.lower(): v for k, v in h.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="the API address, e.g. https://agrimine.onrender.com")
    ap.add_argument("--origin", default="https://agrimine.vercel.app", help="the address of your web app")
    ap.add_argument("--wait", type=int, default=120, help="seconds to wait for a sleeping service")
    a = ap.parse_args()
    base, origin, problems = a.base.rstrip("/"), a.origin.rstrip("/"), []

    print(f"1. waking {base} (up to {a.wait}s) ...")
    started, status, headers, body = time.time(), None, {}, ""
    while time.time() - started < a.wait:
        status, headers, body = call("GET", base + "/api/health")
        if status == 200:
            break
        print(f"   {status or 'no answer'} after {time.time() - started:.0f}s: {body[:100].strip()!r}; retrying")
        time.sleep(5)
    h = lower(headers)
    if status != 200:
        print(f"   FAIL: /api/health never answered 200 (last: {status}). A 502/503/504 here comes from the host's proxy, not from your app:")
        print("   the service is asleep, crashed, out of memory, or not listening on the port the host gave it. Read the service logs.")
        return 1
    print(f"   up after {time.time() - started:.0f}s; routed by: {h.get('x-render-routing') or h.get('server') or '?'}")
    try:
        info = json.loads(body)
    except ValueError:
        info = {}
    print(f"2. running commit: {info.get('commit', 'not reported (this build does not report it, or the host is not Render)')}")

    print(f"3. browser checks, as {origin}")
    for path in PATHS:
        status, headers, body = call("OPTIONS", base + path, {"Origin": origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "content-type"})
        allow = lower(headers).get("access-control-allow-origin")
        ok = status == 200 and allow in (origin, "*")
        print(f"   preflight OPTIONS {path}: {status} allow-origin={allow}  {'ok' if ok else 'FAIL'}")
        if not ok:
            problems.append(f"preflight {path} -> {status}, allow-origin {allow}")
        status, headers, body = call("GET", base + path, {"Origin": origin})
        allow = lower(headers).get("access-control-allow-origin")
        ok = status == 200 and allow in (origin, "*")
        print(f"   GET {path}: {status} allow-origin={allow}  {'ok' if ok else 'FAIL'}")
        if not ok:
            problems.append(f"GET {path} -> {status}, allow-origin {allow}")
    if not problems:
        print("\nPASS: the server allows this origin. If the browser still blocks it, hard-reload the page (Ctrl+Shift+R) and check the NEXT_PUBLIC_API_URL "
              "of the Vercel BUILD (it is baked in at build time: change it, then redeploy).")
        return 0
    print("\nFAIL:", "; ".join(problems))
    if any(" 405" in p or " 404" in p for p in problems):
        print("A 405 or 404 on the preflight means the running app has no CORS middleware: it is an OLD deploy. Compare the commit in step 2 with your latest "
              "commit, and check the service's Events tab: a failed deploy leaves the previous version running.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
