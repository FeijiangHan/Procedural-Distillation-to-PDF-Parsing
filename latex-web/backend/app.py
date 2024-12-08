from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import os
from pathlib import Path
import json
from services.latex_service import LatexService
from services.marker_service import MarkerService
from services.file_service import FileService
from utils.logger import setup_logger
import time
from services.pipeline_service import PipelineService
import zipfile
import io

# 创建应用实例并配置CORS
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],  # 允许前端域名
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# 配置常量
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent.parent  # tex2bbox目录
PAPERS_DIR = PROJECT_ROOT / "data/papers"  # papers目录的相对路径
OUTPUT_DIR = BASE_DIR / "output"  # 输出目录
TEMP_DIR = BASE_DIR / "temp"     # 临时目录
CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"

# 创建必要的目录
for dir_path in [OUTPUT_DIR, TEMP_DIR, CACHE_DIR, LOG_DIR]:
    dir_path.mkdir(exist_ok=True)

# 设置日志
logger = setup_logger('latex_web', LOG_DIR / 'app.log')

# 创建服务实例
latex_service = LatexService(PAPERS_DIR, OUTPUT_DIR, TEMP_DIR)
latex_service.logger = logger  # 设置logger
marker_service = MarkerService(OUTPUT_DIR)
file_service = FileService(PAPERS_DIR, OUTPUT_DIR, CACHE_DIR)
pipeline_service = PipelineService(PAPERS_DIR, OUTPUT_DIR)

@app.errorhandler(Exception)
def handle_error(error):
    """全局错误处理"""
    logger.error(f"Unhandled error: {str(error)}", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "details": str(error)
    }), 500

@app.route('/api/papers', methods=['GET'])
def get_papers():
    """获取可用的论文列表"""
    try:
        papers = file_service.get_available_papers()
        return jsonify({"papers": papers})
    except Exception as e:
        logger.error(f"Error getting papers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tex/<paper_id>', methods=['GET'])
def get_tex(paper_id):
    """获取TeX文件内容"""
    try:
        # 构建文件路径
        papers_dir = Path(__file__).parent / "data/papers"
        tex_path = papers_dir / paper_id / "paper.tex"
        
        if not tex_path.exists():
            return jsonify({
                "error": f"File not found: {paper_id}"
            }), 404
            
        # 读取文件内容
        with open(tex_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({
            "content": content,
            "filename": tex_path.name
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error reading file: {str(e)}"
        }), 500

@app.route('/api/compile', methods=['POST'])
def compile_latex():
    """编译并标注LaTeX文件"""
    try:
        data = request.get_json()
        paper_id = data.get('paperId')
        
        if not paper_id:
            return jsonify({"error": "Missing paper ID"}), 400
            
        logger.info(f"Processing paper {paper_id}")
        success, message, error = pipeline_service.process_tex(paper_id)
        
        if not success:
            logger.error(f"Processing failed: {error}")
            return jsonify({
                "error": "Processing failed",
                "details": error
            }), 500
            
        logger.info(f"Successfully processed paper {paper_id}")
        return jsonify({
            "message": message,
            "markedPdfUrl": f"/api/marked-pdf/{paper_id}"
        })
        
    except Exception as e:
        logger.error(f"Error processing paper: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/marked-pdf/<paper_id>', methods=['GET'])
def get_marked_pdf(paper_id):
    """获取标注后的PDF"""
    try:
        marked_paths = file_service.get_marked_pdf_paths(paper_id)
        if not marked_paths:
            logger.warning(f"No marked PDF found for paper {paper_id}")
            return jsonify({"error": "Marked PDF not found"}), 404
            
        # 直接返回PDF文件
        marked_pdf = marked_paths[0]
        logger.info(f"Serving marked PDF: {marked_pdf}")
        return send_file(
            marked_pdf,
            mimetype='application/pdf',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error serving marked PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/marked-pdf/<paper_id>/<page>', methods=['GET'])
def get_marked_page(paper_id, page):
    """获取特定的标注页面"""
    try:
        page_path = OUTPUT_DIR / paper_id / "visualizations" / page
        if not page_path.exists():
            logger.warning(f"Marked page {page} not found for paper {paper_id}")
            return jsonify({"error": "Marked page not found"}), 404
            
        logger.debug(f"Serving marked page {page} for paper {paper_id}")
        return send_file(
            str(page_path),
            mimetype='image/png',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error serving marked page: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export-annotations/<paper_id>', methods=['GET'])
def export_annotations(paper_id):
    """导出标注数据"""
    try:
        vis_dir = Path(__file__).parent / "visualizations" / paper_id
        if not vis_dir.exists():
            logger.warning(f"No annotations found for paper {paper_id}")
            return jsonify({"error": "No annotations found"}), 404
            
        # 创建内存中的ZIP文件
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 遍历目录中的所有文件
            for file_path in vis_dir.rglob('*'):
                if file_path.is_file():
                    # 计算相对路径
                    arcname = file_path.relative_to(vis_dir)
                    zf.write(file_path, arcname)
        
        # 将指针移到开始
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{paper_id}_annotations.zip"
        )
        
    except Exception as e:
        logger.error(f"Error exporting annotations: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 添加健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    """健��检查"""
    try:
        # 检查必要的目录是否存在且可访问
        for dir_path in [PAPERS_DIR, OUTPUT_DIR, TEMP_DIR, CACHE_DIR]:
            if not dir_path.exists() or not os.access(dir_path, os.W_OK):
                raise Exception(f"Directory {dir_path} is not accessible")
                
        return jsonify({
            "status": "healthy",
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# 添加清理缓存的端点
@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """清理缓存"""
    try:
        file_service.cache.clear()
        logger.info("Cache cleared successfully")
        return jsonify({"message": "Cache cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 添加静态文件服务路由
@app.route('/papers/<path:filename>')
def serve_paper(filename):
    """提供论文文件的静态服务"""
    papers_dir = Path(__file__).parent / "data/papers"
    return send_from_directory(papers_dir, filename)

if __name__ == '__main__':
    logger.info("Starting LaTeX Web application...")
    app.run(debug=True, port=5000) 