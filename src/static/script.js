// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = '';

    const inputArea = document.getElementById('jp-input');
    const resultsArea = document.getElementById('results-area');
    const detailsPanel = document.getElementById('details-panel');
    const detailsContent = document.getElementById('details-content');
    const emptyState = document.getElementById('empty-state');
    const modeSelect = document.getElementById('mode-select');
    const analyzeBtn = document.getElementById('analyze-btn');

    // State
    let currentTokens = [];
    let currentMode = 'pro';

    // Check if elements exist
    if (!analyzeBtn || !inputArea || !resultsArea) {
        console.error('Required DOM elements not found');
        return;
    }

    // Event listeners
    analyzeBtn.addEventListener('click', function(e) {
        e.preventDefault();
        analyze();
    });

    modeSelect.addEventListener('change', function(e) {
        currentMode = e.target.value;
    });

    // Allow Enter key in textarea (with Ctrl/Cmd) to trigger analysis
    inputArea.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            analyze();
        }
    });

    async function analyze() {
        const text = inputArea.value.trim();
        if (!text) {
            resultsArea.innerHTML = '<div class="error-message">Please enter some Japanese text</div>';
            return;
        }

        setLoading(true);
        
        try {
            const endpoints = {
                'lite': '/process_lite',
                'pro': '/process_pro',
                'ultra': '/process_ultra'
            };
            const endpoint = endpoints[currentMode] || '/process_pro';
            
            console.log('Fetching:', endpoint, 'with text:', text);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text }),
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                let errorMsg = 'HTTP ' + response.status;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {
                    // ignore JSON parse error
                }
                throw new Error(errorMsg);
            }

            const data = await response.json();
            console.log('Response data:', data);
            renderResults(data, currentMode);
        } catch (err) {
            console.error('Analysis error:', err);
            resultsArea.innerHTML = '<div class="error-message">Error: ' + err.message + '</div>';
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        analyzeBtn.disabled = isLoading;
        analyzeBtn.textContent = isLoading ? 'Analyzing...' : 'Analyze';
        resultsArea.style.opacity = isLoading ? '0.5' : '1';
    }

    function renderResults(data, mode) {
        resultsArea.innerHTML = '';
        currentTokens = [];

        // Normalized list based on mode
        var items;
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

        items.forEach(function(item, index) {
            var tokenEl = document.createElement('div');
            tokenEl.className = 'token';
            tokenEl.textContent = item.word || item.surface;
            tokenEl.setAttribute('data-index', index);
            
            currentTokens.push(item);

            tokenEl.onclick = function() {
                var allTokens = document.querySelectorAll('.token');
                for (var i = 0; i < allTokens.length; i++) {
                    allTokens[i].classList.remove('active');
                }
                tokenEl.classList.add('active');
                showDetails(item, mode);
            };

            resultsArea.appendChild(tokenEl);
        });
        
        // Auto-select first token
        if (items.length > 0) {
            var firstToken = resultsArea.querySelector('.token');
            if (firstToken) firstToken.click();
        }
    }

    function showDetails(item, mode) {
        emptyState.style.display = 'none';
        detailsContent.style.display = 'block';

        var surface = item.word || item.surface;
        var base = item.base;
        var reading = item.reading;
        
        var conjugationHtml = '';
        
        // Conjugation logic
        if (mode === 'lite' && item.conjugation_hint) {
            conjugationHtml = '<div class="detail-section">' +
                '<div class="section-title">Conjugation</div>' +
                '<div class="conjugation-hint">' + item.conjugation_hint + '</div>' +
            '</div>';
        } else if ((mode === 'pro' || mode === 'ultra') && item.conjugation && item.conjugation.chain && item.conjugation.chain.length > 0) {
            var chain = '';
            for (var i = 0; i < item.conjugation.chain.length; i++) {
                var layer = item.conjugation.chain[i];
                chain += '<div class="tree-node">' +
                    '<span class="layer-number">' + (i + 1) + '.</span>' +
                    '<span style="color:var(--accent-primary)">' + layer.english + '</span>' +
                    '<span style="opacity:0.6">(' + layer.type + ')</span>' +
                    '<div style="font-size:0.8em; margin-top:2px; margin-left:1.5rem;">↳ ' + layer.meaning + '</div>' +
                '</div>';
            }
            
            conjugationHtml = '<div class="detail-section">' +
                '<div class="section-title">Conjugation Layers</div>' +
                '<div class="conjugation-tree">' +
                    '<div style="margin-bottom:0.5rem; color:var(--text-primary); font-weight:500">' + item.conjugation.summary + '</div>' +
                    chain +
                    (item.conjugation.translation_hint ? 
                        '<div style="margin-top:0.5rem; color:var(--success); font-size:0.9em">Hint: "' + item.conjugation.translation_hint + '"</div>' : '') +
                '</div>' +
            '</div>';
        }

        // Meaning logic
        var meaningHtml = '';
        if (mode === 'ultra' && item.meanings && item.meanings.length > 0) {
            var meaningsList = '';
            for (var i = 0; i < item.meanings.length; i++) {
                meaningsList += '<li class="meaning-item">' + item.meanings[i] + '</li>';
            }
            meaningHtml = '<div class="detail-section">' +
                '<div class="section-title">All Meanings (' + item.meanings.length + ')</div>' +
                '<ul class="meaning-list">' + meaningsList + '</ul>' +
            '</div>';
        } else {
            var meaning = item.meaning || '';
            var meaningList = '';
            if (meaning) {
                var parts = meaning.split(/;|\//);
                for (var i = 0; i < parts.length; i++) {
                    var part = parts[i].trim();
                    if (part.length > 0) {
                        meaningList += '<li class="meaning-item">' + part + '</li>';
                    }
                }
            }
            if (!meaningList) {
                meaningList = '<li class="meaning-item" style="opacity:0.5">No definition found</li>';
            }
            meaningHtml = '<div class="detail-section">' +
                '<div class="section-title">Meaning</div>' +
                '<ul class="meaning-list">' + meaningList + '</ul>' +
            '</div>';
        }

        // Tags
        var tagsHtml = '';
        var tags = item.tags || [];
        if (tags.length > 0) {
            var tagsStr = '';
            for (var i = 0; i < tags.length; i++) {
                tagsStr += '<span class="tag">' + tags[i] + '</span>';
            }
            tagsHtml = '<div style="margin-bottom:1rem;">' + tagsStr + '</div>';
        }

        // Grammar Note
        var grammarHtml = '';
        if (item.grammar_note) {
            grammarHtml = '<div class="detail-section">' +
                '<div class="section-title">Grammar Note</div>' +
                '<div class="callout-info">' + item.grammar_note + '</div>' +
            '</div>';
        }

        detailsContent.innerHTML = '<div class="token-detail">' +
            '<div class="detail-header">' +
                '<div class="detail-reading">' + (reading || '') + '</div>' +
                '<div class="detail-surface">' + surface + '</div>' +
                '<div class="detail-base">Base: ' + base + '</div>' +
                (item.pos ? '<div style="margin-top:0.5rem; font-size:0.8rem; opacity:0.7">' + item.pos + '</div>' : '') +
            '</div>' +
            tagsHtml +
            meaningHtml +
            grammarHtml +
            conjugationHtml +
        '</div>';
    }
});
