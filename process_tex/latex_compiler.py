import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from tqdm import tqdm
import time

__all__ = ['LatexCompiler']
class LatexCompiler:
    """Compile LaTeX files using pdflatex"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize compiler
        
        Args:
            output_dir: Base directory for outputs (default: "output")
        """
        self.base_output_dir = Path(output_dir)
        self.required_packages = [
            'texlive-latex-base',
            'texlive-latex-extra',
            'texlive-fonts-recommended',
            'texlive-fonts-extra',  # Contains inconsolata.sty
            'texlive-publishers'    # Contains conference styles
        ]

    def _check_latex_packages(self) -> bool:
        try:
            subprocess.run(['kpsewhich', '--version'], 
                         capture_output=True, check=True)
            
            # 检查输入目录中的所有 .sty 文件
            if hasattr(self, 'input_dir'):
                local_sty_files = list(Path(self.input_dir).glob('*.sty'))
                if local_sty_files:
                    print("\nFound local style files:")
                    for sty_file in local_sty_files:
                        print(f"  - {sty_file.name}")
                    return True
            
            # 如果没有本地 .sty 文件，检查是否安装了必要的包
            print("\nChecking for required LaTeX packages...")
            print("Note: You can also place any required .sty files in the same directory as your .tex file")
            print("\nRecommended packages:")
            for pkg in self.required_packages:
                print(f"  - {pkg}")
            
            return True
            
        except subprocess.CalledProcessError:
            print("Error: kpsewhich command not found. Is TeX Live installed?")
            return False

    def _prepare_output_dir(self, tex_file: Path) -> Path:
        try:
            last_parent = tex_file.parent.name
            
            self.base_output_dir.mkdir(parents=True, exist_ok=True)
            self.base_output_dir.chmod(0o755)
            
            output_dir = self.base_output_dir / last_parent
            output_dir.mkdir(parents=True, exist_ok=True)
            output_dir.chmod(0o777)
            
            for item in output_dir.glob('*'):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            
            return output_dir
            
        except PermissionError as e:
            print(f"\nPermission error creating output directory: {e}")
            print("Try running with sudo or check directory permissions")
            raise
        except Exception as e:
            print(f"\nError creating output directory: {e}")
            raise

    def _cleanup_output_dir(self, output_dir: Path, tex_name: str, clean_auxiliary: bool = False) -> None:
        print("\nCleaning up output directory...")
        
        keep_files = {
            'paper.pdf',
            f'{tex_name}.tex',
        }
        
        if not clean_auxiliary:
            keep_files.update({
                'paper.aux',
                'paper.log'
            })
        
        for file in output_dir.glob('*'):
            if file.name not in keep_files:
                try:
                    if file.is_file():
                        file.unlink()
                        print(f"  Removed {file.name}")
                    elif file.is_dir():
                        shutil.rmtree(file)
                        print(f"  Removed directory {file.name}")
                except Exception as e:
                    print(f"  Warning: Could not remove {file.name}: {e}")

        print("\nRemaining files in output directory:")
        for file in sorted(output_dir.glob('*')):
            print(f"  - {file.name}")

    def compile(self, input_file: str, clean_auxiliary: bool = False) -> bool:
        def read_file_with_encodings(file_path: str) -> str:
            """尝试使用不同的编码读取文件"""
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Error reading file with {encoding}: {str(e)}")
                    continue
            
            # 如果所有编码都失败，尝试二进制读取并解码
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    try:
                        import chardet
                        detected = chardet.detect(content)
                        if detected['encoding']:
                            return content.decode(detected['encoding'])
                    except ImportError:
                        pass
                    return content.decode('utf-8', errors='ignore')
            except Exception as e:
                raise RuntimeError(f"Failed to read file {file_path}: {str(e)}")

        def fix_file_encoding(file_path: Path) -> None:
            """修复文件编码"""
            if file_path.exists():
                try:
                    content = read_file_with_encodings(str(file_path))
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    print(f"Warning: Could not fix encoding for {file_path}: {e}")

        try:
            input_path = Path(input_file).resolve()
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")

            input_dir = input_path.parent
            tex_name = input_path.stem

            self.input_dir = input_dir
            if not self._check_latex_packages():
                return False

            output_dir = self._prepare_output_dir(input_path).resolve()
            
            temp_dir = Path('/tmp/latex_compile')
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True)
            temp_dir.chmod(0o777)
            
            try:
                print("\nCopying and fixing file encodings...")
                # 复制所有文件和目录
                def copy_with_dirs(src_dir: Path, dst_dir: Path):
                    for item in src_dir.glob('**/*'):
                        if item.is_file():
                            relative_path = item.relative_to(src_dir)
                            dst_path = dst_dir / relative_path
                            dst_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # 对特定文件类型进行编码修复
                            if item.suffix.lower() in ['.tex', '.bib', '.bst', '.aux']:
                                try:
                                    content = read_file_with_encodings(str(item))
                                    with open(dst_path, 'w', encoding='utf-8') as f:
                                        f.write(content)
                                except Exception as e:
                                    print(f"Warning: Could not fix encoding for {item}, copying as is: {e}")
                                    shutil.copy2(item, dst_path)
                            else:
                                shutil.copy2(item, dst_path)
                            # print(f"  Copied {relative_path}")

                with tqdm(total=6, desc="Compiling LaTeX", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
                    # 复制和修复文件编码
                    pbar.set_description("Copying files")
                    copy_with_dirs(input_dir, temp_dir)
                    pbar.update(1)
                    
                    # 第一次 pdflatex 编译
                    pbar.set_description("First LaTeX pass")
                    result = subprocess.run(
                        [
                            'pdflatex',
                            '-interaction=nonstopmode',
                            '-shell-escape',
                            '-file-line-error',
                            f"{tex_name}.tex"
                        ],
                        capture_output=True,
                        text=True,
                        cwd=temp_dir
                    )
                    if result.returncode != 0:
                        print("\nLaTeX compilation error (first pass):")
                        print(result.stderr)
                        print(result.stdout)
                        return False
                    pbar.update(1)
                    
                    # 运行 bibtex
                    pbar.set_description("Running BibTeX")
                    result = subprocess.run(
                        ['bibtex', f"{tex_name}.aux"],
                        capture_output=True,
                        text=True,
                        cwd=temp_dir
                    )
                    pbar.update(1)
                    
                    # 第二次和第三次 pdflatex 编译
                    for i in range(2):
                        pbar.set_description(f"LaTeX pass {i+2}/3")
                        result = subprocess.run(
                            [
                                'pdflatex',
                                '-interaction=nonstopmode',
                                '-shell-escape',
                                '-file-line-error',
                                f"{tex_name}.tex"
                            ],
                            capture_output=True,
                            text=True,
                            cwd=temp_dir
                        )
                        if result.returncode != 0:
                            print(f"\nLaTeX compilation error (pass {i+2}):")
                            print(result.stderr)
                            print(result.stdout)
                            return False
                        pbar.update(1)
                    
                    # 复制输出文件
                    pbar.set_description("Copying output files")
                    for ext in ['.pdf', '.aux', '.log', '.bbl', '.blg']:
                        src = temp_dir / f"{tex_name}{ext}"
                        if src.exists():
                            dst = output_dir / f"paper{ext}"
                            shutil.copy2(src, dst)
                    tex_src = temp_dir / f"{tex_name}.tex"
                    tex_dst = output_dir / tex_src.name
                    shutil.copy2(tex_src, tex_dst)
                    pbar.update(1)
                    
                    print(f"\nCompilation successful. Output files in: {output_dir}")
                    print(f"Output PDF: {output_dir}/paper.pdf")
                    return True

            finally:
                shutil.rmtree(temp_dir)

        except Exception as e:
            print(f"Error during compilation: {str(e)}")
            return False

def compile_latex(input_file: str, clean_auxiliary: bool = False) -> bool:
    compiler = LatexCompiler()
    return compiler.compile(input_file, clean_auxiliary)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Compile LaTeX files')
    parser.add_argument('input_file', help='Input LaTeX file', nargs='?')
    parser.add_argument('--clean', action='store_true',
                      help='Clean auxiliary files after compilation')
    parser.add_argument('--install-deps', action='store_true',
                      help='Try to install missing dependencies (requires sudo)')
    
    args = parser.parse_args()
    
    if args.install_deps:
        compiler = LatexCompiler()
        packages = " ".join(compiler.required_packages)
        print(f"\nInstalling required packages: {packages}")
        try:
            subprocess.run(['sudo', 'apt-get', 'install', '-y'] + 
                         compiler.required_packages, check=True)
            print("\nPackages installed successfully!")
            if not args.input_file:
                return 0
        except subprocess.CalledProcessError as e:
            print(f"\nError installing packages: {e}")
            return 1
    
    if not args.input_file:
        parser.error("input_file is required unless using --install-deps")
    
    success = compile_latex(args.input_file, args.clean)
    return 0 if success else 1

if __name__ == "__main__":
    main()