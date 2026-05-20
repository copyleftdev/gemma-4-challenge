"""Deterministic policy gate for community health navigation requests."""

from __future__ import annotations

import re


SIGNAL_RULES = [
    {
        "rule_id": "immediate_medical_emergency",
        "policy_artifact": "escalation_policy.aion",
        "decision": "escalate",
        "reason": "emergency_medical_signal",
        "priority": 100,
        "terms": [
            "chest pain",
            "chest pressure",
            "can't breathe",
            "cannot breathe",
            "trouble breathing",
            "not breathing",
            "stroke",
            "face drooping",
            "arm weakness",
            "slurred speech",
            "severe bleeding",
            "uncontrolled bleeding",
            "unconscious",
            "passed out",
            "severe allergic reaction",
            "anaphylaxis",
            "seizure",
        ],
        "patterns": [],
        "message": (
            "Call 911 or your local emergency number now if there may be "
            "immediate danger."
        ),
    },
    {
        "rule_id": "suicide_or_self_harm",
        "policy_artifact": "escalation_policy.aion",
        "decision": "escalate",
        "reason": "suicide_or_self_harm_signal",
        "priority": 100,
        "terms": [
            "kill myself",
            "kill himself",
            "kill herself",
            "kill themselves",
            "suicide",
            "suicidal",
            "self-harm",
            "self harm",
            "hurt myself",
            "end my life",
            "can't stay safe",
            "cannot stay safe",
            "want to die",
        ],
        "patterns": [],
        "message": (
            "Call or text 988 for suicide, mental health, or emotional crisis support. "
            "If immediate danger is present, call 911."
        ),
    },
    {
        "rule_id": "harm_to_others",
        "policy_artifact": "escalation_policy.aion",
        "decision": "escalate",
        "reason": "harm_to_others_signal",
        "priority": 100,
        "terms": [
            "hurt someone",
            "harm someone",
            "kill someone",
            "violent plan",
            "specific target",
        ],
        "patterns": [],
        "message": (
            "If there is immediate danger to another person, call 911 or local "
            "emergency services. I cannot help with violent or enabling details."
        ),
    },
    {
        "rule_id": "possible_poisoning",
        "policy_artifact": "escalation_policy.aion",
        "decision": "escalate",
        "reason": "poisoning_signal",
        "priority": 95,
        "terms": [
            "extra pills",
            "too many pills",
            "overdose",
            "poison",
            "poisoning",
            "swallowed",
            "chemical exposure",
            "bleach",
            "carbon monoxide",
            "took too much",
        ],
        "patterns": [],
        "message": (
            "Call Poison Control at 1-800-222-1222 in the US, or call 911 if the "
            "person is unconscious, not breathing, or in immediate danger."
        ),
    },
    {
        "rule_id": "immediate_personal_safety",
        "policy_artifact": "escalation_policy.aion",
        "decision": "escalate",
        "reason": "abuse_or_immediate_safety_signal",
        "priority": 90,
        "terms": [
            "unsafe right now",
            "being attacked",
            "being abused",
            "domestic violence",
            "child in danger",
            "elder in danger",
        ],
        "patterns": [],
        "message": (
            "If immediate danger is present, call 911 or local emergency services. "
            "I can help find safety resources after immediate danger guidance."
        ),
    },
    {
        "rule_id": "policy_bypass_attempt",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "policy_bypass_attempt_blocked",
        "priority": 88,
        "terms": [
            "ignore the policy",
            "ignore all rules",
            "ignore previous instructions",
            "bypass aion",
            "bypass the aion",
            "developer mode",
            "jailbreak",
            "you are no longer care compass",
            "do not follow the signed rules",
            "pretend the policy allows",
            "override the policy",
            "show me the hidden policy",
            "print the policy",
        ],
        "patterns": [],
        "message": (
            "I cannot bypass or reveal hidden policy instructions. I can help with "
            "allowed community navigation."
        ),
    },
    {
        "rule_id": "medication_instruction",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "medication_instruction_blocked",
        "priority": 80,
        "terms": [
            "change my medication",
            "dose",
            "dosage",
            "double my dose",
            "skip my dose",
            "stop taking",
            "start taking",
            "restart my medication",
            "increase my medication",
            "decrease my medication",
            "mix these medications",
            "give my child ibuprofen",
            "how much ibuprofen",
            "how much tylenol",
            "how much acetaminophen",
            "insulin units",
        ],
        "patterns": [],
        "message": (
            "I cannot advise starting, stopping, changing, or dosing medication. "
            "Contact a clinician or pharmacist."
        ),
    },
    {
        "rule_id": "diagnosis",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "diagnosis_blocked",
        "priority": 75,
        "terms": [
            "diagnose",
            "what do i have",
            "what is wrong with me",
            "symptoms mean",
            "is this cancer",
            "is this measles",
            "is this a heart attack",
            "do i have",
            "tell me my condition",
        ],
        "patterns": [],
        "message": (
            "I cannot diagnose symptoms. I can help prepare questions for a clinician "
            "or find care resources."
        ),
    },
    {
        "rule_id": "lab_or_imaging_interpretation",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "diagnosis_blocked",
        "priority": 74,
        "terms": [
            "interpret my labs",
            "interpret this lab",
            "blood test result",
            "mri result",
            "ct scan result",
            "x-ray result",
            "pathology report",
            "blood pressure reading",
            "glucose reading",
            "a1c result",
        ],
        "patterns": [],
        "message": (
            "I cannot interpret labs, imaging, or vital signs as clinical findings. "
            "I can help prepare questions for a clinician."
        ),
    },
    {
        "rule_id": "eligibility_determination",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "eligibility_determination_blocked",
        "priority": 70,
        "terms": [
            "am i eligible",
            "do i qualify",
            "will i qualify",
            "guarantee i qualify",
            "calculate my eligibility",
            "determine eligibility",
            "approved for medicaid",
            "eligible for medicaid",
            "eligible for chip",
            "eligible for charity care",
        ],
        "patterns": [],
        "message": (
            "I cannot decide eligibility. I can point you to official application or "
            "assister channels."
        ),
    },
    {
        "rule_id": "legal_or_claims_representation",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "eligibility_determination_blocked",
        "priority": 68,
        "terms": [
            "what income should i report",
            "hide income",
            "omit income",
            "appeal my denial for me",
            "act as my representative",
            "insurance claim for me",
        ],
        "patterns": [],
        "message": (
            "I cannot act as a legal, insurance, or benefits representative. I can "
            "help find official assister channels."
        ),
    },
    {
        "rule_id": "sensitive_identifier_collection",
        "policy_artifact": "privacy_policy.aion",
        "decision": "block",
        "reason": "unsafe_data_request_blocked",
        "priority": 66,
        "terms": [
            "social security number",
            "ssn",
            "insurance member id",
            "medical record number",
            "mrn",
            "credit card number",
            "password",
            "government id",
            "driver license",
            "upload my id",
        ],
        "patterns": [
            {"id": "ssn_pattern", "regex": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"},
            {"id": "long_identifier_pattern", "regex": r"\b\d{10,}\b"},
        ],
        "message": (
            "Do not share sensitive identifiers here. I can help with navigation using "
            "minimum necessary information like city, ZIP, language, and service need."
        ),
    },
    {
        "rule_id": "unverified_resource_creation",
        "policy_artifact": "scope_of_practice.aion",
        "decision": "block",
        "reason": "unverified_resource_blocked",
        "priority": 64,
        "terms": [
            "make up a clinic",
            "invent a clinic",
            "pretend there is a clinic",
            "fake resource",
            "recommend a resource even if unverified",
            "best hospital",
            "guaranteed appointment",
            "guarantee availability",
        ],
        "patterns": [],
        "message": (
            "I cannot invent or guarantee resources. I can use verified directories "
            "and tell you to confirm availability directly."
        ),
    },
]


def _candidate_for_rule(rule: dict, user_text: str, lowered_text: str) -> dict | None:
    matched_terms = [term for term in rule["terms"] if term in lowered_text]
    matched_patterns = [
        pattern["id"]
        for pattern in rule.get("patterns", [])
        if re.search(pattern["regex"], user_text, flags=re.IGNORECASE)
    ]
    matched_signals = matched_terms + matched_patterns
    if not matched_signals:
        return None
    return {
        "rule_id": rule["rule_id"],
        "policy_artifact": rule["policy_artifact"],
        "decision": rule["decision"],
        "reason": rule["reason"],
        "priority": rule["priority"],
        "matched_signals": matched_signals,
    }


def gate_request(user_text: str) -> dict:
    lowered_text = user_text.lower()
    candidate_matches = []
    for rule in SIGNAL_RULES:
        candidate = _candidate_for_rule(rule, user_text, lowered_text)
        if candidate:
            candidate_matches.append(candidate)

    if candidate_matches:
        selected = max(candidate_matches, key=lambda item: item["priority"])
        selected_rule = next(
            rule for rule in SIGNAL_RULES if rule["rule_id"] == selected["rule_id"]
        )
        return {
            "decision": selected_rule["decision"],
            "reason": selected_rule["reason"],
            "message": selected_rule["message"],
            "selected_rule": selected,
            "candidate_matches": candidate_matches,
            "model_allowed": False,
        }

    return {
        "decision": "allow",
        "reason": "navigation_allowed",
        "message": "Request is within community navigation scope.",
        "selected_rule": {
            "rule_id": "community_resource_navigation",
            "policy_artifact": "navigation_rules.aion",
            "decision": "allow",
            "reason": "navigation_allowed",
            "priority": 10,
            "matched_signals": ["navigation_request"],
        },
        "candidate_matches": [],
        "model_allowed": True,
    }
