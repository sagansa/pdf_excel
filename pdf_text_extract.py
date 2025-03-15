import pdfplumber
import sys

def extract_pdf_text(pdf_path, page_numbers=None):
    """Extract text and position information from a PDF file.
    Args:
        pdf_path (str): Path to the PDF file
        page_numbers (list, optional): List of page numbers to extract. If None, extracts all pages.
    """
    try:
        # Validate file path
        if not pdf_path.lower().endswith('.pdf'):
            print("Error: Please provide a PDF file")
            return

        # Open and process PDF
        with pdfplumber.open(pdf_path) as pdf:
            print(f"\nProcessing PDF: {pdf_path}")
            print("=" * 50)
            
            total_pages = len(pdf.pages)
            # Validate page numbers
            if page_numbers:
                valid_pages = [p for p in page_numbers if 1 <= p <= total_pages]
                if not valid_pages:
                    print(f"Error: No valid page numbers provided. PDF has {total_pages} pages.")
                    return
                pages_to_process = valid_pages
            else:
                pages_to_process = range(1, total_pages + 1)

            # Process selected pages
            for page_num in pages_to_process:
                page = pdf.pages[page_num - 1]  # Convert to 0-based index
                print(f"\nPage {page_num}:")
                print("-" * 20)

                # Extract words with their positions
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )

                # Display word information
                for word in words:
                    print(f"Text: '{word['text']}', ")
                    print(f"Position: X0={word['x0']:.2f}, X1={word['x1']:.2f}, ")
                    print(f"         Y0={word['top']:.2f}, Y1={word['bottom']:.2f}")
                    print()

    except FileNotFoundError:
        print(f"Error: File '{pdf_path}' not found")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")

def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python pdf_text_extract.py <pdf_file_path> [page_numbers...]")
        print("Example: python pdf_text_extract.py document.pdf 1 3 5")
        return

    pdf_path = sys.argv[1]
    # Get page numbers if provided
    page_numbers = None
    if len(sys.argv) > 2:
        try:
            page_numbers = [int(p) for p in sys.argv[2:]]
        except ValueError:
            print("Error: Page numbers must be integers")
            return

    extract_pdf_text(pdf_path, page_numbers)

if __name__ == "__main__":
    main()