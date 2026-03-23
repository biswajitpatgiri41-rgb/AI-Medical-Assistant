import requests
import base64
import io
import json
from PIL import Image, ImageEnhance, ImageFilter


INVOKE_URL = "https://openai.com"
API_KEY = "<your-api-key>"

def preprocess_image(image_file):
    """
    Refined preprocessing: Enhances text-to-background contrast 
    without losing stroke detail in handwriting.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    else:
        img = img.convert("L").convert("RGB")

    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.5)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    
    base_height = 1600
    w_percent = (base_height / float(img.size[1]))
    w_size = int((float(img.size[0]) * float(w_percent)))
    img = img.resize((w_size, base_height), Image.Resampling.LANCZOS)

    return img

def compress_image(img):
    """
    Smart compression to stay under the 180KB-200KB base64 string limit
    typically associated with serverless NVIDIA NIM endpoints.
    """
    quality = 90
    final_b64 = ""
    # Adjusted limit to ensure the base64 string doesn't exceed API constraints
    LIMIT_BYTES = 180000 

    while quality > 20:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        img_bytes = buffer.getvalue()
        
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        if len(b64_str) < LIMIT_BYTES:
            final_b64 = b64_str
            break
        
        quality -= 10
        width, height = img.size
        img = img.resize((int(width*0.9), int(height*0.9)), Image.Resampling.LANCZOS)

    return final_b64

def extract_text_from_image(image_file):
    """
    Corrected API call logic for NVIDIA Nemoretriever OCR NIM.
    Matches the v1/infer schema required for NeMo Retriever.
    """
    try:
        processed_img = preprocess_image(image_file)
        image_b64 = compress_image(processed_img)

        if not image_b64:
            return "Error: Image exceeds API size limits even after compression."

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        
        payload = {
            "input": [
                {
                    "type": "image_url",
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }
            ]
        }

        response = requests.post(
            f"{INVOKE_URL}",
            headers=headers,
            json=payload,
            timeout=45
        )

        if response.status_code != 200:
            return f"NVIDIA API Error ({response.status_code}): {response.text}"

        res_json = response.json()

        # NeMo Retriever OCR returns structured data in a 'data' array.
        # It detects text fragments (detections) which we join into a full text.
        extracted_text_list = []
        if "data" in res_json:
            for page in res_json["data"]:
                detections = page.get("text_detections", [])
                # Join the individual text predictions
                page_text = " ".join([d["text_prediction"]["text"] for d in detections if "text_prediction" in d])
                extracted_text_list.append(page_text)
            
            full_text = "\n".join(extracted_text_list)
        else:
            # Fallback for alternative NIM response formats
            full_text = res_json.get("text", "")

        if not full_text or len(full_text.strip()) < 2:
            return "Error: OCR was unable to detect readable characters."

        return full_text.strip()

    except Exception as e:
        return f"OCR Pipeline Exception: {str(e)}"