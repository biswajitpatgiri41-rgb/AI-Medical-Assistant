import os
from openai import OpenAI


API_KEY = "<your-api-key>"
BASE_URL = "https://openai.com"


MODEL_NAME = "deepseek-ai/deepseek-r1-distill-llama-8b"

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)



def get_medical_ai_stream(messages, temperature=0.5, max_tokens=2048):
    """
    Generalized streaming function for DeepSeek-R1 models.
    """
    try:
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
    except Exception as e:
        print(f"NVIDIA API Error: {e}")
        return None


def analyze_medical_text(text):
    """
    Performs deep clinical analysis of raw OCR text.
    """
    if not text or len(str(text).strip()) < 10:
        return None

    system_prompt = (
        "You are an expert Clinical Analyst. Analyze the medical report below. "
        "Output structured Markdown with: "
        "1. Patient Info, 2. Diagnoses, 3. Procedures/Meds, 4. Coding Risks, 5. Simple Summary."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"REPORT CONTENT:\n{text[:12000]}"}
    ]

    return get_medical_ai_stream(messages, temperature=0.3)


def chat_with_report(report_context, user_query):
    """
    Context-aware patient assistant for report explanations.
    """
    if not report_context:
        return None

    system_prompt = (
        "You are Nexus Health AI. Answer the user question strictly using the report context. "
        "If info is missing, say so. End with: '***Disclaimer:** AI-generated. Consult a doctor.*'"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"CONTEXT:\n{report_context[:8000]}\n\nQUESTION: {user_query}"}
    ]


    return get_medical_ai_stream(messages, temperature=0.2, max_tokens=1024)