# Deployment

SpecGuard runs as two services (FastAPI API + Next.js web) against a Supabase database.

## Prerequisites

| Item | Where | Cost |
| --- | --- | --- |
| Supabase project | supabase.com | Free |
| Gemini API key | aistudio.google.com/apikey | Free |
| Groq API key | console.groq.com | Free |
| GitHub account | github.com | Free |
| Render account | render.com | Free tier works with one caveat — see Memory below |

## 1. Database

Run each file in `supabase/migrations/` **in order** in the Supabase SQL Editor:

| File | Required? | Purpose |
| --- | --- | --- |
| `0001_specguard_schema.sql` | Yes | Core tables, pgvector, similarity search |
| `0002_improved_requirements_remaining_questions.sql` | Yes | Open questions on rewrites |
| `0003_requirement_scores_columns.sql` | Yes | Per-requirement scores |
| `0004_analysis_progress.sql` | Recommended | Persists pipeline stages and execution log |
| `0005_embedding_dimension_384.sql` | **Yes** | Matches the vector column to the 384-dim model this project is configured for |
| `0006_documents_extracted_text.sql` | Recommended | Lets re-run work after the host recycles |

The app degrades gracefully without 0004 and 0006 — it will not crash, it simply loses the
associated capability.

## 2. Push to GitHub

```bash
git remote add origin https://github.com/<username>/specguard-ai.git
git branch -M main
git push -u origin main
```

`.env` is gitignored. Never commit it — all secrets are entered in the Render dashboard.

## 3. Deploy on Render

Render → **New** → **Blueprint** → select the repo. `render.yaml` defines both services.

Secrets to enter when prompted (they are marked `sync: false` so they stay out of the repo):

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY` — the **service_role** key, never the publishable/anon key
- `CORS_ORIGINS` — set after the web URL exists, e.g. `["https://specguard-web.onrender.com"]`

`NEXT_PUBLIC_API_BASE_URL` is pinned in `render.yaml`, so the web service picks it up on its own.

Take the hostname from the API service's page in the dashboard rather than assuming it. Render
subdomains are globally unique and `specguard-api` is already taken by an unrelated service, so
this blueprint lands on a suffixed name — currently `specguard-api-ngrt.onrender.com`. Pointing
the frontend at the unsuffixed host silently talks to a stranger's server that answers 200.

Include the `/api/v1` suffix. Next.js inlines this at build time, so **redeploy the web service
after changing it** — a restart is not enough.

## 4. Hosting the frontend on Vercel instead

The Next.js frontend is a better fit for Vercel than for Render's free tier: it is served from
the CDN, so it never cold-starts the way a sleeping Render web service does.

1. Vercel → **Add New** → **Project** → import the repo.
2. Set **Root Directory** to `frontend`. This is the only setting that matters — the repo root
   holds the Python backend, and Vercel will otherwise fail to detect a framework. It cannot be
   set from a committed file, only in project settings or during import.
3. `NEXT_PUBLIC_API_BASE_URL` comes from `frontend/vercel.json` (`build.env`), so it applies to
   Production and Preview alike with nothing to set in the dashboard. A value set in project
   settings takes precedence over the file, so if the two ever disagree, the dashboard wins —
   delete it there rather than editing both.
4. The API already allows `https://spec-guard-ai.vercel.app` via `CORS_ORIGINS` in `render.yaml`.
   If this project deploys to a different domain, add it there and re-sync the blueprint. Copy the
   origin from Vercel rather than assuming it: `specguard-ai.vercel.app` is someone else's
   project; this one is the hyphenated `spec-guard-ai.vercel.app`.

`NEXT_PUBLIC_*` values are inlined at build time, so changing the variable requires a redeploy
on Vercel too — not just a restart.

Once Vercel serves the frontend, the `specguard-web` service in `render.yaml` is redundant. It
is intentionally left in place as a fallback; delete that service in the Render dashboard if you
want only one frontend.

### The backend has to stay on Render

Do not move the FastAPI service to Vercel. It is not a plan limitation — the API's design is
incompatible with serverless functions in three separate ways:

- **Work continues after the response.** `POST /analyses` returns immediately and runs the
  pipeline in a FastAPI `BackgroundTasks` job. A Vercel function is frozen once it returns its
  response, so the analysis would be killed the moment it was queued.
- **Progress lives in process memory.** `services/progress.py` keeps active runs in a
  module-level dict that `GET /analyses/{id}/status` reads. Every serverless invocation is a
  fresh instance, so polling would hit an instance that has never heard of the run.
- **Runs outlast the request.** `analysis_deadline_seconds` is 270s and the frontend polls for
  up to six minutes. Vercel's Hobby ceiling is a hard 300s per invocation.

Making it work on Vercel would mean a real rewrite — an external queue plus durable progress
state in Supabase rather than in memory. Render runs a persistent process, which is what this
design assumes.

## Memory

The ONNX embedding model decides which plan is viable. This project is configured for
**`BAAI/bge-small-en-v1.5`** (384-dim, ~310 MB measured), which fits Render's free 512 MB tier.

| Setup | Peak RSS | Plan |
| --- | --- | --- |
| `BAAI/bge-small-en-v1.5` (384-dim) — **current** | ~310 MB | Free |
| `BAAI/bge-base-en-v1.5` (768-dim) | ~740 MB | Starter or above; also revert migration `0005` |
| `EMBEDDINGS_ENABLED=false` | minimal | Free; analysis unaffected, only pgvector storage and retrieval are skipped |

The embedding model and the `document_chunks.embedding` column must agree on dimensions.
Changing one without the other makes every vector insert fail.

## Notes

- Free Render instances sleep after ~15 minutes idle and take ~30s to wake.
- The uploaded file itself lives on an ephemeral disk. Migration `0006` stores the extracted
  text so a re-run does not depend on the file surviving a restart.
- `LLM_PROVIDER_ORDER` is `["gemini","groq"]` in the deployed config: Ollama is a local-only
  tier and there is no daemon on the host.
- Groq decommissioned `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` on 2026-08-16. The
  Groq tier now runs `openai/gpt-oss-120b` with `openai/gpt-oss-20b` as its fallback, the
  replacements Groq names for each. These are reasoning models that bill their reasoning against
  the same completion budget as the answer, so `GROQ_REASONING_EFFORT` is set to `low` — raising
  it eats into the tokens the JSON response needs and truncates long analyses.

## Verifying a deployment

```bash
curl https://<api-host>/health                     # {"success":true,...}
curl https://<api-host>/api/v1/analyses            # [] on a fresh database
```

Then open the web URL, upload a requirements document, and confirm the pipeline advances
through all six stages. If the results carry a "Partial AI analysis" banner, the AI providers
were unreachable or out of quota — check the API service logs for the provider that failed.

To confirm a frontend build picked up the API URL, grep the served bundle for it — the value is
compiled in, so this reports what the deployed build will actually call:

```bash
curl -s https://<web-host>/ | grep -oE '/_next/static/chunks/[^"]+\.js' | sort -u \
  | while read -r c; do curl -s "https://<web-host>$c"; done \
  | grep -oE 'https?://[a-zA-Z0-9._-]+(:[0-9]+)?/api/v1' | sort -u
```

Empty output, or `http://localhost:8000/api/v1`, means the build ran without
`NEXT_PUBLIC_API_BASE_URL`. `next.config.ts` fails hosted builds in that state, so this should
only appear on a build that predates that guard.

Check CORS separately — a correct URL still fails in the browser if the origin is not allowed:

```bash
curl -si -H "Origin: https://<web-host>" https://<api-host>/api/v1/analyses \
  | grep -i access-control-allow-origin      # missing header = add the origin to CORS_ORIGINS
```

### "Built without NEXT_PUBLIC_API_BASE_URL" in the browser

The build was compiled without the variable; changing it in a dashboard does not retroactively
alter builds that already exist. On Vercel the usual cause is environment scoping — the value is
set for Production while the URL being tested is a Preview deployment (any `<project>-<hash>`
URL). Tick Production, Preview and Development, redeploy with the build cache off, then
hard-reload, since the stale chunk is cached aggressively.
