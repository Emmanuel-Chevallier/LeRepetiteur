// The DEFAULT_PROMPT_GEN is around line 614.

// This replace call is ONLY for DEFAULT_PROMPT_GEN typo fix. I will do HTML/JS in next calls for safety.



const DEFAULT_PROMPT_GRADING = `Rôle : Correcteur. Utilisez LaTeX pour les formules mathématiques.

Attitude :
- Soyez ferme lorsque la réponse est clairement fausse.
- Si la question est un peu vague, tolérez que la réponse le soit aussi.
- Si la réponse n'est pas fausse mais incomplète, vous pouvez fermer les yeux si seuls des détails manquent.

Contexte :
Questions Originales (LaTeX) :
{latex_context}
{course_context_injection}

Soumission de l'étudiant (Texte/Scan) :
{student_submission}

Tâche :
1. Transcrire les réponses.
2. Noter sur 20.
3. Fournir des commentaires (dans la langue originale du cours, suivis d'une traduction en français si ce n'est pas le français).

Sortie JSON :
{
    "grades": [{
        "question_number": 1,
        "question_text": "Texte original...",
        "transcription": "Transcription LITTÉRALE de ce que l'étudiant a écrit pour cette question spécifique (OCR).",
        "score": 4,
        "feedback": "Commentaires détaillés..."
    }],
    "total_score": 15
}`;

const DEFAULT_PROMPT_SUMMARY = `Rôle : Professeur Principal.
Tâche : Rédiger une courte synthèse globale de la classe basée sur ces résultats.

Statistiques :
- Nombre : {count} étudiants
- Moyenne : {avg}/20

Concepts mal compris fréquents :
{weak_points}

Format de sortie : Markdown. Soyez encourageant mais précis.`;

// --- Init ---
async function loadCourses() {
    // Init Default Prompts references in UI if empty
    if (!document.getElementById('genPromptInput').value) document.getElementById('genPromptInput').value = DEFAULT_PROMPT_GEN;
    if (!document.getElementById('gradingPromptInput').value) document.getElementById('gradingPromptInput').value = DEFAULT_PROMPT_GRADING;
    if (document.getElementById('summaryPromptInput') && !document.getElementById('summaryPromptInput').value) document.getElementById('summaryPromptInput').value = DEFAULT_PROMPT_SUMMARY;

    try {
        console.log("Fetching courses...");
        alert("DEBUG: Starting fetch courses...");
        const res = await fetch('/api/courses?_t=' + Date.now());
        console.log("Courses response status:", res.status);
        alert("DEBUG: Fetch status: " + res.status);
        const courses = await res.json();
        console.log("Courses loaded:", courses);
        alert("DEBUG: Loaded " + courses.length + " courses");

        // Populate Main Course Selector AND Force Selector
        const select = document.getElementById('courseSelector');
        const forceSelect = document.getElementById('forceCourseId');

        select.innerHTML = '<option value="">Sélectionner un cours...</option>';
        // Keep default option for force select (Detection Auto)

        courses.forEach(c => {
            // 1. Main Selector
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.innerText = `${c.title} (${c.id})`;
            opt.dataset.course = JSON.stringify(c);
            select.appendChild(opt);

            // 2. Force Selector
            if (forceSelect) {
                const opt2 = document.createElement('option');
                opt2.value = c.id;
                opt2.innerText = `${c.title}`;
                forceSelect.appendChild(opt2);
            }
        });
    } catch (e) {
        console.error("Error loading courses:", e);
    }
}
// --- Smart Grading Queue Logic ---
let pendingFiles = [];
let summaryContext = { courseId: null, quizNum: null };

function addToQueue(fileList) {
    if (!fileList || fileList.length === 0) return;

    for (let f of fileList) {
        // Determine unique ID or just object ref
        // Add status property wrapper
        pendingFiles.push({ file: f, status: 'waiting', result: null });
    }
    renderQueue();
    // Reset input so same file can be selected again if cleared
    document.getElementById('smartScanUpload').value = '';
}

function renderQueue() {
    const list = document.getElementById('scanQueue');
    const btn = document.getElementById('btnProcess');
    list.innerHTML = '';

    if (pendingFiles.length === 0) {
        list.innerHTML = '<li style="padding: 0.5rem; color: #6b7280; text-align: center;">Aucun fichier.</li>';
        btn.disabled = true;
        return;
    }

    btn.disabled = false; // Enable if files exist (and not all processed?) 
    // Better: Enable if at least one is 'waiting'.
    const hasWaiting = pendingFiles.some(item => item.status === 'waiting');
    btn.disabled = !hasWaiting;

    pendingFiles.forEach((item, index) => {
        const li = document.createElement('li');
        li.style.padding = '0.5rem';
        li.style.borderBottom = '1px solid #f3f4f6';
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.alignItems = 'center';

        let statusIcon = '⏳';
        let statusColor = '#6b7280';
        let details = '';

        if (item.status === 'processing') {
            statusIcon = '🔄';
            statusColor = '#2563eb';
            // Add progress message if available
            if (item.progressMessage) {
                details = `<br><small style="color:#2563eb">${item.progressMessage}</small>`;
            }
        }
        else if (item.status === 'done') { statusIcon = '✅'; statusColor = '#059669'; }
        else if (item.status === 'error') { statusIcon = '❌'; statusColor = '#dc2626'; }

        let finalDetails = details;
        if (item.status === 'done' && item.result) {
            finalDetails = `<br><small style="color:#666">👤 ${item.result.student || '?'} | 📝 Quiz #${item.result.quiz || '?'}</small>`;
        }
        else if (item.status === 'error') {
            finalDetails = `<br><small style="color:red">${item.error || 'Erreur inconnue'}</small>`;
        }

        li.innerHTML = `
                    <span>${item.file.name}${finalDetails}</span>
                    <span style="color:${statusColor}; font-weight:bold;">${statusIcon} ${item.status}</span>
                `;
        list.appendChild(li);
    });
}

async function processQueue() {
    const resDiv = document.getElementById('gradeResult');
    const summaryBtn = document.getElementById('btnSummary');

    // Disable button during process
    document.getElementById('btnProcess').disabled = true;

    for (let i = 0; i < pendingFiles.length; i++) {
        const item = pendingFiles[i];
        if (item.status !== 'waiting') continue;

        item.status = 'processing';
        renderQueue();

        const fd = new FormData();
        fd.append('file', item.file);

        // Add Grading Config
        const customGradingPrompt = document.getElementById('gradingPromptInput').value;
        const includeContext = document.getElementById('includeContextCheck').checked;
        const isBulk = true; // Forced as per V6 requirement
        const quizNumOverride = document.getElementById('forceQuizNumber').value;
        const courseOverride = document.getElementById('forceCourseId').value;
        const pagesPerCopy = document.getElementById('pagesPerCopy').value;

        if (customGradingPrompt.trim() !== "") {
            fd.append('custom_prompt', customGradingPrompt);
        }
        if (quizNumOverride && quizNumOverride.trim() !== "") {
            fd.append('override_quiz_number', quizNumOverride);
        }
        if (courseOverride && courseOverride.trim() !== "") {
            fd.append('override_course_id', courseOverride);
        }
        fd.append('pages_per_copy', pagesPerCopy);
        fd.append('include_context', includeContext);
        fd.append('is_bulk', isBulk);

        try {
            const res = await fetch('/api/grading/smart', { method: 'POST', body: fd });

            // Handle Streaming Response (NDJSON)
            if (res.headers.get('content-type') && res.headers.get('content-type').includes('application/x-ndjson')) {
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // Keep incomplete line

                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const msg = JSON.parse(line);
                            if (msg.type === 'progress') {
                                item.status = 'processing';
                                item.progressMessage = msg.message;
                                renderQueue();
                            } else if (msg.type === 'result') {
                                // Final Result (Bulk)
                                item.status = 'done';
                                item.progressMessage = null;

                                // Bulk Results in msg.results or Single Msg?
                                if (msg.results) {
                                    const count = msg.results.length;
                                    const successCount = msg.results.filter(r => !r.error).length;
                                    item.result = { student: `Multi-pages (${successCount}/${count})`, quiz: 'Lots' };

                                    // Context extract
                                    const firstSuccess = msg.results.find(r => !r.error);
                                    if (firstSuccess && firstSuccess.raw_course_id && firstSuccess.quiz) {
                                        summaryContext.courseId = firstSuccess.raw_course_id;
                                        summaryContext.quizNum = firstSuccess.quiz;
                                    }
                                } else {
                                    // Single file result wrapped in stream?
                                    item.result = msg.result || msg;
                                }
                                renderQueue();
                            }
                        } catch (e) {
                            console.error("Stream Parse Error", e);
                        }
                    }
                }
            } else {
                // Fallback Standard JSON
                const data = await res.json();
                if (res.ok) {
                    item.status = 'done';
                    item.result = data.result;
                    if (data.result && data.result.raw_course_id && data.result.quiz) {
                        summaryContext.courseId = data.result.raw_course_id;
                        summaryContext.quizNum = data.result.quiz;
                    }
                } else {
                    item.status = 'error';
                    item.error = data.detail || "Erreur inconnue";
                }
            }
        } catch (e) {
            item.status = 'error';
            console.error(e);
        }
        renderQueue();
    }

    // Restore context from any done item if missing
    if (!summaryContext.courseId || !summaryContext.quizNum) {
        for (let j = 0; j < pendingFiles.length; j++) {
            const doneItem = pendingFiles[j];
            if (doneItem.status === 'done' && doneItem.result && doneItem.result.raw_course_id && doneItem.result.quiz) {
                summaryContext.courseId = doneItem.result.raw_course_id;
                summaryContext.quizNum = doneItem.result.quiz;
                break; // Found one, that's enough
            }
        }
    }

    // Check if we can enable summary section
    if (summaryContext.courseId && summaryContext.quizNum) {
        const summarySection = document.getElementById('summarySection');
        if (summarySection) {
            summarySection.style.display = 'block';
            // Update button text to be sure
            const btn = document.getElementById('btnSummary');
            if (btn) btn.innerText = `✨ Générer Rapport Global (Quiz #${summaryContext.quizNum})`;
        }
    }

    document.getElementById('btnProcess').disabled = false;
}

// Re-render to enable button if user adds more files?
renderQueue();
// Note: renderQueue() enables button if 'waiting' items exist. 
// So if I add files during processing, it might look weird, but acceptable.

// Also refresh gradebook if enabled
if (typeof loadGradebook === "function") {
    // If we have a course ID selected in dropdown, refresh it.
    // Or if the corrected quiz belongs to the selected course.
    const currentSel = document.getElementById('courseSelector').value;
    if (currentSel && currentSel === summaryContext.courseId) {
        loadGradebook();
    }
}
// End processQueue logic and helper check

function togglePromptEditor() {
    const div = document.getElementById('promptEditor');
    div.style.display = div.style.display === 'none' ? 'block' : 'none';
}

function toggleGradingConfig() {
    const div = document.getElementById('gradingConfig');
    div.style.display = div.style.display === 'none' ? 'block' : 'none';
}

function toggleGenPromptEditor() {
    const div = document.getElementById('genPromptEditor');
    div.style.display = div.style.display === 'none' ? 'block' : 'none';
}

async function generateQuizzes() {
    const courseId = document.getElementById('courseSelector').value;
    if (!courseId) {
        alert("Veuillez sélectionner un cours.");
        return;
    }

    document.getElementById('genStatus').innerText = "Génération en cours... (Patientez)";

    // Capture custom prompt
    const promptInput = document.getElementById('genPromptInput');
    const customPrompt = promptInput ? promptInput.value : null;

    try {
        const res = await fetch(`/api/courses/${courseId}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_prompt: customPrompt })
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById('genStatus').innerText = `✅ Génération terminée ! ${data.quizzes ? data.quizzes.length : ''} pdfs créés.`;
            loadGradebook(); // Refresh list to see new quizzes?
        } else {
            document.getElementById('genStatus').innerText = "❌ Erreur: " + data.detail;
        }
    } catch (e) {
        console.error(e);
        document.getElementById('genStatus').innerText = "❌ Erreur technique.";
    }
}


// Retrying with correct function content
async function generateReport() {
    if (!summaryContext.courseId || !summaryContext.quizNum) return;

    const resDiv = document.getElementById('gradeResult');
    resDiv.style.display = 'block';
    resDiv.innerHTML = "<div>🤖 Génération du résumé...</div>";

    const promptInput = document.getElementById('summaryPromptInput');
    // Only send if the editor is visible, OR just always send the value if the user modified it?
    // Let's send it if the editor is visible.
    const isEditorVisible = document.getElementById('promptEditor').style.display !== 'none';
    const customPrompt = isEditorVisible ? promptInput.value : null;

    try {
        const sumRes = await fetch(`/api/courses/${summaryContext.courseId}/quizzes/${summaryContext.quizNum}/summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_prompt: customPrompt })
        });
        const sumData = await sumRes.json();

        if (sumRes.ok) {
            resDiv.innerHTML = `<h3>📝 Résumé Global</h3><div style="background:white; padding:1rem; border:1px solid #ccc">${sumData.summary_html || sumData.summary}</div>`;
        } else {
            resDiv.innerHTML = `<div style="color:red">Erreur Résumé: ${sumData.detail}</div>`;
        }
    } catch (e) {
        resDiv.innerHTML = `<div style="color:red">Erreur Résumé: ${e.message}</div>`;
    }
}

function toggleSummaryPrompt() {
    const div = document.getElementById('summaryPromptConfig');
    div.style.display = div.style.display === 'none' ? 'block' : 'none';
}

// --- DEPLOYMENT ---
// --- DEPLOYMENT ---
async function deployToUniversity(mode = 'smart') {
    const label = mode === 'smart' ? 'Synchronisation Intelligente' : (mode === 'sftp' ? 'Serveur SFTP' : 'Synchronisation Complète');

    if (mode === 'sftp') {
        // SPECIAL FLOW FOR UNIVERSITY SERVER (Port Knocking)
        // 1. Open Page
        window.open("https://www.dil.univ-mrs.fr/portes/", "_blank");

        // 2. Ask Confirmation
        if (typeof openModal === 'function') {
            openModal(
                "🔒 Ouverture du Serveur requise",
                `Une page vient de s'ouvrir pour débloquer l'accès ("Port Knocking").<br>
                         1. Connectez-vous sur cette page.<br>
                         2. Attendez 5 secondes.<br>
                         3. Revenez ici et cliquez sur <strong>Valider</strong>.`,
                async () => await performDeploy(mode, label),
                "✅ Port Ouvert : Lancer Sync",
                "#16a34a" // Green
            );
        } else {
            // Fallback to simple confirm if modal isn't ready
            if (confirm("Une page s'est ouverte. L'avez-vous débloquée ?")) {
                await performDeploy(mode, label);
            }
        }
        return;
    }

    // STANDARD FLOW (Local)
    // Use Generic Modal
    if (typeof openModal === 'function') {
        openModal(
            "Confirmer le déploiement",
            `Lancer la <strong>${label}</strong> ?<br><br><small>Cela mettra à jour les données.</small>`,
            async () => await performDeploy(mode, label),
            "🚀 Déployer", // Custom Label
            "#2563eb" // Blue color
        );
    } else {
        alert("Erreur: Modale non chargée");
    }
}

async function performDeploy(mode, label) {
    const dropBtn = document.querySelector('.dropdown button.btn[style*="7c3aed"]');
    const originalText = dropBtn ? dropBtn.innerText : "🚀 Déployer ▼";

    if (dropBtn) {
        dropBtn.innerText = "⏳ En cours...";
        dropBtn.disabled = true;
    }

    showToast(`Déploiement en cours (${mode})...`, 'blue');

    try {
        const res = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode })
        });

        // --- STREAM HANDLING (SFTP) ---
        if (mode === 'sftp' && res.body) {
            // Open Log Modal (Reuse OpenModal mechanism but more persistent?)
            // Or reuse openModal content div? 
            // Let's create a custom overlay for Logs
            const logOverlay = document.createElement('div');
            logOverlay.style = "position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:11000; display:flex; align-items:center; justify-content:center; flex-direction:column;";
            logOverlay.innerHTML = `
                        <div style="background:#1e1e1e; color:#0f0; width:80%; height:80%; padding:20px; border-radius:8px; font-family:monospace; overflow-y:auto; white-space:pre-wrap;" id="liveLogContainer">Starting Sync...</div>
                        <button class="btn" onclick="this.parentElement.remove(); location.reload();" style="margin-top:20px; background:#dc2626;">Fermer & Rafraîchir</button>
                    `;
            document.body.appendChild(logOverlay);
            const container = document.getElementById('liveLogContainer');

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                container.innerText += chunk;
                container.scrollTop = container.scrollHeight;
            }

            container.innerText += "\n=== TERMINE ===";
            if (dropBtn) { dropBtn.innerText = originalText; dropBtn.disabled = false; }
            return;
        }

        // --- JSON HANDLING (Standard) ---
        if (res.ok) {
            const data = await res.json();
            if (data.message === "Nothing to sync.") {
                showToast("Tout est déjà à jour ! (Rien à envoyer)", "green");
            } else if (data.message === "Already up to date!") {
                showToast("Tout est déjà à jour ! (Smart Sync)", "green");
            } else {
                showToast(`Succès: ${data.message}`, "green");
                // details? data.details is object
                console.log(data);
            }
        } else {
            const err = await res.json();
            showToast(`Erreur: ${err.detail || "Erreur inconnue"}`, "red");
        }
    } catch (e) {
        console.error(e);
        showToast(`Erreur Réseau: ${e.message}`, "red");
    } finally {
        if (dropBtn) {
            dropBtn.innerText = originalText;
            dropBtn.disabled = false;
        }
    }
}

// --- GLOBAL STATE ---
function switchView() {
    const role = document.getElementById('userRole').value;
    document.getElementById('teacherView').style.display = role === 'teacher' ? 'block' : 'none';
    document.getElementById('studentView').style.display = role === 'student' ? 'block' : 'none';
}

// --- Event Listeners ---
const bulkCheck = document.getElementById('isBulkCheck');
if (bulkCheck) {
    bulkCheck.addEventListener('change', (e) => {
        const container = document.getElementById('pagesPerCopyContainer');
        if (container) container.style.display = e.target.checked ? 'block' : 'none';
    });
}

// Trigger once on load
if (bulkCheck && bulkCheck.checked) {
    const container = document.getElementById('pagesPerCopyContainer');
    if (container) container.style.display = 'block';
}

// document.getElementById('btnProcess').addEventListener('click', processQueue);

// NEW: Student Management (Table)
async function createStudentsBatch() {
    const startId = document.getElementById('batchStartId').value;
    const count = document.getElementById('batchCount').value;

    if (!startId || !count) {
        alert("Veuillez remplir le numéro de départ et le nombre d'étudiants.");
        return;
    }

    try {
        const res = await fetch('/api/students/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start_id: parseInt(startId), count: parseInt(count) })
        });
        const data = await res.json();

        if (res.ok) {
            alert(`Terminé ! Créés: ${data.created}, Ignorés (déjà existants): ${data.skipped}`);
            loadStudentsGlobal();
            document.getElementById('batchStartId').value = '';
            document.getElementById('batchCount').value = '';
        } else {
            alert("Erreur: " + data.detail);
        }
    } catch (e) {
        console.error(e);
        alert("Erreur réseau");
    }
}

async function loadStudentsGlobal() {
    const tbody = document.getElementById('studentTableBody');
    if (!tbody) return;

    try {
        const students = await (await fetch(`/api/students?_t=${Date.now()}`)).json();
        tbody.innerHTML = '';

        if (students.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1rem;">Aucun étudiant.</td></tr>';
            return;
        }

        // Sort
        students.sort((a, b) => a.id.localeCompare(b.id));

        students.forEach(s => {
            const tr = document.createElement('tr');
            const passDisplay = s.password ? `<code style="background:#e0e7ff; padding:2px 4px; border-radius:3px;">${s.password}</code>` : '<span style="color:#9ca3af; font-style:italic;">Aucun</span>';

            tr.innerHTML = `
                        <td style="padding:8px; border:1px solid #e5e7eb; text-align:center;">${s.id}</td>
                        <td style="padding:8px; border:1px solid #e5e7eb; text-align:center;">${s.name}</td>
                        <td style="padding:8px; border:1px solid #e5e7eb; text-align:center;">${passDisplay}</td>
                        <td style="padding:8px; border:1px solid #e5e7eb; text-align:center;">
                            <button type="button" class="delete-student-btn" data-sid="${s.id}" style="background:#ef4444; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">Supprimer</button>
                        </td>
                    `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Erreur chargement étudiants:", e);
        tbody.innerHTML = '<tr><td colspan="4" style="color:red; text-align:center;">Erreur de chargement.</td></tr>';
    }
}

async function addStudent() {
    const idInput = document.getElementById('newStudentId');
    const sid = idInput.value;

    if (!sid || sid.length !== 4 || isNaN(sid)) {
        alert("L'ID doit comporter exactement 4 chiffres.");
        return;
    }

    try {
        const res = await fetch('/api/students', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: sid })
        });

        if (res.ok) {
            idInput.value = "";
            loadStudentsGlobal();
        } else {
            const err = await res.json();
            alert("Erreur: " + err.detail);
        }
    } catch (e) {
        alert("Erreur réseau: " + e.message);
    }
}

window.removeStudent = async function (sid) {
    // DEBUG ALERT
    alert("DEBUG: Début suppression pour " + sid);

    if (!confirm(`Confirmer la suppression de ${sid} ?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/students/${sid}`, { method: 'DELETE' });

        if (res.ok) {
            alert("Candidat supprimé avec succès !");
            await loadStudentsGlobal();
        } else {
            const err = await res.json();
            alert("Erreur Serveur: " + (err.detail || "Inconnue"));
        }
    } catch (e) {
        alert("Erreur Technique: " + e.message);
    }
}

async function generatePasswords() {
    console.log("Starting Password Generation...");
    if (!confirm("Générer des mots de passe pour les étudiants qui n'en ont pas ?")) return;

    const btn = document.querySelector('button[onclick="generatePasswords()"]');
    const originalText = btn ? btn.innerText : "🔑 Générer les";
    if (btn) {
        btn.innerText = "⏳ Génération...";
        btn.disabled = true;
    }

    try {
        console.log("Sending POST request...");
        const res = await fetch('/api/students/passwords/generate', { method: 'POST' });

        if (!res.ok) {
            throw new Error(`Erreur Serveur: ${res.status}`);
        }

        const data = await res.json();
        console.log("Response:", data);
        alert(data.message || "Génération terminée.");
        await loadStudentsGlobal();
    } catch (e) {
        console.error(e);
        alert("Erreur génération: " + e.message);
    } finally {
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    }
}

async function createCourse() {
    const name = document.getElementById('newCourseTitle').value;
    if (!name) return alert("Nom required");

    await fetch('/api/courses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    loadCourses();
    document.getElementById('newCourseTitle').value = '';
}

async function loadCourseDetails() {
    const select = document.getElementById('courseSelector');
    const courseId = select.value;
    alert("DEBUG: loadCourseDetails called. ID=" + courseId);
    const details = document.getElementById('courseDetails');

    if (!courseId) {
        details.style.display = 'none';
        return;
    }

    // Fetch fresh course data
    const courses = await (await fetch('/api/courses')).json();
    const course = courses.find(c => c.id === courseId);

    if (!course) {
        alert("Erreur: Cours introuvable.");
        return;
    }

    details.style.display = 'block';

    // Populate Settings
    // Populate Settings
    document.getElementById('startLine').value = course.start_line || 0;
    document.getElementById('endLine').value = course.end_line || '';

    // Populate Prompts (Check default fallbacks if empty in DB)
    document.getElementById('genPromptInput').value = course.custom_prompt || DEFAULT_PROMPT_GEN;
    document.getElementById('gradingPromptInput').value = course.custom_grading_prompt || DEFAULT_PROMPT_GRADING;
    // Summary prompt if exists
    const summaryInput = document.getElementById('summaryPromptInput');
    if (summaryInput) {
        summaryInput.value = course.custom_summary_prompt || DEFAULT_PROMPT_SUMMARY;
    }

    // Update Next Quiz Label
    const nextNum = (course.quiz_count || 0) + 1;
    document.getElementById('nextQuizLabel').innerText = `(Prochain: Quiz #${nextNum})`;

    // Load Students Checklist
    const allStudents = await (await fetch('/api/students')).json();
    const enrolled = course.enrolled_students || [];

    const listDiv = document.getElementById('studentChecklist');
    listDiv.innerHTML = '';

    if (allStudents.length === 0) {
        listDiv.innerHTML = '<i>Aucun étudiant dans la base.</i>';
    }

    allStudents.forEach(s => {
        const div = document.createElement('div');
        const isChecked = enrolled.includes(s.id) ? 'checked' : '';
        div.innerHTML = `
                    <label style="display:block; cursor:pointer;">
                        <input type="checkbox" value="${s.id}" ${isChecked}> 
                        Candidat #${s.id}
                    </label>`;
        listDiv.appendChild(div);
    });

    // Show Current File
    const currentFileDiv = document.getElementById('currentLatexFile');
    if (course.latex_file_path) {
        const parts = course.latex_file_path.split(/[/\\]/);
        const filename = parts[parts.length - 1];
        currentFileDiv.innerText = `Fichier actuel : ${filename}`;
    } else {
        currentFileDiv.innerText = "Aucun fichier source ajouté.";
    }

    // Load Gradebook
    loadGradebook();
}


async function updateEnrollments() {
    // ... existing implementation
    const courseId = document.getElementById('courseSelector').value;
    // ...
    // (Not changing this logic, just ensuring structure is correct)
    // But replace_file_content needs to replace the broken mess. 
    // I will replace from line 301 to 384 with the corrected function.
}

async function saveSpecificPrompt(type) {
    const courseId = document.getElementById('courseSelector').value;
    if (!courseId) return alert("Sélectionnez un cours d'abord.");

    let payload = {};
    if (type === 'gen') {
        payload.custom_prompt = document.getElementById('genPromptInput').value;
    } else if (type === 'grading') {
        payload.custom_grading_prompt = document.getElementById('gradingPromptInput').value;
    } else if (type === 'summary') {
        // Ensure element exists/is visible
        const elem = document.getElementById('summaryPromptInput');
        payload.custom_summary_prompt = elem ? elem.value : null;
    }

    try {
        await fetch(`/api/courses/${courseId}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        alert("Prompt sauvegardé !");
    } catch (e) {
        alert("Erreur de sauvegarde : " + e);
    }
}

async function saveSettings() {

    const courseId = document.getElementById('courseSelector').value;
    const start = document.getElementById('startLine').value;
    const end = document.getElementById('endLine').value;

    // Collect Prompts
    const genPrompt = document.getElementById('genPromptInput').value;
    const gradingPrompt = document.getElementById('gradingPromptInput').value;
    const summaryPrompt = document.getElementById('summaryPromptInput') ? document.getElementById('summaryPromptInput').value : null;

    await fetch(`/api/courses/${courseId}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start_line: start,
            end_line: end,
            custom_prompt: genPrompt,
            custom_grading_prompt: gradingPrompt,
            custom_summary_prompt: summaryPrompt
        })
    });
    alert("Sauvegardé ! (Configuration, Prompts)");
    loadCourses();
}

async function updateEnrollments() {
    const courseId = document.getElementById('courseSelector').value;
    const checkboxes = document.querySelectorAll('#studentChecklist input[type="checkbox"]:checked');
    const ids = Array.from(checkboxes).map(cb => cb.value);

    await fetch(`/api/courses/${courseId}/enrollments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_ids: ids })
    });

    alert("Inscriptions mises à jour !");
    loadCourses(); // Refresh to update dataset
}


async function saveSettingsAndPreview() {
    const courseId = document.getElementById('courseSelector').value;
    const start = document.getElementById('startLine').value;
    const end = document.getElementById('endLine').value;

    // 1. Save Settings
    await fetch(`/api/courses/${courseId}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_line: start, end_line: end })
    });

    // 2. Fetch Preview
    document.getElementById('previewContainer').style.display = 'block';
    document.getElementById('previewContainer').innerText = "Chargement...";

    try {
        const res = await fetch(`/api/courses/${courseId}/preview`);
        const data = await res.json();

        document.getElementById('previewContainer').innerHTML = `
                    <strong>Aperçu (${data.interval_count} lignes) :</strong><br>
                    <pre style="background:#f9f9f9; padding:5px;">${data.preview}</pre>
                `;
    } catch (e) {
        document.getElementById('previewContainer').innerText = "Erreur: " + e.message;
    }
}

async function deleteCourse() {
    const courseId = document.getElementById('courseSelector').value;
    if (!courseId) return;

    // Use Global Modal
    if (typeof openModal === 'function') {
        openModal(
            "Confirmer la suppression",
            `⚠️ Attention !<br><br>Êtes-vous sûr de vouloir supprimer DÉFINITIVEMENT le cours "<strong>${courseId}</strong>" ?<br><br>Cela effacera tous les fichiers et données associés.`,
            async () => await performDelete('course', courseId)
        );
    } else {
        alert("Erreur: Modale non chargée");
    }
}

async function uploadLatex() {
    const courseId = document.getElementById('courseSelector').value;
    const file = document.getElementById('latexUpload').files[0];
    if (!file) return;

    const fd = new FormData();
    fd.append('file', file);

    document.getElementById('uploadStatus').innerText = "Uploading...";
    await fetch(`/api/courses/${courseId}/upload`, { method: 'POST', body: fd });
    document.getElementById('uploadStatus').innerText = "Done!";
}



async function generateQuizzes() {
    const courseId = document.getElementById('courseSelector').value;
    const customPrompt = document.getElementById('genPromptInput').value;
    const regenerate = document.getElementById('regenerateCheck').checked;
    const specificInstructions = document.getElementById('specificInstructionsInput').value;

    document.getElementById('genStatus').innerText = "Génération en cours... (Patientez)";

    const payload = {
        custom_prompt: customPrompt,
        regenerate: regenerate,
        specific_instructions: specificInstructions
    };

    try {
        const response = await fetch(`/api/courses/${courseId}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error("Erreur réseau ou serveur");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const msg = JSON.parse(line);
                    if (msg.type === 'progress') {
                        document.getElementById('genStatus').innerText = `Génération en cours : ${msg.current} / ${msg.total} (${msg.message})`;
                    } else if (msg.type === 'result') {
                        let html = `✅ Succès! ${msg.count} questionnaires générés.`;
                        if (msg.global_pdf_url) {
                            html += `<br><a href="${msg.global_pdf_url}" target="_blank" class="btn" style="display:inline-block; margin-top:10px; background:#059669; text-decoration:none;">📥 Afficher le PDF Global</a>`;
                        }
                        document.getElementById('genStatus').innerHTML = html;
                    }
                } catch (e) {
                    console.error("Parse error", e);
                }
            }
        }
    } catch (e) {
        document.getElementById('genStatus').innerText = "Erreur: " + e.message;
    }
}


async function loadGradebook() {
    const courseId = document.getElementById('courseSelector').value;
    if (!courseId) return;

    const div = document.getElementById('gradebookContainer');
    div.innerHTML = "Chargement...";

    try {
        const res = await fetch(`/api/courses/${courseId}/grades`);
        const data = await res.json();

        // data = { quizzes: [1, 2], students: [ { student_name: "Alice", grades: { "1": {score:15, modified:false}, ... } } ] }

        if (data.students.length === 0) {
            div.innerHTML = "Pas de données de notes.";
            return;
        }

        let html = '<table><thead><tr><th style="text-align:left;">Étudiant</th>';
        data.quizzes.forEach(q => {
            html += `<th>Quiz #${q}</th>`;
        });
        html += '</tr></thead><tbody>';

        data.students.forEach(s => {
            html += `<tr><td style="text-align:left; font-weight:bold;">${s.student_name}</td>`;
            data.quizzes.forEach(q => {
                const cellData = s.grades[String(q)];
                let scoreDisplay = "-";
                let cellClass = "";
                let onclick = `window.open('/student_history?student_id=${s.student_id}&course_id=' + document.getElementById('courseSelector').value + '&quiz=${q}', '_blank')`;

                let dataScore = "";
                if (cellData) {
                    dataScore = cellData.score;
                    if (cellData.modified && cellData.original_score !== undefined && cellData.score != cellData.original_score) {
                        scoreDisplay = `${cellData.score} <span style="font-size:0.8em; color:#6b7280;">(${cellData.original_score})</span>`;
                        cellClass = "modified-grade";
                    } else {
                        scoreDisplay = cellData.score;
                    }
                }

                html += `<td data-score="${dataScore}" class="${cellClass}" onclick="${onclick}" style="cursor:pointer;" title="Ouvrir l'historique détaillé">${scoreDisplay}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        div.innerHTML = html;

    } catch (e) {
        div.innerHTML = `<span style="color:red">Erreur: ${e.message}</span>`;
    }
}

async function editGrade(studentId, quizNum, cellElement) {
    const currentVal = cellElement.getAttribute('data-score') || (cellElement.innerText === "-" ? "" : cellElement.innerText);

    // Avoid double init
    if (cellElement.querySelector('input')) return;

    cellElement.innerHTML = `<input type="number" step="0.5" value="${currentVal}" style="width:60px" id="editInput">`;
    const input = cellElement.querySelector('input');
    input.focus();

    // Save on blur or enter
    async function save() {
        const newVal = input.value;
        if (newVal === currentVal) {
            // Restore without api call
            cellElement.innerHTML = currentVal || "-";
            return;
        }

        if (newVal === "") {
            alert("La note ne peut pas être vide (mettez 0 si nul)");
            return;
        }

        // API Call
        const courseId = document.getElementById('courseSelector').value;
        try {
            await fetch(`/api/courses/${courseId}/grades`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: studentId,
                    quiz_number: quizNum,
                    score: parseFloat(newVal)
                })
            });
            // Reload to show formatted/styled result (yellow)
            loadGradebook();
        } catch (e) {
            alert("Erreur: " + e.message);
            cellElement.innerHTML = currentVal || "-";
        }
    }

    input.onblur = save;
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            input.blur();
        }
    };
}

// --- Student Portal Logic ---

// 1. Load Students into Login Dropdown
async function loadStudentLogin() {
    const select = document.getElementById('studentLoginSelect');
    if (!select) return;

    try {
        const students = await (await fetch('/api/students')).json();
        select.innerHTML = '<option value="">-- Choisir ID --</option>';
        students.sort((a, b) => a.id.localeCompare(b.id));
        students.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.innerText = `Candidat #${s.id}`;
            select.appendChild(opt);
        });
    } catch (e) { console.error(e); }
}

// 2. Load Courses for selected Student
async function loadStudentCourses() {
    const sid = document.getElementById('studentLoginSelect').value;
    const courseSelect = document.getElementById('studentCourseSelect');
    const quizSection = document.getElementById('studentQuizListSection');
    const viewer = document.getElementById('studentQuizViewer');

    courseSelect.innerHTML = '<option value="">Chargement...</option>';
    quizSection.style.display = 'none';
    viewer.style.display = 'none';

    if (!sid) {
        courseSelect.innerHTML = '<option value="">-- Choisir un cours --</option>';
        return;
    }

    try {
        const courses = await (await fetch('/api/courses')).json();
        courseSelect.innerHTML = '<option value="">-- Choisir un cours --</option>';

        // Filter: Only courses where student is enrolled? 
        // Ideally yes, but for now show all or filter if enrolled_students has it.
        courses.forEach(c => {
            // Check enrollment
            if (c.enrolled_students && c.enrolled_students.includes(sid)) {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.innerText = c.title;
                courseSelect.appendChild(opt);
            }
        });

        if (courseSelect.options.length === 1) {
            courseSelect.innerHTML += '<option disabled>(Aucun cours inscrit)</option>';
        }

    } catch (e) { console.error(e); }
}

// 3. Load Quizzes
async function loadStudentQuizzes() {
    const sid = document.getElementById('studentLoginSelect').value;
    const cid = document.getElementById('studentCourseSelect').value;
    const listDiv = document.getElementById('studentQuizList');
    const section = document.getElementById('studentQuizListSection');
    const viewer = document.getElementById('studentQuizViewer');

    if (!sid || !cid) return;

    section.style.display = 'block';
    listDiv.innerHTML = "Chargement...";
    viewer.style.display = 'none';

    try {
        const res = await fetch(`/api/students/${sid}/courses/${cid}/quizzes`);
        const quizzes = await res.json();

        listDiv.innerHTML = '';

        if (quizzes.length === 0) {
            listDiv.innerHTML = "<i>Aucune correction disponible pour l'instant.</i>";
            return;
        }

        quizzes.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'btn';
            btn.style.background = '#4b5563';

            // Score badge
            let scoreText = "?";
            if (q.correction && (q.correction.total_score !== undefined || q.correction.effective_score !== undefined)) {
                let effectiveScore = q.correction.effective_score !== undefined ? q.correction.effective_score : q.correction.total_score;
                if (effectiveScore != q.correction.total_score) {
                    scoreText = `${effectiveScore}(${q.correction.total_score})/20`;
                } else {
                    scoreText = effectiveScore + "/20";
                }
            }

            btn.innerText = `Quiz #${q.quiz_number} (${scoreText})`;
            btn.onclick = () => openQuizViewer(q);
            listDiv.appendChild(btn);
        });

    } catch (e) { console.error(e); }
}

// 4. Viewer
function openQuizViewer(quizData) {
    const viewer = document.getElementById('studentQuizViewer');
    const iframe = document.getElementById('scanViewer');
    const feedbackDiv = document.getElementById('feedbackViewer');
    const title = document.getElementById('viewerTitle');

    viewer.style.display = 'block';
    title.innerText = `Quiz #${quizData.quiz_number}`;

    // Scan
    if (quizData.scan_url) {
        iframe.src = quizData.scan_url + "#toolbar=1&view=FitH";
    } else {
        iframe.src = "about:blank"; // Or placeholder
    }

    // Feedback
    if (quizData.correction) {
        const c = quizData.correction;
        const effectiveScore = c.effective_score !== undefined ? c.effective_score : c.total_score;
        let scoreDisplay = effectiveScore == c.total_score 
            ? `<span style="font-size:1.5em">${c.total_score}/20</span>`
            : `<span style="font-size:1.5em; color:#059669">${effectiveScore}</span><span style="font-size:0.8em; color:#6b7280;">(${c.total_score})</span><span style="font-size:1.5em; color:#059669">/20</span>`;

        let html = `<div style="display:flex; justify-content:flex-start; gap: 2rem; align-items:center; border-bottom:2px solid #eee; padding-bottom:0.5rem; margin-bottom:1rem;">
                        <h2 style="color:#2563eb; margin:0;">Note : ${scoreDisplay}</h2>
                    </div>`;

        if (c.weak_concepts && c.weak_concepts.length > 0) {
            html += `<div style="margin-bottom:1rem;"><strong>Points à revoir :</strong><br>`;
            c.weak_concepts.forEach(tag => {
                html += `<span style="display:inline-block; background:#fee2e2; color:#991b1b; padding:2px 8px; borderRadius:12px; margin:2px; font-size:0.9em;">${tag}</span>`;
            });
            html += `</div>`;
        }

        if (c.transcription) {
            html += `<details><summary style="cursor:pointer; color:#555;">Voir ma transcription</summary><p style="background:#f9fafb; padding:0.5rem; font-family:monospace; font-size:0.9em;">${c.transcription}</p></details>`;
        }

        html += `<h3>Détails par question</h3>`;
        c.grades.forEach(g => {
            html += `<div style="margin-bottom:1rem; border-left:4px solid #ddd; padding-left:1rem;">
                        <strong>Q${g.question}</strong> <span style="float:right; font-weight:bold;">${g.score} pts</span>
                        <p style="margin:0.2rem 0; color:#374151;">${g.feedback}</p>
                    </div>`;
        });

        feedbackDiv.innerHTML = html;
    } else {
        feedbackDiv.innerHTML = "Pas de correction détaillée.";
    }

    // Auto scroll to viewer
    viewer.scrollIntoView({ behavior: 'smooth' });
}

// Init Calls (Add to main loading)
// We need to call loadStudentLogin() either on init or when switching tab.
// Let's add it to the main block below.



// --- Chat Linking ---
// We removed specific chat student selector, so we link it to the main login

async function sendChat() {
    // Use the logged-in student ID
    const studentId = document.getElementById('studentLoginSelect').value;
    if (!studentId) {
        alert("Veuillez sélectionner votre ID étudiant d'abord (Section 1. Identification).");
        return;
    }

    const input = document.getElementById('chatInput');
    const message = input.value;
    if (!message) return;

    const historyDiv = document.getElementById('chatHistory');
    historyDiv.innerHTML += `<div style="margin-bottom:0.5rem; text-align:right;"><b>You:</b> ${message}</div>`;
    input.value = '';

    // Scroll to bottom
    historyDiv.scrollTop = historyDiv.scrollHeight;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                course_id: document.getElementById('studentCourseSelect').value,
                message: message,
                history: []
            })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        // Create container
        const msgId = 'msg-' + Date.now();
        historyDiv.innerHTML += `<div id="${msgId}" style="margin-bottom:0.8rem; text-align:left; background:#f3f4f6; padding:0.8rem; border-radius:4px; line-height:1.6;"><b>Tutor:</b> <span class="content"></span></div>`;
        historyDiv.scrollTop = historyDiv.scrollHeight;

        const contentSpan = document.querySelector(`#${msgId} .content`);
        let fullText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;
            contentSpan.innerHTML = marked.parse(fullText);
            historyDiv.scrollTop = historyDiv.scrollHeight;
        }

        // Final Math Render
        if (window.MathJax) {
            window.MathJax.typesetPromise([document.getElementById(msgId)]).catch(err => console.log(err));
        }

    } catch (e) {
        console.error(e);
        historyDiv.innerHTML += `<div style="color:red;">Erreur connexion chatbot.</div>`;
    }
}

// --- Drag & Drop Init ---
(function () {
    const dropZone = document.getElementById('smartScanDropZone');
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.background = '#e5e7eb';
        });
        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.style.background = '#f9fafb';
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.background = '#f9fafb';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                addToQueue(e.dataTransfer.files);
            }
        });
    }
})();

// --- UNIVERSAL Modal Logic ---
let onConfirmCallback = null;

const modal = document.getElementById('confirmModal');
const confirmText = document.getElementById('confirmText');
const modalTitle = document.querySelector('#confirmModal h3');
const toast = document.getElementById('toast');

/**
 * Generic Function to open the confirmation modal.
 * @param {string} title - The header title of the modal.
 * @param {string} message - The HTML content of the message.
 * @param {Function} callback - Async function to execute on confirmation.
 * @param {string} confirmLabel - Text for the confirm button (default: "Supprimer").
 * @param {string} confirmColor - Background color for the confirm button (default: "#dc2626").
 */
function openModal(title, message, callback, confirmLabel = "Supprimer", confirmColor = "#dc2626") {
    if (modalTitle) modalTitle.innerText = title;
    if (confirmText) confirmText.innerHTML = message;

    const btn = document.getElementById('confirmBtn');
    if (btn) {
        btn.innerText = confirmLabel;
        btn.style.background = confirmColor;
    }

    onConfirmCallback = callback;
    if (modal) modal.style.display = 'flex';
}

function showToast(msg, color = '#333') {
    if (toast) {
        toast.innerHTML = msg;
        toast.style.background = color;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }
}

// --- Event Delegation (Students) ---
document.addEventListener('click', (e) => {
    if (e.target && e.target.classList.contains('delete-student-btn')) {
        const sid = e.target.getAttribute('data-sid');
        if (sid) {
            openModal(
                "Confirmer la suppression",
                `Voulez-vous vraiment supprimer l'étudiant <strong>${sid}</strong> ?`,
                async () => await performDelete('student', sid)
            );
        }
    }
});

// Modal Actions
const cancelBtn = document.getElementById('cancelBtn');
if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
        if (modal) modal.style.display = 'none';
        onConfirmCallback = null;
    });
}

const confirmBtn = document.getElementById('confirmBtn');
if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
        if (modal) modal.style.display = 'none'; // Close first
        if (onConfirmCallback) {
            await onConfirmCallback();
            onConfirmCallback = null; // Reset
        }
    });
}

// Helper for Deletions (Student/Course)
async function performDelete(type, id) {
    showToast(`Suppression de ${id}...`, 'orange');
    try {
        let url = '';
        if (type === 'student') url = `/api/students/${id}`;
        if (type === 'course') url = `/api/courses/${id}`;

        const res = await fetch(url, { method: 'DELETE' });

        if (res.ok) {
            showToast("Suppression réussie !", "green");
            if (type === 'student') {
                await loadStudentsGlobal();
            } else if (type === 'course') {
                document.getElementById('courseDetails').style.display = 'none';
                document.getElementById('courseSelector').value = "";
                await loadCourses();
            }
        } else {
            const err = await res.json();
            showToast("Erreur: " + err.detail, "red");
        }
    } catch (e) {
        showToast("Erreur réseau: " + e.message, "purple");
    }
}

// --- SCAN VERIFICATION LOGIC ---
// --- SMART SCAN V2 LOGIC ---
var v2Queue = []; // { file_id, filename, analysis, is_graded }
window.v2Queue = v2Queue;

async function handleV2Upload(files) {
    alert("Feature temporarily disabled for debugging.");
    console.log("handleV2Upload called with", files);
}

function renderV2Queue() {
    const tbody = document.getElementById('v2_queue_body');
    tbody.innerHTML = '';

    let readyCount = 0;

    v2Queue.sort((a, b) => {
        const aMissing = (!a.analysis.student_id || !a.analysis.quiz_number) ? 1 : 0;
        const bMissing = (!b.analysis.student_id || !b.analysis.quiz_number) ? 1 : 0;
        return bMissing - aMissing; // Missing first
    });

    v2Queue.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = "1px solid #eee";

        const sid = item.analysis.student_id || "";
        const qnum = item.analysis.quiz_number || "";

        const isComplete = (sid && qnum);
        if (item.status === 'ready' && isComplete) readyCount++;

        // Inputs
        const inputId = `<input type="text" value="${sid}" style="width:80px; text-align:center; border:${sid ? '1px solid #ccc' : '2px solid red'}" onchange="updateV2Item(${index}, 'student_id', this.value)">`;
        const inputQuiz = `<input type="number" value="${qnum}" style="width:60px; text-align:center; border:${qnum ? '1px solid #ccc' : '2px solid red'}" onchange="updateV2Item(${index}, 'quiz_number', this.value)">`;

        let statusHtml = isComplete ? `<span style="color:orange">À valider</span>` : `<span style="color:red; font-weight:bold;">⚠️ Incomplet</span>`;
        if (item.status === 'grading') statusHtml = `<span style="color:blue">Correction...</span>`;
        if (item.status === 'done') statusHtml = `<span style="color:green">✅ Terminé</span>`;
        if (item.status === 'error') statusHtml = `<span style="color:red">❌ Erreur</span>`;

        tr.innerHTML = `
                    <td style="padding:10px;">${item.filename}</td>
                    <td style="padding:10px;">${inputId}</td>
                    <td style="padding:10px;">${inputQuiz}</td>
                    <td style="padding:10px;">${statusHtml}</td>
                    <td style="padding:10px;">
                        <button class="btn" style="background:#ef4444; padding:2px 5px; font-size:0.8em;" onclick="removeV2Item(${index})">🗑️</button>
                    </td>
                `;
        tbody.appendChild(tr);
    });

    const btn = document.getElementById('v2_btn_grade');
    const allValid = (v2Queue.length > 0 && readyCount === v2Queue.length);
    document.getElementById('v2_count_ready').innerText = readyCount + " / " + v2Queue.length;

    if (allValid) {
        btn.parentElement.style.opacity = "1";
        btn.disabled = false;
        btn.title = "Lancer la correction";
    } else {
        btn.parentElement.style.opacity = "0.5";
        btn.disabled = true;
        btn.title = "Veuillez valider tous les scans avant de lancer.";
    }
}

function updateV2Item(index, field, value) {
    if (v2Queue[index]) {
        if (field === 'student_id') v2Queue[index].analysis.student_id = value;
        if (field === 'quiz_number') v2Queue[index].analysis.quiz_number = value;
        renderV2Queue();
    }
}

function removeV2Item(index) {
    v2Queue.splice(index, 1);
    renderV2Queue();
}

async function processV2Queue() {
    const courseId = document.getElementById('courseSelector').value;
    if (!courseId) {
        alert("Veuillez sélectionner un cours cible dans la liste principale.");
        return;
    }

    const promptVal = document.getElementById('v2_prompt').value;

    for (let i = 0; i < v2Queue.length; i++) {
        const item = v2Queue[i];
        if (item.status !== 'ready') continue;

        if (!item.analysis.student_id || !item.analysis.quiz_number) continue;

        // Update Status
        item.status = 'grading';
        renderV2Queue();

        try {
            const res = await fetch('/api/grade_scan_verified', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: item.file_id,
                    student_id: item.analysis.student_id,
                    quiz_number: parseInt(item.analysis.quiz_number),
                    course_id: courseId,
                    custom_prompt: promptVal
                })
            });

            if (!res.ok) throw new Error("Failed");

            const result = await res.json();
            console.log("Grading Result:", result);

            item.status = 'done';
        } catch (e) {
            console.error(e);
            item.status = 'error';
        }

        renderV2Queue();
    }

    alert("Traitement terminé !");
}
// Initialize Data (Immediate)
(async function init() {
    console.log("Script executed. Starting init...");

    console.log("1. Init Courses...");
    try { await loadCourses(); } catch (e) { console.error("Err Courses", e); }

    console.log("2. Init Global Students...");
    try { await loadStudentsGlobal(); } catch (e) { console.error("Err Students", e); }

    console.log("3. Init Student Login...");
    try { await loadStudentLogin(); } catch (e) { console.error("Err Login", e); }

    console.log("Init Complete.");
})();
    </script >
</body >

</html >