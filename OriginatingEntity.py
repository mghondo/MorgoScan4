import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pytesseract import Output
import os


def process_pdf(pdf_path):
    """
    Extract the company name to the right of 'Originating Entity' using OCR.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        tuple: (filename, result) where result is the company name or an error message.
    """
    filename = os.path.basename(pdf_path)

    if not os.path.exists(pdf_path):
        return (filename, f"PDF file not found: {pdf_path}")

    # Convert first PDF page to high-res image
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = 2  # Reduced zoom for better text grouping
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_path = "high_res_page.png"
    pix.save(img_path)
    doc.close()

    # OCR with optimized configuration
    ocr_data = pytesseract.image_to_data(
        Image.open(img_path),
        output_type=Output.DICT,
        config='--psm 4',  # Assume column-based text
        lang='eng'
    )

    # Find "Originating" and "Entity" positions
    originating_idx = -1
    entity_idx = -1
    for i in range(len(ocr_data["text"])):
        text = ocr_data["text"][i].strip().lower()
        if "originating" in text:
            originating_idx = i
        elif "entity" in text and originating_idx != -1 and (i - originating_idx) <= 2:
            entity_idx = i
            break

    if originating_idx == -1 or entity_idx == -1:
        return (filename, "Could not locate 'Originating Entity'")

    # Calculate combined bounding box
    orig_left = ocr_data["left"][originating_idx]
    orig_top = ocr_data["top"][originating_idx]
    entity_right = ocr_data["left"][entity_idx] + ocr_data["width"][entity_idx]

    # Find text to the right of "Entity"
    company_text = []
    y_tolerance = 15  # Vertical position tolerance

    for i in range(len(ocr_data["text"])):
        if ocr_data["left"][i] > entity_right and \
                abs(ocr_data["top"][i] - orig_top) < y_tolerance:
            company_text.append(ocr_data["text"][i])

    # Clean the result
    if company_text:
        cleaned = ' '.join(company_text) \
            .replace('LLC', '') \
            .replace('For Agency Use Only', '') \
            .replace(', ', '') \
            .replace('[', '') \
            .replace(']', '') \
            .strip()
        return (filename, cleaned if cleaned else "No company name found")

    return (filename, "No company name found")