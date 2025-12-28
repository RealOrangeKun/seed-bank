const App = {
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

        mode: 'accurate' // 'accurate' or 'fast'
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
        imageTabs: document.getElementById('image-tabs')
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
        const API_URL = 'http://localhost:8000'; // Define API_URL here or as a global constant

        try {
            const response = await fetch(`${API_URL}/`);
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
        const { dropZone, fileInput, btnNewAnalysis, filterAll, filterGood, filterBad, modelAccurate, modelFast, btnExport } = this.elements;

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
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                this.handleFiles(e.target.files);
            }
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
        this.showLoading(true);
        this.hideError();

        const formData = new FormData();
        files.forEach(file => {
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

        try {
            // Load all images for display
            this.state.images = await Promise.all(files.map(file => this.loadImage(file)));

            const response = await fetch(`http://localhost:8000${endpoint}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }

            const data = await response.json();
            this.state.results = data.results;

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
                this.state.currentTabIndex = index;
                // Reset zoom/pan on tab switch
                this.state.zoomLevel = 1;
                this.state.offsetX = 0;
                this.state.offsetY = 0;
                this.state.highlightedSeedId = null;

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
        const { statGoodCount, statGoodPercent, statBadCount, statBadPercent, statTotal, statProgressBar } = this.elements;

        statGoodCount.textContent = stats.good_seeds;
        statGoodPercent.textContent = `${stats.good_percentage}%`;
        statBadCount.textContent = stats.bad_seeds;
        statBadPercent.textContent = `${stats.bad_percentage}%`;
        statTotal.textContent = result.total_seeds;

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

            // Removed confidence score as requested
            item.innerHTML = `
                <div class="flex items-center gap-3">
                    <i data-lucide="${icon}" class="w-5 h-5 ${iconColor}"></i>
                    <div>
                        <p class="font-medium text-gray-900 text-sm">Seed #${seed.id}</p>
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

        this.elements.fileInput.value = '';
        this.elements.resultsSection.classList.add('hidden');
        this.elements.uploadSection.classList.remove('hidden');
        this.hideError();
    },

    generatePDF() {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();

        this.state.results.forEach((result, index) => {
            const image = this.state.images[index];
            const file = this.state.files[index];
            const stats = result.statistics;

            if (index > 0) {
                doc.addPage();
            }

            // Title
            doc.setFontSize(20);
            doc.setTextColor(22, 163, 74); // Seed green
            doc.text("Seed Quality Analysis Report", 20, 20);

            // Date & File
            doc.setFontSize(10);
            doc.setTextColor(100);
            doc.text(`Generated on: ${new Date().toLocaleString()}`, 20, 30);
            doc.text(`File: ${file.name}`, 20, 35);

            // Stats
            doc.setFontSize(14);
            doc.setTextColor(0);
            doc.text("Summary Statistics", 20, 45);

            doc.setFontSize(12);
            doc.text(`Total Seeds Detected: ${result.total_seeds}`, 20, 55);
            doc.text(`Good Seeds: ${stats.good_seeds} (${stats.good_percentage}%)`, 20, 65);
            doc.text(`Bad Seeds: ${stats.bad_seeds} (${stats.bad_percentage}%)`, 20, 75);

            const modeLabel = 'Batch Analysis (Accurate)';
            doc.text(`Mode Used: ${modeLabel}`, 20, 85);

            // --- Full Image Generation ---
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');

            tempCanvas.width = image.width;
            tempCanvas.height = image.height;

            tempCtx.drawImage(image, 0, 0);

            if (result && result.bounding_boxes) {
                result.bounding_boxes.forEach(box => {
                    const x = box.x1;
                    const y = box.y1;
                    const w = box.width;
                    const h = box.height;

                    tempCtx.strokeStyle = box.color;
                    tempCtx.lineWidth = 5;
                    tempCtx.strokeRect(x, y, w, h);

                    const fontSize = 24;
                    tempCtx.font = `bold ${fontSize}px Arial`;
                    tempCtx.fillStyle = box.color;
                    tempCtx.fillText(`#${box.id}`, x, y - 10);
                });
            }

            const imgData = tempCanvas.toDataURL("image/jpeg", 0.8);

            const pdfWidth = doc.internal.pageSize.getWidth();
            const imgProps = doc.getImageProperties(imgData);
            const imgHeight = (imgProps.height * (pdfWidth - 40)) / imgProps.width;

            doc.addImage(imgData, 'JPEG', 20, 95, pdfWidth - 40, imgHeight);

            // --- Detailed Table with Crops ---
            const startY = 95 + imgHeight + 10;

            doc.text("Detailed Seed List", 20, startY);

            // Prepare data and crops
            const crops = [];
            const tableData = result.bounding_boxes.map(seed => {
                crops.push(this.getCroppedSeedDataUrl(image, seed));
                return [
                    seed.id,
                    '',
                    seed.quality,
                    `${seed.classification_confidence}%`
                ];
            });

            doc.autoTable({
                startY: startY + 5,
                head: [['ID', 'Image', 'Quality', 'Conf %']],
                body: tableData,
                theme: 'grid',
                headStyles: { fillColor: [22, 163, 74] },
                columnStyles: {
                    0: { cellWidth: 20 },
                    1: { cellWidth: 30, minCellHeight: 20 },
                    2: { cellWidth: 30 },
                    3: { cellWidth: 30 }
                },
                didDrawCell: (data) => {
                    if (data.column.index === 1 && data.cell.section === 'body') {
                        const img = crops[data.row.index];
                        if (img) {
                            // Draw image centered in cell
                            const dim = 12;
                            const x = data.cell.x + (data.cell.width - dim) / 2;
                            const y = data.cell.y + (data.cell.height - dim) / 2;
                            doc.addImage(img, 'JPEG', x, y, dim, dim);
                        }
                    }
                }
            });
        });

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        doc.save(`seed-analysis-report-${timestamp}.pdf`);
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
    }
};

// Start the app
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
