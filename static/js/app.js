/**
 * IA DCI - Application JavaScript
 * Script principal pour l'interface utilisateur
 */

// Configuration injectée par le template (sera remplacée au chargement)
let rtlLanguages = [];
let fallbackModel = '';
let activeTab = 'translation';

// Références aux éléments du DOM
const form = document.getElementById('assistantForm');
const sourceLang = document.getElementById('source_lang');
const targetLang = document.getElementById('target_lang');
const modelSelect = document.getElementById('model');
const languageSelectors = document.getElementById('languageSelectors');

const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = {
    translation: document.getElementById('translationTab'),
    correction: document.getElementById('correctionTab'),
    reformulation: document.getElementById('reformulationTab'),
    summary: document.getElementById('summaryTab'),
};

const translationInput = document.getElementById('textInput');
const translationOutput = document.getElementById('translatedTextOutput');
const copyTranslationBtn = document.getElementById('copyTranslationBtn');

const correctionInput = document.getElementById('correctionInput');
const correctionOutput = document.getElementById('correctionOutput');
const correctionDiff = document.getElementById('correctionDiff');
const correctionExplanations = document.getElementById('correctionExplanations');
const correctionExplanationList = document.getElementById('correctionExplanationList');
const copyCorrectionBtn = document.getElementById('copyCorrectionBtn');

const reformulationInput = document.getElementById('reformulationInput');
const reformulationOutput = document.getElementById('reformulationOutput');
const reformulationHighlights = document.getElementById('reformulationHighlights');
const reformulationHighlightList = document.getElementById('reformulationHighlightList');
const copyReformulationBtn = document.getElementById('copyReformulationBtn');

const summaryInput = document.getElementById('summaryInput');
const summaryOutput = document.getElementById('summaryOutput');
const summaryDecisions = document.getElementById('summaryDecisions');
const summaryActions = document.getElementById('summaryActions');
const copySummaryBtn = document.getElementById('copySummaryBtn');

// Image upload elements
const imageUploadZone = document.getElementById('imageUploadZone');
const summaryImageInput = document.getElementById('summaryImageInput');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const imagePreview = document.getElementById('imagePreview');
const imageClearBtn = document.getElementById('imageClearBtn');
let summaryImageBase64 = null;

let rtlLanguageSet = new Set();

const submitButtons = {
    translation: document.getElementById('translateSubmitBtn'),
    correction: document.getElementById('correctionSubmitBtn'),
    reformulation: document.getElementById('reformulationSubmitBtn'),
    summary: document.getElementById('summarySubmitBtn'),
};

const progress = document.getElementById('progress');
const progressText = document.getElementById('progressText');
const errorDiv = document.getElementById('error');
const errorText = document.getElementById('errorText');

const progressMessages = {
    translation: 'Traduction en cours...',
    correction: 'Correction en cours...',
    reformulation: 'Reformulation en cours...',
    summary: 'Génération du compte rendu...',
};

const streamingMessages = {
    translation: 'L\'IA génère la traduction...',
    correction: 'L\'IA corrige le texte...',
    reformulation: 'L\'IA reformule le texte...',
    summary: 'L\'IA génère le compte rendu...',
};

// ============================================================================
// INITIALISATION - Configuration depuis le template
// ============================================================================

/**
 * Initialise l'application avec les données du template.
 * @param {Object} config - Configuration injectée depuis le template
 */
function initApp(config) {
    rtlLanguages = config.rtlLanguages || [];
    fallbackModel = config.defaultModel || '';
    rtlLanguageSet = new Set(Array.isArray(rtlLanguages) ? rtlLanguages : []);

    // Initialiser les gestionnaires
    setupTabHandlers();
    setupCopyHandlers();
    setupLanguageHandlers();
    setupImageUploadHandlers();
    setupFormHandler();
    setupScrollSync();
    loadModels();
}

// ============================================================================
// STREAMING HELPER - Affichage progressif des réponses
// ============================================================================

/**
 * Effectue une requête streaming et affiche les tokens progressivement.
 * @param {string} url - URL de l'endpoint streaming
 * @param {FormData} formData - Données du formulaire
 * @param {HTMLElement} outputElement - Élément où afficher les tokens (textarea ou div)
 * @param {Function} onComplete - Callback appelé à la fin avec le texte complet
 * @returns {Promise<string>} - Le texte complet généré
 */
async function streamRequest(url, formData, outputElement, onComplete) {
    const response = await fetch(url, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Erreur de streaming');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    // Réinitialiser l'output
    if (outputElement.tagName === 'TEXTAREA') {
        outputElement.value = '';
    } else {
        outputElement.textContent = '';
    }

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();

                    if (data === '[DONE]') {
                        if (onComplete) {
                            onComplete(fullText);
                        }
                        return fullText;
                    }

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.error) {
                            throw new Error(parsed.error);
                        }
                        if (parsed.token) {
                            fullText += parsed.token;
                            // Mise à jour progressive de l'affichage
                            if (outputElement.tagName === 'TEXTAREA') {
                                outputElement.value = fullText;
                                // Auto-scroll vers le bas
                                outputElement.scrollTop = outputElement.scrollHeight;
                            } else {
                                outputElement.textContent = fullText;
                                outputElement.scrollTop = outputElement.scrollHeight;
                            }
                        }
                    } catch (e) {
                        if (e.message && !e.message.includes('JSON')) {
                            throw e;
                        }
                        // Ignorer les erreurs de parsing JSON (lignes incomplètes)
                    }
                }
            }
        }
    } finally {
        reader.releaseLock();
    }

    if (onComplete) {
        onComplete(fullText);
    }
    return fullText;
}

// ============================================================================
// TAB HANDLERS
// ============================================================================

function setupTabHandlers() {
    tabButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const tab = button.dataset.tab;
            if (tab === activeTab) {
                return;
            }

            activeTab = tab;

            tabButtons.forEach((btn) => {
                btn.classList.toggle('active', btn.dataset.tab === tab);
                btn.setAttribute('aria-selected', btn.dataset.tab === tab ? 'true' : 'false');
            });

            Object.entries(tabContents).forEach(([key, content]) => {
                content.classList.toggle('active', key === tab);
            });

            errorDiv.style.display = 'none';
            progress.style.display = 'none';

            const requiresLanguages = tab === 'translation';
            languageSelectors.style.display = requiresLanguages ? 'grid' : 'none';
        });
    });
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function renderList(container, items) {
    container.innerHTML = '';
    if (!items || !items.length) {
        return;
    }

    const fragment = document.createDocumentFragment();
    items.forEach((item) => {
        const li = document.createElement('li');
        // Handle both string items and object items (e.g., {change, impact})
        if (typeof item === 'string') {
            li.textContent = item;
        } else if (typeof item === 'object' && item !== null) {
            // Format object fields nicely
            const parts = [];
            if (item.change) parts.push(item.change);
            if (item.impact) parts.push(`Impact: ${item.impact}`);
            if (item.text) parts.push(item.text);
            if (item.description) parts.push(item.description);
            li.textContent = parts.length > 0 ? parts.join(' — ') : JSON.stringify(item);
        } else {
            li.textContent = String(item);
        }
        fragment.appendChild(li);
    });
    container.appendChild(fragment);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// IMAGE UPLOAD HANDLERS
// ============================================================================

function handleImageFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const base64Data = e.target.result;
        // Extract just the base64 part (remove data:image/...;base64, prefix)
        summaryImageBase64 = base64Data.split(',')[1];

        imagePreview.src = base64Data;
        imagePreviewContainer.classList.add('visible');
        imageUploadZone.classList.add('has-image');
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    summaryImageBase64 = null;
    imagePreview.src = '';
    imagePreviewContainer.classList.remove('visible');
    imageUploadZone.classList.remove('has-image');
    summaryImageInput.value = '';
}

function setupImageUploadHandlers() {
    // Click to upload
    imageUploadZone.addEventListener('click', (e) => {
        if (e.target === imageClearBtn || e.target.closest('.image-clear-btn')) {
            return;
        }
        summaryImageInput.click();
    });

    // File input change
    summaryImageInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleImageFile(e.target.files[0]);
        }
    });

    // Clear button
    imageClearBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        clearImage();
    });

    // Drag and drop
    imageUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        imageUploadZone.classList.add('drag-over');
    });

    imageUploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        imageUploadZone.classList.remove('drag-over');
    });

    imageUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        imageUploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleImageFile(e.dataTransfer.files[0]);
        }
    });
}

// ============================================================================
// DIFF GENERATION
// ============================================================================

/**
 * Génère un HTML de diff entre le texte original et le texte corrigé.
 * Utilise une approche mot par mot pour surligner les différences.
 */
function generateDiffHtml(original, corrected) {
    // Tokeniser les textes en mots et espaces
    const tokenize = (text) => {
        const tokens = [];
        let current = '';
        for (const char of text) {
            if (/\s/.test(char)) {
                if (current) tokens.push({ type: 'word', value: current });
                tokens.push({ type: 'space', value: char });
                current = '';
            } else {
                current += char;
            }
        }
        if (current) tokens.push({ type: 'word', value: current });
        return tokens;
    };

    const originalTokens = tokenize(original);
    const correctedTokens = tokenize(corrected);

    // Extraire uniquement les mots pour la comparaison LCS
    const origWords = originalTokens.filter(t => t.type === 'word').map(t => t.value);
    const corrWords = correctedTokens.filter(t => t.type === 'word').map(t => t.value);

    // Algorithme LCS (Longest Common Subsequence)
    const m = origWords.length;
    const n = corrWords.length;
    const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (origWords[i - 1].toLowerCase() === corrWords[j - 1].toLowerCase()) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    // Backtrack pour trouver les différences
    let i = m, j = n;
    const operations = [];

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && origWords[i - 1].toLowerCase() === corrWords[j - 1].toLowerCase()) {
            operations.unshift({ type: 'same', orig: origWords[i - 1], corr: corrWords[j - 1] });
            i--; j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            operations.unshift({ type: 'add', corr: corrWords[j - 1] });
            j--;
        } else {
            operations.unshift({ type: 'del', orig: origWords[i - 1] });
            i--;
        }
    }

    // Générer le HTML
    let html = '';
    for (const op of operations) {
        if (op.type === 'same') {
            html += `<span>${escapeHtml(op.corr)}</span> `;
        } else if (op.type === 'del') {
            html += `<span class="diff-deleted">${escapeHtml(op.orig)}</span> `;
        } else if (op.type === 'add') {
            html += `<span class="diff-added">${escapeHtml(op.corr)}</span> `;
        }
    }

    return html.trim();
}

// ============================================================================
// LANGUAGE HANDLERS
// ============================================================================

function updateLanguageDirection() {
    const sourceIsRTL = rtlLanguageSet.has(sourceLang.value);
    const targetIsRTL = rtlLanguageSet.has(targetLang.value);

    translationInput.dir = sourceIsRTL ? 'rtl' : 'ltr';
    translationInput.classList.toggle('rtl-support', sourceIsRTL);

    translationOutput.dir = targetIsRTL ? 'rtl' : 'ltr';
    translationOutput.classList.toggle('rtl-support', targetIsRTL);
}

function updateTargetLanguageOptions() {
    const selectedSource = sourceLang.value;
    const currentTarget = targetLang.value;

    // Masquer/afficher les options selon la langue source
    Array.from(targetLang.options).forEach(option => {
        if (option.value === selectedSource) {
            option.hidden = true;
            option.disabled = true;
        } else {
            option.hidden = false;
            option.disabled = false;
        }
    });

    // Si la langue cible actuelle est la même que la source, sélectionner une autre
    if (currentTarget === selectedSource) {
        const firstAvailable = Array.from(targetLang.options).find(
            opt => opt.value !== selectedSource && !opt.hidden
        );
        if (firstAvailable) {
            targetLang.value = firstAvailable.value;
        }
    }

    updateLanguageDirection();
}

function setupLanguageHandlers() {
    sourceLang.addEventListener('change', updateTargetLanguageOptions);
    targetLang.addEventListener('change', updateLanguageDirection);
    updateTargetLanguageOptions(); // Initialiser au chargement
}

// ============================================================================
// COPY HANDLERS
// ============================================================================

function showCopyFeedback(button) {
    const original = button.textContent;
    button.textContent = '✅ Copié !';
    setTimeout(() => {
        button.textContent = original;
    }, 1500);
}

async function copyToClipboard(text, button) {
    if (!text) {
        return;
    }
    try {
        await navigator.clipboard.writeText(text);
        showCopyFeedback(button);
    } catch (err) {
        console.warn('Impossible de copier le texte', err);
    }
}

function setupCopyHandlers() {
    copyTranslationBtn.addEventListener('click', () => copyToClipboard(translationOutput.value, copyTranslationBtn));
    copyCorrectionBtn.addEventListener('click', () => copyToClipboard(correctionOutput.value, copyCorrectionBtn));
    copyReformulationBtn.addEventListener('click', () => copyToClipboard(reformulationOutput.value, copyReformulationBtn));
    copySummaryBtn.addEventListener('click', () => copyToClipboard(summaryOutput.value, copySummaryBtn));
}

// ============================================================================
// JSON PARSING
// ============================================================================

/**
 * Parse une réponse JSON potentiellement enveloppée dans du markdown.
 */
function parseJsonResponse(rawText) {
    // Essayer d'extraire un bloc ```json ... ```
    const jsonBlockMatch = rawText.match(/```json\s*([\s\S]*?)\s*```/);
    if (jsonBlockMatch) {
        try {
            return JSON.parse(jsonBlockMatch[1].trim());
        } catch (e) { }
    }

    // Essayer de trouver un objet JSON dans le texte
    const braceStart = rawText.indexOf('{');
    if (braceStart !== -1) {
        let depth = 0;
        let inString = false;
        let escapeNext = false;

        for (let i = braceStart; i < rawText.length; i++) {
            const char = rawText[i];

            if (escapeNext) {
                escapeNext = false;
                continue;
            }
            if (char === '\\') {
                escapeNext = true;
                continue;
            }
            if (char === '"') {
                inString = !inString;
            } else if (!inString) {
                if (char === '{') depth++;
                else if (char === '}') {
                    depth--;
                    if (depth === 0) {
                        try {
                            return JSON.parse(rawText.slice(braceStart, i + 1));
                        } catch (e) { }
                        break;
                    }
                }
            }
        }
    }

    // Fallback: essayer de parser directement
    try {
        return JSON.parse(rawText.trim());
    } catch (e) {
        return null;
    }
}

// ============================================================================
// FORM HANDLER
// ============================================================================

function setupFormHandler() {
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        errorDiv.style.display = 'none';

        const activeButton = submitButtons[activeTab];
        if (!activeButton) {
            return;
        }

        activeButton.disabled = true;
        progressText.textContent = streamingMessages[activeTab] || progressMessages[activeTab] || 'Traitement en cours...';
        progress.style.display = 'block';

        try {
            const formData = new FormData();
            if (modelSelect.value) {
                formData.append('model', modelSelect.value);
            }

            switch (activeTab) {
                case 'translation': {
                    formData.append('text', translationInput.value);
                    formData.append('source_lang', sourceLang.value);
                    formData.append('target_lang', targetLang.value);

                    // Utiliser le streaming pour la traduction
                    await streamRequest(
                        '/translate-text-stream',
                        formData,
                        translationOutput
                    );
                    break;
                }
                case 'correction': {
                    formData.append('text', correctionInput.value);

                    // Streaming : afficher le JSON brut pendant la génération
                    // puis parser à la fin pour extraire les données structurées
                    const rawResponse = await streamRequest(
                        '/correct-text-stream',
                        formData,
                        correctionOutput  // Affiche temporairement dans le textarea caché
                    );

                    // Parser le JSON une fois le streaming terminé
                    const data = parseJsonResponse(rawResponse);
                    if (data) {
                        const correctedText = data.corrected_text || '';
                        correctionOutput.value = correctedText;

                        // Générer et afficher le diff avec surlignage
                        const originalText = correctionInput.value;
                        correctionDiff.innerHTML = generateDiffHtml(originalText, correctedText);

                        renderList(correctionExplanationList, data.explanations || []);
                        correctionExplanations.style.display = (data.explanations && data.explanations.length) ? 'block' : 'none';
                    } else {
                        // Si le parsing échoue, afficher le texte brut
                        correctionDiff.textContent = rawResponse;
                        correctionExplanations.style.display = 'none';
                    }
                    break;
                }
                case 'reformulation': {
                    formData.append('text', reformulationInput.value);

                    // Streaming avec parsing JSON à la fin
                    const rawResponse = await streamRequest(
                        '/reformulate-text-stream',
                        formData,
                        reformulationOutput
                    );

                    const data = parseJsonResponse(rawResponse);
                    if (data) {
                        reformulationOutput.value = data.reformulated_text || rawResponse;
                        renderList(reformulationHighlightList, data.highlights || []);
                        reformulationHighlights.style.display = (data.highlights && data.highlights.length) ? 'block' : 'none';
                    } else {
                        reformulationHighlights.style.display = 'none';
                    }
                    break;
                }
                case 'summary': {
                    formData.append('text', summaryInput.value);

                    // Include image if uploaded
                    if (summaryImageBase64) {
                        formData.append('image_base64', summaryImageBase64);
                    }

                    // Streaming avec parsing JSON à la fin
                    const rawResponse = await streamRequest(
                        '/meeting-summary-stream',
                        formData,
                        summaryOutput
                    );

                    const data = parseJsonResponse(rawResponse);
                    if (data) {
                        summaryOutput.value = data.summary || rawResponse;
                        renderList(summaryDecisions, data.decisions || []);
                        renderList(summaryActions, data.action_items || []);
                    }

                    // Clear image after successful processing
                    clearImage();
                    break;
                }
                default:
                    throw new Error('Onglet inconnu');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            activeButton.disabled = false;
            progress.style.display = 'none';
        }
    });
}

function showError(message) {
    errorText.textContent = message;
    errorDiv.style.display = 'block';
}

// ============================================================================
// SCROLL SYNC
// ============================================================================

/**
 * Synchronise le défilement entre deux éléments scrollables.
 */
function setupScrollSync() {
    function syncScroll(element1, element2) {
        let syncing = false;

        function sync(source, target) {
            if (syncing) return;
            syncing = true;
            const maxScroll = source.scrollHeight - source.clientHeight;
            const ratio = maxScroll > 0 ? source.scrollTop / maxScroll : 0;
            const targetMaxScroll = target.scrollHeight - target.clientHeight;
            target.scrollTop = ratio * targetMaxScroll;
            syncing = false;
        }

        element1.addEventListener('scroll', () => sync(element1, element2));
        element2.addEventListener('scroll', () => sync(element2, element1));
    }

    // Synchronisation pour la traduction
    syncScroll(translationInput, translationOutput);

    // Synchronisation pour la correction (textarea input et div diff)
    syncScroll(correctionInput, correctionDiff);
}

// ============================================================================
// MODEL LOADING
// ============================================================================

async function loadModels() {
    // Descriptions des modèles pour aider l'utilisateur
    const modelDescriptions = {
        'ministral': '⚡ Le plus rapide',
        'magistral': '✨ Le plus qualitatif mais plus lent',
    };

    function getModelLabel(modelName) {
        const lowerName = modelName.toLowerCase();
        for (const [key, desc] of Object.entries(modelDescriptions)) {
            if (lowerName.includes(key)) {
                return `${modelName} - ${desc}`;
            }
        }
        return modelName;
    }

    try {
        const response = await fetch('/models');
        if (!response.ok) {
            throw new Error('HTTP error');
        }

        const data = await response.json();
        const models = Array.isArray(data.models) ? data.models : [];
        const defaultModel = data.default_model || fallbackModel;

        let uniqueModels = Array.from(new Set(models.filter(Boolean)));
        uniqueModels.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));

        if (defaultModel) {
            uniqueModels = [defaultModel, ...uniqueModels.filter((modelName) => modelName !== defaultModel)];
        }

        if (!uniqueModels.length && defaultModel) {
            uniqueModels = [defaultModel];
        }

        modelSelect.innerHTML = '';
        uniqueModels.forEach((modelName) => {
            const option = document.createElement('option');
            option.value = modelName;
            option.textContent = getModelLabel(modelName);
            if (modelName === defaultModel) {
                option.selected = true;
            }
            modelSelect.appendChild(option);
        });
    } catch (error) {
        console.warn('Impossible de récupérer la liste des modèles Ollama', error);
        if (!modelSelect.options.length) {
            const option = document.createElement('option');
            option.value = fallbackModel;
            option.textContent = getModelLabel(fallbackModel);
            modelSelect.appendChild(option);
        }
    }
}
