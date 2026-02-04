const App = {
    API_URL: 'http://localhost:8000', // API base URL

    state: {
        files: [], // Array of uploaded files
        results: [], // Array of analysis results per image
        images: [], // Array of loaded Image objects
        currentTabIndex: 0,

        // View state (per tab, but for simplicity we reset on tab switch or keep global if preferred. 
        // Let's keep global for now, resetting on tab switch)
        scale: 1,
        zoomLevel: 1,
        offsetX: 0,
        offsetY: 0,
        isDragging: false,
        lastMouseX: 0,
        lastMouseY: 0,
        highlightedSeedId: null,

        mode: 'accurate', // 'accurate' or 'fast'
        // Report metadata for PDF (execution time, overall stats)
        reportMetadata: null, // { processingDurationMs, overallStatistics: { good_seeds, bad_seeds, good_percentage, bad_percentage } }

        // History state
        historyPage: 1,
        historyLimit: 20,
        historyStatusFilter: null,
        historyStats: null
    },

    elements: {
        dropZone: document.getElementById('drop-zone'),
        fileInput: document.getElementById('file-input'),
        uploadSection: document.getElementById('upload-section'),
        loadingSection: document.getElementById('loading-section'),
        resultsSection: document.getElementById('results-section'),
        errorMessage: document.getElementById('error-message'),
        errorText: document.getElementById('error-text'),
        canvas: document.getElementById('image-canvas'),
        canvasContainer: document.getElementById('canvas-container'),
        seedsList: document.getElementById('seeds-list'),
        statGoodCount: document.getElementById('stat-good-count'),
        statGoodPercent: document.getElementById('stat-good-percent'),
        statBadCount: document.getElementById('stat-bad-count'),
        statBadPercent: document.getElementById('stat-bad-percent'),
        statTotal: document.getElementById('stat-total'),
        statProgressBar: document.getElementById('stat-progress-bar'),
        statExecutionTime: document.getElementById('stat-execution-time'),
        btnNewAnalysis: document.getElementById('btn-new-analysis'),
        btnZoomIn: document.getElementById('zoom-in'),
        btnZoomOut: document.getElementById('zoom-out'),
        btnZoomReset: document.getElementById('zoom-reset'),
        filterAll: document.getElementById('view-all'),
        filterGood: document.getElementById('view-good'),
        filterBad: document.getElementById('view-bad'),

        // System Status
        statusDot: document.getElementById('system-status-dot'),
        statusText: document.getElementById('system-status-text'),
        modelAccurate: document.getElementById('model-accurate'),
        modelFast: document.getElementById('model-fast'),
        btnExport: document.getElementById('btn-export'),
        imageTabs: document.getElementById('image-tabs'),

        // History elements
        historySection: document.getElementById('history-section'),
        btnHistory: document.getElementById('btn-history'),
        btnBackFromHistory: document.getElementById('btn-back-from-history'),
        logoHome: document.getElementById('logo-home'),
        historyStats: document.getElementById('history-stats'),
        batchesList: document.getElementById('batches-list'),
        historyPagination: document.getElementById('history-pagination'),
        filterStatusAll: document.getElementById('filter-status-all'),
        filterStatusCompleted: document.getElementById('filter-status-completed'),
        filterStatusFailed: document.getElementById('filter-status-failed'),
        filterStatusPending: document.getElementById('filter-status-pending')
    },

    init() {
        // Initialize Details Card Elements here to ensure DOM is ready
        this.elements.detailsCard = document.getElementById('seed-details-card');
        this.elements.detailId = document.getElementById('detail-id');
        this.elements.detailQuality = document.getElementById('detail-quality');
        this.elements.detailConfidence = document.getElementById('detail-confidence');
        this.elements.detailArea = document.getElementById('detail-area');
        this.elements.detailDims = document.getElementById('detail-dims');
        this.elements.detailRatio = document.getElementById('detail-ratio');

        this.bindEvents();
        this.setupCanvasInteractions();
        this.checkBackendStatus();
    },

    async checkBackendStatus() {
        const { statusDot, statusText } = this.elements;

        try {
            const response = await fetch(`${this.API_URL}/`);
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'running') {
                    statusDot.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
                    statusText.textContent = 'System Ready';
                    return;
                }
            }
            throw new Error('Backend not ready');
        } catch (error) {
            console.error('Backend check failed:', error);
            statusDot.className = 'w-2 h-2 rounded-full bg-red-500';
            statusText.textContent = 'System Offline';

            // Retry after 5 seconds
            setTimeout(() => this.checkBackendStatus(), 5000);
        }
    },

    bindEvents() {
        const { dropZone, fileInput, btnNewAnalysis, filterAll, filterGood, filterBad, modelAccurate, modelFast, btnExport, btnHistory, btnBackFromHistory, filterStatusAll, filterStatusCompleted, filterStatusFailed, filterStatusPending } = this.elements;

        // Drag & Drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-seed-green-500', 'bg-seed-green-50');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-seed-green-500', 'bg-seed-green-50');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-seed-green-500', 'bg-seed-green-50');
            if (e.dataTransfer.files.length) {
                this.handleFiles(e.dataTransfer.files);
            }
        });

        // File Input
        dropZone.addEventListener('click', () => {
            fileInput.click();
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                // Immediately convert FileList to Array to prevent reference issues
                const filesArray = Array.from(e.target.files);
                // Use setTimeout to break out of the event loop and prevent navigation
                setTimeout(() => {
                    this.handleFiles(filesArray);
                }, 0);
            }
            // Clear the input value to allow re-selection of the same file
            e.target.value = '';
        });

        // New Analysis
        btnNewAnalysis.addEventListener('click', () => this.reset());

        // Filters
        filterAll.addEventListener('click', () => this.filterSeeds('all'));
        filterGood.addEventListener('click', () => this.filterSeeds('Good'));
        filterBad.addEventListener('click', () => this.filterSeeds('Bad'));

        // Model Selection
        modelAccurate.addEventListener('click', () => this.setMode('accurate'));
        modelFast.addEventListener('click', () => this.setMode('fast'));

        // Export
        btnExport.addEventListener('click', () => this.generatePDF());

        // History navigation - check if elements exist
        if (btnHistory) {
            btnHistory.addEventListener('click', () => {
                console.log('History button clicked');
                this.showHistory();
            });
        }
        if (btnBackFromHistory) {
            btnBackFromHistory.addEventListener('click', () => {
                this.hideHistory();
                this.elements.uploadSection.classList.remove('hidden');
            });
        }
        if (this.elements.logoHome) {
            this.elements.logoHome.addEventListener('click', () => {
                this.hideHistory();
                this.reset();
            });
        }

        // History filters - check if elements exist
        if (filterStatusAll) {
            filterStatusAll.addEventListener('click', () => this.setHistoryStatusFilter(null));
        }
        if (filterStatusCompleted) {
            filterStatusCompleted.addEventListener('click', () => this.setHistoryStatusFilter('COMPLETED'));
        }
        if (filterStatusFailed) {
            filterStatusFailed.addEventListener('click', () => this.setHistoryStatusFilter('FAILED'));
        }
        if (filterStatusPending) {
            filterStatusPending.addEventListener('click', () => this.setHistoryStatusFilter('PENDING'));
        }
    },

    setMode(mode) {
        this.state.mode = mode;
        const { modelAccurate, modelFast } = this.elements;

        if (mode === 'accurate') {
            modelAccurate.className = "px-4 py-2 rounded-md text-sm font-medium bg-seed-green-100 text-seed-green-700 shadow-sm transition-all flex items-center gap-2";
            modelFast.className = "px-4 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-all flex items-center gap-2";
        } else {
            modelFast.className = "px-4 py-2 rounded-md text-sm font-medium bg-seed-green-100 text-seed-green-700 shadow-sm transition-all flex items-center gap-2";
            modelAccurate.className = "px-4 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-all flex items-center gap-2";
        }
    },

    setupCanvasInteractions() {
        const { btnZoomIn, btnZoomOut, btnZoomReset, canvas, canvasContainer } = this.elements;

        // Button Zoom
        btnZoomIn.addEventListener('click', () => this.updateZoom(0.2));
        btnZoomOut.addEventListener('click', () => this.updateZoom(-0.2));
        btnZoomReset.addEventListener('click', () => {
            this.state.zoomLevel = 1;
            this.state.offsetX = 0;
            this.state.offsetY = 0;
            this.draw();
        });

        // Mouse Wheel Zoom
        canvasContainer.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            this.updateZoom(delta);
        });

        // Pan (Drag)
        canvas.addEventListener('mousedown', (e) => {
            this.state.isDragging = true;
            this.state.lastMouseX = e.clientX;
            this.state.lastMouseY = e.clientY;
            canvas.style.cursor = 'grabbing';
        });

        window.addEventListener('mousemove', (e) => {
            if (!this.state.isDragging) return;

            const dx = e.clientX - this.state.lastMouseX;
            const dy = e.clientY - this.state.lastMouseY;

            this.state.offsetX += dx;
            this.state.offsetY += dy;

            this.state.lastMouseX = e.clientX;
            this.state.lastMouseY = e.clientY;

            this.draw();
        });

        window.addEventListener('mouseup', () => {
            this.state.isDragging = false;
            canvas.style.cursor = 'grab';
        });
    },

    updateZoom(delta) {
        const newZoom = Math.max(0.5, Math.min(5, this.state.zoomLevel + delta));
        this.state.zoomLevel = newZoom;
        this.draw();
    },

    handleFiles(fileList) {
        const files = Array.from(fileList).filter(file => file.type.startsWith('image/'));

        if (files.length === 0) {
            this.showError('Please upload valid image files (JPG, PNG).');
            return;
        }

        this.state.files = files;
        this.uploadImages(files);
    },

    async uploadImages(files) {
        console.log('uploadImages called with', files.length, 'files');

        this.showLoading(true);
        this.hideError();

        const formData = new FormData();
        files.forEach(file => {
            console.log('Appending file:', file.name, file.type, file.size);
            formData.append('files', file);
        });

        // Note: Batch endpoint is always /api/analyze-batch, but we might want to pass mode?
        // The current backend /api/analyze-batch doesn't seem to take a mode param, it uses default models.
        // If we want fast mode for batch, we might need to update backend or just use accurate for now.
        // Let's assume /api/analyze-batch uses the default (accurate) models for now as per backend code.
        // Wait, the user asked for batch analysis. The backend has /api/analyze-batch.
        // Does /api/analyze-batch support fast mode? Looking at main.py... no, it uses detect_seeds (local).
        // So batch analysis will always be "Accurate" mode for now unless we modify backend.
        // I will proceed with /api/analyze-batch.

        const endpoint = '/api/analyze-batch';
        console.log('Sending POST to:', `${this.API_URL}${endpoint}`);

        try {
            // Load all images for display
            console.log('Loading images for display...');
            this.state.images = await Promise.all(files.map(file => this.loadImage(file)));
            console.log('Images loaded successfully');

            console.log('Starting fetch request...');
            const response = await fetch(`${this.API_URL}${endpoint}`, {
                method: 'POST',
                body: formData
            });

            console.log('Fetch completed, status:', response.status);

            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }

            console.log('Parsing JSON response...');
            const data = await response.json();
            console.log('Response data:', data);

            this.state.results = data.results;
            this.state.reportMetadata = {
                processingDurationMs: data.processing_duration_ms ?? null,
                overallStatistics: data.overall_statistics ?? null
            };

            // Initialize view
            this.state.currentTabIndex = 0;
            this.showResults();
            this.renderTabs();
            this.updateView();

        } catch (error) {
            console.error(error);
            this.showError(error.message || 'Failed to analyze images.');
            this.showLoading(false);
        }
    },

    loadImage(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => resolve(img);
                img.onerror = reject;
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    },

    renderTabs() {
        const tabsContainer = this.elements.imageTabs;
        tabsContainer.innerHTML = '';

        this.state.files.forEach((file, index) => {
            const btn = document.createElement('button');
            const isActive = index === this.state.currentTabIndex;

            btn.className = `px-4 py-2 text-sm font-medium whitespace-nowrap rounded-t-lg border-b-2 transition-colors ${isActive
                ? 'border-seed-green-600 text-seed-green-600 bg-white'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`;
            btn.textContent = file.name;

            btn.addEventListener('click', () => {
                console.log('Tab clicked:', index);
                this.state.currentTabIndex = index;
                // Reset zoom/pan on tab switch
                this.state.zoomLevel = 1;
                this.state.offsetX = 0;
                this.state.offsetY = 0;
                this.state.highlightedSeedId = null;

                console.log('Current tab index:', this.state.currentTabIndex);
                console.log('Current image:', this.getImage());
                console.log('Current result:', this.getCurrentResult());

                this.renderTabs(); // Re-render to update active state
                this.updateView();
            });

            tabsContainer.appendChild(btn);
        });
    },

    updateView() {
        this.renderStats();
        this.renderSeedsList();
        this.draw();
    },

    getCurrentResult() {
        return this.state.results[this.state.currentTabIndex];
    },

    getCurrentImage() {
        return this.state.images[this.state.currentTabIndex];
    },

    draw() {
        const image = this.getImage();
        const result = this.getCurrentResult();

        if (!image) return;

        const canvas = this.elements.canvas;
        const ctx = canvas.getContext('2d');
        const container = this.elements.canvasContainer;

        // Canvas size matches container for full interactive area
        canvas.width = container.clientWidth;
        canvas.height = 500; // Fixed height

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Calculate base scale to fit image in canvas initially
        const scaleX = canvas.width / image.width;
        const scaleY = canvas.height / image.height;
        const baseScale = Math.min(scaleX, scaleY);

        // Apply transformations
        ctx.save();

        // Center the image initially
        const centerX = (canvas.width - image.width * baseScale * this.state.zoomLevel) / 2;
        const centerY = (canvas.height - image.height * baseScale * this.state.zoomLevel) / 2;

        ctx.translate(centerX + this.state.offsetX, centerY + this.state.offsetY);
        ctx.scale(baseScale * this.state.zoomLevel, baseScale * this.state.zoomLevel);

        // Draw Image
        ctx.drawImage(image, 0, 0);

        // Draw Bounding Boxes
        if (result && result.bounding_boxes) {
            const apiScaleX = image.width / result.image_dimensions.width;
            const apiScaleY = image.height / result.image_dimensions.height;

            result.bounding_boxes.forEach(box => {
                const x = box.x1 * apiScaleX;
                const y = box.y1 * apiScaleY;
                const w = box.width * apiScaleX;
                const h = box.height * apiScaleY;

                // Highlight logic
                const isHighlighted = this.state.highlightedSeedId === box.id;

                // Draw Box
                ctx.strokeStyle = isHighlighted ? '#FFFF00' : box.color;
                ctx.lineWidth = (isHighlighted ? 4 : 2) / (baseScale * this.state.zoomLevel);
                ctx.strokeRect(x, y, w, h);

                // Fill
                if (box.quality === 'Bad' || isHighlighted) {
                    ctx.fillStyle = box.color + '33';
                    ctx.fillRect(x, y, w, h);
                }

                // Draw Label (Seed ID)
                const fontSize = Math.max(12, 14 / (baseScale * this.state.zoomLevel));
                ctx.font = `bold ${fontSize}px Arial`;
                ctx.fillStyle = isHighlighted ? '#FFFF00' : box.color;
                ctx.fillText(`#${box.id}`, x, y - 5);
            });
        }

        ctx.restore();
    },

    renderStats() {
        const result = this.getCurrentResult();
        if (!result) return;

        const stats = result.statistics;
        const { statGoodCount, statGoodPercent, statBadCount, statBadPercent, statTotal, statProgressBar, statExecutionTime } = this.elements;

        statGoodCount.textContent = stats.good_seeds;
        statGoodPercent.textContent = `${stats.good_percentage}%`;
        statBadCount.textContent = stats.bad_seeds;
        statBadPercent.textContent = `${stats.bad_percentage}%`;
        statTotal.textContent = result.total_seeds;

        if (statExecutionTime) {
            const ms = this.state.reportMetadata?.processingDurationMs;
            statExecutionTime.textContent = ms != null ? `${(ms / 1000).toFixed(2)} s` : '--';
        }

        // Animate progress bar
        setTimeout(() => {
            statProgressBar.style.width = `${stats.good_percentage}%`;
        }, 100);
    },

    renderSeedsList(filter = 'all') {
        const result = this.getCurrentResult();
        if (!result) return;

        const list = this.elements.seedsList;
        list.innerHTML = '';

        const seeds = result.bounding_boxes.filter(seed => {
            if (filter === 'all') return true;
            return seed.quality === filter;
        });

        if (seeds.length === 0) {
            list.innerHTML = '<div class="text-center py-4 text-gray-400">No seeds found for this filter.</div>';
            return;
        }

        seeds.forEach(seed => {
            const item = document.createElement('div');
            item.className = `p-3 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors flex items-center justify-between group ${this.state.highlightedSeedId === seed.id ? 'bg-blue-50 border-blue-200' : ''}`;

            const iconColor = seed.quality === 'Good' ? 'text-green-500' : 'text-red-500';
            const icon = seed.quality === 'Good' ? 'check-circle' : 'x-circle';

            const typeColors = {
                'coffee': 'seed-type-coffee',
                'maize': 'seed-type-maize'
            };
            const seedType = (seed.seed_type || 'Unknown').toLowerCase();
            const typeClass = typeColors[seedType] || 'seed-type-unknown';
            const displayType = seed.seed_type ? (seed.seed_type.charAt(0).toUpperCase() + seed.seed_type.slice(1)) : 'Unknown';

            // Removed confidence score as requested
            item.innerHTML = `
                <div class="flex items-center gap-3">
                    <i data-lucide="${icon}" class="w-5 h-5 ${iconColor}"></i>
                    <div>
                        <div class="flex items-center gap-2">
                            <p class="font-medium text-gray-900 text-sm">Seed #${seed.id}</p>
                            <span class="seed-type-badge ${typeClass}">
                                ${displayType}
                            </span>
                        </div>
                    </div>
                </div>
                <div class="text-xs font-medium px-2 py-1 rounded bg-gray-100 text-gray-600 group-hover:bg-white">
                    ${seed.quality}
                </div>
            `;

            item.addEventListener('click', () => {
                this.state.highlightedSeedId = seed.id;
                this.renderSeedsList(filter); // Re-render to update active state

                // Zoom to seed
                const image = this.getImage();
                if (image) {
                    const canvas = this.elements.canvas;
                    const container = this.elements.canvasContainer;

                    canvas.width = container.clientWidth;
                    canvas.height = 500;

                    const scaleX = canvas.width / image.width;
                    const scaleY = canvas.height / image.height;
                    const baseScale = Math.min(scaleX, scaleY);

                    // Target zoom level
                    this.state.zoomLevel = 3;
                    const currentScale = baseScale * this.state.zoomLevel;

                    // Calculate scale between API coords and Image coords
                    // (Handle case where API returns coords for a different image size than the loaded one)
                    const apiScaleX = image.width / result.image_dimensions.width;
                    const apiScaleY = image.height / result.image_dimensions.height;

                    // Ensure coordinates are numbers to prevent string concatenation
                    const sX = Number(seed.x1);
                    const sY = Number(seed.y1);
                    const sW = Number(seed.width);
                    const sH = Number(seed.height);

                    const scaledX = sX * apiScaleX;
                    const scaledY = sY * apiScaleY;
                    const scaledW = sW * apiScaleX;
                    const scaledH = sH * apiScaleY;

                    const seedCenterX = scaledX + scaledW / 2;
                    const seedCenterY = scaledY + scaledH / 2;

                    const centerX = (canvas.width - image.width * currentScale) / 2;
                    const centerY = (canvas.height - image.height * currentScale) / 2;

                    this.state.offsetX = (canvas.width / 2) - centerX - (seedCenterX * currentScale);
                    this.state.offsetY = (canvas.height / 2) - centerY - (seedCenterY * currentScale);

                    // Show Details
                    this.showSeedDetails(seed);
                }

                this.draw();
            });

            list.appendChild(item);
        });

        lucide.createIcons();
    },

    showSeedDetails(seed) {
        const { detailsCard, detailId, detailQuality, detailConfidence } = this.elements;

        detailsCard.classList.remove('hidden');

        detailId.textContent = `#${seed.id}`;
        detailQuality.textContent = seed.quality;
        detailQuality.className = `font-medium ${seed.quality === 'Good' ? 'text-green-600' : 'text-red-600'}`;

        // Use classification_confidence as requested
        detailConfidence.textContent = `${seed.classification_confidence}%`;

        // Inject Seed Type if not present or update it
        let detailTypeRow = document.getElementById('detail-type-row');
        if (!detailTypeRow) {
            const container = detailsCard.querySelector('.space-y-3');
            detailTypeRow = document.createElement('div');
            detailTypeRow.id = 'detail-type-row';
            detailTypeRow.className = 'flex justify-between';
            detailTypeRow.innerHTML = `
                <span class="text-gray-500">Type</span>
                <span id="detail-type" class="font-medium">--</span>
            `;
            // Insert as first item
            container.insertBefore(detailTypeRow, container.firstChild);
        }

        const detailType = document.getElementById('detail-type');
        if (detailType) {
            detailType.textContent = seed.seed_type ? (seed.seed_type.charAt(0).toUpperCase() + seed.seed_type.slice(1)) : 'Unknown';
        }
    },

    filterSeeds(filter) {
        // Update button styles
        const buttons = {
            'all': this.elements.filterAll,
            'Good': this.elements.filterGood,
            'Bad': this.elements.filterBad
        };

        Object.keys(buttons).forEach(key => {
            const btn = buttons[key];
            if (key === filter) {
                btn.classList.add('bg-gray-100', 'text-gray-900', 'shadow-sm');
                btn.classList.remove('text-gray-600', 'hover:bg-gray-50');
            } else {
                btn.classList.remove('bg-gray-100', 'text-gray-900', 'shadow-sm');
                btn.classList.add('text-gray-600', 'hover:bg-gray-50');
            }
        });

        this.renderSeedsList(filter);
    },

    showLoading(isLoading) {
        if (isLoading) {
            this.elements.uploadSection.classList.add('hidden');
            this.elements.loadingSection.classList.remove('hidden');
            this.elements.resultsSection.classList.add('hidden');
        } else {
            this.elements.loadingSection.classList.add('hidden');
        }
    },

    showResults() {
        this.elements.loadingSection.classList.add('hidden');
        this.elements.resultsSection.classList.remove('hidden');
    },

    showError(msg) {
        this.elements.errorMessage.classList.remove('hidden');
        this.elements.errorText.textContent = msg;
    },

    hideError() {
        this.elements.errorMessage.classList.add('hidden');
    },

    reset() {
        this.state.files = [];
        this.state.results = [];
        this.state.images = [];
        this.state.currentTabIndex = 0;
        this.state.highlightedSeedId = null;
        this.state.zoomLevel = 1;
        this.state.offsetX = 0;
        this.state.offsetY = 0;
        this.state.reportMetadata = null;

        this.elements.fileInput.value = '';
        this.elements.resultsSection.classList.add('hidden');
        this.elements.uploadSection.classList.remove('hidden');
        this.hideError();
    },

    generatePDF() {
        if (!this.state.results || this.state.results.length === 0) {
            this.showError('No results to export.');
            return;
        }
        if (!window.jspdf || !window.jspdf.jsPDF) {
            this.showError('PDF library not loaded.');
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        const pageW = doc.internal.pageSize.getWidth();
        const pageH = doc.internal.pageSize.getHeight();
        const GREEN = [22, 163, 74];
        const GOOD = [34, 197, 94];
        const BAD = [239, 68, 68];
        const MUTED = [100, 116, 139];
        const LIGHT_BG = [248, 250, 252];

        try {
            const meta = this.state.reportMetadata;
            let totalGood = 0, totalBad = 0, totalSeeds = 0;
            this.state.results.forEach(r => {
                totalGood += r.statistics?.good_seeds || 0;
                totalBad += r.statistics?.bad_seeds || 0;
                totalSeeds += r.total_seeds || 0;
            });
            const overallStats = meta?.overallStatistics ?? (totalSeeds > 0 ? {
                good_seeds: totalGood,
                bad_seeds: totalBad,
                good_percentage: Math.round((totalGood / totalSeeds) * 1000) / 10,
                bad_percentage: Math.round((totalBad / totalSeeds) * 1000) / 10
            } : null);
            const executionMs = meta?.processingDurationMs ?? null;

            // ========== Page 1: Summary / Analytics (beautiful layout) ==========
            doc.setFontSize(24);
            doc.setTextColor(...GREEN);
            doc.text("Seed Quality Analysis Report", pageW / 2, 22, { align: 'center' });

            doc.setFontSize(10);
            doc.setTextColor(...MUTED);
            doc.text(`Generated ${new Date().toLocaleString()}`, pageW / 2, 30, { align: 'center' });
            doc.text(`${this.state.results.length} image(s) analyzed`, pageW / 2, 36, { align: 'center' });

            let y = 46;

            // Execution time callout (box with padding)
            if (executionMs != null) {
                const sec = (executionMs / 1000).toFixed(2);
                const boxX = 20, boxY = y - 2, boxW = 64, boxH = 24;
                doc.setDrawColor(203, 213, 225);
                doc.setFillColor(...LIGHT_BG);
                doc.rect(boxX, boxY, boxW, boxH, 'FD');
                doc.setFontSize(10);
                doc.setTextColor(30, 64, 175);
                doc.text("Execution time", boxX + 8, boxY + 9);
                doc.setFontSize(14);
                doc.setTextColor(0);
                doc.text(`${sec} s`, boxX + 8, boxY + 19);
                y += boxH + 8;
            }

            // Overall stats (left) and pie chart (right) on one row
            if (overallStats) {
                const pieSize = 55;
                const pieX = pageW - 20 - pieSize;

                doc.setFontSize(11);
                doc.setTextColor(0);
                doc.text(`Total seeds: ${overallStats.good_seeds + overallStats.bad_seeds}`, 20, y);
                doc.setTextColor(...GOOD);
                doc.text(`Good: ${overallStats.good_seeds} (${overallStats.good_percentage}%)`, 20, y + 8);
                doc.setTextColor(...BAD);
                doc.text(`Bad: ${overallStats.bad_seeds} (${overallStats.bad_percentage}%)`, 20, y + 16);
                doc.setTextColor(0);

                if (totalSeeds > 0) {
                    const scale = 3;
                    const pieCanvas = document.createElement('canvas');
                    pieCanvas.width = 120 * scale;
                    pieCanvas.height = 120 * scale;
                    const pCtx = pieCanvas.getContext('2d');
                    pCtx.scale(scale, scale);
                    const cx = 60, cy = 60, r = 48;
                    const goodPct = overallStats.good_seeds / totalSeeds;
                    const badPct = overallStats.bad_seeds / totalSeeds;
                    const startAngle = -Math.PI / 2;
                    const goodPctLabel = Math.round(overallStats.good_percentage);
                    const badPctLabel = Math.round(overallStats.bad_percentage);
                    if (goodPct > 0) {
                        pCtx.beginPath();
                        pCtx.moveTo(cx, cy);
                        pCtx.arc(cx, cy, r, startAngle, startAngle + goodPct * 2 * Math.PI);
                        pCtx.closePath();
                        pCtx.fillStyle = 'rgb(34, 197, 94)';
                        pCtx.fill();
                    }
                    if (badPct > 0) {
                        pCtx.beginPath();
                        pCtx.moveTo(cx, cy);
                        pCtx.arc(cx, cy, r, startAngle + goodPct * 2 * Math.PI, startAngle + 2 * Math.PI);
                        pCtx.closePath();
                        pCtx.fillStyle = 'rgb(239, 68, 68)';
                        pCtx.fill();
                    }
                    pCtx.font = 'bold 12px Arial';
                    pCtx.textAlign = 'center';
                    pCtx.textBaseline = 'middle';
                    const labelR = r * 0.55;
                    pCtx.shadowColor = 'rgba(0,0,0,0.6)';
                    pCtx.shadowBlur = 4;
                    pCtx.shadowOffsetX = 0;
                    pCtx.shadowOffsetY = 0;
                    if (goodPct >= 0.08) {
                        const midAngle = startAngle + goodPct * Math.PI;
                        const tx = cx + labelR * Math.cos(midAngle);
                        const ty = cy + labelR * Math.sin(midAngle);
                        pCtx.fillStyle = '#fff';
                        pCtx.fillText(goodPctLabel + '%', tx, ty);
                    }
                    if (badPct >= 0.08) {
                        const midAngle = startAngle + goodPct * 2 * Math.PI + badPct * Math.PI;
                        const tx = cx + labelR * Math.cos(midAngle);
                        const ty = cy + labelR * Math.sin(midAngle);
                        pCtx.fillStyle = '#fff';
                        pCtx.fillText(badPctLabel + '%', tx, ty);
                    }
                    pCtx.shadowBlur = 0;
                    pCtx.shadowColor = 'transparent';
                    const pieDataUrl = pieCanvas.toDataURL('image/png');
                    doc.addImage(pieDataUrl, 'PNG', pieX, y, pieSize, pieSize);
                }
                y += Math.max(28, pieSize + 5);
            }

            const summaryContentEndY = y;
            const imageStartPages = [];

            // ========== Per-image pages ==========
            this.state.results.forEach((result, index) => {
                const image = this.state.images[index];
                const file = this.state.files[index];
                const stats = result.statistics;
                if (!image || !result) return;

                imageStartPages[index] = doc.internal.getNumberOfPages() + 1;
                const fileName = (file?.name) || result.filename || `image_${index}.jpg`;
                doc.addPage();

                doc.setFontSize(20);
                doc.setTextColor(...GREEN);
                doc.text("Seed Quality Analysis Report", 20, 20);
                doc.setFontSize(10);
                doc.setTextColor(...MUTED);
                doc.text(`Generated ${new Date().toLocaleString()}`, 20, 28);
                doc.text(`File: ${fileName}`, 20, 34);

                doc.setFontSize(12);
                doc.setTextColor(0);
                doc.text("Summary", 20, 44);

                // Calculate seed type stats
                const typeStats = {};
                (result.bounding_boxes || []).forEach(seed => {
                    const type = (seed.seed_type || 'Unknown');
                    const displayType = type.charAt(0).toUpperCase() + type.slice(1);
                    if (!typeStats[displayType]) {
                        typeStats[displayType] = { good: 0, bad: 0, total: 0 };
                    }
                    typeStats[displayType].total++;
                    if (seed.quality === 'Good') typeStats[displayType].good++;
                    else typeStats[displayType].bad++;
                });

                doc.setFontSize(11);
                doc.text(`Total: ${result.total_seeds}  •  Good: ${stats.good_seeds} (${stats.good_percentage}%)  •  Bad: ${stats.bad_seeds} (${stats.bad_percentage}%)`, 20, 52);

                // Add Type Breakdown
                let typeY = 58;
                const typeText = "By Type: " + Object.keys(typeStats).map(type => {
                    const s = typeStats[type];
                    return `${type} (${s.good}G / ${s.bad}B)`;
                }).join("  •  ");

                if (Object.keys(typeStats).length > 0) {
                    doc.text(typeText, 20, typeY);
                    typeY += 6;
                }

                doc.text(`Mode: ${this.state.mode === 'fast' ? 'Fast' : 'Accurate'}`, 20, typeY);

                const tempCanvas = document.createElement('canvas');
                const tempCtx = tempCanvas.getContext('2d');
                tempCanvas.width = image.width;
                tempCanvas.height = image.height;
                tempCtx.drawImage(image, 0, 0);
                if (result.bounding_boxes) {
                    result.bounding_boxes.forEach(box => {
                        tempCtx.strokeStyle = box.color;
                        tempCtx.lineWidth = 5;
                        tempCtx.strokeRect(box.x1, box.y1, box.width, box.height);
                        tempCtx.font = 'bold 24px Arial';
                        tempCtx.fillStyle = box.color;
                        tempCtx.fillText(`#${box.id}`, box.x1, box.y1 - 10);
                    });
                }
                let imgData;
                try {
                    imgData = tempCanvas.toDataURL("image/jpeg", 0.8);
                } catch (e) {
                    console.error('Canvas export failed:', e);
                    this.showError('Export failed: images must be loaded with CORS. Try opening the batch again.');
                    return;
                }
                const imgProps = doc.getImageProperties(imgData);
                const imgH = (imgProps.height * (pageW - 40)) / imgProps.width;
                doc.addImage(imgData, 'JPEG', 20, typeY + 8, pageW - 40, imgH);

                // doc.setFontSize(20);
                // doc.setTextColor(...GREEN);
                // doc.text("Seed Quality Analysis Report", 20, 20);
                // doc.setFontSize(10);
                // doc.setTextColor(...MUTED);
                // doc.text("Generated " + new Date().toLocaleString(), 20, 28);
                // doc.text("File: " + fileName, 20, 34);

                doc.setFontSize(12);
                doc.addPage();
                doc.setFontSize(14);
                doc.setTextColor(0);
                doc.text("Detailed Seed List", 20, 22);
                doc.setFontSize(10);
                doc.setTextColor(...MUTED);
                doc.text("File: " + fileName, 20, 30);
                const crops = [];
                const tableData = (result.bounding_boxes || []).map(seed => {
                    try { crops.push(this.getCroppedSeedDataUrl(image, seed)); } catch (_) { crops.push(null); }
                    const displayType = seed.seed_type ? (seed.seed_type.charAt(0).toUpperCase() + seed.seed_type.slice(1)) : '-';
                    return [seed.id, '', displayType, seed.quality, String(seed.classification_confidence) + '%'];
                });
                doc.autoTable({
                    startY: 36,
                    head: [['ID', 'Image', 'Type', 'Quality', 'Conf %']],
                    body: tableData,
                    theme: 'grid',
                    headStyles: { fillColor: GREEN },
                    columnStyles: { 0: { cellWidth: 20 }, 1: { cellWidth: 30, minCellHeight: 20 }, 2: { cellWidth: 30 }, 3: { cellWidth: 30 }, 4: { cellWidth: 30 } },
                    didDrawCell: (data) => {
                        if (data.column.index === 1 && data.cell.section === 'body' && crops[data.row.index]) {
                            const img = crops[data.row.index];
                            const dim = 12;
                            doc.addImage(img, 'JPEG', data.cell.x + (data.cell.width - dim) / 2, data.cell.y + (data.cell.height - dim) / 2, dim, dim);
                        }
                    }
                });
            });

            // Per-image breakdown on page 1 (with Page column); table may add pages so we fix refs and redraw
            if (this.state.results.length > 1) {
                const pagesBeforeTable = doc.internal.getNumberOfPages();
                doc.setPage(1);
                doc.setFontSize(12);
                doc.setTextColor(0);
                doc.text("Per-image breakdown", 20, summaryContentEndY);
                const buildTableBody = (pageRefs) => this.state.results.map((r, i) => {
                    const s = r.statistics || {};
                    const total = r.total_seeds || 0;
                    const goodPct = total > 0 ? Math.round((s.good_seeds || 0) / total * 1000) / 10 : 0;
                    const name = (this.state.files[i]?.name) || r.filename || `Image ${i + 1}`;
                    return [name.length > 28 ? name.slice(0, 25) + '...' : name, s.good_seeds || 0, s.bad_seeds || 0, total, goodPct + '%', String(pageRefs[i] ?? '')];
                });
                doc.autoTable({
                    startY: summaryContentEndY + 5,
                    head: [['Image', 'Good', 'Bad', 'Total', 'Good %', 'Page']],
                    body: buildTableBody(imageStartPages),
                    theme: 'grid',
                    headStyles: { fillColor: GREEN },
                    columnStyles: { 0: { cellWidth: 58 }, 1: { cellWidth: 18 }, 2: { cellWidth: 18 }, 3: { cellWidth: 18 }, 4: { cellWidth: 22 }, 5: { cellWidth: 18 } }
                });
                const pagesAddedByTable = doc.internal.getNumberOfPages() - pagesBeforeTable;
                for (let i = 0; i < imageStartPages.length; i++) {
                    imageStartPages[i] += pagesAddedByTable;
                }
                doc.setFillColor(255, 255, 255);
                doc.rect(20, summaryContentEndY + 5, pageW - 40, pageH - (summaryContentEndY + 5) - 12, 'F');
                for (let p = pagesBeforeTable + 1; p <= doc.internal.getNumberOfPages(); p++) {
                    doc.setPage(p);
                    doc.rect(20, 15, pageW - 40, pageH - 25, 'F');
                }
                doc.setPage(1);
                doc.text("Per-image breakdown", 20, summaryContentEndY);
                doc.autoTable({
                    startY: summaryContentEndY + 5,
                    head: [['Image', 'Good', 'Bad', 'Total', 'Good %', 'Page']],
                    body: buildTableBody(imageStartPages),
                    theme: 'grid',
                    headStyles: { fillColor: GREEN },
                    columnStyles: { 0: { cellWidth: 58 }, 1: { cellWidth: 18 }, 2: { cellWidth: 18 }, 3: { cellWidth: 18 }, 4: { cellWidth: 22 }, 5: { cellWidth: 18 } }
                });
            }

            // Page numbers on every page (including those added by autoTable for long seed lists)
            const totalPages = doc.internal.getNumberOfPages();
            for (let p = 1; p <= totalPages; p++) {
                doc.setPage(p);
                doc.setFontSize(9);
                doc.setTextColor(128);
                doc.text('Page ' + p + ' of ' + totalPages, pageW / 2, pageH - 10, { align: 'center' });
            }

            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            doc.save(`seed-analysis-report-${timestamp}.pdf`);
        } catch (err) {
            console.error('PDF export failed:', err);
            this.showError(err.message || 'Failed to generate PDF.');
        }
    },

    getCroppedSeedDataUrl(image, box) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const w = box.width;
        const h = box.height;

        // Add some padding? No, exact crop is fine.
        canvas.width = w;
        canvas.height = h;

        // Draw crop
        ctx.drawImage(image, box.x1, box.y1, w, h, 0, 0, w, h);
        return canvas.toDataURL('image/jpeg', 0.9);
    },

    getImage() {
        return this.state.images[this.state.currentTabIndex];
    },

    // ============================================================================
    // History Functions
    // ============================================================================

    async showHistory() {
        console.log('showHistory called');
        if (!this.elements.historySection) {
            console.error('History section not found');
            return;
        }

        this.elements.uploadSection.classList.add('hidden');
        this.elements.resultsSection.classList.add('hidden');
        this.elements.loadingSection.classList.add('hidden');
        this.elements.historySection.classList.remove('hidden');

        await this.loadHistoryStats();
        await this.loadBatches();
    },

    hideHistory() {
        this.elements.historySection.classList.add('hidden');
        // Don't automatically show upload - let the caller decide what to show
    },

    async loadHistoryStats() {
        try {
            const response = await fetch(`${this.API_URL}/api/stats`);
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Stats API error:', response.status, errorText);
                throw new Error(`Failed to load stats: ${response.status}`);
            }

            const data = await response.json();
            if (data.success && data.stats) {
                this.state.historyStats = data.stats;
                this.renderHistoryStats(data.stats);
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            console.error('Failed to load history stats:', error);
            // Show empty stats instead of error
            this.renderHistoryStats({
                total_batches: 0,
                total_seeds_analyzed: 0,
                total_good_seeds: 0,
                total_bad_seeds: 0,
                overall_good_percentage: 0.0,
                overall_bad_percentage: 0.0
            });
        }
    },

    renderHistoryStats(stats) {
        const statsHtml = `
            <div class="bg-white p-5 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow" style="display: flex; flex-direction: column;">
                <div class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Total Batches</div>
                <div class="text-3xl font-bold text-gray-900">${stats.total_batches}</div>
            </div>
            <div class="bg-white p-5 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow" style="display: flex; flex-direction: column;">
                <div class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Total Seeds</div>
                <div class="text-3xl font-bold text-gray-900">${stats.total_seeds_analyzed.toLocaleString()}</div>
            </div>
            <div class="bg-white p-5 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow" style="display: flex; flex-direction: column;">
                <div class="flex items-center gap-2 mb-3">
                    <div class="p-2 bg-green-500 rounded-lg text-white flex-shrink-0" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="check-circle" class="w-5 h-5"></i>
                    </div>
                    <div class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Good Seeds</div>
                </div>
                <div class="text-3xl font-bold text-green-600">${stats.total_good_seeds.toLocaleString()}</div>
                <div class="text-xs font-medium text-gray-500 mt-2">${stats.overall_good_percentage.toFixed(1)}%</div>
            </div>
            <div class="bg-white p-5 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow" style="display: flex; flex-direction: column;">
                <div class="flex items-center gap-2 mb-3">
                    <div class="p-2 bg-red-500 rounded-lg text-white flex-shrink-0" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="x-circle" class="w-5 h-5"></i>
                    </div>
                    <div class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Bad Seeds</div>
                </div>
                <div class="text-3xl font-bold text-red-600">${stats.total_bad_seeds.toLocaleString()}</div>
                <div class="text-xs font-medium text-gray-500 mt-2">${stats.overall_bad_percentage.toFixed(1)}%</div>
            </div>
        `;
        this.elements.historyStats.innerHTML = statsHtml;
        // Force grid display
        this.elements.historyStats.style.display = 'grid';
        this.elements.historyStats.style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';
        this.elements.historyStats.style.gap = '1rem';
        // Initialize icons after DOM is ready
        setTimeout(() => {
            if (typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons();
            }
        }, 50);
    },

    async loadBatches() {
        const { historyPage, historyLimit, historyStatusFilter } = this.state;

        let url = `${this.API_URL}/api/batches?page=${historyPage}&limit=${historyLimit}`;
        if (historyStatusFilter) {
            url += `&status=${historyStatusFilter}`;
        }

        try {
            this.elements.batchesList.innerHTML = '<div class="text-center py-10 text-gray-400"><i data-lucide="loader" class="w-8 h-8 mx-auto mb-2 animate-spin"></i><p>Loading batches...</p></div>';
            lucide.createIcons();

            const response = await fetch(url);
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('No scan history found');
                }
                throw new Error('Failed to load batches');
            }

            const data = await response.json();
            this.renderBatches(data.batches);
            this.renderPagination(data.pagination);
        } catch (error) {
            console.error('Failed to load batches:', error);
            const message = error.message === 'No scan history found'
                ? '<div class="text-center py-10 text-gray-500">No scan history found</div>'
                : '<div class="text-center py-10 text-red-500">Failed to load batches</div>';
            this.elements.batchesList.innerHTML = message;
        }
    },

    renderBatches(batches) {
        if (batches.length === 0) {
            this.elements.batchesList.innerHTML = `
                <div class="text-center py-20">
                    <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-100 mb-4">
                        <i data-lucide="inbox" class="w-10 h-10 text-gray-400"></i>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">No batches found</h3>
                    <p class="text-gray-500">Upload some images to get started!</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        const batchesHtml = batches.map(batch => {
            const statusConfig = {
                'COMPLETED': {
                    badge: 'bg-green-100 text-green-700 border-green-200',
                    icon: 'check-circle'
                },
                'FAILED': {
                    badge: 'bg-red-100 text-red-700 border-red-200',
                    icon: 'x-circle'
                },
                'PENDING': {
                    badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
                    icon: 'clock'
                },
                'PROCESSING': {
                    badge: 'bg-blue-100 text-blue-700 border-blue-200',
                    icon: 'loader'
                }
            };

            const status = statusConfig[batch.status] || {
                badge: 'bg-gray-100 text-gray-700 border-gray-200',
                icon: 'help-circle'
            };

            const date = new Date(batch.created_at);
            const formattedDate = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            const goodPercentage = batch.total_seeds > 0
                ? ((batch.good_seeds_count / batch.total_seeds) * 100).toFixed(1)
                : 0;

            return `
                <div class="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-all duration-200 cursor-pointer group overflow-hidden" data-batch-id="${batch.id}">
                    <div class="p-5">
                        <div class="flex items-start justify-between mb-4">
                            <div class="flex-1">
                                <div class="flex items-center gap-3 mb-2">
                                    <h3 class="text-xl font-bold text-gray-900">Batch #${batch.id}</h3>
                                    <span class="px-2.5 py-1 rounded-md text-xs font-semibold border ${status.badge} flex items-center gap-1">
                                        <i data-lucide="${status.icon}" class="w-3 h-3"></i>
                                        ${batch.status}
                                    </span>
                                </div>
                                <p class="text-sm text-gray-500 flex items-center gap-1">
                                    <i data-lucide="calendar" class="w-4 h-4"></i>
                                    ${formattedDate}
                                </p>
                            </div>
                            ${batch.first_image_url ? `
                                <div class="ml-4 flex-shrink-0">
                                    <img src="${this.API_URL}${batch.first_image_url}" 
                                         alt="Batch ${batch.id}" 
                                         class="w-24 h-24 object-cover rounded-lg border-2 border-gray-200 group-hover:border-seed-green-300 transition-colors"
                                         onerror="this.style.display='none'">
                                </div>
                            ` : `
                                <div class="ml-4 flex-shrink-0 w-24 h-24 bg-gray-100 rounded-lg flex items-center justify-center border-2 border-gray-200">
                                    <i data-lucide="image" class="w-8 h-8 text-gray-400"></i>
                                </div>
                            `}
                        </div>
                        
                        <!-- Stats Grid -->
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                            <div class="bg-gray-50 rounded-lg p-3 border border-gray-100">
                                <div class="text-xs font-medium text-gray-500 mb-1 uppercase tracking-wide">Total</div>
                                <div class="text-lg font-bold text-gray-900">${batch.total_seeds}</div>
                            </div>
                            <div class="bg-green-50 rounded-lg p-3 border border-green-100">
                                <div class="text-xs font-medium text-green-600 mb-1 uppercase tracking-wide">Good</div>
                                <div class="text-lg font-bold text-green-700">${batch.good_seeds_count}</div>
                                <div class="text-xs text-green-600 mt-0.5">${goodPercentage}%</div>
                            </div>
                            <div class="bg-red-50 rounded-lg p-3 border border-red-100">
                                <div class="text-xs font-medium text-red-600 mb-1 uppercase tracking-wide">Bad</div>
                                <div class="text-lg font-bold text-red-700">${batch.bad_seeds_count}</div>
                                <div class="text-xs text-red-600 mt-0.5">${(100 - goodPercentage).toFixed(1)}%</div>
                            </div>
                            <div class="bg-blue-50 rounded-lg p-3 border border-blue-100">
                                <div class="text-xs font-medium text-blue-600 mb-1 uppercase tracking-wide">Confidence</div>
                                <div class="text-lg font-bold text-blue-700">${(batch.avg_confidence_score * 100).toFixed(1)}%</div>
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div class="flex items-center justify-between pt-4 border-t border-gray-100">
                            <div class="flex items-center gap-4 text-sm text-gray-600">
                                <span class="flex items-center gap-1">
                                    <i data-lucide="image" class="w-4 h-4"></i>
                                    ${batch.image_count} image${batch.image_count !== 1 ? 's' : ''}
                                </span>
                                ${batch.processing_duration_ms ? `
                                    <span class="flex items-center gap-1">
                                        <i data-lucide="clock" class="w-4 h-4"></i>
                                        ${(batch.processing_duration_ms / 1000).toFixed(1)}s
                                    </span>
                                ` : ''}
                            </div>
                            <button class="flex items-center gap-2 px-4 py-2 bg-seed-green-600 hover:bg-seed-green-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm group-hover:shadow-md">
                                <span>View Details</span>
                                <i data-lucide="arrow-right" class="w-4 h-4 group-hover:translate-x-1 transition-transform"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        this.elements.batchesList.innerHTML = batchesHtml;
        lucide.createIcons();

        // Add click handlers
        this.elements.batchesList.querySelectorAll('[data-batch-id]').forEach(el => {
            el.addEventListener('click', () => {
                const batchId = parseInt(el.getAttribute('data-batch-id'));
                this.loadBatchDetails(batchId);
            });
        });
    },

    renderPagination(pagination) {
        if (pagination.total_pages <= 1) {
            this.elements.historyPagination.innerHTML = '';
            return;
        }

        const paginationHtml = `
            <div class="flex items-center justify-center gap-3 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <button ${!pagination.has_prev ? 'disabled' : ''} 
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${pagination.has_prev
                ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 shadow-sm'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-transparent'
            }"
                    ${pagination.has_prev ? `onclick="App.goToHistoryPage(${pagination.page - 1})"` : ''}>
                    <i data-lucide="chevron-left" class="w-4 h-4"></i>
                    Previous
                </button>
                <div class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-50 rounded-lg">
                    Page <span class="font-bold text-gray-900">${pagination.page}</span> of <span class="font-bold text-gray-900">${pagination.total_pages}</span>
                </div>
                <button ${!pagination.has_next ? 'disabled' : ''}
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${pagination.has_next
                ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 shadow-sm'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-transparent'
            }"
                    ${pagination.has_next ? `onclick="App.goToHistoryPage(${pagination.page + 1})"` : ''}>
                    Next
                    <i data-lucide="chevron-right" class="w-4 h-4"></i>
                </button>
            </div>
        `;
        this.elements.historyPagination.innerHTML = paginationHtml;
        lucide.createIcons();
    },

    goToHistoryPage(page) {
        this.state.historyPage = page;
        this.loadBatches();
    },

    setHistoryStatusFilter(status) {
        this.state.historyStatusFilter = status;
        this.state.historyPage = 1; // Reset to first page

        // Update button styles
        const buttons = {
            null: this.elements.filterStatusAll,
            'COMPLETED': this.elements.filterStatusCompleted,
            'FAILED': this.elements.filterStatusFailed,
            'PENDING': this.elements.filterStatusPending
        };

        Object.keys(buttons).forEach(key => {
            const btn = buttons[key];
            if (key === (status || 'null')) {
                btn.classList.add('bg-gray-100', 'text-gray-900', 'shadow-sm');
                btn.classList.remove('text-gray-600', 'hover:bg-gray-50');
            } else {
                btn.classList.remove('bg-gray-100', 'text-gray-900', 'shadow-sm');
                btn.classList.add('text-gray-600', 'hover:bg-gray-50');
            }
        });

        this.loadBatches();
    },

    async loadBatchDetails(batchId) {
        try {
            this.showLoading(true);

            // Fetch batch details
            const batchResponse = await fetch(`${this.API_URL}/api/batches/${batchId}`);
            if (!batchResponse.ok) throw new Error('Failed to load batch details');
            const batchData = await batchResponse.json();

            // Fetch detections
            const detectionsResponse = await fetch(`${this.API_URL}/api/batches/${batchId}/detections`);
            if (!detectionsResponse.ok) throw new Error('Failed to load detections');
            const detectionsData = await detectionsResponse.json();

            // Process data for display
            const batch = batchData.batch;
            const images = batch.images;

            console.log('Batch images from API:', images);

            // Load images with crossOrigin so we can draw them to canvas for PDF export
            this.state.images = await Promise.all(images.map((img, idx) => {
                return new Promise((resolve, reject) => {
                    const image = new Image();
                    image.crossOrigin = 'anonymous';
                    const imageUrl = `${this.API_URL}${img.url}`;
                    image.onload = () => resolve(image);
                    image.onerror = (e) => {
                        console.error(`Failed to load image ${idx} (ID: ${img.id}):`, imageUrl, e);
                        const placeholder = new Image();
                        placeholder.width = img.width || 800;
                        placeholder.height = img.height || 600;
                        const canvas = document.createElement('canvas');
                        canvas.width = img.width || 800;
                        canvas.height = img.height || 600;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#f0f0f0';
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        ctx.fillStyle = '#999';
                        ctx.font = '20px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText('Image failed to load', canvas.width / 2, canvas.height / 2);
                        placeholder.src = canvas.toDataURL();
                        resolve(placeholder);
                    };
                    image.src = imageUrl;
                });
            }));

            // Group detections by image
            const detectionsByImage = {};
            detectionsData.detections.forEach(det => {
                if (!detectionsByImage[det.image_id]) {
                    detectionsByImage[det.image_id] = [];
                }
                detectionsByImage[det.image_id].push(det);
            });

            // Create a map of image ID to loaded Image object
            const imageMap = {};
            images.forEach((img, idx) => {
                imageMap[img.id] = this.state.images[idx];
            });

            console.log('Image map:', Object.keys(imageMap).map(id => ({ id, url: images.find(img => img.id == id)?.url })));

            // Format results - ensure we match images by ID, not index
            this.state.results = images.map((img, idx) => {
                const detections = detectionsByImage[img.id] || [];
                const goodCount = detections.filter(d => d.quality_label === 'GOOD').length;
                const badCount = detections.filter(d => d.quality_label === 'BAD').length;
                const total = detections.length;

                // Get the corresponding loaded image
                const loadedImage = imageMap[img.id];
                if (!loadedImage) {
                    console.error(`No loaded image found for image ID ${img.id}`);
                }

                // Convert detections to bounding boxes format
                const bounding_boxes = detections.map((det, detIdx) => {
                    // Convert normalized coordinates back to pixel coordinates
                    const x1 = det.box_x_norm * img.width;
                    const y1 = det.box_y_norm * img.height;
                    const width = det.box_w_norm * img.width;
                    const height = det.box_h_norm * img.height;

                    return {
                        id: detIdx,
                        x1: x1,
                        y1: y1,
                        x2: x1 + width,
                        y2: y1 + height,
                        width: width,
                        height: height,
                        area: det.area,
                        aspect_ratio: det.aspect_ratio,
                        centroid: { x: det.centroid_x, y: det.centroid_y },
                        quality: det.quality_label === 'GOOD' ? 'Good' : 'Bad',
                        detection_confidence: det.detection_confidence,
                        good_percentage: det.good_percentage,
                        bad_percentage: det.bad_percentage,
                        classification_confidence: (det.confidence_score * 100).toFixed(2),
                        raw_probability: det.confidence_score,
                        color: det.quality_label === 'GOOD' ? '#00FF00' : '#FF0000'
                    };
                });

                return {
                    filename: img.original_filename || `image_${idx}`,
                    image_index: idx,
                    image_id: img.id, // Store image ID for reference
                    total_seeds: total,
                    bounding_boxes: bounding_boxes,
                    statistics: {
                        good_seeds: goodCount,
                        bad_seeds: badCount,
                        good_percentage: total > 0 ? ((goodCount / total) * 100).toFixed(2) : 0,
                        bad_percentage: total > 0 ? ((badCount / total) * 100).toFixed(2) : 0
                    },
                    image_dimensions: {
                        width: img.width,
                        height: img.height
                    }
                };
            });

            // Ensure images array matches results array order
            // Reorder images array to match results order
            this.state.images = images.map(img => imageMap[img.id]);

            // Set files for tabs - ensure same length as images
            this.state.files = images.map((img, idx) => ({
                name: img.original_filename || `image_${idx}.jpg`
            }));

            // Ensure arrays are aligned
            if (this.state.images.length !== this.state.results.length) {
                console.error('Mismatch: images.length =', this.state.images.length, 'results.length =', this.state.results.length);
            }
            if (this.state.files.length !== this.state.images.length) {
                console.error('Mismatch: files.length =', this.state.files.length, 'images.length =', this.state.images.length);
            }

            // Show results - hide all other sections first
            this.elements.historySection.classList.add('hidden');
            this.elements.uploadSection.classList.add('hidden');
            this.elements.loadingSection.classList.add('hidden');

            this.state.currentTabIndex = 0;
            this.state.zoomLevel = 1;
            this.state.offsetX = 0;
            this.state.offsetY = 0;
            this.state.highlightedSeedId = null;
            this.state.reportMetadata = {
                processingDurationMs: batch.processing_duration_ms ?? null,
                overallStatistics: batch.total_seeds != null ? {
                    good_seeds: batch.good_seeds_count ?? 0,
                    bad_seeds: batch.bad_seeds_count ?? 0,
                    good_percentage: batch.good_percentage ?? 0,
                    bad_percentage: batch.bad_percentage ?? 0
                } : null
            };

            this.showResults();
            this.renderTabs();
            this.updateView();

            console.log('Batch details loaded. Current tab:', this.state.currentTabIndex);
            console.log('Current image:', this.getImage());
            console.log('Current result:', this.getCurrentResult());

        } catch (error) {
            console.error('Failed to load batch details:', error);
            this.showError(error.message || 'Failed to load batch details');
            this.showLoading(false);
        }
    }
};

// Start the app
document.addEventListener('DOMContentLoaded', () => {
    App.init();
    // Make App available globally for inline onclick handlers
    window.App = App;
});
