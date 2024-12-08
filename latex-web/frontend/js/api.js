const API = {
    BASE_URL: 'http://localhost:5000/api',
    
    async getPapers() {
        const response = await fetch(`${this.BASE_URL}/papers`);
        if (!response.ok) throw new Error('Failed to fetch papers');
        return response.json();
    },
    
    async getTexContent(paperId) {
        const response = await fetch(`${this.BASE_URL}/tex/${paperId}`);
        if (!response.ok) throw new Error('Failed to fetch TeX content');
        return response.json();
    },
    
    async compilePaper(paperId) {
        const response = await fetch(`${this.BASE_URL}/compile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ paperId })
        });
        if (!response.ok) throw new Error('Failed to compile paper');
        return response.json();
    },
    
    getMarkedPdfUrl(paperId) {
        return `${this.BASE_URL}/marked-pdf/${paperId}`;
    },
    
    async exportAnnotations(paperId) {
        window.location.href = `${this.BASE_URL}/export-annotations/${paperId}`;
    }
}; 