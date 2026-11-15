# Deployment

The backend needs a process with enough memory for FAISS and the
`paraphrase-multilingual-MiniLM-L12-v2` model. A free service with 512 MB RAM
may run out of memory during the model load. Use a 1 GB instance if startup
fails.

## Backend on Render or Railway

1. Create a web service from this repository.
2. Set the root directory to `backend`.
3. Use the Dockerfile in that directory.
4. Set these environment variables:
   - `JWT_SECRET`: a long random value
   - `CORS_ORIGINS`: the exact frontend URL, without a trailing slash
   - `LLM_MODE`: `mock` for the simulated 1.5 second response, or `anthropic`
   - `ANTHROPIC_API_KEY`: required only when `LLM_MODE=anthropic`
5. Set the health check path to `/health`.

Backend URL: `https://YOUR-BACKEND-URL.example.com`

## Frontend on Vercel or Netlify

1. Create a project from this repository.
2. Set the project root to `frontend`.
3. Set `VITE_API_URL` to the backend URL.
4. Build with `npm run build`.
5. Set the deployed frontend URL as the backend `CORS_ORIGINS` value.

Frontend URL: `https://YOUR-FRONTEND-URL.example.com`

The free tier is suitable for a demo, not a production workload. The SQLite
database is local to the service, so entries can be lost when the service is
recreated.
