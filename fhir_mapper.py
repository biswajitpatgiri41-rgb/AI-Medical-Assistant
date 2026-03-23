import json
import uuid
from openai import OpenAI


client = OpenAI(
    base_url="https://openai.com",
    api_key="<Your-API_Key>"
)

MODEL_NAME = "openai/gpt-oss-120b"

def map_to_fhir(data):
    """
    RCM-Normalized FHIR R4 Harmonizer: 
    Converts unstructured medical/financial data into a structured Payer-Ready 
    Revenue Reconciliation Bundle (Claim, EOB, Patient, Condition).
    """
    patient_id = f"patient-{uuid.uuid4().hex[:8]}"
    claim_id = f"claim-{uuid.uuid4().hex[:8]}"
    eob_id = f"eob-{uuid.uuid4().hex[:8]}"
    
    
    enrichment_prompt = f"""
    [ROLE] Senior Medical Coder
    [TASK] Normalize clinical text to official FHIR R4 coding systems for Revenue Reconciliation.
    
    [DATA]
    Diagnoses: {data.get('diagnosis', [])}
    Procedures: {data.get('procedures', [])}
    
    [OUTPUT]
    Return JSON: 
    {{
        "conditions": [{{"text": "...", "code": "...", "system": "http://snomed.info/sct"}}],
        "procedures": [{{"text": "...", "code": "...", "system": "http://www.ama-assn.org/go/cpt"}}]
    }}
    """
    
    try:
        enrichment = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": enrichment_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        enriched_data = json.loads(enrichment.choices[0].message.content)
    except:
        enriched_data = {"conditions": [], "procedures": []}

    
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": []
    }

    
    patient_name = data.get("patient_name", "Unknown Patient")
    bundle["entry"].append({
        "fullUrl": f"urn:uuid:{patient_id}",
        "resource": {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"use": "official", "text": patient_name}],
            "active": True
        },
        "request": {"method": "POST", "url": "Patient"}
    })

   
    for idx, item in enumerate(enriched_data.get("conditions", [])):
        cond_id = f"cond-{idx}"
        bundle["entry"].append({
            "fullUrl": f"urn:uuid:{cond_id}",
            "resource": {
                "resourceType": "Condition",
                "id": cond_id,
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "code": {
                    "coding": [{"system": item.get("system"), "code": item.get("code"), "display": item.get("text")}]
                },
                "subject": {"reference": f"urn:uuid:{patient_id}"}
            },
            "request": {"method": "POST", "url": "Condition"}
        })

   
    claim_resource = {
        "resourceType": "Claim",
        "id": claim_id,
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "institutional"}]},
        "use": "claim",
        "patient": {"reference": f"urn:uuid:{patient_id}"},
        "created": data.get("dates", ["2026-03-22"])[0],
        "provider": {"display": data.get("provider_info", "Unknown Hospital/Provider")},
        "priority": {"coding": [{"code": "normal"}]},
        "insurance": [{"sequence": 1, "focal": True, "coverage": {"display": "Self-Pay / To Be Adjudicated"}}],
        "item": [],
        "total": {"value": data.get("total_billed_amount", 0.0), "currency": "USD"}
    }

    
    billing_items = data.get("billing_line_items", [])
    if not billing_items and enriched_data.get("procedures"):
        billing_items = [{"item": p.get("text"), "cost": 0.0} for p in enriched_data["procedures"]]

    for i, item in enumerate(billing_items):
        claim_resource["item"].append({
            "sequence": i + 1,
            "productOrService": {
                "coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "Pending Mapping"}],
                "text": item.get("item", "Unclassified Service")
            },
            "unitPrice": {"value": item.get("cost", 0.0), "currency": "USD"},
            "net": {"value": item.get("cost", 0.0), "currency": "USD"}
        })

    bundle["entry"].append({
        "fullUrl": f"urn:uuid:{claim_id}",
        "resource": claim_resource,
        "request": {"method": "POST", "url": "Claim"}
    })

    
    bundle["entry"].append({
        "fullUrl": f"urn:uuid:{eob_id}",
        "resource": {
            "resourceType": "ExplanationOfBenefit",
            "id": eob_id,
            "status": "active",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "institutional"}]},
            "use": "claim",
            "patient": {"reference": f"urn:uuid:{patient_id}"},
            "outcome": "complete",
            "claim": {"reference": f"urn:uuid:{claim_id}"},
            "total": [{"category": {"text": "Total Billed"}, "amount": {"value": data.get("total_billed_amount", 0.0), "currency": "USD"}}],
            "supportingInfo": [{"sequence": 1, "category": {"text": "Clinical Summary"}, "valueString": data.get("raw_text_summary", "Normalized via AI Engine")}]
        },
        "request": {"method": "POST", "url": "ExplanationOfBenefit"}
    })

    return bundle