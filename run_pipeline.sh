#!/bin/bash

# 检查输入参数
if [ $# -ne 1 ]; then
    echo "Usage: $0 <tex_file>"
    echo "Example: $0 data/papers/arXiv-2401.04925v4/acl_latex.tex"
    exit 1
fi

TEX_FILE=$1
TEX_DIR=$(dirname "$TEX_FILE")
TEX_NAME=$(basename "$TEX_FILE" .tex)
MARKED_TEX="${TEX_DIR}/${TEX_NAME}_marked.tex"
BASE_NAME=$(basename "$TEX_DIR")
OUTPUT_DIR="output/$BASE_NAME"

echo "Processing TeX file: $TEX_FILE"
echo "Marked TeX file: $MARKED_TEX"
echo "Output directory: $OUTPUT_DIR"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"
mkdir -p "visualizations/$BASE_NAME"

# 1. 标记 LaTeX 文件
echo "Step 1: Marking LaTeX file..."
python3 -m latex_marker.latex_marker "$TEX_FILE" \
    --output-file "$MARKED_TEX" \
    --single-column

# 2. 编译标记后的 LaTeX 文件
echo -e "\nStep 2: Compiling marked LaTeX..."
python3 process_tex/latex_compiler.py "$MARKED_TEX" --clean

# 3. 处理 aux 文件
echo -e "\nStep 3: Processing aux file..."
python3 process_aux/aux_processor.py "$OUTPUT_DIR/paper.aux"

# 4. 提取坐标
echo -e "\nStep 4: Extracting coordinates..."
python3 process_aux/coordinate_extractor.py "$OUTPUT_DIR/paper_ordered.aux"

# 5. 计算边界框
echo -e "\nStep 5: Calculating bounding boxes..."
python3 process_aux/bbox_calculator.py "$OUTPUT_DIR/latex_coordinates.json" \
    --output-file "$OUTPUT_DIR/latex_coordinates_bbox.json"

# 6. 可视化边界框
echo -e "\nStep 6: Visualizing bounding boxes..."
python3 process_aux/bbox_visualizer.py "$OUTPUT_DIR/paper.pdf" \
    "$OUTPUT_DIR/latex_coordinates_bbox.json" \
    --output-dir visualizations/$BASE_NAME \
    --dpi 72

echo -e "\nPipeline completed successfully!"