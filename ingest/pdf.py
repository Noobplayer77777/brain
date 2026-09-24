import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

def parse_pdf(file_path: str) -> list[dict]:
    doc = fitz.open(file_path)
    pages_data = []
    
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        used_ocr = False
        
        # If text is too short, assume it might be a scanned image
        if len(text) < 50:
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            ocr_text = pytesseract.image_to_string(img).strip()
            if len(ocr_text) > len(text):
                text = ocr_text
                used_ocr = True
        
        pages_data.append({
            "page_no": i + 1,
            "text": text,
            "used_ocr": used_ocr
        })
    
    return pages_data
