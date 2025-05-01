import fitz  # PyMuPDF
from pytesseract import pytesseract, Output
from PIL import Image, ImageEnhance, ImageFilter
import os
import re
import camelot
import pdfplumber

def extract_driver_names_with_camelot(pdf_path):
    """
    Extracts driver names from table-based manifests using Camelot.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        tuple: (filename, list of driver names).
    """
    filename = os.path.basename(pdf_path)
    try:
        tables = camelot.read_pdf(pdf_path, pages="1,2", flavor="stream")
        driver_names = []

        for table in tables:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if "Name of Person Transporting" in str(cell):
                        if j + 1 < len(row):
                            name = str(row[j + 1]).strip()
                            if name and len(name) > 3:
                                name = re.sub(r"Employee ID of Driver|CCE\d+", "", name).strip()
                                driver_names.append(name)

        return (filename, driver_names)

    except Exception:
        return (filename, [])

def extract_driver_names_with_pdfplumber(pdf_path):
    """
    Extracts driver names from table-based manifests using pdfplumber.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        tuple: (filename, list of driver names).
    """
    filename = os.path.basename(pdf_path)
    try:
        driver_names = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:2]:
                tables = page.extract_tables()

                for table in tables:
                    for row in table:
                        if row and any(cell and "Name of Person Transporting" in str(cell) for cell in row):
                            idx = next(i for i, cell in enumerate(row) if cell and "Name of Person Transporting" in str(cell))
                            if idx + 1 < len(row) and row[idx + 1]:
                                name = str(row[idx + 1]).strip()
                                name = re.sub(r"Employee ID of Driver|CCE\d+", "", name).strip()
                                driver_names.append(name)

        return (filename, driver_names)

    except Exception:
        return (filename, [])

def extract_driver_names_with_ocr(pdf_path, page_number=0):
    """
    Extracts driver names using OCR (Tesseract).
    Args:
        pdf_path (str): Path to the PDF file.
        page_number (int): Page number to process (0-based).
    Returns:
        tuple: (filename, list of driver names).
    """
    filename = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        if page_number >= len(doc):
            return (filename, [])

        page = doc[page_number]

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

        image = Image.open(image_path)
        image = image.convert("L")
        image = image.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.0)

        custom_config = r'--oem 3 --psm 6'
        ocr_data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
        os.remove(image_path)

        all_names = []

        for i in range(len(ocr_data["text"])):
            if ocr_data["text"][i].strip() == "Name of Person Transporting":
                word_top = ocr_data["top"][i]
                word_left_end = ocr_data["left"][i] + ocr_data["width"][i]
                for j in range(i + 1, len(ocr_data["text"])):
                    if ocr_data["left"][j] > word_left_end and abs(ocr_data["top"][j] - word_top) < 30:
                        all_names.append(ocr_data["text"][j].strip())

        return (filename, all_names)

    except Exception:
        return (filename, [])