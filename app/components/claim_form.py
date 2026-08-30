"""Shared structured-field form widgets for entering a claim.

Dropdown options are restricted to the categories observed in the curated
100-claim training sample (see docs/limitations.md) - safe for the rule
engine and the ML encoder, though a production system would offer the full
insurer schema.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

OPTIONS = {
    "Make": ["Accura", "BMW", "Chevrolet", "Dodge", "Ford", "Honda", "Mazda", "Mercury", "Pontiac", "Saab"],
    "Sex": ["Male", "Female"],
    "MaritalStatus": ["Married", "Single"],
    "Fault": ["Policy Holder", "Third Party"],
    "PolicyType": ["Sedan - All Perils", "Sedan - Collision", "Sedan - Liability", "Sport - Collision", "Utility - All Perils"],
    "VehicleCategory": ["Sedan", "Sport", "Utility"],
    "VehiclePrice": ["less than 20000", "20000 to 29000", "30000 to 39000", "40000 to 59000", "60000 to 69000", "more than 69000"],
    "AgentType": ["External", "Internal"],
    "BasePolicy": ["Liability", "Collision", "All Perils"],
    "Days_Policy_Accident": ["none", "1 to 7", "8 to 15", "15 to 30", "more than 30"],
    "Days_Policy_Claim": ["8 to 15", "15 to 30", "more than 30"],
    "PastNumberOfClaims": ["none", "1", "2 to 4", "more than 4"],
    "AgeOfVehicle": ["new", "2 years", "3 years", "4 years", "5 years", "6 years", "7 years", "more than 7"],
    "AgeOfPolicyHolder": ["16 to 17", "18 to 20", "21 to 25", "26 to 30", "31 to 35", "36 to 40", "41 to 50", "51 to 65", "over 65"],
    "PoliceReportFiled": ["Yes", "No"],
    "WitnessPresent": ["Yes", "No"],
    "NumberOfSuppliments": ["none", "1 to 2", "3 to 5", "more than 5"],
    "AddressChange_Claim": ["no change", "1 year", "2 to 3 years", "4 to 8 years", "over 8 years"],
    "NumberOfCars": ["1 vehicle", "2 vehicles", "3 to 4", "5 to 8", "more than 8"],
    "AccidentArea": ["Urban", "Rural"],
}


def render_claim_form(key_prefix: str = "new_claim", defaults: dict | None = None) -> dict | None:
    """Renders the structured claim form. Returns a dict of raw fields plus
    accident_date/claim_date on submit, or None if not yet submitted."""
    defaults = defaults or {}

    with st.form(key=f"{key_prefix}_form"):
        st.markdown("##### Vehicle & Policyholder")
        c1, c2, c3 = st.columns(3)
        make = c1.selectbox("Make", OPTIONS["Make"], index=OPTIONS["Make"].index(defaults.get("Make", "Honda")))
        sex = c2.selectbox("Sex", OPTIONS["Sex"])
        marital = c3.selectbox("Marital Status", OPTIONS["MaritalStatus"])

        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Policyholder Age", min_value=16, max_value=90, value=int(defaults.get("Age", 35)))
        age_of_policyholder = c2.selectbox("Age of Policyholder (bucket)", OPTIONS["AgeOfPolicyHolder"], index=4)
        driver_rating = c3.number_input("Driver Rating", min_value=1, max_value=4, value=2)

        c1, c2, c3 = st.columns(3)
        vehicle_category = c1.selectbox("Vehicle Category", OPTIONS["VehicleCategory"])
        vehicle_price = c2.selectbox("Vehicle Price Range", OPTIONS["VehiclePrice"], index=1)
        vehicle_age = c3.selectbox("Age of Vehicle", OPTIONS["AgeOfVehicle"], index=4)

        st.markdown("##### Policy")
        c1, c2, c3 = st.columns(3)
        base_policy = c1.selectbox("Base Policy", OPTIONS["BasePolicy"], index=1)
        policy_type = c2.selectbox("Policy Type", OPTIONS["PolicyType"], index=1)
        agent_type = c3.selectbox("Agent Type", OPTIONS["AgentType"])

        c1, c2, c3 = st.columns(3)
        deductible = c1.number_input("Deductible", min_value=300, max_value=1000, value=400, step=50)
        days_policy_accident = c2.selectbox("Days Since Policy Start (at accident)", OPTIONS["Days_Policy_Accident"], index=4)
        days_policy_claim = c3.selectbox("Days Since Policy Start (at claim)", OPTIONS["Days_Policy_Claim"], index=2)

        st.markdown("##### Incident")
        c1, c2, c3 = st.columns(3)
        accident_area = c1.selectbox("Accident Area", OPTIONS["AccidentArea"])
        fault = c2.selectbox("Fault", OPTIONS["Fault"])
        accident_date_in = c3.date_input("Accident Date", value=date.today())

        c1, c2 = st.columns(2)
        claim_date_in = c1.date_input("Claim Filed Date", value=date.today())
        number_of_cars = c2.selectbox("Number of Cars Involved", OPTIONS["NumberOfCars"])

        st.markdown("##### Evidence & History")
        c1, c2, c3 = st.columns(3)
        police_report = c1.selectbox("Police Report Filed", OPTIONS["PoliceReportFiled"])
        witness = c2.selectbox("Witness Present", OPTIONS["WitnessPresent"])
        past_claims = c3.selectbox("Past Number of Claims", OPTIONS["PastNumberOfClaims"])

        c1, c2 = st.columns(2)
        supplements = c1.selectbox("Number of Supplementary Repairs", OPTIONS["NumberOfSuppliments"])
        address_change = c2.selectbox("Address Change Since Claim", OPTIONS["AddressChange_Claim"])

        st.markdown("##### Optional: narrative & photo")
        narrative_text = st.text_area("Narrative / adjuster notes (optional)", height=100)
        image_file = st.file_uploader("Accident photo (optional)", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("Analyze Claim")

    if not submitted:
        return None

    return {
        "raw_fields": {
            "Make": make, "Sex": sex, "MaritalStatus": marital, "Age": age,
            "AgeOfPolicyHolder": age_of_policyholder, "DriverRating": driver_rating,
            "VehicleCategory": vehicle_category, "VehiclePrice": vehicle_price, "AgeOfVehicle": vehicle_age,
            "BasePolicy": base_policy, "PolicyType": policy_type, "AgentType": agent_type,
            "Deductible": deductible, "Days_Policy_Accident": days_policy_accident, "Days_Policy_Claim": days_policy_claim,
            "AccidentArea": accident_area, "Fault": fault, "NumberOfCars": number_of_cars,
            "PoliceReportFiled": police_report, "WitnessPresent": witness, "PastNumberOfClaims": past_claims,
            "NumberOfSuppliments": supplements, "AddressChange_Claim": address_change,
            "Year": accident_date_in.year,
        },
        "accident_date": accident_date_in,
        "claim_date": claim_date_in,
        "narrative_text": narrative_text.strip() or None,
        "image_file": image_file,
    }
