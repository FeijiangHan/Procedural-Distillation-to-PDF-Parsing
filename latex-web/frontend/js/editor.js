const texEditor = {
    editor: null,
    
    init() {
        // 获取编辑器容器
        const container = document.getElementById('editor');
        if (!container) {
            console.error('Editor container not found');
            return;
        }
        
        // 创建编辑器实例
        this.editor = CodeMirror(container, {
            mode: 'stex',  // LaTeX模式
            theme: 'default',
            lineNumbers: true,
            lineWrapping: true,
            readOnly: true, // 设置为只读
            viewportMargin: Infinity
        });
    },
    
    setContent(content) {
        if (!this.editor) {
            console.error('Editor not initialized');
            return;
        }
        this.editor.setValue(content || '');
        this.editor.refresh();
    },
    
    getContent() {
        return this.editor ? this.editor.getValue() : '';
    }
}; 