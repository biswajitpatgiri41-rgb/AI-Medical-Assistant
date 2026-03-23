import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from fpdf import FPDF
import io


try:
    from parser import extract_text
    from extractor import extract_medical_entities
    from fhir_mapper import map_to_fhir
    from icd_mapper import detect_icd
    from claim_validator import validate_claim
    from llm_engine import analyze_medical_text, chat_with_report
    # Assuming reconciliation logic is in your reconciliation.py or similar
    from reconciliation import reconcile_revenue 
except ImportError as e:
    st.error(f"⚠️ Missing Module: {e}")

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Title
    pdf.cell(190, 10, "Nexus Health RCM - Reconciliation Report", ln=True, align='C')
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(10)
    
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "1. Administrative & Payer Data", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(190, 8, f"Patient Name: {data['entities'].get('patient_name', 'N/A')}", ln=True)
    pdf.cell(190, 8, f"Provider/NPI Info: {data['entities'].get('provider_info', 'N/A')}", ln=True)
    pdf.ln(5)
    
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "2. Revenue Reconciliation Logic", ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 8, "Line Item Description", border=1)
    pdf.cell(60, 8, "Amount (USD)", border=1, ln=True)
    pdf.set_font("Arial", "", 10)
    
    line_items = data['entities'].get('billing_line_items', [])
    total = 0.0
    for item in line_items:
        pdf.cell(130, 8, str(item.get('item', 'Unknown')), border=1)
        pdf.cell(60, 8, f"${item.get('cost', 0.0):.2f}", border=1, ln=True)
        total += item.get('cost', 0.0)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 8, "Total Billed Amount Extracted", border=1)
    pdf.cell(60, 8, f"${total:.2f}", border=1, ln=True)
    pdf.ln(10)
    
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "3. Normalized Clinical Coding (ICD-10/CPT)", ln=True)
    pdf.set_font("Arial", "", 11)
    for code in data['icd']:
        pdf.cell(190, 7, f"- [{code.get('code', 'N/A')}] {code.get('description', 'N/A')}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(190, 5, "Confidential: This document is a normalized administrative layer output for RCM reconciliation and payer alignment.")
    
    return pdf.output(dest='S').encode('latin-1')

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nexus Health AI",
    page_icon="🏥",
    layout="wide"
)

# ---------------- CUSTOM UI (FIXED COLOR CONTRAST) ----------------
st.markdown("""
<style>
    /* Metric Card Fix */
    [data-testid="stMetricValue"] {
        color: #1E88E5 !important;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #555555 !important;
        font-size: 1.1rem;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff; /* White background for the card */
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .reconciliation-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 20px;
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_file' not in st.session_state:
    st.session_state.last_file = None

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("🏥 Nexus Health RCM")
    st.success("v2.1 - 2026 Production")
    
    st.divider()
    
    with st.expander("🛠️ Normalization Layer", expanded=True):
        st.caption("Standard: **FHIR R4 / CPT / ICD-10**")
        st.caption("Stakeholder: **Billing & RCM Managers**")
        fast_chat = st.toggle("Fast Chat (No Reasoning)", value=True)
    
    st.divider()
    if st.button("🗑️ Reset Engine", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

# ---------------- MAIN HEADER ----------------
st.title("AI Clinical & Administrative Normalization Engine")
st.markdown("Normalizing clinical narratives into **structured claim fields** and **Revenue Reconciliation** logic.")

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader(
    "Upload Clinical Document or Hospital Bill",
    type=["pdf", "docx", "jpg", "png"],
    help="Supports Discharge Summaries, Lab Reports, and Invoices."
)

# ---------------- PROCESSING ----------------
if uploaded_file:
    if st.session_state.last_file != uploaded_file.name:
        with st.status("🚀 Normalizing Intelligence...", expanded=True) as status:
            st.write("⚙️ Data Ingestion: Extracting Raw Assets...")
            raw_text = extract_text(uploaded_file)
            
            st.write("🔍 AI Extraction Layer: Parsing Entities & Line Items...")
            entities = extract_medical_entities(raw_text)
            
            st.write("🧬 FHIR Mapping: Converting to Interoperable Resources...")
            fhir_data = map_to_fhir(entities)
            
            st.write("📊 Coding Normalization: Mapping ICD-10...")
            icd_results = detect_icd(raw_text)
            
            st.write("⚖️ Revenue Logic: Validating Claim Integrity...")
            errors = validate_claim(entities)

            # Revenue Reconciliation Logic (PS-2)
            rec_results = reconcile_revenue(entities, raw_text)

            st.session_state.processed_data = {
                "text": raw_text,
                "entities": entities,
                "fhir": fhir_data,
                "icd": icd_results,
                "errors": errors,
                "reconciliation": rec_results
            }
            st.session_state.last_file = uploaded_file.name
            status.update(label="✅ Normalization Complete", state="complete")

    data = st.session_state.processed_data

    # ---------------- RCM DASHBOARD ----------------
    col_metrics, col_risk = st.columns([3, 1])
    
    with col_metrics:
        m1, m2, m3 = st.columns(3)
        m1.metric("Billed Amount", f"${data['entities'].get('total_billed_amount', 0.0):,.2f}")
        m2.metric("Normalized Codes", len(data['icd']), "ICD-10 Detected")
        
        # Calculate Denial Risk Score
        # Risk increases with reconciliation issues and validation errors
        base_risk = (len(data['reconciliation']['issues']) * 20) + (len(data['errors']) * 10)
        risk_score = min(100, base_risk)
        
        m3.metric("Denial Risk Score", f"{risk_score}%", delta="High Risk" if risk_score > 50 else "Low Risk", delta_color="inverse")

    with col_risk:
        # Denial Risk Gauge Chart
        fig_risk = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = risk_score,
            title = {'text': "Denial Probability", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "#1E88E5"},
                'steps' : [
                    {'range': [0, 30], 'color': "#c8e6c9"},
                    {'range': [30, 70], 'color': "#fff9c4"},
                    {'range': [70, 100], 'color': "#ffcdd2"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}))
        fig_risk.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
        st.plotly_chart(fig_risk, use_container_width=True)

    # ---------------- TABS ----------------
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "💰 Revenue Reconciliation", 
        "📋 Administrative Audit Log",
        "🧬 FHIR Standards", 
        "🔍 Clinical Insights", 
        "📊 Analytics", 
        "💬 RCM Assistant",
        "📄 Export Claim Bundle"
    ])

    with t1:
        st.subheader("Revenue Reconciliation Logic")
        st.markdown("Comparing extracted clinical justification against billed financial line items.")
        
        col_rec_a, col_rec_b = st.columns([2, 1])
        
        with col_rec_a:
            st.write("**Billed Line Items (Extracted from Document)**")
            line_items = data['entities'].get('billing_line_items', [])
            if line_items:
                df_rec = pd.DataFrame(line_items)
                st.table(df_rec)
            else:
                st.info("No explicit financial line items detected in this document.")
            
            st.write("**Clinical Justification (Normalization Layer)**")
            st.info(data['entities'].get('raw_text_summary', 'No justification available.'))

        with col_rec_b:
            st.write("**Reconciliation Issues**")
            rec_issues = data['reconciliation']['issues']
            if rec_issues:
                for issue in rec_issues:
                    st.error(f"**{issue['severity']}**: {issue['message']}")
            else:
                st.success("Revenue and Clinical records are 100% reconciled.")

    with t2:
        st.subheader("Administrative Audit Log")
        st.markdown("Transparency layer: Tracking how clinical unstructured text was normalized into administrative codes.")
        
        # Construct Audit Log Data
        audit_data = []
        # Log ICD mappings
        for icd in data['icd']:
            audit_data.append({
                "Timestamp": datetime.now().strftime("%H:%M:%S"),
                "Source Text": icd.get("description", "Unknown"),
                "Action": "Normalized to ICD-10",
                "Target Code": icd.get("code", "N/A"),
                "Confidence": "High"
            })
        # Log Procedure mappings
        for proc in data['entities'].get('procedures', []):
            audit_data.append({
                "Timestamp": datetime.now().strftime("%H:%M:%S"),
                "Source Text": proc,
                "Action": "Normalized to CPT/HCPCS",
                "Target Code": "Pending Payer Sync",
                "Confidence": "Medium"
            })
            
        if audit_data:
            st.table(pd.DataFrame(audit_data))
        else:
            st.info("No normalization actions logged for this document.")

    with t3:
        st.subheader("FHIR R4 Normalization Bundle")
        st.caption("Standardized format for TPA and EHR interoperability.")
        st.code(json.dumps(data['fhir'], indent=2), language="json")

    with t4:
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.subheader("AI Clinical Audit Reasoning")
            with st.chat_message("assistant"):
                st.write_stream(analyze_medical_text(data['text']))
            
            st.subheader("Normalized ICD-10 Coding")
            if data['icd']:
                st.dataframe(pd.DataFrame(data['icd']), use_container_width=True, hide_index=True)

        with col_right:
            st.subheader("Admin Entities")
            with st.expander("Normalized Schema", expanded=True):
                st.json(data['entities'])

    with t5:
        st.subheader("Administrative Dashboard")
        stats = pd.DataFrame({
            "Field": ["Line Items", "Procedures", "Codes", "Risk Flags"],
            "Count": [len(data['entities'].get('billing_line_items', [])), 
                      len(data['entities'].get('procedures', [])), 
                      len(data['icd']), 
                      len(data['reconciliation']['issues'])]
        })
        st.plotly_chart(px.bar(stats, x="Field", y="Count", color="Field", text_auto=True), use_container_width=True)

    with t6:
        st.subheader("💬 RCM Policy & Claim Assistant")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Ask about payer policy or reconciliation errors..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                response = st.write_stream(chat_with_report(data['text'], prompt))
            st.session_state.messages.append({"role": "assistant", "content": response})

    with t7:
        st.subheader("Download Normalized RCM Bundle")
        st.markdown("Download the structured data for Payer Submission or Revenue Reconciliation.")
        
        pdf_data = create_pdf(data)
        st.download_button(
            label="📥 Download RCM Reconciliation PDF",
            data=pdf_data,
            file_name=f"RCM_Bundle_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        st.write("---")
        st.markdown("### Preview of Administrative Normalization")
        st.write(f"**Provider Info:** {data['entities'].get('provider_info', 'Unknown')}")
        st.write(f"**Detected Procedures:** {', '.join(data['entities'].get('procedures', ['None']))}")

else:
    st.info("👋 Welcome to Nexus Health AI. Please upload a Health Record (Summary, Lab, or Bill) to begin normalization.")

st.divider()
st.caption(f"Developed for Hackathon 2026 | PS-2 RCM Normalization Engine")