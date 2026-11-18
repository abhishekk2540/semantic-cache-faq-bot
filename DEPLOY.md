# Deployment Guide

## Prerequisites

1. **Clerk account** – sign up at [clerk.com](https://clerk.com) (free tier is fine)
2. **GitHub repo** – push this project to GitHub

---

## Step 1: Set Up Clerk

1. Go to [dashboard.clerk.com](https://dashboard.clerk.com) and create a new application.
2. Choose your sign-in methods (Email, Google, GitHub, etc.).
3. From the **API Keys** page, copy:
   - **Publishable key** → starts with `pk_test_...` or `pk_live_...`
   - **Frontend API URL** → looks like `https://your-app.clerk.accounts.dev`

---

## Step 2: Deploy the Backend on Render

The backend needs a process with enough memory for FAISS and the
`paraphrase-multilingual-MiniLM-L12-v2` model. A free service with 512 MB RAM
may run out of memory during model load. **Use a 1 GB instance** if startup fails.

### Steps

1. Go to [render.com](https://render.com) → **New** → **Web Service**.
2. Connect your GitHub repo.
3. Configure:
   | Setting | Value |
   |---------|-------|
   | **Name** | `semantic-cache-api` (or anything) |
   | **Root Directory** | `backend` |
   | **Environment** | `Docker` |
   | **Dockerfile Path** | `./Dockerfile` |
   | **Instance Type** | Starter (1 GB RAM) or higher |
   | **Health Check Path** | `/health` |

4. Add these **Environment Variables**:

   | Variable | Value |
   |----------|-------|
   | `CLERK_FRONTEND_API` | `https://your-app.clerk.accounts.dev` (from Clerk dashboard) |
   | `CORS_ORIGINS` | Your Vercel frontend URL (e.g. `https://semantic-cache.vercel.app`) |
   | `LLM_MODE` | `mock` (for demo) or `anthropic` (for real LLM) |
   | `ANTHROPIC_API_KEY` | Only needed if `LLM_MODE=anthropic` |

5. Click **Create Web Service** and wait for the build.
6. Note the **backend URL**: `https://semantic-cache-api.onrender.com`

### Verify

```
curl https://semantic-cache-api.onrender.com/health
# → {"ok":true,"llm_mode":"mock",...}
```

---

## Step 3: Deploy the Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. Import your GitHub repo.
3. Configure:

   | Setting | Value |
   |---------|-------|
   | **Framework Preset** | Vite |
   | **Root Directory** | `frontend` |
   | **Build Command** | `npm run build` |
   | **Output Directory** | `dist` |

4. Add these **Environment Variables**:

   | Variable | Value |
   |----------|-------|
   | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_...` or `pk_live_...` (from Clerk dashboard) |
   | `VITE_API_URL` | `https://semantic-cache-api.onrender.com` (your Render backend URL) |

5. Click **Deploy**.
6. Note the **frontend URL**: `https://semantic-cache.vercel.app`

---

## Step 4: Connect Everything

1. **Update Render's `CORS_ORIGINS`** to your actual Vercel URL:
   ```
   CORS_ORIGINS=https://semantic-cache.vercel.app
   ```
   (Render will auto-redeploy.)

2. **Add your Vercel URL to Clerk's allowed origins**:
   - Clerk Dashboard → your app → **Paths** (or **Domains**).
   - Add `https://semantic-cache.vercel.app`.

3. **Test**: Open your Vercel URL → Click "Sign in" → authenticate → chat.

---

## Architecture After Clerk Migration

```
┌──────────────────┐    Clerk session JWT    ┌──────────────────┐
│                  │  ───────────────────────▶│                  │
│  React Frontend  │                         │  FastAPI Backend  │
│  (Vercel)        │  ◀───────────────────── │  (Render/Docker)  │
│                  │       JSON responses     │                  │
└──────────────────┘                         └──────────────────┘
        │                                            │
        │  ClerkProvider                             │  Verifies JWT
        │  useAuth().getToken()                      │  via Clerk JWKS
        ▼                                            ▼
┌──────────────────┐                         ┌──────────────────┐
│  Clerk Auth      │                         │  Clerk JWKS      │
│  (hosted)        │                         │  Endpoint        │
└──────────────────┘                         └──────────────────┘
```

---

## Local Development

1. Copy env files:
   ```bash
   cp frontend/.env.example frontend/.env
   cp backend/.env.example backend/.env
   ```

2. Fill in your Clerk keys in both `.env` files.

3. Delete the old database (schema changed):
   ```bash
   rm backend/cache_app.db
   ```

4. Start the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

5. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. Open `http://localhost:5173` → Sign in with Clerk → use the app.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing VITE_CLERK_PUBLISHABLE_KEY` | Add it to `frontend/.env` or Vercel env vars |
| `401 Invalid token` | Check `CLERK_FRONTEND_API` on the backend matches your Clerk app |
| Backend OOM on Render | Upgrade to a 1 GB+ instance |
| CORS errors | Ensure `CORS_ORIGINS` exactly matches your frontend URL (no trailing slash) |
| Old DB schema errors | Delete `backend/cache_app.db` and restart |

---

## What Changed (Clerk Migration)

- **Removed**: `/auth/register`, `/auth/login` endpoints, password hashing, JWT creation, `Login.jsx` form
- **Added**: Clerk JWKS verification on the backend, `ClerkProvider` + `useAuth` on the frontend
- **User IDs** are now Clerk's `user_...` strings (TEXT) instead of auto-increment integers
- **User provisioning** is automatic — first API call creates the user row
- **No secrets to manage** — no `JWT_SECRET`; Clerk signs tokens with RS256 and the backend verifies via JWKS
