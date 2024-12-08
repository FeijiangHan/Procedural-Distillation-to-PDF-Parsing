// 初始化Monaco编辑器
let editor = null;

const texEditor = {
    container: document.getElementById('texEditor'),

    init() {
        // 创建 pre 和 code 元素
        const pre = document.createElement('pre');
        pre.className = 'line-numbers language-latex';
        const code = document.createElement('code');
        code.className = 'language-latex';
        pre.appendChild(code);
        this.container.appendChild(pre);
        this.codeElement = code;
    },

    setContent(content) {
        if (!content) {
            this.codeElement.textContent = '';
            return;
        }

        // 设置内容并高亮
        this.codeElement.textContent = content;
        // 使用 requestAnimationFrame 延迟高亮处理
        requestAnimationFrame(() => {
            Prism.highlightElement(this.codeElement);
        });
    }
}; 