const API_BASE_URL = ''; // Relative path since we serve from same origin

const inputArea = document.getElementById('jp-input');
const resultsArea = document.getElementById('results-area');
const detailsPanel = document.getElementById('details-panel');
const detailsContent = document.getElementById('details-content');
const emptyState = document.getElementById('empty-state');

// State
let currentTokens = [];

async function analyze(type) {
    const text = inputArea.value.trim();
    if (!text) return;

    setLoading(true);
    
    try {
        const endpoint = type === 'simple' ? '/analyze_simple' : '/analyze_full';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) throw new Error('Analysis failed');

        const data = await response.json();
        renderResults(data, type);
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

function renderResults(data, type) {
    resultsArea.innerHTML = '';
    currentTokens = [];

    // Normalized list based on type
    const items = type === 'simple' ? data.vocabulary : data.phrases;
    
    if (!items || items.length === 0) {
        resultsArea.innerHTML = '<div class="no-results">No tokens found.</div>';
        return;
    }

    items.forEach((item, index) => {
        // Create token element
        const tokenEl = document.createElement('div');
        tokenEl.className = 'token';
        tokenEl.textContent = item.word || item.surface; // Handle both simplified and full
        tokenEl.dataset.index = index;
        
        // Store item for click handler
        currentTokens.push(item);

        tokenEl.onclick = () => {
            // Active state
            document.querySelectorAll('.token').forEach(t => t.classList.remove('active'));
            tokenEl.classList.add('active');
            
            showDetails(item, type);
        };

        resultsArea.appendChild(tokenEl);
    });
}

function showDetails(item, type) {
    emptyState.style.display = 'none';
    detailsContent.style.display = 'block';

    // Extract fields based on type
    const surface = item.word || item.surface;
    const base = item.base;
    const reading = item.reading;
    const meaning = item.meaning;
    
    let conjugationHtml = '';
    
    // Conjugation logic
    if (type === 'simple' && item.conjugation_hint) {
        conjugationHtml = `
            <div class="detail-section">
                <div class="section-title">Conjugation</div>
                <div class="conjugation-hint">${item.conjugation_hint}</div>
            </div>
        `;
    } else if (type === 'full' && item.conjugation) {
        const chain = item.conjugation.chain.map(layer => `
            <div class="tree-node">
                <span style="color:var(--accent-primary)">${layer.form}</span> 
                <span style="opacity:0.6">(${layer.type})</span>
                <div style="font-size:0.8em; margin-top:2px;">↳ ${layer.meaning}</div>
            </div>
        `).join('');
        
        conjugationHtml = `
            <div class="detail-section">
                <div class="section-title">Conjugation Structure</div>
                <div class="conjugation-tree">
                    <div style="margin-bottom:0.5rem; color:var(--text-primary)">
                        ${item.conjugation.summary}
                    </div>
                    ${chain}
                    ${item.conjugation.translation_hint ? 
                        `<div style="margin-top:0.5rem; color:var(--success); font-size:0.9em">
                            Use: "${item.conjugation.translation_hint}"
                        </div>` : ''}
                </div>
            </div>
        `;
    }

    // Meaning logic (simple string or potentially complex if I expand later, but currently string)
    // Sometimes meaning contains semicolons or newlines
    const meaninList = meaning ? meaning.split(/;|\//).filter(m => m.trim().length > 0)
        .map(m => `<li class="meaning-item">${m.trim()}</li>`).join('') : '<li class="meaning-item" style="opacity:0.5">No definition found</li>';


    // Tags (Full only usually)
    let tagsHtml = '';
    if (item.tags && item.tags.length > 0) {
        tagsHtml = `
            <div style="margin-bottom:1rem;">
                ${item.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        `;
    }

    // Grammar Note (Full only)
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

            <div class="detail-section">
                <div class="section-title">Meaning</div>
                <ul class="meaning-list">
                    ${meaninList}
                </ul>
            </div>

            ${grammarHtml}
            ${conjugationHtml}
        </div>
    `;
}
