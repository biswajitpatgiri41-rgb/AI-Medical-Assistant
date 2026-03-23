import os
from openai import OpenAI


client = OpenAI(
    base_url="https://openai.com",
    api_key="<Your-API-Key>"
)

MODEL_NAME = "openai/gpt-oss-120b"

def validate_claim(data):
    """
    Advanced Clinical Integrity Auditor:
    Validates structural integrity and performs AI-driven medical necessity audits.
    """
    if not data:
        return ["CRITICAL: No data provided for validation."]

    errors = []
    
    
    billed_amount = data.get("total_billed_amount")
    
    if not data.get("patient_name"):
        errors.append("CRITICAL: Patient Identity not found in document.")
    
    if not data.get("diagnosis"):
        errors.append("CRITICAL: Clinical diagnosis missing; cannot establish medical necessity.")
        
    if billed_amount is None:
        errors.append("WARNING: Financial field 'Total Billed' is missing.")
    elif not isinstance(billed_amount, (int, float)):
        errors.append(f"ERROR: Invalid currency format for amount: {billed_amount}")
    elif billed_amount <= 0:
        errors.append("WARNING: Financial values are zero or negative.")

    
    audit_prompt = f"""
    [ROLE] Senior Clinical Auditor
    [TASK] Evaluate 'Medical Necessity' and 'Clinical Consistency'.
    
    [DATA]
    - Patient: {data.get('patient_name', 'Unknown')}
    - Diagnoses: {data.get('diagnosis', 'Not Listed')}
    - Clinical Evidence: {data.get('raw_text_summary', 'No summary available')}

    [INSTRUCTIONS]
    1. Identify if the diagnosis is supported by the lab findings/text.
    2. Flag missing standard-of-care procedures for this diagnosis.
    3. Return ONLY specific audit warnings. If perfect, return 'VALID'.
    
    [FORMAT]
    - Start each warning with 'AUDIT:'
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a clinical compliance auditor focused on HIPAA and CMS guidelines."},
                {"role": "user", "content": audit_prompt}
            ],
            temperature=0.1, # Keep it strictly factual
            max_tokens=250
        )
        
        audit_result = response.choices[0].message.content.strip()
        
        if "VALID" not in audit_result.upper():
           
            ai_warnings = [line.strip() for line in audit_result.split('\n') if line.strip()]
            errors.extend(ai_warnings)

    except Exception as e:
        
        errors.append(f"SYSTEM: AI Auditor is currently offline ({str(e)})")

    return errors