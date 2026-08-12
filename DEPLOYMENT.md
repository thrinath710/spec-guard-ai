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

Then on the **web** service set:

- `NEXT_PUBLIC_API_BASE_URL` = `https://specguard-api.onrender.com/api/v1`

Include the `/api/v1` suffix. Next.js inlines this at build time, so **redeploy the web service
after changing it**.

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

## Verifying a deployment

```bash
curl https://<api-host>/health                     # {"success":true,...}
curl https://<api-host>/api/v1/analyses            # [] on a fresh database
```

Then open the web URL, upload a requirements document, and confirm the pipeline advances
through all six stages. If the results carry a "Partial AI analysis" banner, the AI providers
were unreachable or out of quota — check the API service logs for the provider that failed.
