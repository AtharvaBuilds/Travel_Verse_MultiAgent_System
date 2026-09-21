/**
 * UI rendering helpers — Travel Planner AI
 * All DOM manipulation for the results dashboard lives here.
 */

let _leafletMap = null;
let _leafletMarker = null;

// ── Number / date helpers ──────────────────────────────────────────────────

function fmtNum(n) {
    return new Intl.NumberFormat('en-IN').format(n);
}

function fmtDateTime(iso) {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleString('en-US', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', hour12: true,
        });
    } catch { return iso; }
}

function fmtShortDate(dateStr) {
    if (!dateStr) return '';
    try {
        return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric',
        });
    } catch { return dateStr.slice(5); }
}

function fmtCoord(v) { return v != null ? parseFloat(v).toFixed(4) : '?'; }

function truncate(s, n) { return s && s.length > n ? s.slice(0, n) + '…' : (s || ''); }

function weatherEmoji(temp, precip) {
    if (precip > 70) return '🌧️';
    if (precip > 40) return '🌦️';
    if (temp > 35)   return '☀️';
    if (temp > 28)   return '🌤️';
    if (temp > 18)   return '⛅';
    if (temp > 8)    return '🌥️';
    return '❄️';
}

// ── Minimal markdown → HTML ────────────────────────────────────────────────

function mdToHtml(text) {
    if (!text) return '';
    let h = text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^#{4} (.+)$/gm, '<h5 class="md-h5">$1</h5>')
        .replace(/^#{3} (.+)$/gm, '<h4 class="md-h4">$1</h4>')
        .replace(/^#{2} (.+)$/gm, '<h3 class="md-h3">$1</h3>')
        .replace(/^#{1} (.+)$/gm, '<h2 class="md-h2">$1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/^[-•*] (.+)$/gm, '<li>$1</li>')
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Wrap contiguous <li> in <ul>
    h = h.replace(/(<li>[\s\S]*?<\/li>)(\s*<li>[\s\S]*?<\/li>)*/g, m => `<ul>${m}</ul>`);

    // Paragraphs
    return h.split(/\n\n+/).map(p => {
        p = p.trim();
        if (!p) return '';
        if (/^<[huo]/.test(p)) return p;
        return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).filter(Boolean).join('');
}

// ── Itinerary section parser ───────────────────────────────────────────────

function parseItinerary(text) {
    const out = { overview: '', days: [], weather: '', flights: '', budget: '' };
    if (!text) return out;

    // Overview block
    const ovMatch = text.match(/##\s*(?:trip\s*)?overview\s*\n([\s\S]+?)(?=\n##|$)/i);
    if (ovMatch) {
        out.overview = ovMatch[1].trim();
    } else {
        const before = text.match(/^([\s\S]+?)(?=\n##)/);
        if (before) out.overview = before[1].trim();
    }

    // Day sections (### Day N or ## Day N)
    const dayRe = /##[#]?\s+Day\s+(\d+)[:\s-]*(.+?)?\n([\s\S]+?)(?=\n##[#]?\s+Day|\n##[^#]|$)/gi;
    let m;
    while ((m = dayRe.exec(text)) !== null) {
        out.days.push({ num: parseInt(m[1]), title: (m[2] || '').trim(), content: m[3].trim() });
    }

    // Other sections
    const wx = text.match(/##[#]?\s+Weather[^\n]*\n([\s\S]+?)(?=\n##|$)/i);
    if (wx) out.weather = wx[1].trim();
    const fl = text.match(/##[#]?\s+Flight[^\n]*\n([\s\S]+?)(?=\n##|$)/i);
    if (fl) out.flights = fl[1].trim();
    const bud = text.match(/##[#]?\s+Budget[^\n]*\n([\s\S]+?)(?=\n##|$)/i);
    if (bud) out.budget = bud[1].trim();

    return out;
}

// ── Results meta ───────────────────────────────────────────────────────────

function renderResultsMeta(result) {
    const el = document.getElementById('results-meta');
    if (!el) return;
    const items = [];
    if (result.no_of_nights)  items.push(`🌙 ${result.no_of_nights} nights`);
    if (result.travelers)      items.push(`👥 ${result.travelers} traveller${result.travelers > 1 ? 's' : ''}`);
    if (result.start_date)     items.push(`📅 ${fmtShortDate(result.start_date)}`);
    if (result.accommodation_preference && result.accommodation_preference !== 'any') {
        const map = { budget: 'Budget stay', 'mid-range': 'Mid-range', luxury: 'Luxury' };
        items.push(`🏨 ${map[result.accommodation_preference] || result.accommodation_preference}`);
    }
    if (result.origin_city)    items.push(`🏠 From ${result.origin_city}`);
    el.innerHTML = items.map(i => `<span class="meta-badge">${i}</span>`).join('');
}

// ── Destination card ───────────────────────────────────────────────────────

function renderDestination(result) {
    const el = document.getElementById('destination-content');
    if (!el) return;
    const loc = result.destination_location || {};
    el.innerHTML = `
        <div class="destination-hero">
            <div class="destination-city">${result.destination_city || '—'}</div>
            <div class="destination-country">${loc.country || ''}</div>
            ${loc.latitude ? `<div class="destination-coords">🌐 ${fmtCoord(loc.latitude)}°, ${fmtCoord(loc.longitude)}°${loc.timezone ? ' · ' + loc.timezone : ''}</div>` : ''}
            <div class="destination-airports">
                <div class="airport-badge">
                    <span class="airport-label">Departs</span>
                    <span class="airport-code">${result.departure_iata || '—'}</span>
                    <span class="airport-city">${result.origin_city || ''}</span>
                </div>
                <div class="airport-arrow">→</div>
                <div class="airport-badge">
                    <span class="airport-label">Arrives</span>
                    <span class="airport-code">${result.arrival_iata || '—'}</span>
                    <span class="airport-city">${result.destination_city || ''}</span>
                </div>
            </div>
            ${loc.population ? `<div class="timezone">👥 Pop. ${fmtNum(loc.population)}</div>` : ''}
        </div>`;
}

// ── Weather card ───────────────────────────────────────────────────────────

function renderWeather(result) {
    const el = document.getElementById('weather-content');
    if (!el) return;
    const cur = (result.weather || {}).current || {};
    const daily = (result.weather || {}).daily || {};
    const temp = cur.temperature_2m, hum = cur.relative_humidity_2m, wind = cur.wind_speed_10m;
    if (temp === undefined) { el.innerHTML = '<div class="empty-state"><p>Weather data unavailable</p></div>'; return; }

    const times = daily.time || [], maxT = daily.temperature_2m_max || [],
          minT = daily.temperature_2m_min || [], pp = daily.precipitation_probability_max || [];

    const forecast = times.slice(0, 5).map((d, i) => `
        <div class="forecast-day">
            <div class="forecast-date">${fmtShortDate(d)}</div>
            <div class="forecast-emoji">${weatherEmoji(maxT[i], pp[i])}</div>
            <div class="forecast-temps"><span class="temp-max">${Math.round(maxT[i] ?? 0)}°</span><span class="temp-min">${Math.round(minT[i] ?? 0)}°</span></div>
            <div class="forecast-precip">${pp[i] ?? 0}% 💧</div>
        </div>`).join('');

    el.innerHTML = `
        <div class="weather-current">
            <div class="weather-main">
                <div class="weather-temp-big">${Math.round(temp)}°C</div>
                <div class="weather-emoji-big">${weatherEmoji(temp, pp[0])}</div>
            </div>
            <div class="weather-stats">
                <div class="weather-stat"><span>💧</span><span class="stat-value">${hum ?? '—'}%</span><span class="stat-label">Humidity</span></div>
                <div class="weather-stat"><span>💨</span><span class="stat-value">${wind ?? '—'} km/h</span><span class="stat-label">Wind</span></div>
            </div>
        </div>
        ${forecast ? `<div class="weather-forecast"><div class="forecast-label">5-Day Forecast</div><div class="forecast-strip">${forecast}</div></div>` : ''}`;
}

// ── Budget card ────────────────────────────────────────────────────────────

function renderBudget(result) {
    const el = document.getElementById('budget-content');
    if (!el) return;
    const inr = result.budget_inr || 0, usd = result.budget_usd || 0,
          rate = result.exchange_rate || 0, nights = result.no_of_nights || 1, trav = result.travelers || 1;
    el.innerHTML = `
        <div class="budget-main">
            <div class="budget-inr"><span class="currency-symbol">₹</span><span class="budget-amount">${fmtNum(Math.round(inr))}</span><span class="currency-label">INR</span></div>
            <div class="budget-convert-arrow">↓</div>
            <div class="budget-usd"><span class="currency-symbol">$</span><span class="budget-amount">${fmtNum(Math.round(usd))}</span><span class="currency-label">USD</span></div>
        </div>
        ${rate ? `<div class="budget-rate">1 INR ≈ ${parseFloat(rate).toFixed(5)} USD</div>` : ''}
        <div class="budget-breakdown">
            <div class="breakdown-item"><span class="breakdown-label">Per night</span><span class="breakdown-value">$${Math.round(usd / nights)}</span></div>
            ${trav > 1 ? `<div class="breakdown-item"><span class="breakdown-label">Per person</span><span class="breakdown-value">$${Math.round(usd / trav)}</span></div>` : ''}
            <div class="breakdown-item"><span class="breakdown-label">Duration</span><span class="breakdown-value">${nights} nights</span></div>
        </div>`;
}

// ── Flights card ───────────────────────────────────────────────────────────

function renderFlights(result) {
    const el = document.getElementById('flights-content');
    if (!el) return;
    const flights = result.flights || [];
    if (!flights.length) {
        el.innerHTML = `<div class="empty-state"><span class="empty-icon">✈️</span><p>No live flight data for this route right now.</p><p class="empty-hint">Check airline websites or Google Flights for current schedules.</p></div>`;
        return;
    }
    el.innerHTML = `<div class="flights-list">${flights.map(f => `
        <div class="flight-card">
            <div class="flight-airline">
                <span class="airline-name">${f.airline || 'Unknown'}</span>
                ${f.flight_iata ? `<span class="badge">${f.flight_iata}</span>` : ''}
                ${f.status ? `<span class="badge badge-${f.status.toLowerCase()}">${f.status}</span>` : ''}
            </div>
            <div class="flight-route">
                <div class="route-point"><div class="route-iata">${f.departure_iata || '—'}</div><div class="route-time">${fmtDateTime(f.departure_time)}</div><div class="route-airport">${truncate(f.departure_airport, 26)}</div></div>
                <div class="route-line"><div class="route-divider"></div><span>✈️</span><div class="route-divider"></div></div>
                <div class="route-point"><div class="route-iata">${f.arrival_iata || '—'}</div><div class="route-time">${fmtDateTime(f.arrival_time)}</div><div class="route-airport">${truncate(f.arrival_airport, 26)}</div></div>
            </div>
        </div>`).join('')}</div>`;
}

// ── Map card ───────────────────────────────────────────────────────────────

function renderMap(result) {
    const loc = result.destination_location || {};
    const lat = loc.latitude, lng = loc.longitude;
    const mapEl = document.getElementById('leaflet-map');
    if (!mapEl) return;
    if (!lat || !lng) { mapEl.innerHTML = '<div class="empty-state" style="height:100%;display:flex;align-items:center;justify-content:center"><p>Map not available</p></div>'; return; }

    if (!_leafletMap) {
        _leafletMap = L.map('leaflet-map', { scrollWheelZoom: false }).setView([lat, lng], 11);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(_leafletMap);
    } else {
        _leafletMap.setView([lat, lng], 11);
        if (_leafletMarker) _leafletMap.removeLayer(_leafletMarker);
    }
    _leafletMarker = L.marker([lat, lng]).addTo(_leafletMap)
        .bindPopup(`<b>${result.destination_city || ''}</b><br>${loc.country || ''}`).openPopup();
    setTimeout(() => _leafletMap.invalidateSize(), 200);
}

// ── Itinerary card ─────────────────────────────────────────────────────────

function renderItinerary(result) {
    const el = document.getElementById('itinerary-content');
    if (!el) return;
    const text = result.itinerary || '';
    if (!text) { el.innerHTML = '<div class="empty-state"><p>Itinerary not available</p></div>'; return; }

    const sec = parseItinerary(text);
    let html = '';

    if (sec.overview) html += `<div class="itinerary-overview">${mdToHtml(sec.overview)}</div>`;

    if (sec.days.length) {
        html += `<div class="timeline">${sec.days.map(d => `
            <div class="timeline-item">
                <div class="timeline-marker"><div class="timeline-day-num">Day<br>${d.num}</div></div>
                <div class="timeline-content">
                    ${d.title ? `<h4 class="timeline-title">${d.title}</h4>` : ''}
                    <div class="timeline-body">${mdToHtml(d.content)}</div>
                </div>
            </div>`).join('')}</div>`;
    } else {
        html += `<div class="timeline-body">${mdToHtml(text)}</div>`;
    }

    [['weather', '🌤️ Weather Considerations'], ['flights', '✈️ Flight Considerations'], ['budget', '💰 Budget Considerations']]
        .forEach(([k, label]) => {
            if (sec[k]) html += `<details class="itinerary-section" open><summary class="section-summary">${label}</summary><div class="section-content">${mdToHtml(sec[k])}</div></details>`;
        });

    el.innerHTML = html;
}

// ── Trip at a Glance ───────────────────────────────────────────────────────

function renderGlance(result) {
    const el = document.getElementById('glance-content');
    if (!el) return;

    const dest      = result.destination_city || '—';
    const origin    = result.origin_city || '—';
    const nights    = result.no_of_nights || 0;
    const travelers = result.travelers || 1;
    const budgetInr = result.budget_inr || 0;
    const budgetUsd = result.budget_usd || 0;
    const rate      = result.exchange_rate || 0;
    const accom     = result.accommodation_preference || 'any';
    const completed = result.completed_tasks || [];

    const accomLabel = { any: 'Any', budget: 'Budget', 'mid-range': 'Mid-range', luxury: 'Luxury' }[accom] || accom;
    const accomIcon  = { any: '🏨', budget: '🛖', 'mid-range': '🏩', luxury: '🏰' }[accom] || '🏨';

    const perNight   = nights > 0  ? Math.round(budgetUsd / nights)    : 0;
    const perPerson  = travelers > 0 ? Math.round(budgetUsd / travelers) : 0;

    // Agent success rate
    const agentTotal   = 6;
    const agentDone    = completed.length;
    const successPct   = Math.round((agentDone / agentTotal) * 100);

    el.innerHTML = `
        <!-- Section heading -->
        <div class="glance-heading">
            <span class="glance-title">Trip at a Glance</span>
            <span class="glance-route">${origin} → ${dest}</span>
        </div>

        <!-- Stat grid -->
        <div class="glance-stats">
            <div class="glance-stat">
                <div class="gstat-icon">🌙</div>
                <div class="gstat-val">${nights}</div>
                <div class="gstat-lbl">Nights</div>
            </div>
            <div class="glance-stat">
                <div class="gstat-icon">👥</div>
                <div class="gstat-val">${travelers}</div>
                <div class="gstat-lbl">Traveller${travelers !== 1 ? 's' : ''}</div>
            </div>
            <div class="glance-stat">
                <div class="gstat-icon">₹</div>
                <div class="gstat-val">${fmtNum(Math.round(budgetInr))}</div>
                <div class="gstat-lbl">Budget (INR)</div>
            </div>
            <div class="glance-stat glance-stat-accent">
                <div class="gstat-icon">$</div>
                <div class="gstat-val">${fmtNum(Math.round(budgetUsd))}</div>
                <div class="gstat-lbl">Budget (USD)</div>
            </div>
            <div class="glance-stat">
                <div class="gstat-icon">${accomIcon}</div>
                <div class="gstat-val" style="font-size:1rem">${accomLabel}</div>
                <div class="gstat-lbl">Stay type</div>
            </div>
            <div class="glance-stat">
                <div class="gstat-icon">🌙</div>
                <div class="gstat-val">$${perNight}</div>
                <div class="gstat-lbl">Per night</div>
            </div>
            ${travelers > 1 ? `
            <div class="glance-stat">
                <div class="gstat-icon">🧍</div>
                <div class="gstat-val">$${perPerson}</div>
                <div class="gstat-lbl">Per person</div>
            </div>` : ''}
            ${rate ? `
            <div class="glance-stat">
                <div class="gstat-icon">💱</div>
                <div class="gstat-val" style="font-size:.85rem">${parseFloat(rate).toFixed(4)}</div>
                <div class="gstat-lbl">1 INR = ? USD</div>
            </div>` : ''}
        </div>

        <!-- Agent completion bar -->
        <div class="glance-agents">
            <div class="glance-agents-top">
                <span class="glance-agents-label">AI Agents Completed</span>
                <span class="glance-agents-count">${agentDone} / ${agentTotal}</span>
            </div>
            <div class="glance-bar-track">
                <div class="glance-bar-fill" style="width:${successPct}%"></div>
            </div>
            <div class="glance-chips">
                ${completed.map(t => `<span class="glance-chip glance-chip-done">✓ ${t.replace(/_/g,' ')}</span>`).join('')}
            </div>
        </div>
    `;
}

// ── Combined render ────────────────────────────────────────────────────────

function renderAllResults(result) {
    renderResultsMeta(result);
    renderDestination(result);
    renderWeather(result);
    renderBudget(result);
    renderFlights(result);
    renderMap(result);
    renderGlance(result);
    renderItinerary(result);
}
