import os
from app import BankStatementProcessor

class PDFExcelConverter:
    def __init__(self):
        self.pdf_folder = "pdfs"
        self.excel_folder = "excel"
        
        # Create folders if they don't exist
        os.makedirs(self.pdf_folder, exist_ok=True)
        os.makedirs(self.excel_folder, exist_ok=True)

    def convert_bca_statement(self, pdf_path):
        """Convert BCA bank statement PDF to Excel"""
        # Get the filename without extension
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Create output Excel path
        excel_path = os.path.join(self.excel_folder, f"{base_name}.xlsx")
        
        # Process the PDF
        processor = BankStatementProcessor()
        processor.process_pdf(pdf_path)
        processor.save_to_excel(excel_path)
        
        return excel_path

def main():
    converter = PDFExcelConverter()
    
    # Process the BCA statement PDF
    pdf_path = "pdfs/4671357722_JAN_2025.pdf"
    
    try:
        excel_path = converter.convert_bca_statement(pdf_path)
        print(f"Successfully converted BCA statement to Excel: {excel_path}")
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")

if __name__ == "__main__":
    main()