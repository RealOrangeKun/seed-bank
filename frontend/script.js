const App = {
    state: {
        currentFile: null,
        apiResponse: null,
        image: null,
        scale: 1, // Base scale to fit image in container
        zoomLevel: 1, // User zoom level
        offsetX: 0, // Pan X
        offsetY: 0, // Pan Y
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
        modelAccurate: document.getElementById('model-accurate'),
        modelFast: document.getElementById('model-fast'),
        btnExport: document.getElementById('btn-export')
    },

    init() {
        this.bindEvents();
        this.setupCanvasInteractions();
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
                this.handleFile(e.dataTransfer.files[0]);
            }
        });

        // File Input
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                this.handleFile(e.target.files[0]);
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

    handleFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showError('Please upload a valid image file (JPG, PNG).');
            return;
        }

        this.state.currentFile = file;
        this.uploadImage(file);
    },

    async uploadImage(file) {
        this.showLoading(true);
        this.hideError();

        const formData = new FormData();
        formData.append('file', file);

        const endpoint = this.state.mode === 'fast' ? '/api/analyze/fast' : '/api/analyze';

        try {
            // Load image for display first
            await this.loadImage(file);

            const response = await fetch(`http://localhost:8000${endpoint}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }

            const data = await response.json();
            this.state.apiResponse = data;

            this.showResults();
            this.renderStats();
            this.renderSeedsList();

            // Reset view
            this.state.zoomLevel = 1;
            this.state.offsetX = 0;
            this.state.offsetY = 0;

            this.draw();

        } catch (error) {
            console.error(error);
            this.showError(error.message || 'Failed to analyze image.');
            this.showLoading(false);
        }
    },

    loadImage(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    this.state.image = img;
                    resolve(img);
                };
                img.onerror = reject;
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    },

    draw() {
        if (!this.state.image) return;

        const canvas = this.elements.canvas;
        const ctx = canvas.getContext('2d');
        const container = this.elements.canvasContainer;

        // Canvas size matches container for full interactive area
        canvas.width = container.clientWidth;
        canvas.height = 500; // Fixed height

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Calculate base scale to fit image in canvas initially
        const scaleX = canvas.width / this.state.image.width;
        const scaleY = canvas.height / this.state.image.height;
        const baseScale = Math.min(scaleX, scaleY);

        // Apply transformations
        ctx.save();

        // Center the image initially
        const centerX = (canvas.width - this.state.image.width * baseScale * this.state.zoomLevel) / 2;
        const centerY = (canvas.height - this.state.image.height * baseScale * this.state.zoomLevel) / 2;

        ctx.translate(centerX + this.state.offsetX, centerY + this.state.offsetY);
        ctx.scale(baseScale * this.state.zoomLevel, baseScale * this.state.zoomLevel);

        // Draw Image
        ctx.drawImage(this.state.image, 0, 0);

        // Draw Bounding Boxes
        if (this.state.apiResponse && this.state.apiResponse.bounding_boxes) {
            const apiScaleX = this.state.image.width / this.state.apiResponse.image_dimensions.width;
            const apiScaleY = this.state.image.height / this.state.apiResponse.image_dimensions.height;

            this.state.apiResponse.bounding_boxes.forEach(box => {
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
        const stats = this.state.apiResponse.statistics;
        const { statGoodCount, statGoodPercent, statBadCount, statBadPercent, statTotal, statProgressBar } = this.elements;

        statGoodCount.textContent = stats.good_seeds;
        statGoodPercent.textContent = `${stats.good_percentage}%`;
        statBadCount.textContent = stats.bad_seeds;
        statBadPercent.textContent = `${stats.bad_percentage}%`;
        statTotal.textContent = this.state.apiResponse.total_seeds;

        // Animate progress bar
        setTimeout(() => {
            statProgressBar.style.width = `${stats.good_percentage}%`;
        }, 100);
    },

    renderSeedsList(filter = 'all') {
        const list = this.elements.seedsList;
        list.innerHTML = '';

        const seeds = this.state.apiResponse.bounding_boxes.filter(seed => {
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

            item.innerHTML = `
                <div class="flex items-center gap-3">
                    <i data-lucide="${icon}" class="w-5 h-5 ${iconColor}"></i>
                    <div>
                        <p class="font-medium text-gray-900 text-sm">Seed #${seed.id}</p>
                        <p class="text-xs text-gray-500">Conf: ${(seed.classification_probability * 100).toFixed(1)}%</p>
                    </div>
                </div>
                <div class="text-xs font-medium px-2 py-1 rounded bg-gray-100 text-gray-600 group-hover:bg-white">
                    ${seed.quality}
                </div>
            `;

            item.addEventListener('click', () => {
                this.state.highlightedSeedId = seed.id;
                this.renderSeedsList(filter); // Re-render to update active state
                this.draw(); // Re-draw canvas to show highlight

                // Scroll into view logic could go here
            });

            list.appendChild(item);
        });

        lucide.createIcons();
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
        this.state.currentFile = null;
        this.state.apiResponse = null;
        this.state.image = null;
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
        const stats = this.state.apiResponse.statistics;

        // Title
        doc.setFontSize(20);
        doc.setTextColor(22, 163, 74); // Seed green
        doc.text("Seed Quality Analysis Report", 20, 20);

        // Date
        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(`Generated on: ${new Date().toLocaleString()}`, 20, 30);

        // Stats
        doc.setFontSize(14);
        doc.setTextColor(0);
        doc.text("Summary Statistics", 20, 45);

        doc.setFontSize(12);
        doc.text(`Total Seeds Detected: ${this.state.apiResponse.total_seeds}`, 20, 55);
        doc.text(`Good Seeds: ${stats.good_seeds} (${stats.good_percentage}%)`, 20, 65);
        doc.text(`Bad Seeds: ${stats.bad_seeds} (${stats.bad_percentage}%)`, 20, 75);

        const modeLabel = this.state.mode === 'fast' ? 'Fast (YOLO)' : 'Accurate (Faster R-CNN)';
        doc.text(`Mode Used: ${modeLabel}`, 20, 85);

        // --- Full Image Generation ---
        // Create a temporary canvas to draw the full image with boxes
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');

        // Set dimensions to original image size
        tempCanvas.width = this.state.image.width;
        tempCanvas.height = this.state.image.height;

        // Draw original image
        tempCtx.drawImage(this.state.image, 0, 0);

        // Draw all bounding boxes
        if (this.state.apiResponse && this.state.apiResponse.bounding_boxes) {
            // No scaling needed as we are drawing on original dimensions
            this.state.apiResponse.bounding_boxes.forEach(box => {
                const x = box.x1;
                const y = box.y1;
                const w = box.width;
                const h = box.height;

                // Draw Box
                tempCtx.strokeStyle = box.color;
                tempCtx.lineWidth = 5; // Thicker line for high-res image
                tempCtx.strokeRect(x, y, w, h);

                // Draw Label
                const fontSize = 24; // Larger font
                tempCtx.font = `bold ${fontSize}px Arial`;
                tempCtx.fillStyle = box.color;
                tempCtx.fillText(`#${box.id}`, x, y - 10);
            });
        }

        const imgData = tempCanvas.toDataURL("image/jpeg", 0.8);

        // Scale image to fit PDF width
        const pdfWidth = doc.internal.pageSize.getWidth();
        const imgProps = doc.getImageProperties(imgData);
        const imgHeight = (imgProps.height * (pdfWidth - 40)) / imgProps.width;

        // Add Image
        doc.addImage(imgData, 'JPEG', 20, 95, pdfWidth - 40, imgHeight);

        // --- Detailed Table ---
        const startY = 95 + imgHeight + 10;

        doc.text("Detailed Seed List", 20, startY);

        const tableData = this.state.apiResponse.bounding_boxes.map(seed => [
            seed.id,
            seed.quality,
            `${(seed.classification_probability * 100).toFixed(1)}%`
        ]);

        doc.autoTable({
            startY: startY + 5,
            head: [['Seed ID', 'Quality', 'Confidence']],
            body: tableData,
            theme: 'grid',
            headStyles: { fillColor: [22, 163, 74] }, // Seed green
        });

        // Save
        doc.save("seed-analysis-report.pdf");
    }
};

// Start the app
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
