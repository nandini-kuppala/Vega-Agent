import io
import os
import tempfile
import base64
import subprocess
from pathlib import Path
import shutil

class LaTeXPDFConverter:
    """Converts LaTeX documents to PDF format"""
    
    def __init__(self):
        """Initialize the LaTeX to PDF converter"""
        pass
    
    def convert_latex_to_pdf(self, latex_content, filename="resume"):
        """
        Convert LaTeX content to PDF using pdflatex or an alternative approach.
        
        For web apps where pdflatex might not be available, this provides a fallback
        to a web service or other conversion mechanism.
        """
        try:
            # Method 1: Try using pdflatex if available on the system
            return self._convert_with_pdflatex(latex_content, filename)
        except Exception as e:
            # If pdflatex fails, explain the issue
            error_message = f"PDF conversion failed: {str(e)}\n\n"
            error_message += "To generate a PDF from this LaTeX code:\n"
            error_message += "1. Copy the LaTeX code\n"
            error_message += "2. Paste it into an online LaTeX editor like Overleaf (overleaf.com)\n"
            error_message += "3. Generate and download the PDF from there"
            
            # Return the LaTeX code as a text document for the user to use elsewhere
            return None, error_message, latex_content
    
    def _convert_with_pdflatex(self, latex_content, filename="resume"):
        """
        Convert LaTeX to PDF using the pdflatex command-line tool.
        
        Args:
            latex_content: String containing LaTeX document
            filename: Output filename (without extension)
            
        Returns:
            PDF bytes, success message, and LaTeX content
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write the LaTeX content to a .tex file
            tex_file = os.path.join(temp_dir, f"{filename}.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)
            
            # Run pdflatex to generate the PDF
            try:
                # First run - compile the document
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", f"{filename}.tex"],
                    cwd=temp_dir,
                    check=True,
                    capture_output=True
                )
                
                # Second run - resolve references
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", f"{filename}.tex"],
                    cwd=temp_dir,
                    check=True,
                    capture_output=True
                )
                
                # Read the generated PDF
                pdf_file = os.path.join(temp_dir, f"{filename}.pdf")
                with open(pdf_file, "rb") as f:
                    pdf_data = f.read()
                
                return pdf_data, "PDF generated successfully!", latex_content
                
            except subprocess.CalledProcessError as e:
                # Get the log file for error information
                log_file = os.path.join(temp_dir, f"{filename}.log")
                log_content = ""
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        log_content = f.read()
                
                error_message = f"PDF generation failed: {str(e)}\nCheck the LaTeX log for details."
                raise RuntimeError(f"{error_message}\n\nLog excerpt:\n{log_content[-500:]}")

    def create_download_link(self, content, filename, format_type):
        """Create a download link for various file types"""
        if format_type == "pdf" and content:
            # For PDF binary data
            b64 = base64.b64encode(content).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf">Download as PDF</a>'
        elif format_type == "latex":
            # For LaTeX text
            b64 = base64.b64encode(content.encode()).decode()
            href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.tex">Download as LaTeX</a>'
        else:
            # Generic text
            b64 = base64.b64encode(content.encode()).decode()
            href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.{format_type}">Download as {format_type.upper()}</a>'
        
        return href
    def convert(self, latex_content, filename="resume"):
        """
        Convert LaTeX content to PDF.
        
        Args:
            latex_content: String containing LaTeX document
            filename: Output filename (without extension)
            
        Returns:
            PDF binary data or None if conversion fails
        """
        try:
            # Try to convert LaTeX to PDF
            pdf_data, _, _ = self.convert_latex_to_pdf(latex_content, filename)
            return pdf_data
        except Exception as e:
            # If conversion fails, return None
            print(f"PDF conversion failed: {str(e)}")
            return None