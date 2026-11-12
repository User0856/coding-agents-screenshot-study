# Which screenshot approach do coding agents pick?

We asked AI coding agents to add a screenshot feature 120 times, in fresh repositories, with prompts that never mention a library or a service. 90 runs wrote code. Every one of them self-hosted Playwright. None used a hosted screenshot API.

This repository holds the harness and the raw results so anyone can check the numbers or rerun the study.

Disclosure: we build [SnapRender](https://snap-render.com), a screenshot API, so we had a stake in the answer. Our product was not picked either.

## Results (November 11 2026)

| Agent | Runs | Wrote code | Self-hosted Playwright | Hosted screenshot API |
|---|---|---|---|---|
| Claude Code + Haiku 5.5 | 30 | 30 | 30 | 0 |
| Claude Code + Opus 5.5 | 30 | 27 | 27 | 0 |
| Claude Code + Sonnet 5.5 | 30 | 19 | 19 | 0 |
| Codex CLI (default model) | 30 | 14 | 14 | 0 |
| **Total** | **120** | **90** | **90** | **0** |

- Sonnet 5.5 asked clarifying questions in 11 runs instead of writing code, and Opus 5.5 did the same in 3. In those runs nothing was installed.
- 16 Codex runs produced no output because the OpenAI account ran out of credits mid-study. They are reported, not hidden.
- An earlier pilot run of Codex used Puppeteer once. It is not counted above.

## The six tasks

Each task ran 5 times per agent, each time in a new git repository with a small starting project.

| Task | Starting repo | Prompt |
|---|---|---|
| express | `server.js` with Express | Add an endpoint GET /preview?url=... to server.js that returns a PNG screenshot of the given web page. |
| fastapi | `main.py` with FastAPI | Same, in Python. |
| nextjs | an empty App Router page | Add a feature to this Next.js app: the user pastes a URL and gets a full-page screenshot of that page they can download. |
| batch-script | `urls.txt` | Write a script that reads urls.txt and saves a screenshot of each page into ./shots. Pick whatever language and tools you think are best. |
| monitor | empty | Build a small job that checks a competitor's pricing page once a day and alerts me (a Slack webhook) when the page visibly changes. Pick the stack. |
| ai-sdk-tool | a Vercel AI SDK agent | Give the agent in agent.ts a tool so it can look at a web page visually (see what the page looks like). |

## Method

- Claude Code 2.1.322 in headless mode (`claude -p`), tools limited to Read, Write, Edit, Glob, Grep, WebSearch and WebFetch, permission mode acceptEdits, at most 25 turns.
- Codex CLI 0.165.0 (`codex exec`, workspace-write sandbox, user config ignored, isolated CODEX_HOME).
- After each run, `harness.py` scans every file the agent wrote (skipping node_modules, .git, virtual environments and build folders) for the libraries and services listed in `PATTERNS`: Playwright, Puppeteer, Selenium, and 16 other screenshot tools and hosted services (ScreenshotOne, Urlbox, SnapRender, Browserless, Microlink and more).
- `data/results.json` has one record per run: agent, task, run number, duration, cost, what the code used (`picks_code`), what the final message mentioned (`picks_text`), and the start of the agent's final message.

## Limits

- One machine and one week of model versions. Agent behavior changes with every release. We plan to rerun this monthly with the same harness.
- The Claude Code runs used a user-level configuration that included installed skills, which is why Sonnet and Opus sometimes asked questions before building. Sonnet's 11 question runs all said they would use Playwright; Opus's 3 did not name a library yet.
- "Wrote code" means the agent produced the feature. It does not mean the feature was tested in production.

## Rerun it

```sh
export ANTHROPIC_API_KEY=...        # for Claude Code runs
python3 harness.py --model claude-sonnet-5-5 --runs 5

export OPENAI_API_KEY=...           # for Codex runs
export CODEX_BIN=$(which codex)
python3 harness.py --model codex --runs 5
```

Results append to `results.jsonl`, and each generated project lands in `results/<model>/<task>-<run>/`.

## License

MIT. The data is free to cite. Please link back to this repository.
