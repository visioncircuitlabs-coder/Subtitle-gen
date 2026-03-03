document.addEventListener('DOMContentLoaded', () => {
    const uploadSection = document.getElementById('upload-section');
    const processingSection = document.getElementById('processing-section');
    const completeSection = document.getElementById('complete-section');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');

    const processBar = document.getElementById('process-bar');
    const processPercent = document.getElementById('process-percent');

    const downloadVideoBtn = document.getElementById('download-video-btn');
    const downloadSrtBtn = document.getElementById('download-srt-btn');
    const resetBtn = document.getElementById('reset-btn');
    const errorResetBtn = document.getElementById('error-reset-btn');

    const steps = document.querySelectorAll('.step');
    const stepOrder = ['validating', 'extracting_audio', 'transcribing',
                       'generating_subtitles', 'burning_subtitles'];

    let currentJobId = null;
    let eventSource = null;

    const upload = initUpload(onUploadComplete, showError);

    resetBtn.addEventListener('click', resetAll);
    errorResetBtn.addEventListener('click', resetAll);

    function showSection(section) {
        [uploadSection, processingSection, completeSection, errorSection]
            .forEach(s => s.hidden = true);
        section.hidden = false;
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        showSection(errorSection);
    }

    function onUploadComplete(jobId) {
        currentJobId = jobId;
        showSection(processingSection);
        resetSteps();
        processBar.style.width = '0%';
        processPercent.textContent = '0%';
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
            try {
                data = JSON.parse(e.data);
            } catch {
                return;
            }

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
            // Don't show error for normal close
        });
    }

    function updateProgress(stage, progress) {
        const pct = Math.round(progress * 100);
        processBar.style.width = pct + '%';
        processPercent.textContent = pct + '%';

        const currentIdx = stepOrder.indexOf(stage);
        steps.forEach((stepEl, i) => {
            const stepName = stepEl.dataset.step;
            const idx = stepOrder.indexOf(stepName);
            stepEl.classList.remove('active', 'done');
            if (idx < currentIdx) {
                stepEl.classList.add('done');
            } else if (idx === currentIdx) {
                stepEl.classList.add('active');
            }
        });
    }

    function showComplete(jobId) {
        downloadVideoBtn.href = `/api/download/${jobId}/video`;
        downloadSrtBtn.href = `/api/download/${jobId}/subtitle`;
        showSection(completeSection);
    }

    function resetSteps() {
        steps.forEach(s => s.classList.remove('active', 'done'));
    }

    function resetAll() {
        if (eventSource) eventSource.close();
        currentJobId = null;
        upload.resetUploadUI();
        showSection(uploadSection);
    }
});
