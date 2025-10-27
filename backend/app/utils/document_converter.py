"""Document conversion utilities using pandoc"""
import subprocess
import tempfile
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PandocNotFoundError(Exception):
    """Raised when pandoc is not installed or not found in PATH"""
    pass


class DocumentConversionError(Exception):
    """Raised when document conversion fails"""
    pass


class DocumentConverter:
    """Convert documents between formats using pandoc"""
    
    @staticmethod
    def check_pandoc_installed() -> bool:
        """Check if pandoc is installed and available"""
        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def markdown_to_docx(
        markdown_content: str,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        Convert markdown content to Word (docx) format
        
        Args:
            markdown_content: The markdown content to convert
            output_filename: Optional filename for the output (without extension)
        
        Returns:
            bytes: The docx file content as bytes
        
        Raises:
            PandocNotFoundError: If pandoc is not installed
            DocumentConversionError: If conversion fails
        """
        # Check if pandoc is installed
        if not DocumentConverter.check_pandoc_installed():
            logger.error("Pandoc is not installed or not found in PATH")
            raise PandocNotFoundError(
                "Pandoc is not installed. Please install pandoc to use this feature."
            )
        
        # Create temporary directory for file operations
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create temporary markdown file
            md_file = Path(temp_dir) / "input.md"
            docx_file = Path(temp_dir) / "output.docx"
            
            # Write markdown content to temp file
            md_file.write_text(markdown_content, encoding='utf-8')
            
            logger.info(f"Converting markdown to docx using pandoc...")
            
            # Call pandoc to convert markdown to docx
            result = subprocess.run(
                [
                    'pandoc',
                    str(md_file),
                    '-o', str(docx_file),
                    '--from', 'markdown',
                    '--to', 'docx',
                    '--standalone',
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Pandoc conversion failed: {error_msg}")
                raise DocumentConversionError(f"Pandoc conversion failed: {error_msg}")
            
            # Read the generated docx file
            if not docx_file.exists():
                raise DocumentConversionError("Output docx file was not created")
            
            docx_bytes = docx_file.read_bytes()
            logger.info(f"Successfully converted markdown to docx ({len(docx_bytes)} bytes)")
            
            return docx_bytes
            
        except subprocess.TimeoutExpired:
            logger.error("Pandoc conversion timed out")
            raise DocumentConversionError("Conversion timed out after 30 seconds")
        
        except Exception as e:
            if isinstance(e, (PandocNotFoundError, DocumentConversionError)):
                raise
            logger.error(f"Unexpected error during conversion: {str(e)}")
            raise DocumentConversionError(f"Unexpected error: {str(e)}")
        
        finally:
            # Clean up temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")

