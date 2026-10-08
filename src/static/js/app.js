// State
let currentSearchResults = [];
let activeFilter = 'all';
let currentSeriesData = null;
let activeSeasonNumber = 1;
let selectedMovieForDownload = null;

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchSubmitBtn = document.getElementById('searchSubmitBtn');
const searchResults = document.getElementById('searchResults');
const searchSpinner = document.getElementById('searchSpinner');
const noResults = document.getElementById('noResults');
const typeFilters = document.getElementById('typeFilters');

const activeDownloadsList = document.getElementById('activeDownloadsList');
const completedDownloadsList = document.getElementById('completedDownloadsList');
const activeDownloadsCount = document.getElementById('activeDownloadsCount');
const noDownloads = document.getElementById('noDownloads');

const settingsForm = document.getElementById('settingsForm');
const testUrlBtn = document.getElementById('testUrlBtn');
const testResult = document.getElementById('testResult');

// Navigation Tabs
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetTab = document.getElementById(btn.dataset.tab);
        if (targetTab) {
            targetTab.classList.add('active');
        }
    });
});

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Modal helpers
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
};

// --- Search Functionality ---
async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    searchSpinner.style.display = 'block';
    searchResults.innerHTML = '';
    noResults.style.display = 'none';

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        searchSpinner.style.display = 'none';
        if (data.ok && data.results && data.results.length > 0) {
            currentSearchResults = data.results;
            renderSearchResults();
        } else {
            currentSearchResults = [];
            noResults.style.display = 'block';
        }
    } catch (err) {
        searchSpinner.style.display = 'none';
        noResults.style.display = 'block';
        showToast('Errore durante la ricerca: ' + err.message, 'error');
    }
}

searchSubmitBtn.addEventListener('click', performSearch);
searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') performSearch();
});

// Filter Pills
typeFilters.querySelectorAll('.pill').forEach(pill => {
    pill.addEventListener('click', () => {
        typeFilters.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeFilter = pill.dataset.filter;
        renderSearchResults();
    });
});

function renderSearchResults() {
    searchResults.innerHTML = '';
    const filtered = currentSearchResults.filter(item => {
        if (activeFilter === 'all') return true;
        return item.type === activeFilter;
    });

    if (filtered.length === 0) {
        noResults.style.display = 'block';
        return;
    }
    noResults.style.display = 'none';

    filtered.forEach(item => {
        const card = document.createElement('div');
        card.className = 'title-card';

        const posterSrc = item.poster_url || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="300" viewBox="0 0 200 300"><rect fill="%231f2937" width="200" height="300"/><text fill="%236b7280" font-family="sans-serif" font-size="16" dy="10.5" font-weight="bold" x="50%" y="50%" text-anchor="middle">No Poster</text></svg>';

        const isTv = item.type === 'tv';
        const typeBadgeText = isTv ? 'Serie TV' : 'Film';
        const scoreText = item.score ? `★ ${item.score}` : '';

        card.innerHTML = `
            <div class="card-poster-wrapper">
                <img class="card-poster" src="${posterSrc}" alt="${escapeHtml(item.name)}" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'300\\'><rect fill=\\'%231f2937\\' width=\\'200\\' height=\\'300\\'/><text fill=\\'%236b7280\\' font-size=\\'16\\' x=\\'50%\\' y=\\'50%\\' text-anchor=\\'middle\\'>No Poster</text></svg>'">
                <span class="card-badge-type">${typeBadgeText}</span>
                ${scoreText ? `<span class="card-badge-score">${scoreText}</span>` : ''}
            </div>
            <div class="card-content">
                <div class="card-title" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
                <div class="card-meta">
                    <span>${item.year || ''}</span>
                    <span>${isTv ? (item.seasons_count ? item.seasons_count + ' stag.' : '') : ''}</span>
                </div>
                <div class="card-actions">
                    <button class="card-btn ${isTv ? 'secondary' : ''}" onclick="handleCardAction(${item.id})">
                        ${isTv ? 'Vedi Episodi' : 'Scarica Film'}
                    </button>
                </div>
            </div>
        `;
        searchResults.appendChild(card);
    });
}

function handleCardAction(titleId) {
    const item = currentSearchResults.find(t => t.id === titleId);
    if (!item) return;

    if (item.type === 'tv') {
        openTvModal(item);
    } else {
        openMovieModal(item);
    }
}

// --- Movie Modal ---
function openMovieModal(item) {
    selectedMovieForDownload = item;
    document.getElementById('movieModalTitle').textContent = item.name;
    document.getElementById('movieModalPoster').src = item.poster_url || '';
    document.getElementById('movieModalYear').textContent = item.year ? `Anno: ${item.year}` : '';
    document.getElementById('movieModalPlot').textContent = item.plot || 'Nessuna trama disponibile.';
    openModal('movieModal');
}

document.getElementById('confirmMovieDownloadBtn').addEventListener('click', async () => {
    if (!selectedMovieForDownload) return;

    const quality = document.getElementById('movieQualitySelect').value;
    const audio = document.getElementById('movieAudioSelect').value;

    try {
        const res = await fetch('/api/download/movie', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_id: selectedMovieForDownload.id,
                title_name: selectedMovieForDownload.name,
                year: selectedMovieForDownload.year || '',
                quality: quality,
                audio_lang: audio,
                poster_url: selectedMovieForDownload.poster_url
            })
        });
        const data = await res.json();
        closeModal('movieModal');
        if (data.ok) {
            showToast(`'${selectedMovieForDownload.name}' aggiunto alla coda download!`, 'success');
            // Switch to download tab
            document.querySelector('.nav-btn[data-tab="downloadsTab"]').click();
        } else {
            showToast('Errore: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Errore avvio download: ' + err.message, 'error');
    }
});

// --- TV Series Modal ---
async function openTvModal(item) {
    openModal('tvModal');
    document.getElementById('tvModalTitle').textContent = `Caricamento ${item.name}...`;
    document.getElementById('tvSeasonsBar').innerHTML = '<div class="spinner" style="width:20px;height:20px;"></div>';
    document.getElementById('tvEpisodesList').innerHTML = '';

    try {
        const res = await fetch(`/api/titles/${item.id}?slug=${item.slug}`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.detail || 'Impossibile caricare i dettagli');

        currentSeriesData = data.details;
        document.getElementById('tvModalTitle').textContent = currentSeriesData.name;
        renderTvSeasons();
    } catch (err) {
        document.getElementById('tvModalTitle').textContent = 'Errore';
        document.getElementById('tvEpisodesList').innerHTML = `<p style="color:var(--danger)">Errore: ${err.message}</p>`;
    }
}

function renderTvSeasons() {
    const bar = document.getElementById('tvSeasonsBar');
    bar.innerHTML = '';
    const seasons = currentSeriesData.seasons || [];

    if (seasons.length === 0) {
        bar.innerHTML = '<span style="color:var(--text-muted)">Nessuna stagione trovata</span>';
        renderTvEpisodes(currentSeriesData.episodes || []);
        return;
    }

    seasons.forEach((s, idx) => {
        const tab = document.createElement('button');
        tab.className = `season-tab ${idx === 0 ? 'active' : ''}`;
        tab.textContent = s.name || `Stagione ${s.number}`;
        tab.addEventListener('click', () => {
            bar.querySelectorAll('.season-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            activeSeasonNumber = s.number;
            loadSeasonEpisodes(s.number);
        });
        bar.appendChild(tab);
    });

    activeSeasonNumber = seasons[0].number;
    renderTvEpisodes(currentSeriesData.episodes || []);
}

async function loadSeasonEpisodes(seasonNum) {
    const list = document.getElementById('tvEpisodesList');
    list.innerHTML = '<div class="spinner" style="width:24px;height:24px;margin:2rem auto;"></div>';

    try {
        const res = await fetch(`/api/titles/${currentSeriesData.id}/season/${seasonNum}?slug=${currentSeriesData.slug}`);
        const data = await res.json();
        if (data.ok) {
            renderTvEpisodes(data.episodes);
        } else {
            list.innerHTML = '<p>Nessun episodio trovato per questa stagione.</p>';
        }
    } catch (err) {
        list.innerHTML = `<p style="color:var(--danger)">Errore nel caricamento: ${err.message}</p>`;
    }
}

function renderTvEpisodes(episodes) {
    const list = document.getElementById('tvEpisodesList');
    list.innerHTML = '';
    document.getElementById('episodesCountText').textContent = `${episodes.length} episodi`;

    const downloadSeasonBtn = document.getElementById('downloadSeasonBtn');
    downloadSeasonBtn.onclick = () => downloadWholeSeason(episodes);

    if (episodes.length === 0) {
        list.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Nessun episodio disponibile.</p>';
        return;
    }

    episodes.forEach(ep => {
        const item = document.createElement('div');
        item.className = 'episode-item';
        item.innerHTML = `
            <div class="episode-info">
                <div class="episode-title">Episodio ${ep.number}: ${escapeHtml(ep.name || '')}</div>
                ${ep.plot ? `<div class="episode-plot">${escapeHtml(ep.plot)}</div>` : ''}
            </div>
            <button class="primary-btn btn-sm" onclick="downloadSingleEpisode(${ep.id}, ${ep.number}, '${escapeQuotes(ep.name || '')}')">
                Scarica
            </button>
        `;
        list.appendChild(item);
    });
}

async function downloadSingleEpisode(epId, epNum, epName) {
    try {
        const res = await fetch('/api/download/episode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_id: currentSeriesData.id,
                title_name: currentSeriesData.name,
                year: currentSeriesData.year || '',
                episode_id: epId,
                season_number: activeSeasonNumber,
                episode_number: epNum,
                episode_name: epName,
                poster_url: currentSeriesData.poster_url
            })
        });
        const data = await res.json();
        if (data.ok) {
            showToast(`Episodio S${activeSeasonNumber}x${epNum} in coda!`, 'success');
        } else {
            showToast('Errore: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Errore avvio download: ' + err.message, 'error');
    }
}

async function downloadWholeSeason(episodes) {
    if (!episodes || episodes.length === 0) return;
    try {
        const res = await fetch('/api/download/season', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_id: currentSeriesData.id,
                title_name: currentSeriesData.name,
                year: currentSeriesData.year || '',
                season_number: activeSeasonNumber,
                episodes: episodes,
                poster_url: currentSeriesData.poster_url
            })
        });
        const data = await res.json();
        if (data.ok) {
            closeModal('tvModal');
            showToast(`Tutta la stagione (${episodes.length} episodi) aggiunta alla coda!`, 'success');
            document.querySelector('.nav-btn[data-tab="downloadsTab"]').click();
        } else {
            showToast('Errore: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Errore: ' + err.message, 'error');
    }
}

// --- Downloads SSE & Real-time Monitor ---
function setupDownloadsMonitor() {
    let evtSource = null;
    let pollTimer = null;
    let isSSEConnected = false;

    async function fetchOnce() {
        try {
            const res = await fetch('/api/downloads');
            const data = await res.json();
            if (data.ok) {
                renderDownloads(data.tasks);
            }
        } catch (e) {}
    }

    function startPollingFallback() {
        if (pollTimer) return;
        pollTimer = setInterval(async () => {
            if (isSSEConnected) {
                clearInterval(pollTimer);
                pollTimer = null;
                return;
            }
            await fetchOnce();
            if (!evtSource || evtSource.readyState === EventSource.CLOSED) {
                connectSSE();
            }
        }, 3000);
    }

    function connectSSE() {
        if (evtSource) {
            try { evtSource.close(); } catch (e) {}
        }
        evtSource = new EventSource('/api/downloads/stream');

        evtSource.onopen = function() {
            isSSEConnected = true;
            if (pollTimer) {
                clearInterval(pollTimer);
                pollTimer = null;
            }
        };

        evtSource.onmessage = function(event) {
            try {
                const tasks = JSON.parse(event.data);
                renderDownloads(tasks);
            } catch (e) {}
        };

        evtSource.onerror = function() {
            isSSEConnected = false;
            try { evtSource.close(); } catch (e) {}
            startPollingFallback();
        };
    }

    fetchOnce();
    connectSSE();
}

function renderDownloads(tasks) {
    const activeTasks = tasks.filter(t => ['queued', 'resolving', 'downloading', 'waiting_network'].includes(t.status));
    const completedTasks = tasks.filter(t => ['completed', 'failed', 'cancelled'].includes(t.status));

    // Update navbar badge
    if (activeTasks.length > 0) {
        activeDownloadsCount.textContent = activeTasks.length;
        activeDownloadsCount.style.display = 'inline-block';
    } else {
        activeDownloadsCount.style.display = 'none';
    }

    if (tasks.length === 0) {
        noDownloads.style.display = 'block';
        document.getElementById('activeDownloadsContainer').style.display = 'none';
        document.getElementById('completedDownloadsContainer').style.display = 'none';
        return;
    }

    noDownloads.style.display = 'none';
    document.getElementById('activeDownloadsContainer').style.display = activeTasks.length > 0 ? 'block' : 'none';
    document.getElementById('completedDownloadsContainer').style.display = completedTasks.length > 0 ? 'block' : 'none';

    // Render Active
    activeDownloadsList.innerHTML = '';
    activeTasks.forEach(task => {
        const item = createDownloadItemElement(task, true);
        activeDownloadsList.appendChild(item);
    });

    // Render Completed
    completedDownloadsList.innerHTML = '';
    completedTasks.forEach(task => {
        const item = createDownloadItemElement(task, false);
        completedDownloadsList.appendChild(item);
    });
}

function createDownloadItemElement(task, isActive) {
    const div = document.createElement('div');
    div.className = 'download-item';

    const statusMap = {
        queued: 'In coda',
        resolving: 'Ricerca flussi HLS',
        downloading: 'Download HLS in corso',
        waiting_network: 'In attesa Wi-Fi 📶',
        completed: 'Completato',
        failed: 'Errore',
        cancelled: 'Annullato'
    };

    const statusLabel = statusMap[task.status] || task.status;
    const posterSrc = task.poster_url || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="48" height="68"><rect fill="%231f2937" width="48" height="68"/></svg>';

    const hasTotal = task.total_size && task.total_size !== '--';
    const sizeDisplay = hasTotal ? `${task.downloaded_size} / ${task.total_size}` : task.downloaded_size;

    let progressHtml = '';
    if (isActive) {
        const multDisplay = (task.speed_mult && task.speed_mult !== '0x' && task.speed_mult !== 'N/A') ? `(${escapeHtml(task.speed_mult)})` : '';
        progressHtml = `
            <div class="progress-container">
                <div class="progress-track">
                    <div class="progress-fill" style="width: ${task.progress}%"></div>
                </div>
                <div class="progress-details">
                    <span>${task.progress}% ${multDisplay}</span>
                    <span>Restanti: ${escapeHtml(task.eta)}</span>
                    <span>${escapeHtml(sizeDisplay)}</span>
                </div>
            </div>
        `;
    }

    let errorHtml = '';
    if (task.status === 'failed' && task.error_message) {
        errorHtml = `<div style="font-size:0.8rem;color:var(--danger);margin-top:0.25rem;">${escapeHtml(task.error_message)}</div>`;
    } else if (task.status === 'waiting_network' && task.error_message) {
        errorHtml = `<div style="font-size:0.8rem;color:var(--warning);margin-top:0.25rem;">📶 ${escapeHtml(task.error_message)}</div>`;
    }

    const currentSpeed = task.download_speed || (task.speed && !task.speed.includes('(') ? task.speed : '');
    const hasSpeed = isActive && currentSpeed && currentSpeed !== '0 B/s' && currentSpeed !== '0x';

    div.innerHTML = `
        <div class="download-main">
            <img class="download-poster" src="${posterSrc}" alt="Poster">
            <div class="download-info">
                <div class="download-title" title="${escapeHtml(task.display_title)}">${escapeHtml(task.display_title)}</div>
                <div class="download-meta">
                    <span class="badge badge-status-${task.status}">${statusLabel}</span>
                    <span class="badge badge-quality">${task.quality || 'HD'}</span>
                    ${hasSpeed ? `<span class="badge badge-speed">⚡ ${escapeHtml(currentSpeed)}</span>` : ''}
                    ${task.downloaded_size ? `<span>Dimensione: ${escapeHtml(sizeDisplay)}</span>` : ''}
                    ${task.file_path && !isActive ? `<span title="${escapeHtml(formatPathForDisplay(task.file_path))}" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">📁 ${escapeHtml(formatPathForDisplay(task.file_path))}</span>` : ''}
                </div>
                ${errorHtml}
            </div>
            <div class="download-actions">
                ${isActive ? `
                    <button class="btn-icon" title="Annulla download" onclick="cancelDownload('${task.id}')">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                ` : `
                    ${(task.status === 'failed' || task.status === 'cancelled') ? `
                        <button class="btn-icon" title="Riprova download" onclick="retryDownload('${task.id}')">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                        </button>
                    ` : ''}
                    <button class="btn-icon" title="Rimuovi da cronologia" onclick="deleteDownload('${task.id}', false)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                `}
            </div>
        </div>
        ${progressHtml}
    `;

    return div;
}

async function cancelDownload(taskId) {
    try {
        const res = await fetch(`/api/downloads/${taskId}/cancel`, { method: 'POST' });
        const data = await res.json();
        if (data.ok) showToast('Download annullato', 'info');
    } catch (e) {}
}

async function retryDownload(taskId) {
    try {
        const res = await fetch(`/api/downloads/${taskId}/retry`, { method: 'POST' });
        const data = await res.json();
        if (data.ok) showToast('Download rimesso in coda', 'success');
    } catch (e) {
        showToast('Errore durante il riavvio del download', 'error');
    }
}

async function deleteDownload(taskId, deleteFile) {
    try {
        const res = await fetch(`/api/downloads/${taskId}?delete_file=${deleteFile}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) showToast('Elemento rimosso', 'info');
    } catch (e) {}
}

// --- Settings Form ---
settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        streamingcommunity_url: document.getElementById('streamingUrl').value.trim(),
        movies_dir: document.getElementById('moviesDir').value.trim(),
        tv_dir: document.getElementById('tvDir').value.trim(),
        preferred_quality: document.getElementById('preferredQuality').value,
        preferred_audio: document.getElementById('preferredAudio').value,
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.ok) {
            showToast('Impostazioni salvate con successo!', 'success');
        } else {
            showToast('Errore salvataggio impostazioni', 'error');
        }
    } catch (err) {
        showToast('Errore: ' + err.message, 'error');
    }
});

// Test URL Connection Button
testUrlBtn.addEventListener('click', async () => {
    const url = document.getElementById('streamingUrl').value.trim();
    if (!url) return;

    testResult.style.display = 'block';
    testResult.className = 'test-status';
    testResult.textContent = 'Verifica connessione in corso...';

    try {
        const res = await fetch('/api/settings/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ streamingcommunity_url: url })
        });
        const data = await res.json();
        if (data.ok) {
            testResult.className = 'test-status success';
            testResult.textContent = `✓ ${data.message} (HTTP ${data.status_code})`;
        } else {
            testResult.className = 'test-status error';
            testResult.textContent = `✗ ${data.message}`;
        }
    } catch (err) {
        testResult.className = 'test-status error';
        testResult.textContent = `✗ Errore: ${err.message}`;
    }
});

// Utility
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m];
    });
}

function escapeQuotes(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'");
}

function formatPathForDisplay(filePath) {
    if (!filePath) return '';
    if (filePath.startsWith('/host_c/')) {
        return 'C:\\' + filePath.slice(8).replace(/\//g, '\\');
    }
    const match = filePath.match(/^\/host_([a-zA-Z])\/(.*)$/);
    if (match) {
        return match[1].toUpperCase() + ':\\' + match[2].replace(/\//g, '\\');
    }
    return filePath;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupDownloadsMonitor();
});
