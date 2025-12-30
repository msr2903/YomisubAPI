const API_BASE_URL = ''; // Relative path since we serve from same origin

const inputArea = document.getElementById('jp-input');
const resultsArea = document.getElementById('results-area');
const detailsPanel = document.getElementById('details-panel');
const detailsContent = document.getElementById('details-content');
const emptyState = document.getElementById('empty-state');

// State
let currentTokens = [];
let currentMode = 'pro'; // Default mode

// Mode selector
const modeButtons = document.querySelectorAll('.mode-btn');
modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        modeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
    });
});

async function analyze() {
    const text = inputArea.value.trim();
    if (!text) return;

    setLoading(true);
    
    try {
        const endpoints = {
            'lite': '/analyze_lite',
            'pro': '/analyze_pro',
            'ultra': '/analyze_ultra'
        };
        const endpoint = endpoints[currentMode] || '/analyze_pro';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) throw new Error('Analysis failed');

        const data = await response.json();
        renderResults(data, currentMode);
    } catch (err) {
        console.error(err);
        resultsArea.innerHTML = `<div class="error">Error: ${err.message}</div>`;
    } finally {
        setLoading(false);
    }
}

function setLoading(isLoading) {
    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = isLoading);
    resultsArea.style.opacity = isLoading ? '0.5' : '1';
}

function renderResults(data, mode) {
    resultsArea.innerHTML = '';
    currentTokens = [];

    // Normalized list based on mode
    let items;
    if (mode === 'lite') {
        items = data.vocabulary;
    } else if (mode === 'ultra') {
        items = data.tokens;
    } else {
        items = data.phrases;
    }
    
    if (!items || items.length === 0) {
        resultsArea.innerHTML = '<div class="no-results">No tokens found.</div>';
        return;
    }

    items.forEach((item, index) => {
        // Create token element
        const tokenEl = document.createElement('div');
        tokenEl.className = 'token';
        tokenEl.textContent = item.word || item.surface;
        tokenEl.dataset.index = index;
        
        // Store item for click handler
        currentTokens.push(item);

        tokenEl.onclick = () => {
            // Active state
            document.querySelectorAll('.token').forEach(t => t.classList.remove('active'));
            tokenEl.classList.add('active');
            
            showDetails(item, mode);
        };

        resultsArea.appendChild(tokenEl);
    });
}

function showDetails(item, mode) {
    emptyState.style.display = 'none';
    detailsContent.style.display = 'block';

    // Extract fields based on mode
    const surface = item.word || item.surface;
    const base = item.base;
    const reading = item.reading;
    
    let conjugationHtml = '';
    
    // Conjugation logic
    if (mode === 'lite' && item.conjugation_hint) {
        conjugationHtml = `
            <div class="detail-section">
                <div class="section-title">Conjugation</div>
                <div class="conjugation-hint">${item.conjugation_hint}</div>
            </div>
        `;
    } else if ((mode === 'pro' || mode === 'ultra') && item.conjugation && item.conjugation.chain.length > 0) {
        const chain = item.conjugation.chain.map((layer, idx) => `
            <div class="tree-node">
                <span class="layer-number">${idx + 1}.</span>
                <span style="color:var(--accent-primary)">${layer.english}</span>
                <span style="opacity:0.6">(${layer.type})</span>
                <div style="font-size:0.8em; margin-top:2px; margin-left:1.5rem;">↳ ${layer.meaning}</div>
            </div>
        `).join('');
        
        conjugationHtml = `
            <div class="detail-section">
                <div class="section-title">Conjugation Layers</div>
                <div class="conjugation-tree">
                    <div style="margin-bottom:0.5rem; color:var(--text-primary); font-weight:500">
                        ${item.conjugation.summary}
                    </div>
                    ${chain}
                    ${item.conjugation.translation_hint ? 
                        `<div style="margin-top:0.5rem; color:var(--success); font-size:0.9em">
                            Hint: "${item.conjugation.translation_hint}"
                        </div>` : ''}
                </div>
            </div>
        `;
    }

    // Meaning logic - handle single string or array
    let meaningHtml = '';
    if (mode === 'ultra' && item.meanings && item.meanings.length > 0) {
        // Ultra mode: show all meanings as a list
        const meaningsList = item.meanings.map(m => 
            `<li class="meaning-item">${m}</li>`
        ).join('');
        meaningHtml = `
            <div class="detail-section">
                <div class="section-title">All Meanings</div>
                <ul class="meaning-list">
                    ${meaningsList}
                </ul>
            </div>
        `;
    } else {
        // Pro/Lite mode: single meaning string
        const meaning = item.meaning || '';
        const meaningList = meaning ? meaning.split(/;|\//).filter(m => m.trim().length > 0)
            .map(m => `<li class="meaning-item">${m.trim()}</li>`).join('') 
            : '<li class="meaning-item" style="opacity:0.5">No definition found</li>';
        meaningHtml = `
            <div class="detail-section">
                <div class="section-title">Meaning</div>
                <ul class="meaning-list">
                    ${meaningList}
                </ul>
            </div>
        `;
    }

    // Tags
    let tagsHtml = '';
    const tags = item.tags || [];
    if (tags.length > 0) {
        tagsHtml = `
            <div style="margin-bottom:1rem;">
                ${tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        `;
    }

    // Grammar Note (Pro and Ultra)
    let grammarHtml = '';
    if (item.grammar_note) {
        grammarHtml = `
            <div class="detail-section">
                <div class="section-title">Grammar Note</div>
                <div class="callout-info" style="padding:0.75rem; background:rgba(59,130,246,0.1); border-radius:8px; font-size:0.9rem;">
                    ${item.grammar_note}
                </div>
            </div>
        `;
    }

    detailsContent.innerHTML = `
        <div class="token-detail">
            <div class="detail-header">
                <div class="detail-reading">${reading || ''}</div>
                <div class="detail-surface">${surface}</div>
                <div class="detail-base">Base: ${base}</div>
                ${item.pos ? `<div style="margin-top:0.5rem; font-size:0.8rem; opacity:0.7">${item.pos}</div>` : ''}
            </div>
            
            ${tagsHtml}
            ${meaningHtml}
            ${grammarHtml}
            ${conjugationHtml}
        </div>
    `;
}
