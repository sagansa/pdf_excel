import PyPDF2
import os
try:  # Support both new and legacy PyPDF2 packages
    from PyPDF2.errors import PdfReadError  # type: ignore[attr-defined]
except (ImportError, AttributeError):  # pragma: no cover
    try:
        from PyPDF2.utils import PdfReadError  # type: ignore
    except (ImportError, AttributeError):
        class PdfReadError(Exception):  # type: ignore
            """Fallback PdfReadError for very old PyPDF2 releases."""
            pass

def unlock_pdf(input_path, password, output_path=None):
    """Unlock a password-protected PDF file.
    
    Args:
        input_path (str): Path to the password-protected PDF file
        password (str): Password to unlock the PDF
        output_path (str, optional): Path to save the unlocked PDF. If not provided,
                                    will use input filename with '_unlocked' suffix
    
    Returns:
        str: Path to the unlocked PDF file
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        PdfReadError: If password is incorrect or PDF is corrupted
    """
    # Validate input file
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"PDF file not found: {input_path}")
    
    # Generate output path if not provided
    if output_path is None:
        file_name, file_ext = os.path.splitext(input_path)
        output_path = f"{file_name}_unlocked{file_ext}"
    
    try:
        # Open the PDF file
        with open(input_path, 'rb') as file:
            # Create PDF reader object
            reader = PyPDF2.PdfReader(file)
            
            # Check if PDF is encrypted
            if not reader.is_encrypted:
                raise ValueError("PDF is not password protected")
            
            # Try to decrypt with provided password
            try:
                decrypt_result = reader.decrypt(password)
            except NotImplementedError as e:
                raise RuntimeError(
                    "AES encrypted PDF requires the 'pycryptodome' package to be installed."
                ) from e
            except Exception as e:
                message = str(e)
                if 'pycryptodome' in message.lower():
                    raise RuntimeError(
                        "AES encrypted PDF requires the 'pycryptodome' package to be installed."
                    ) from e
                raise RuntimeError(f"Failed to decrypt PDF: {message}") from e

            if not decrypt_result:
                raise PdfReadError("Incorrect password")
            
            # Create a PDF writer object
            writer = PyPDF2.PdfWriter()
            
            # Add all pages to writer
            for page in reader.pages:
                writer.add_page(page)
            
            # Save the unlocked PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
    except PdfReadError as e:
        raise PdfReadError(f"Error reading PDF: {str(e)}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")

# Example usage
if __name__ == '__main__':
    try:
        # Get input from user
        input_path = input("Enter the path to the PDF file: ")
        password = input("Enter the PDF password: ")
        
        # Unlock the PDF
        output_path = unlock_pdf(input_path, password)
        print(f"\nPDF successfully unlocked! Saved to: {output_path}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
