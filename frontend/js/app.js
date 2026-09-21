/**
 * app.js — Main application logic for Travel Planner AI
 * Orchestrates form, SSE progress, results dashboard, and copilot.
 */

// Track how many agents have completed
let _agentsDone = 0;
const TOTAL_AGENTS = 6;

// Human-readable messages for each agent event
const AGENT_MESSAGES = {
    destination: {
        start:    { icon: '📍', text: 'Destination Research started — looking up airports & coordinates…' },
        done:     { icon: '✅', text: 'Destination Research complete — airports & location found!' },
        error:    { icon: '⚠️', text: 'Destination Research hit an issue — continuing with available data.' },
    },
    flight: {
        start:    { icon: '✈️', text: 'Flight Search started — scanning routes for your dates…' },
        done:     { icon: '✅', text: 'Flight Search complete — available flights retrieved!' },
        error:    { icon: '⚠️', text: 'Flight Search encountered an issue — some flights may be missing.' },
    },
    weather: {
        start:    { icon: '🌤️', text: 'Weather Analysis started — checking forecasts for your trip window…' },
        done:     { icon: '✅', text: 'Weather Analysis complete — forecast data ready!' },
        error:    { icon: '⚠️', text: 'Weather Analysis hit an issue — weather data may be unavailable.' },
    },
    exchange_rate: {
        start:    { icon: '💱', text: 'Exchange Rate agent started — fetching live INR → USD rate…' },
        done:     { icon: '✅', text: 'Exchange Rate fetched — currency conversion ready!' },
        error:    { icon: '⚠️', text: 'Exchange Rate issue — using fallback conversion rate.' },
    },
    budget_calculation: {
        start:    { icon: '💰', text: 'Budget Calculation started — converting your budget to USD…' },
        done:     { icon: '✅', text: 'Budget Calculation complete — per-night & per-person costs ready!' },
        error:    { icon: '⚠️', text: 'Budget Calculation hit an issue — budget estimate may be incomplete.' },
    },
    itinerary: {
        start:    { icon: '🗓️', text: 'Itinerary Creation started — crafting your personalised day-by-day plan…' },
        done:     { icon: '✅', text: 'Itinerary Creation complete — your perfect trip is ready!' },
        error:    { icon: '⚠️', text: 'Itinerary Creation hit an issue — a partial plan may still be available.' },
    },
};

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initForm();
    initGallery();
    copilot = new TravelCopilot();
    document.getElementById('plan-new-trip-btn')?.addEventListener('click', resetToHero);
    document.getElementById('progress-cancel-btn')?.addEventListener('click', resetToHero);
});

// ── Gallery initialisation ─────────────────────────────────────────────────

async function initGallery() {
    const { images } = await fetchImages();
    if (!images || images.length === 0) return;

    // Shuffle and store globally so ui.js can use them
    window._galleryImages = [...images].sort(() => Math.random() - 0.5);
    _buildMarquee(window._galleryImages);
    _fillMosaicSlots(window._galleryImages);
}

function _buildMarquee(imgs) {
    const track = document.getElementById('hero-marquee-track');
    if (!track || !imgs.length) return;

    const makeCard = (url) => {
        const card = document.createElement('div');
        card.className = 'hero-marquee-card';
        const img = document.createElement('img');
        img.src = url;
        img.className = 'hero-marquee-img';
        img.alt = '';
        img.loading = 'lazy';
        img.onerror = () => card.style.display = 'none';
        card.appendChild(img);
        return card;
    };

    // Insert original + clone for seamless infinite loop
    [...imgs, ...imgs].map(makeCard).forEach(c => track.appendChild(c));
}

function _fillMosaicSlots(imgs) {
    if (!imgs || !imgs.length) return;
    // Shuffle fresh for each fill
    const pool = [...imgs].sort(() => Math.random() - 0.5);
    document.querySelectorAll('.gallery-img[data-slot]').forEach(img => {
        const slot = parseInt(img.dataset.slot);
        img.src = pool[slot % pool.length];
        img.style.opacity = '1';
        img.loading = 'lazy';
    });
}

// Called by ui.js renderGallery to refresh mosaic on results page
function refreshGalleryMosaic(destCity) {
    const imgs = window._galleryImages;
    _fillMosaicSlots(imgs);

    // Destination cover photo — pick first available image
    const coverImg = document.getElementById('dest-cover-img');
    if (coverImg && imgs && imgs.length) {
        coverImg.src = imgs[Math.floor(Math.random() * imgs.length)];
        coverImg.style.display = 'block';
    }

    // Update gallery label
    const destLabel = document.getElementById('gallery-dest-label');
    if (destLabel) destLabel.querySelector('span').textContent = `📍 ${destCity}`;
}

// ── Theme ──────────────────────────────────────────────────────────────────

function initTheme() {
    const root = document.documentElement;
    const btn  = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('theme') || 'dark';
    applyTheme(saved);

    btn?.addEventListener('click', () => {
        const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        localStorage.setItem('theme', next);
    });
}

function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const darkIcon  = document.querySelector('.theme-icon-dark');
    const lightIcon = document.querySelector('.theme-icon-light');
    if (darkIcon)  darkIcon.hidden  = theme === 'light';
    if (lightIcon) lightIcon.hidden = theme === 'dark';
}

// ── Form ───────────────────────────────────────────────────────────────────

function initForm() {
    const dateInput = document.getElementById('start_date');
    if (dateInput) dateInput.min = new Date().toISOString().slice(0, 10);
    document.getElementById('trip-form')?.addEventListener('submit', handleFormSubmit);
}

async function handleFormSubmit(e) {
    e.preventDefault();
    clearFormError();

    const data = {
        origin_city:              document.getElementById('origin_city').value.trim(),
        destination_city:         document.getElementById('destination_city').value.trim(),
        budget:                   parseFloat(document.getElementById('budget').value),
        no_of_nights:             parseInt(document.getElementById('no_of_nights').value),
        start_date:               document.getElementById('start_date').value || null,
        travelers:                parseInt(document.getElementById('travelers').value) || 1,
        accommodation_preference: document.getElementById('accommodation_preference').value,
    };

    if (!data.origin_city)              return showFormError('Please enter your origin city.');
    if (!data.destination_city)         return showFormError('Please enter your destination city.');
    if (!data.budget || data.budget < 1000) return showFormError('Please enter a valid budget (min ₹1,000).');
    if (!data.no_of_nights || data.no_of_nights < 1) return showFormError('Please enter number of nights.');

    setBtnLoading(true);

    try {
        const { trip_id } = await planTrip(data);
        showProgressSection(data);
        startStreaming(trip_id);
    } catch (err) {
        setBtnLoading(false);
        showFormError('Failed to start planning: ' + err.message);
    }
}

// ── Agent progress ─────────────────────────────────────────────────────────

function startStreaming(tripId) {
    resetAgentStatuses();

    streamTripProgress(tripId, {
        onAgentStart:    (d) => {
            setAgentStatus(d.agent, 'running');
            appendActivityLog(d.agent, 'start');
            setCurrentTask(AGENT_MESSAGES[d.agent]?.start?.text || `${d.agent} started…`);
        },
        onAgentComplete: (d) => {
            setAgentStatus(d.agent, 'done');
            appendActivityLog(d.agent, 'done');
            _agentsDone++;
            updateProgressBar(_agentsDone);
        },
        onAgentError:    (d) => {
            setAgentStatus(d.agent, 'error');
            appendActivityLog(d.agent, 'error');
            _agentsDone++;
            updateProgressBar(_agentsDone);
            console.warn('Agent error:', d.agent, d.error);
        },
        onComplete:      (result) => {
            appendActivityLogRaw('🎉', 'success', 'All agents done — loading your trip results…');
            setTimeout(() => showResultsSection(result), 600);
        },
        onError:         (msg) => {
            appendActivityLogRaw('❌', 'error', 'Connection error: ' + msg);
            setBtnLoading(false);
            showFormError('Planning error: ' + msg);
            setTimeout(resetToHero, 2000);
        },
    });
}

function resetAgentStatuses() {
    _agentsDone = 0;
    updateProgressBar(0);
    setCurrentTask('Initialising agents…');
    clearActivityLog();

    document.querySelectorAll('.agent-item').forEach(item => {
        item.dataset.status = 'pending';
        item.querySelector('.status-pending-icon')?.classList.remove('hidden');
        item.querySelector('.status-running-icon')?.classList.add('hidden');
        item.querySelector('.status-done-icon')?.classList.add('hidden');
        item.querySelector('.status-error-icon')?.classList.add('hidden');
    });
}

function setAgentStatus(agentKey, status) {
    const item = document.querySelector(`.agent-item[data-agent="${agentKey}"]`);
    if (!item) return;
    item.dataset.status = status;
    item.querySelector('.status-pending-icon')?.classList.toggle('hidden', status !== 'pending');
    item.querySelector('.status-running-icon')?.classList.toggle('hidden', status !== 'running');
    item.querySelector('.status-done-icon')?.classList.toggle('hidden', status !== 'done');
    item.querySelector('.status-error-icon')?.classList.toggle('hidden', status !== 'error');
}

// ── Activity Log ───────────────────────────────────────────────────────────

function clearActivityLog() {
    const log = document.getElementById('activity-log');
    if (!log) return;
    log.innerHTML = `
        <div class="activity-log-empty" id="activity-log-empty">
            <div class="activity-spinner" aria-hidden="true"></div>
            <span>Waiting for agents to start…</span>
        </div>`;
}

function appendActivityLog(agentKey, eventType) {
    const msg = AGENT_MESSAGES[agentKey]?.[eventType];
    if (!msg) return;
    const typeClass = eventType === 'done' ? 'success' : eventType === 'error' ? 'error' : 'info';
    appendActivityLogRaw(msg.icon, typeClass, msg.text);
}

function appendActivityLogRaw(icon, typeClass, text) {
    const log = document.getElementById('activity-log');
    if (!log) return;

    // Remove the empty placeholder on first message
    document.getElementById('activity-log-empty')?.remove();

    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
    const entry = document.createElement('div');
    entry.className = `activity-entry activity-${typeClass}`;
    entry.innerHTML = `
        <span class="activity-icon">${icon}</span>
        <div class="activity-body">
            <span class="activity-text">${text}</span>
            <span class="activity-time">${time}</span>
        </div>`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

// ── Progress bar ───────────────────────────────────────────────────────────

function updateProgressBar(done) {
    const pct = Math.round((done / TOTAL_AGENTS) * 100);
    const fill = document.getElementById('progress-bar-fill');
    const label = document.getElementById('progress-bar-label');
    if (fill)  fill.style.width = pct + '%';
    if (label) label.textContent = `${done} / ${TOTAL_AGENTS} agents done`;
}

function setCurrentTask(text) {
    const el = document.getElementById('ai-current-task');
    if (el) el.textContent = text;
}

// ── Section transitions ────────────────────────────────────────────────────

function showProgressSection(data) {
    document.getElementById('hero-section').hidden     = true;
    document.getElementById('progress-section').hidden = false;
    document.getElementById('results-section').hidden  = true;

    // Show trip details in subtitle
    if (data) {
        const sub = document.getElementById('ai-current-task');
        if (sub) sub.textContent = `Planning ${data.origin_city} → ${data.destination_city} · ${data.no_of_nights} nights`;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showResultsSection(result) {
    document.getElementById('progress-section').hidden = true;
    document.getElementById('results-section').hidden  = false;
    setBtnLoading(false);

    const destName = document.getElementById('result-destination-name');
    if (destName) destName.textContent = result.destination_city || '';

    renderAllResults(result);

    copilot.setContext(result);
    copilot.showFab();

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function resetToHero() {
    document.getElementById('hero-section').hidden     = false;
    document.getElementById('progress-section').hidden = true;
    document.getElementById('results-section').hidden  = true;
    document.getElementById('copilot-fab').hidden      = true;
    copilot?.close();
    setBtnLoading(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── UI helpers ─────────────────────────────────────────────────────────────

function setBtnLoading(loading) {
    const btn = document.getElementById('plan-btn');
    if (!btn) return;
    btn.disabled = loading;
    btn.querySelector('.btn-spinner')?.classList.toggle('hidden', !loading);
    btn.querySelector('.btn-icon')?.classList.toggle('hidden', loading);
    btn.querySelector('.btn-text').textContent = loading ? 'Planning your trip…' : 'Plan My Trip';
    btn.querySelector('.btn-arrow')?.classList.toggle('hidden', loading);
}

function showFormError(msg) {
    const el = document.getElementById('form-error');
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
}

function clearFormError() {
    const el = document.getElementById('form-error');
    if (el) el.hidden = true;
}
