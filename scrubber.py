import json
from openai import OpenAI

# Initialize the OpenAI-compatible client
client = OpenAI(
    base_url="https://openai.com",
    api_key="<your-api-key>"
)

MODEL_NAME = "openai/gpt-oss-120b"

def scrub_claim(entities, icd_codes):
    """
    Intelligent Normalization Scrubber (PS-2 Core Logic):
    Performs 'Claim Scrubbing' to predict insurance denials and detect 
    billing anomalies like Upcoding or lack of Medical Necessity.
    """
    
    scrub_report = {
        "denial_prediction_score": 0,  # 0 to 100 (Higher means more likely to be denied)
        "flags": [],
        "recommendations": [],
        "status": "Pass"
    }

    # Preparation of data for the AI Auditor
    billed_items = [item.get("item") for item in entities.get("billing_line_items", [])]
    clinical_dx = [icd.get("description") for icd in icd_codes]
    procedures = entities.get("procedures", [])

    # AI-Driven Medical Necessity & Upcoding Audit
    scrub_prompt = f"""
    [ROLE] Professional Insurance Claim Scrubber
    [TASK] Audit the following clinical vs. billing data for anomalies.

    [DATA]
    - Diagnoses (ICD-10): {clinical_dx}
    - Documented Procedures: {procedures}
    - Billed Line Items: {billed_items}
    - Total Billed: ${entities.get('total_billed_amount')}

    [AUDIT CRITERIA]
    1. MEDICAL NECESSITY: Are the billed items justified by the diagnoses?
    2. UPCODING: Does the price/complexity of the bill exceed the clinical findings?
    3. MISSING DOCUMENTATION: Are there billed procedures that weren't documented in notes?

    [OUTPUT FORMAT]
    Return JSON: 
    {{
        "risk_score": int, 
        "anomalies": ["string"], 
        "fix_suggestions": ["string"]
    }}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a claim scrubbing engine. Be strict and factual."},
                {"role": "user", "content": scrub_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.1
        )

        audit_result = json.loads(response.choices[0].message.content)
        
        scrub_report["denial_prediction_score"] = audit_result.get("risk_score", 0)
        scrub_report["flags"] = audit_result.get("anomalies", [])
        scrub_report["recommendations"] = audit_result.get("fix_suggestions", [])
        
        if scrub_report["denial_prediction_score"] > 50:
            scrub_report["status"] = "High Risk - Review Required"
        elif scrub_report["denial_prediction_score"] > 20:
            scrub_report["status"] = "Warning - Minor Issues"
        else:
            scrub_report["status"] = "Clean Claim"

    except Exception as e:
        scrub_report["flags"].append(f"Scrubber System Error: {str(e)}")
        scrub_report["status"] = "System Error"

    return scrub_report

def analyze_revenue_leakage(entities):
    """
    Identifies procedures documented in text but NOT found in the bill.
    This fulfills the 'Revenue Reconciliation Logic' deliverable.
    """
    leakage = []
    documented = [p.lower() for p in entities.get("procedures", [])]
    billed = [b.get("item", "").lower() for b in entities.get("billing_line_items", [])]

    for proc in documented:
        # Check if the documented procedure is missing from the bill
        if not any(proc in b_item for b_item in billed):
            leakage.append({
                "item": proc,
                "impact": "Potential Revenue Loss",
                "action": "Add to billable line items"
            })
            
    return leakage