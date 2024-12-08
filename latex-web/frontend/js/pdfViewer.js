const pdfViewer = {
    pdfDoc: null,
    pageNum: 1,
    scale: 1.5,
    canvas: document.getElementById('pdfCanvas'),
    ctx: document.getElementById('pdfCanvas').getContext('2d'),

    async loadPDF(url) {
        try {
            const loadingTask = pdfjsLib.getDocument(url);
            this.pdfDoc = await loadingTask.promise;
            this.renderPage(1);
        } catch (error) {
            console.error('Error loading PDF:', error);
            throw error;
        }
    },

    async renderPage(num) {
        if (!this.pdfDoc) return;

        const page = await this.pdfDoc.getPage(num);
        const viewport = page.getViewport({ scale: this.scale });

        this.canvas.height = viewport.height;
        this.canvas.width = viewport.width;

        await page.render({
            canvasContext: this.ctx,
            viewport: viewport
        }).promise;
    },

    zoomIn() {
        if (this.scale < 3) {
            this.scale += 0.1;
            this.renderPage(this.pageNum);
        }
    },

    zoomOut() {
        if (this.scale > 0.5) {
            this.scale -= 0.1;
            this.renderPage(this.pageNum);
        }
    }
}; 