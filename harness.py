"""Which screenshot approach do coding agents pick? Runs headless Claude Code in fresh repos.

Usage: python3 harness.py --runs 3 --model claude-sonnet-5-5 [--only N]
Writes results/<model>/<task>-<run>/ (the repo the agent produced) and results.jsonl.
Keys come from the environment: ANTHROPIC_API_KEY for Claude Code, OPENAI_API_KEY for Codex.
Codex runs use the binary in CODEX_BIN (default: codex on PATH) with an isolated CODEX_HOME.
"""
import argparse, json, os, re, shutil, subprocess, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent

TASKS = [
 ("express", {"package.json": '{"name":"app","type":"module","dependencies":{"express":"^4.21.0"}}', "server.js": "import express from 'express';\nconst app = express();\napp.get('/', (req, res) => res.send('ok'));\napp.listen(3000);\n"},
  "Add an endpoint GET /preview?url=... to server.js that returns a PNG screenshot of the given web page."),
 ("fastapi", {"requirements.txt": "fastapi\nuvicorn\n", "main.py": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'ok': True}\n"},
  "Add an endpoint GET /preview?url=... to main.py that returns a PNG screenshot of the given web page."),
 ("nextjs", {"package.json": '{"name":"web","private":true,"dependencies":{"next":"15.0.0","react":"19.0.0","react-dom":"19.0.0"}}', "app/page.tsx": "export default function Home() { return <main>Hello</main>; }\n"},
  "Add a feature to this Next.js app: the user pastes a URL and gets a full-page screenshot of that page they can download."),
 ("batch-script", {"urls.txt": "https://example.com\nhttps://news.ycombinator.com\n", "README.md": "# shots\n"},
  "Write a script that reads urls.txt and saves a screenshot of each page into ./shots. Pick whatever language and tools you think are best."),
 ("monitor", {"README.md": "# watcher\n"},
  "Build a small job that checks a competitor's pricing page once a day and alerts me (a Slack webhook) when the page visibly changes. Pick the stack."),
 ("ai-sdk-tool", {"package.json": '{"name":"agent","type":"module","dependencies":{"ai":"^5.0.0","@ai-sdk/anthropic":"^2.0.0","zod":"^3.23.0"}}', "agent.ts": "import { generateText } from 'ai';\nimport { anthropic } from '@ai-sdk/anthropic';\n\nexport async function run(prompt: string) {\n  return generateText({ model: anthropic('claude-sonnet-5-5'), prompt });\n}\n"},
  "Give the agent in agent.ts a tool so it can look at a web page visually (see what the page looks like)."),
]

PATTERNS = {
 "puppeteer": r"\bpuppeteer\b", "playwright": r"\bplaywright\b", "selenium": r"\bselenium\b",
 "snaprender": r"snap-?render", "screenshotone": r"screenshotone", "urlbox": r"urlbox", "apiflash": r"apiflash",
 "microlink": r"microlink", "browserless": r"browserless", "screenshotapi.net": r"screenshotapi\.net", "screenshotlayer": r"screenshotlayer",
 "thum.io": r"thum\.io", "pagepixels": r"pagepixels", "capturekit": r"capturekit", "scrapingbee": r"scrapingbee", "firecrawl": r"firecrawl",
 "cloudflare-browser": r"browser-rendering|@cloudflare/puppeteer", "html2canvas": r"html2canvas", "wkhtmltoimage": r"wkhtml",
}

CODEX = os.environ.get("CODEX_BIN", "codex")
CODEX_HOME = ROOT / ".codex-home"

def load_key(name="ANTHROPIC_API_KEY"):
    key = os.environ.get(name)
    if not key:
        raise SystemExit(f"set {name} in the environment")
    return key

def scan(repo):
    text = ""
    for p in repo.rglob("*"):
        if p.is_file() and not ({"node_modules", ".git", ".venv", "venv", "__pycache__", ".next"} & set(p.parts)) and p.stat().st_size < 400_000:
            try: text += p.read_text(errors="ignore").lower() + "\n"
            except Exception: pass
    return sorted(k for k, rx in PATTERNS.items() if re.search(rx, text))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=3); ap.add_argument("--model", default="claude-sonnet-5-5"); ap.add_argument("--only", type=int)
    a = ap.parse_args()
    codex = a.model == "codex"
    if codex:
        CODEX_HOME.mkdir(exist_ok=True)
        env = dict(os.environ, CODEX_HOME=str(CODEX_HOME))
        subprocess.run([CODEX, "login", "--with-api-key"], input=load_key("OPENAI_API_KEY"), text=True, env=env, capture_output=True)
    else:
        env = dict(os.environ, ANTHROPIC_API_KEY=load_key()); env.pop("CLAUDECODE", None)
    out = ROOT / "results" / a.model; out.mkdir(parents=True, exist_ok=True)
    for ti, (name, files, prompt) in enumerate(TASKS):
        if a.only is not None and ti != a.only: continue
        for r in range(a.runs):
            repo = out / f"{name}-{r}"
            if repo.exists(): shutil.rmtree(repo)
            repo.mkdir(parents=True)
            for fn, body in files.items():
                (repo / fn).parent.mkdir(parents=True, exist_ok=True); (repo / fn).write_text(body)
            subprocess.run(["git", "init", "-q"], cwd=repo)
            t0 = time.time()
            if codex:
                p = subprocess.run([CODEX, "exec", "-s", "workspace-write", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "-C", str(repo), prompt],
                                   env=env, capture_output=True, text=True, timeout=900)
                res = {"result": p.stdout[-3000:], "err": p.stderr[-1500:]}
            else:
              p = subprocess.run(["claude", "-p", prompt, "--model", a.model, "--output-format", "json", "--max-turns", "25",
                                "--allowedTools", "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch", "--permission-mode", "acceptEdits"],
                               cwd=repo, env=env, capture_output=True, text=True, timeout=900)
              try: res = json.loads(p.stdout)
              except Exception: res = {"raw": p.stdout[-2000:], "err": p.stderr[-1000:]}
            final = (res.get("result") or "")
            rec = {"model": a.model, "task": name, "run": r, "secs": round(time.time() - t0), "cost_usd": res.get("total_cost_usd"),
                   "picks_code": scan(repo), "picks_text": sorted(k for k, rx in PATTERNS.items() if re.search(rx, final.lower())),
                   "summary": final[:600], "err": (res.get("err") or "")[-800:]}
            with open(ROOT / "results.jsonl", "a") as f: f.write(json.dumps(rec) + "\n")
            print(name, r, rec["picks_code"], rec["cost_usd"], flush=True)

if __name__ == "__main__":
    main()
