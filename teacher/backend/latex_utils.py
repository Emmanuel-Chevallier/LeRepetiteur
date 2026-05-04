import os
import subprocess
from pathlib import Path
from typing import List, Optional

def extract_content(latex_path: Path) -> str:
    """
    Reads a LaTeX file and returns its content.
    TODO: Implement smarter extraction (e.g., stripping preamble) if needed.
    For now, return the whole file to give the LLM full context.
    """
    if not latex_path.exists():
        raise FileNotFoundError(f"File not found: {latex_path}")
    
    with open(latex_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def escape_latex(text: str) -> str:
    """
    Escapes special LaTeX characters.
    """
    chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}"
    }
    return "".join(chars.get(c, c) for c in text)

def compile_latex(latex_content: str, output_dir: Path, filename: str) -> Optional[Path]:
    """
    Compiles LaTeX content to PDF using pdflatex.
    Returns the path to the generated PDF or None if failed.
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    tex_file = output_dir / f"{filename}.tex"
    pdf_file = output_dir / f"{filename}.pdf"

    with open(tex_file, "w", encoding="utf-8") as f:
        f.write(latex_content)

    # Run pdflatex twice to resolve references (if any)
    # We run in the output directory to avoid cluttering root
    try:
        # First run
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_file.name],
            cwd=output_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return pdf_file
    except subprocess.CalledProcessError as e:
        print(f"LaTeX Compilation Error: {e}")
        # Check if PDF exists despite error (common with minor LaTeX issues)
        if pdf_file.exists() and pdf_file.stat().st_size > 0:
             print(f"Warning: PDF generated despite LaTeX errors: {pdf_file}")
             return pdf_file
        return None
