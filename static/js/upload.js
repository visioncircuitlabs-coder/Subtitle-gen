const ALLOWED_EXT = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv'];
const MAX_SIZE_MB = 500;

function initUpload(onComplete, onError) {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const progressSection = document.getElementById('upload-progress');
    const filenameEl = document.getElementById('upload-filename');
    const barEl = document.getElementById('upload-bar');
    const statusEl = document.getElementById('upload-status');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });

    function handleFile(file) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXT.includes(ext)) {
            onError(`Unsupported format "${ext}". Use: ${ALLOWED_EXT.join(', ')}`);
            return;
        }

        const sizeMB = file.size / (1024 * 1024);
        if (sizeMB > MAX_SIZE_MB) {
            onError(`File too large (${sizeMB.toFixed(0)}MB). Max: ${MAX_SIZE_MB}MB`);
            return;
        }

        dropZone.hidden = true;
        progressSection.hidden = false;
        filenameEl.textContent = file.name;
        barEl.style.width = '0%';
        statusEl.textContent = 'Uploading...';

        uploadFile(file);
    }

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload');

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                barEl.style.width = pct + '%';
                statusEl.textContent = `Uploading... ${pct}%`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                barEl.style.width = '100%';
                statusEl.textContent = 'Upload complete';
                onComplete(data.job_id);
            } else {
                let msg = 'Upload failed';
                try {
                    msg = JSON.parse(xhr.responseText).detail || msg;
                } catch {}
                resetUploadUI();
                onError(msg);
            }
        });

        xhr.addEventListener('error', () => {
            resetUploadUI();
            onError('Upload failed — check your connection');
        });

        xhr.send(formData);
    }

    function resetUploadUI() {
        dropZone.hidden = false;
        progressSection.hidden = true;
        fileInput.value = '';
    }

    return { resetUploadUI };
}
