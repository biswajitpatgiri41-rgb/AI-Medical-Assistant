import re

def extract_entities(text):

    patient = re.findall(r"(?:Patient Name|Name)\s*[:\-]\s*(.*)", text, re.IGNORECASE)

    diagnosis = re.findall(r"(?:Diagnosis|Disease|Condition)\s*[:\-]\s*(.*)", text, re.IGNORECASE)

    meds = re.findall(r"(?:Medication|Medicine|Drug)\s*[:\-]\s*(.*)", text, re.IGNORECASE)

    dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)

    return {
        "patient_name": patient,
        "dates": dates,
        "diagnosis": diagnosis,
        "medications": meds
    }