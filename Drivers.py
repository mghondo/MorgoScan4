import fitz  # PyMuPDF
from pytesseract import pytesseract, Output
from PIL import Image, ImageEnhance, ImageFilter
import os
import re
import camelot
import pdfplumber
import warnings

# Suppress warnings (e.g., CryptographyDeprecationWarning)
warnings.filterwarnings("ignore")

def extract_driver_names_with_camelot(pdf_path):
    """
    Extracts driver names from table-based manifests using Camelot.
    """
    try:
        tables = camelot.read_pdf(pdf_path, pages="1,2", flavor="stream")  # Stream mode for structured tables
        driver_names = []

        for table in tables:
            df = table.df  # Convert table to a pandas DataFrame
            # Look for rows containing "Name of Person Transporting"
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if "Name of Person Transporting" in str(cell):
                        # Extract name from the next column
                        if j + 1 < len(row):
                            name = str(row[j + 1]).strip()
                            if name and len(name) > 3:  # Basic validation
                                # Clean up extraneous text (e.g., "Employee ID of Driver")
                                name = re.sub(r"Employee ID of Driver|CCE\d+", "", name).strip()
                                driver_names.append(name)

        return driver_names

    except Exception:
        return []

def extract_driver_names_with_pdfplumber(pdf_path):
    """
    Extracts driver names from table-based manifests using pdfplumber.
    """
    try:
        driver_names = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:2]:  # Process only the first two pages
                tables = page.extract_tables()

                for table in tables:
                    for row in table:
                        if row and any(cell and "Name of Person Transporting" in str(cell) for cell in row):
                            # Extract name from the next column
                            idx = next(i for i, cell in enumerate(row) if cell and "Name of Person Transporting" in str(cell))
                            if idx + 1 < len(row) and row[idx + 1]:
                                name = str(row[idx + 1]).strip()
                                # Clean up extraneous text (e.g., "Employee ID of Driver")
                                name = re.sub(r"Employee ID of Driver|CCE\d+", "", name).strip()
                                driver_names.append(name)

        return driver_names

    except Exception:
        return []

def extract_driver_names_with_ocr(pdf_path, page_number=0):
    """
    Extracts driver names using OCR (Tesseract).
    """
    try:
        doc = fitz.open(pdf_path)
        if page_number >= len(doc):
            return []

        page = doc[page_number]

        # Version-compatible way to get high-resolution image
        try:
            pix = page.render_pixmap(dpi=600)
        except AttributeError:
            try:
                pix = page.get_pixmap(dpi=600)
            except TypeError:
                matrix = fitz.Matrix(4, 4)
                pix = page.get_pixmap(matrix=matrix)

        image_path = "temp_page.png"
        pix.save(image_path)

        # Enhanced image preprocessing
        image = Image.open(image_path)
        image = image.convert("L")  # Convert to grayscale
        image = image.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.0)

        # Apply OCR with custom configuration
        custom_config = r'--oem 3 --psm 6'
        ocr_data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
        os.remove(image_path)

        all_names = []

        # Extract names using OCR logic (linear or tabular formats)
        for i in range(len(ocr_data["text"])):
            if ocr_data["text"][i].strip() == "Name of Person Transporting":
                word_top = ocr_data["top"][i]
                word_left_end = ocr_data["left"][i] + ocr_data["width"][i]
                for j in range(i + 1, len(ocr_data["text"])):
                    if ocr_data["left"][j] > word_left_end and abs(ocr_data["top"][j] - word_top) < 30:
                        all_names.append(ocr_data["text"][j].strip())

        return all_names

    except Exception:
        return []

if __name__ == "__main__":
    pdf_file = "Appalachian Pharm Processing, LLC.pdf"

    if os.path.exists(pdf_file):
        driver_names = []

        # Try extracting driver names with Camelot
        camelot_driver_names = extract_driver_names_with_camelot(pdf_file)
        driver_names.extend(camelot_driver_names)

        # Try extracting driver names with pdfplumber
        pdfplumber_driver_names = extract_driver_names_with_pdfplumber(pdf_file)
        driver_names.extend(pdfplumber_driver_names)

        # Try extracting driver names with OCR
        for page_num in [0, 1]:  # Check both pages
            ocr_driver_names = extract_driver_names_with_ocr(pdf_file, page_number=page_num)
            driver_names.extend(ocr_driver_names)

        # Remove duplicates and format output
        unique_driver_names = list(dict.fromkeys(driver_names))  # Remove duplicates while preserving order

        if unique_driver_names:
            for i, name in enumerate(unique_driver_names, 1):
                print(f"Driver {i}: {name}")
        else:
            print("No driver names found in the PDF")
    else:
        print(f"PDF file not found: {pdf_file}")