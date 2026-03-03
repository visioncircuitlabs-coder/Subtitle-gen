document.addEventListener('DOMContentLoaded', () => {
    // Sections
    const sections = {
        upload: document.getElementById('upload-section'),
        processing: document.getElementById('processing-section'),
        complete: document.getElementById('complete-section'),
        error: document.getElementById('error-section'),
    };

    // Processing elements
    const processBar = document.getElementById('process-bar');
    const processPercent = document.getElementById('process-percent');
    const processStage = document.getElementById('process-stage');

    // Download
    const downloadVideoBtn = document.getElementById('download-video-btn');
    const downloadSrtBtn = document.getElementById('download-srt-btn');

    // Pipeline steps
    const pipeSteps = document.querySelectorAll('.pipe-step');
    const pipeLines = document.querySelectorAll('.pipe-line');
    const stepOrder = ['validating', 'extracting_audio', 'transcribing',
                       'generating_subtitles', 'burning_subtitles'];

    const stageNames = {
        validating: 'Validating video...',
        extracting_audio: 'Extracting audio...',
        transcribing: 'Transcribing speech...',
        generating_subtitles: 'Generating subtitles...',
        burning_subtitles: 'Burning subtitles into video...',
    };

    let eventSource = null;

    const upload = initUpload(onUploadComplete, showError);

    document.getElementById('reset-btn').addEventListener('click', resetAll);
    document.getElementById('error-reset-btn').addEventListener('click', resetAll);

    // Spawn background particles
    spawnParticles();

    function showSection(name) {
        Object.entries(sections).forEach(([key, el]) => {
            el.hidden = key !== name;
            if (key === name) {
                el.style.animation = 'none';
                el.offsetHeight; // reflow
                el.style.animation = 'cardIn 0.5s cubic-bezier(0.16,1,0.3,1)';
            }
        });
    }

    function showError(msg) {
        document.getElementById('error-message').textContent = msg;
        showSection('error');
    }

    function onUploadComplete(jobId) {
        showSection('processing');
        resetPipeline();
        processBar.style.width = '0%';
        processPercent.textContent = '0%';
        processStage.textContent = 'Starting...';
        startProcessing(jobId);
    }

    async function startProcessing(jobId) {
        try {
            const res = await fetch(`/api/process/${jobId}`, { method: 'POST' });
            if (!res.ok) {
                const data = await res.json();
                showError(data.detail || 'Failed to start processing');
                return;
            }
        } catch {
            showError('Failed to connect to server');
            return;
        }
        connectSSE(jobId);
    }

    function connectSSE(jobId) {
        if (eventSource) eventSource.close();
        eventSource = new EventSource(`/api/progress/${jobId}`);

        eventSource.addEventListener('message', (e) => {
            let data;
            try { data = JSON.parse(e.data); } catch { return; }

            if (data.stage === 'heartbeat') return;

            if (data.stage === 'error') {
                eventSource.close();
                showError(data.message || 'Processing failed');
                return;
            }

            if (data.stage === 'complete') {
                eventSource.close();
                showComplete(jobId);
                return;
            }

            updateProgress(data.stage, data.progress);
        });

        eventSource.addEventListener('error', () => {
            eventSource.close();
        });
    }

    function updateProgress(stage, progress) {
        const pct = Math.round(progress * 100);
        processBar.style.width = pct + '%';
        processPercent.textContent = pct + '%';
        processStage.textContent = stageNames[stage] || stage;

        const currentIdx = stepOrder.indexOf(stage);

        pipeSteps.forEach((el, i) => {
            el.classList.remove('active', 'done');
            if (i < currentIdx) el.classList.add('done');
            else if (i === currentIdx) el.classList.add('active');
        });

        // Color the connecting lines for completed steps
        pipeLines.forEach((line, i) => {
            if (i < currentIdx) {
                line.style.background = 'var(--success)';
            } else {
                line.style.background = 'var(--border)';
            }
        });
    }

    function showComplete(jobId) {
        downloadVideoBtn.href = `/api/download/${jobId}/video`;
        downloadSrtBtn.href = `/api/download/${jobId}/subtitle`;
        showSection('complete');
    }

    function resetPipeline() {
        pipeSteps.forEach(s => s.classList.remove('active', 'done'));
        pipeLines.forEach(l => l.style.background = 'var(--border)');
    }

    function resetAll() {
        if (eventSource) eventSource.close();
        upload.resetUploadUI();
        showSection('upload');
    }

    function spawnParticles() {
        const container = document.getElementById('particles');
        for (let i = 0; i < 30; i++) {
            const p = document.createElement('div');
            p.className = 'particle';
            p.style.left = Math.random() * 100 + '%';
            p.style.animationDuration = (8 + Math.random() * 12) + 's';
            p.style.animationDelay = (Math.random() * 10) + 's';
            p.style.width = p.style.height = (1 + Math.random() * 2) + 'px';
            container.appendChild(p);
        }
    }
});
