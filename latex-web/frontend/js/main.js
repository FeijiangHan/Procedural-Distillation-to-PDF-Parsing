// UI元素
let paperSelect;
let processBtn;
let loadingIndicator;
let errorToast;
let exportBtn;

// 当前选中的论文
let selectedPaper = null;
let hasProcessedPaper = false;  // 添加标记表示是否已处理

// 显示/隐藏加载指示器
function setLoading(loading, isProcessing = false) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const paperSelect = document.getElementById('paperSelect');
    const processBtn = document.getElementById('processBtn');
    const exportBtn = document.getElementById('exportBtn');

    // 控制加载指示器显示
    if (isProcessing) {
        // 处理时显示步骤动画
        loadingIndicator.classList.remove('hidden');
    } else {
        // 非处理时隐藏加载指示器
        loadingIndicator.classList.add('hidden');
    }

    // 禁用/启用按钮
    paperSelect.disabled = loading;
    processBtn.disabled = loading || !selectedPaper;
    exportBtn.disabled = loading || !hasProcessedPaper;
}

// 显示错误信息
function showError(message) {
    errorToast.textContent = message;
    errorToast.classList.remove('hidden');
    setTimeout(() => {
        errorToast.classList.add('hidden');
    }, 3000);
}

// 初始化应用
async function init() {
    try {
        // 获取DOM元素
        paperSelect = document.getElementById('paperSelect');
        processBtn = document.getElementById('processBtn');
        loadingIndicator = document.getElementById('loadingIndicator');
        errorToast = document.getElementById('errorToast');
        exportBtn = document.getElementById('exportBtn');

        // 初始化编辑器
        texEditor.init();

        // 加载论文列表
        const response = await API.getPapers();
        paperSelect.innerHTML = '<option value="">Select a paper...</option>' +
            response.papers.map(paper => 
                `<option value="${paper.id}" data-tex="${paper.texFile}">
                    ${paper.id}/paper.tex
                </option>`
            ).join('');
        paperSelect.disabled = false;

        // 绑��事件处理器
        paperSelect.addEventListener('change', handlePaperSelect);
        processBtn.addEventListener('click', handleProcess);
        exportBtn.addEventListener('click', handleExport);

    } catch (error) {
        showError('Failed to initialize application');
        console.error(error);
    }
}

// 处理论文选择
async function handlePaperSelect() {
    const option = paperSelect.selectedOptions[0];
    if (!option.value) return;

    // 如果选择相同的论文，直接返回
    if (selectedPaper && selectedPaper.id === option.value) {
        return;
    }

    selectedPaper = {
        id: option.value,
        texFile: option.dataset.tex
    };
    hasProcessedPaper = false;

    setLoading(true, false);  // 加载但不显示步骤动画
    try {
        // 先清空编辑器内容
        texEditor.setContent('');
        
        const response = await API.getTexContent(selectedPaper.id);
        texEditor.setContent(response.content);
        
        processBtn.disabled = false;
        exportBtn.disabled = true;
    } catch (error) {
        showError('Failed to load TeX content');
        console.error(error);
    } finally {
        setLoading(false, false);
    }
}

// 处理编译和标注
async function handleProcess() {
    if (!selectedPaper) return;

    setLoading(true, true);  // 显示步骤动画
    resetProcessingSteps();

    try {
        // 启动处理
        const compilationPromise = API.compilePaper(selectedPaper.id);
        
        // 模拟处理步骤
        const steps = [
            { name: 'LaTeX Marking', duration: 3000 },
            { name: 'PDF Compilation', duration: 1000 },
            { name: 'Structure Analysis', duration: 1000 },
            { name: 'Coordinate Extraction', duration: 1000 },
            { name: 'Bounding Box Calculation', duration: 1000 },
            { name: 'PDF Visualization', duration: 1000 }
        ];

        // 按顺序执行每个步骤
        for (const step of steps) {
            // 更新当前步骤状态为处理中
            updateProcessingStep(step.name, 'processing');
            
            // 等待指定时间
            await new Promise(resolve => setTimeout(resolve, step.duration));
            
            // 如果是最后一步，等待实际的PDF生成
            if (step.name === 'PDF Visualization') {
                try {
                    const response = await compilationPromise;
                    markedViewer.setContent(API.getMarkedPdfUrl(selectedPaper.id));
                    updateProcessingStep(step.name, 'completed');
                    hasProcessedPaper = true;
                    exportBtn.disabled = false;
                } catch (error) {
                    showError('Processing failed');
                    console.error(error);
                    hasProcessedPaper = false;
                    exportBtn.disabled = true;
                }
            } else {
                // 完成当前步骤
                updateProcessingStep(step.name, 'completed');
            }
        }

    } catch (error) {
        showError('Processing failed');
        console.error(error);
        hasProcessedPaper = false;
        exportBtn.disabled = true;
    } finally {
        setTimeout(() => {
            setLoading(false, false);  // 处理完成后隐藏动画
        }, 1000);
    }
}

function updateProcessingStep(stepName, status) {
    const step = document.querySelector(`.step[data-step="${stepName}"]`);
    if (step) {
        step.className = `step ${status}`;
        // 更新图标
        const icon = step.querySelector('.step-icon');
        if (icon) {
            icon.textContent = status === 'completed' ? '✓' : '○';
        }
    }
}

function resetProcessingSteps() {
    document.querySelectorAll('.step').forEach(step => {
        step.className = 'step pending';
        const icon = step.querySelector('.step-icon');
        if (icon) {
            icon.textContent = '○';
        }
    });
}

// 处理导出
async function handleExport() {
    if (!selectedPaper) return;
    
    try {
        await API.exportAnnotations(selectedPaper.id);
    } catch (error) {
        showError('Failed to export annotations');
        console.error(error);
    }
}

// 等待DOM加载完成后再初始化
document.addEventListener('DOMContentLoaded', init); 

async function loadTexContent(paperId) {
    try {
        const response = await fetch(`http://localhost:5000/api/tex/${paperId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // 显示内容到编辑器
        const editor = document.getElementById('editor');
        editor.value = data.content;
        
        // 更新文件名显示
        const filename = document.getElementById('filename');
        if (filename) {
            filename.textContent = data.filename;
        }
        
    } catch (error) {
        console.error('Error loading TeX content:', error);
        alert('Failed to load TeX content. Please check the console for details.');
    }
} 