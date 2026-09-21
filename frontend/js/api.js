/**
 * API Client — Travel Planner AI
 * All HTTP and SSE communication with the FastAPI backend.
 * API_BASE comes from config.js — empty string = same origin (local/Render full),
 * or set to your Render URL for split Render+Vercel deployment.
 */

const API_BASE = (typeof CONFIG !== 'undefined' && CONFIG.API_BASE) ? CONFIG.API_BASE : '';


/** POST /api/trip/plan — returns { trip_id, status, message } */
async function planTrip(data) {
    const res = await fetch(`${API_BASE}/api/trip/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

/**
 * GET /api/trip/stream/{tripId} — SSE stream
 * Callbacks: onAgentStart, onAgentComplete, onAgentError, onComplete, onError
 * Returns the EventSource so the caller can close it if needed.
 */
function streamTripProgress(tripId, callbacks = {}) {
    const source = new EventSource(`${API_BASE}/api/trip/stream/${tripId}`);

    source.onmessage = (ev) => {
        let data;
        try { data = JSON.parse(ev.data); }
        catch { return; }

        switch (data.event) {
            case 'agent_start':    callbacks.onAgentStart?.(data);    break;
            case 'agent_complete': callbacks.onAgentComplete?.(data); break;
            case 'agent_error':    callbacks.onAgentError?.(data);    break;
            case 'complete':
                callbacks.onComplete?.(data.result);
                source.close();
                break;
            case 'error':
                callbacks.onError?.(data.message || 'Unknown error');
                source.close();
                break;
        }
    };

    source.onerror = () => {
        callbacks.onError?.('Lost connection to server. Please try again.');
        source.close();
    };

    return source;
}

/** GET /api/trip/result/{tripId} — polling fallback */
async function getTripResult(tripId) {
    const res = await fetch(`${API_BASE}/api/trip/result/${tripId}`);
    return res.json();
}

/** POST /api/copilot/chat — returns { reply, suggested_actions } */
async function sendCopilotMessage(message, tripContext = null) {
    const res = await fetch(`${API_BASE}/api/copilot/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, trip_context: tripContext }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

/** GET /api/images — returns { images: [...urls], by_folder: {...} } */
async function fetchImages() {
    try {
        const res = await fetch(`${API_BASE}/api/images`);
        return res.ok ? res.json() : { images: [], by_folder: {} };
    } catch {
        return { images: [], by_folder: {} };
    }
}
