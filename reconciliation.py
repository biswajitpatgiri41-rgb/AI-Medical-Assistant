import pandas as pd

def reconcile_revenue(entities, raw_text):
    """
    Advanced Revenue Reconciliation Logic (PS-2 Deliverable):
    Cross-references clinical evidence (Clinical Layer) against 
    billing line items (Administrative Layer) to find revenue leakage.
    """
    reconciliation_results = {
        "issues": [],
        "revenue_leakage_detected": 0.0,
        "compliance_score": 100,
        "summary": ""
    }
    
    issues = []
    clinical_evidence = entities.get("procedures", []) + entities.get("medications", [])
    billed_items = entities.get("billing_line_items", [])
    
    # Extract just the text names of billed items for easy comparison
    billed_names = [item.get("item", "").lower() for item in billed_items]
    
  
    for service in clinical_evidence:
        found_in_bill = any(service.lower() in b_name for b_name in billed_names)
        if not found_in_bill:
            issues.append({
                "severity": "High - Revenue Leakage",
                "message": f"Clinical work '{service}' was documented but does not appear as a billed line item.",
                "type": "Unbilled Service"
            })
            reconciliation_results["compliance_score"] -= 10

    
    for bill in billed_items:
        item_name = bill.get("item", "")
        if item_name.lower() not in raw_text.lower():
            issues.append({
                "severity": "Critical - Audit Risk",
                "message": f"Billed item '{item_name}' lacks supporting documentation in the clinical narrative.",
                "type": "Unsupported Charge"
            })
            reconciliation_results["compliance_score"] -= 15

    # 3. FINANCIAL INTEGRITY CHECKS
    total_calculated = sum(item.get("cost", 0.0) for item in billed_items)
    extracted_total = entities.get("total_billed_amount", 0.0)
    
    if abs(total_calculated - extracted_total) > 1.0:
        issues.append({
            "severity": "Medium - Financial Variance",
            "message": f"Sum of line items (${total_calculated:.2f}) does not match total billed amount (${extracted_total:.2f}).",
            "type": "Calculation Mismatch"
        })
        reconciliation_results["compliance_score"] -= 5

    # 4. PATIENT IDENTITY RECONCILIATION
    if not entities.get("patient_name") or entities.get("patient_name") == "Unknown":
        issues.append({
            "severity": "Critical - Identity Missing",
            "message": "Patient identification could not be normalized. Claim will be rejected.",
            "type": "Administrative"
        })
        reconciliation_results["compliance_score"] = 0

    reconciliation_results["issues"] = issues
    reconciliation_results["revenue_leakage_detected"] = total_calculated
    
    # Final Summary Generation
    if not issues:
        reconciliation_results["summary"] = "Revenue and Clinical records are 100% reconciled."
    else:
        reconciliation_results["summary"] = f"Detected {len(issues)} discrepancies between clinical documentation and billing."

    return reconciliation_results