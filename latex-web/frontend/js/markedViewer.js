const markedViewer = {
    container: document.querySelector('.marked-content'),

    setContent(pdfUrl) {
        // 创建iframe来显示PDF
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        
        // 设置PDF URL
        iframe.src = pdfUrl;
        
        // 清空容器并添加iframe
        this.container.innerHTML = '';
        this.container.appendChild(iframe);
    }
}; 