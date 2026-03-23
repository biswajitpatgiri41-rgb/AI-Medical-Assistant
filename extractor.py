import json
import os
from openai import OpenAI


client = OpenAI(
    base_url="https://openai.com",
    api_key="<Your-API-key>"
)

MODEL_NAME = "openai/gpt-oss-120b"

def extract_medical_entities(text):
    """
    RCM-Optimized Extraction Engine:
    Normalizes clinical data into structured administrative fields for 
    Revenue Reconciliation and FHIR Claim mapping.
    """
    
    
    default_schema = {
        "patient_name": "Unknown",
        "dates": [],
        "diagnosis": [],        
        "procedures": [],       
        "medications": [],
        "provider_info": "Unknown", 
        "total_billed_amount": 0.0,
        "billing_line_items": [], 
        "raw_text_summary": "No clinical summary available."
    }

    if not text or len(str(text).strip()) < 10:
        return default_schema

    
    prompt = f"""
    [ROLE] Senior Revenue Cycle Management (RCM) Data Analyst.
    [TASK] Extract and normalize data from the medical record for Insurance Claim filing and Revenue Reconciliation.

    [EXTRACTION RULES]
    1. patient_name: Full legal name.
    2. dates: All service, admission, and discharge dates.
    3. diagnosis: Clinical findings and confirmed diseases (ICD-ready).
    4. procedures: Any tests, surgeries, or scans performed (CPT-ready).
    5. medications: All drugs with dosages and frequencies.
    6. provider_info: Extract Doctor names, Hospital name, or NPI/Tax IDs if present.
    7. total_billed_amount: NUMBER ONLY. The final total charge on the document.
    8. billing_line_items: Array of objects [{{"item": "string", "cost": number}}]. Extract individual billable services.
    9. raw_text_summary: A concise clinical justification for the services rendered (Medical Necessity).

    [TEXT]
    {text[:8000]}

    [FORMAT] Return ONLY a valid JSON object.
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an RCM normalization engine. Output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.1
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        
      
        billed = data.get("total_billed_amount")
        try:
            if billed is None:
                data["total_billed_amount"] = 0.0
            else:
                clean_billed = str(billed).replace('$', '').replace(',', '').strip()
                data["total_billed_amount"] = float(clean_billed)
        except (ValueError, TypeError):
            data["total_billed_amount"] = 0.0

       
        if "billing_line_items" in data and isinstance(data["billing_line_items"], list):
            for item in data["billing_line_items"]:
                if isinstance(item, dict) and "cost" in item:
                    try:
                        item["cost"] = float(str(item["cost"]).replace('$', '').replace(',', '').strip())
                    except:
                        item["cost"] = 0.0

        
        for key, default_val in default_schema.items():
            if key not in data or data[key] is None:
                data[key] = default_val
            
        return data

    except Exception as e:
        print(f"RCM Extraction Pipeline Error: {e}")
        return default_schema