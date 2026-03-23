import time
import json
from openai import OpenAI


client = OpenAI(
    base_url="https://openai.com",
    api_key="<Your-API-Key>"
)


MODEL_NAME = "openai/gpt-oss-120b"

def detect_icd(text):
    """
    Dynamically maps text to specific ICD-10-CM codes using NVIDIA NIM 120b model.
    Ensures high specificity for clinical findings.
    """
    if not text or len(text.strip()) < 10:
        return []

    context = text[:5000] 

    
    prompt = f"""
    You are a Certified Medical Coder (CPC). 
    Your task is to analyze the medical text and extract highly specific ICD-10-CM codes.
    
    GUIDELINES:
    1. Identify definitive diagnoses (e.g., 'Diabetes').
    2. Identify clinical findings/abnormalities (e.g., 'Hyperbilirubinemia' for high Bilirubin).
    3. Use the most specific code possible (e.g., K76.89 for other specified diseases of liver).
    
    Text: 
    {context}
    
    Format the output as a JSON list: [{{ "disease": "Clinical Name", "icd_code": "Code" }}]
    Return ONLY raw JSON. If nothing is found, return [].
    """

    for i in range(2): 
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a professional medical coding engine. Output only valid JSON lists."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.1 
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            
            if isinstance(data, dict):
                for key in ["codes", "icd_codes", "results", "diagnoses"]:
                    if key in data:
                        return data[key]
                # If no key found, check if the dict is the first entry
                return [data] if "icd_code" in data else []
                
            return data if isinstance(data, list) else []

        except Exception as e:
            print(f"ICD Mapping Error (Attempt {i+1}): {e}")
            time.sleep(2)

    return []