import re
import os
import sys

def remove_latex_comments(content):
    """
    Remove LaTeX comment content while preserving % symbols and original spacing.
    Multiple consecutive empty lines will be reduced to a single empty line.
    """
    lines = content.split('\n')
    result = []
    empty_line_count = 0
    
    for line in lines:
        # Process each line to handle escaped % and comments
        processed_line = ''
        i = 0
        while i < len(line):
            if line[i:i+2] == '\\%':
                processed_line += '\\%'
                i += 2
            elif line[i] == '%':
                # Keep the % symbol but remove the comment content
                processed_line += '%'
                break
            else:
                processed_line += line[i]
                i += 1
        
        processed_line = processed_line.rstrip()
        
        # Handle empty lines
        if not processed_line or processed_line == '%':
            empty_line_count += 1
            if empty_line_count <= 1:  # Only keep the first empty line
                result.append(processed_line)
        else:
            empty_line_count = 0  # Reset counter for non-empty lines
            result.append(processed_line)
    
    # Join lines preserving single empty lines
    return '\n'.join(result)

def merge_tex_files(output_dir, merged_file):
    """合并所有分割的tex文件"""
    # 获取所有分割文件并按序排序
    split_files = sorted([f for f in os.listdir(output_dir) if f.startswith('split_part_')],
                        key=lambda x: int(x.split('_')[-1].split('.')[0]))
    
    merged_content = []
    preamble = ''
    has_document_begin = False
    
    # 读取并合并所有文件
    for i, filename in enumerate(split_files):
        with open(os.path.join(output_dir, filename), 'r', encoding='utf-8') as f:
            content = f.read()
            
            if i == 0:
                # 从第一个文件提取导言区和文档开始
                doc_start = content.find('\\begin{document}')
                if doc_start != -1:
                    preamble = content[:doc_start]
                    content = content[doc_start:]
                    has_document_begin = True
            else:
                # 移除其他文件的导言区和文档结构标记
                doc_start = content.find('\\begin{document}')
                if doc_start != -1:
                    content = content[doc_start + len('\\begin{document}'):]
            
            # 移除所有文件中的文档结束标记
            content = content.replace('\\end{document}', '')
            
            if content.strip():
                merged_content.append(content.strip())
    
    # 写入合并后的文件
    with open(merged_file, 'w', encoding='utf-8') as f:
        if preamble:
            f.write(preamble.strip())
            f.write('\n')
        if not has_document_begin:
            f.write('\\begin{document}\n')
        f.write('\n'.join(merged_content))
        f.write('\n\\end{document}\n')

def split_tex_file(tex_file, output_dir, max_sections=1):
    """
    Split a LaTeX file into smaller files, preserving element integrity.
    """
    if not os.path.exists(tex_file):
        raise FileNotFoundError(f"输入文件不存在: {tex_file}")

    os.makedirs(output_dir, exist_ok=True)
    
    try:
        with open(tex_file, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        try:
            with open(tex_file, 'r', encoding='latin-1') as file:
                content = file.read()
        except Exception as e:
            raise Exception(f"无法读取文件 {tex_file}: {str(e)}")

    # 移除注释
    content = remove_latex_comments(content)

    # 提取文档结构
    doc_start = content.find('\\begin{document}')
    doc_end = content.find('\\end{document}')
    
    if doc_start == -1:
        raise ValueError("文件中未找到 \\begin{document}")
    
    # 提取导言区和文档开始部分
    preamble = content[:doc_start + len('\\begin{document}')]
    
    # 提取主要内容
    main_content = content[doc_start + len('\\begin{document}'):doc_end]
    
    # 分割主要内容
    sections = []
    
    # 找到所有section的位置
    section_matches = list(re.finditer(r'\\section(\*?)\{[^}]*\}', main_content))
    
    # 处理文档开始到第一个section的内容（包括导言区）
    if section_matches:
        first_section_start = section_matches[0].start()
        initial_content = preamble + main_content[:first_section_start].strip()
        if initial_content:
            sections.append(initial_content)
    else:
        # 如果没有section，将整个文档作为一个块
        sections.append(preamble + main_content)
    
    # 处理每个section
    for i in range(len(section_matches)):
        start = section_matches[i].start()
        if i < len(section_matches) - 1:
            end = section_matches[i + 1].start()
        else:
            end = len(main_content)
        
        section_content = main_content[start:end].strip()
        if section_content:
            sections.append(section_content)
    
    # 确保最后一个section包含文结束标记
    if sections:
        sections[-1] = sections[-1] + '\n\\end{document}'
    
    # 按max_sections分组
    chunks = []
    for i in range(0, len(sections), max_sections):
        chunk = '\n\n'.join(sections[i:i + max_sections])
        if chunk.strip():
            chunks.append(chunk)
    
    # 写入分割后的文件
    for idx, chunk in enumerate(chunks, 1):
        chunk_filename = os.path.join(output_dir, f"split_part_{idx}.tex")
        try:
            with open(chunk_filename, 'w', encoding='utf-8') as output_file:
                output_file.write(chunk)
            print(f"已保存分块到 {chunk_filename}")
        except Exception as e:
            print(f"保存文件 {chunk_filename} 时出错: {str(e)}", file=sys.stderr)
    
    # 合并验证
    merged_file = os.path.join(output_dir, "merged.tex")
    merge_tex_files(output_dir, merged_file)

if __name__ == "__main__":
    try:
        tex_file = "data/acl_latex.tex"
        output_dir = "data/output_chunks"
        split_tex_file(tex_file, output_dir, max_sections=1)
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
