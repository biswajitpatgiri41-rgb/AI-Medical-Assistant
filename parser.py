import PyPDF2
import io
import base64
from PIL import Image
from docx import Document


try:
    from ocr import extract_text_from_image 
except ImportError:
    def extract_text_from_image(file): 
        return "Error: ocr.py module not found."

def file_to_base64(uploaded_file):
    """
    Helper to convert uploaded file buffer to Base64 string for NVIDIA NIM.
    """
    uploaded_file.seek(0)
    return base64.b64encode(uploaded_file.read()).decode('utf-8')

def extract_text(uploaded_file):
    """
    Universal Ingestion Module:
    Prioritizes digital text extraction, falls back to OCR for scanned docs.
    """
    if uploaded_file is None:
        return "No file uploaded."

    file_name = uploaded_file.name.lower()
    uploaded_file.seek(0) # Always start at the beginning of the file

    # --- 1. Digital PDF Extraction ---
    if file_name.endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # If we found substantial text, it's a digital PDF
            if len(text.strip()) > 20:
                return text.strip()
            
            
            st_msg = "Scanned PDF detected. Routing to OCR..."
            print(st_msg)
            return extract_text_from_image(uploaded_file)

        except Exception as e:
            return f"PDF Extraction Error: {str(e)}"

    # --- 2. Word Document Extraction ---
    elif file_name.endswith(".docx"):
        try:
            doc = Document(uploaded_file)
            full_text = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(full_text)
        except Exception as e:
            return f"DOCX Extraction Error: {str(e)}"

    # --- 3. Image Extraction (OCR/VLM) ---
    elif file_name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        try:
            return extract_text_from_image(uploaded_file)
        except Exception as e:
            return f"Image OCR Error: {str(e)}"

    return "Unsupported format. Please use PDF, DOCX, or Images (JPG/PNG)."