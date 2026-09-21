/**
 * config.js — Deployment Configuration
 *
 * IMPORTANT: Update API_BASE before deploying to Vercel.
 *
 * Local dev:  leave API_BASE as '' (same-origin, FastAPI serves everything)
 * Production: set API_BASE to your Render backend URL
 *             e.g. 'https://travel-planner-ai-backend.onrender.com'
 *
 * How to find your Render URL:
 *   1. Deploy backend to Render (see DEPLOY.md)
 *   2. Go to Render dashboard → your service → copy the URL shown at top
 *   3. Paste it below (no trailing slash)
 */

const CONFIG = {
    // ── Change this to your Render URL when deploying frontend to Vercel ──
    API_BASE: 'https://travel-verse-multiagent-system-1.onrender.com',   // '' = same origin (local dev / Render full deploy)
                    // 'https://your-app.onrender.com' = split deploy
};
