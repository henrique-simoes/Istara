#!/usr/bin/env python3
"""Generate the rich multi-modal dataset for the 150-Turn Agentic Engine Stress Test.

Outputs written to tests/data/stress_test_150_turns/:
  1. corpus_manifest.json (35 canonical documents from tests/document_corpus/canonical/)
  2. simulated_surveys_100.json (100 multi-clinic patient & caregiver survey responses)
  3. usability_testing_20.json (20 usability lab sessions with tasks, SUS, UMUX, and error logs)
  4. codebook_lifecycle.json (3-stage qualitative codebook evolution: v1.0 -> v1.1 -> v2.0)
  5. trajectory_150_turns.json (150-turn sequential UX researcher prompt trajectory with 32 steering events)
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "tests" / "data" / "stress_test_150_turns"
CANONICAL_DIR = REPO_ROOT / "tests" / "document_corpus" / "canonical"


def generate_corpus_manifest() -> dict:
    """Select 35 diverse canonical sources from manifest.json."""
    manifest_path = CANONICAL_DIR / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        canonical_manifest = json.load(f)

    # Key sources across methods
    target_ids = [
        # Interviews (6)
        "CR-001", "CR-002", "CR-003", "CR-004", "CR-005", "CR-006",
        # Participant Profiles (4)
        "CR-025", "CR-026", "CR-027", "CR-028",
        # Diary Studies (4)
        "CR-037", "CR-038", "CR-039", "CR-040",
        # Usability Sessions (6)
        "CR-047", "CR-048", "CR-049", "CR-050", "CR-051", "CR-052",
        # Journey Maps & Field Notes (4)
        "CR-093", "CR-094", "CR-099", "CR-100",
        # Competitors & Heuristics (5)
        "CR-125", "CR-126", "CR-127", "CR-130", "CR-131",
        # Accessibility & Laws of UX (4)
        "CR-135", "CR-136", "CR-140", "CR-141",
        # Stakeholders & Reports (2)
        "CR-148", "CR-171",
    ]

    selected_sources = []
    by_id = {s["id"]: s for s in canonical_manifest["sources"]}

    for tid in target_ids:
        if tid in by_id:
            src = by_id[tid]
            rel_path = f"tests/document_corpus/canonical/{src['relative_path']}"
            full_path = REPO_ROOT / rel_path
            selected_sources.append({
                "id": src["id"],
                "title": src["title"],
                "method": src["method"],
                "phase": src["phase"],
                "role": src.get("role", "participant"),
                "language": src.get("language", "en"),
                "clinic": src.get("clinic", "general"),
                "relative_path": rel_path,
                "file_exists": full_path.exists(),
                "file_type": src.get("file_type", "md"),
                "tags": src.get("tags", []),
                "skills": src.get("skills", []),
                "word_count": src.get("word_count", 0),
            })

    return {
        "project": "CareNav Renewal - 150 Turn Stress Test",
        "description": "35 canonical multi-modal documents selected for long-horizon agentic reasoning",
        "total_selected": len(selected_sources),
        "sources": selected_sources,
    }


def generate_simulated_surveys_100() -> list[dict]:
    """Generate 100 realistic patient and caregiver survey responses."""
    random.seed(42)  # Deterministic generation

    clinics = [
        "Community Health Center",
        "Cardiology Specialty Clinic",
        "Oncology Infusion Center",
        "Pediatric Outpatient Pavilion",
        "Post-Operative Surgical Clinic",
        "Geriatric Primary Care",
    ]

    roles = [
        ("patient", 0.55),
        ("family_caregiver", 0.35),
        ("healthcare_proxy", 0.10),
    ]

    languages = [("en", 0.70), ("es", 0.20), ("pt-BR", 0.10)]
    age_brackets = ["18-29", "30-49", "50-64", "65-79", "80+"]

    readiness_qual_templates = {
        1: [
            "The app said 'Not Ready' with zero explanation. I panicked thinking my surgery was cancelled, but the nurse just had not clicked the lab checkbox.",
            "Complete lack of transparency. A red exclamation mark appeared with no phone number or clinic note to clarify what was needed.",
            "I spent two hours on hold because the check-in screen claimed insurance was invalid when it was already verified in person.",
        ],
        2: [
            "Status changed overnight without any alert. If I had not checked the portal by chance, I would have arrived fasting for an appointment that was postponed.",
            "The checklist showed everything completed, but when I arrived at cardiology, they said the EKG from last month was missing.",
        ],
        3: [
            "Decent overview, but the technical terms like 'pre-authorization pending' mean nothing to an 80-year-old patient.",
            "It gives a general status, but it does not tell you WHICH specific doctor note or blood test is holding up the green light.",
        ],
        4: [
            "Generally clear. I could see that the fasting blood draw was still needed before the endocrinologist visit.",
            "Helpful reminders, though sometimes the SMS arrives after I already completed the questionnaire online.",
        ],
        5: [
            "Very clear. The step-by-step breakdown showed exactly what the clinic had received and what was pending on my end.",
            "Loved the clear indicator showing Dr. Vance had reviewed my pre-op clearance. Gave me total peace of mind.",
        ],
    }

    proxy_privacy_qual_templates = {
        1: [
            "I will never allow proxy access if it means my daughter can read my behavioral health counseling notes. There must be strict compartmentalization.",
            "Terrified that sensitive reproductive health records will be exposed to my ex-spouse who has shared custody access for our child.",
            "My son manages my appointments, but he does not need to see my oncology prognosis before I discuss it with my oncologist.",
        ],
        2: [
            "Caregiver permissions are currently all-or-nothing. I want my son to see appointment times, but NOT my medication list or doctor notes.",
            "Too broad. I need granular checkboxes: let my caregiver handle logistics, but keep clinical consultation notes strictly confidential.",
        ],
        3: [
            "Acceptable if there is a clear warning banner telling me exactly what my caregiver is able to see.",
            "It works fine for scheduling, but the privacy settings are confusing and hard to find on a mobile phone.",
        ],
        4: [
            "I am comfortable with my spouse seeing appointment logistics and lab instructions, provided psychological notes remain locked.",
            "Very helpful for elderly parents who cannot navigate smartphones, as long as the patient explicitly signs the digital waiver.",
        ],
        5: [
            "Full proxy access is a lifesaver for my 86-year-old mother who has dementia. I need to see every clinical detail to keep her safe.",
            "As a full-time caregiver, having complete transparency into appointments and physician notes is critical for preventing medication errors.",
        ],
    }

    clinical_evidence_templates = [
        "A green badge means nothing to me unless I can click it and see Dr. Vance's signed clinical note confirming my clearance.",
        "Don't just say 'Labs Cleared' - show me the date, the laboratory name, and the doctor's electronic signature.",
        "I trust my doctor, not an automated algorithm. Always show the exact medical note that triggered the appointment clearance.",
        "Without the source note attached, staff and patients are left guessing whether the triage decision was made by an AI or a clinician.",
        "Traceability is non-negotiable in healthcare. Every status flag should link directly to the underlying EHR entry.",
    ]

    responses = []
    for i in range(1, 101):
        resp_id = f"resp-150s-{i:03d}"
        part_id = f"P-ST150-{i:03d}"

        r_val = random.random()
        role = "patient" if r_val < 0.55 else ("family_caregiver" if r_val < 0.90 else "healthcare_proxy")

        l_val = random.random()
        lang = "en" if l_val < 0.70 else ("es" if l_val < 0.90 else "pt-BR")

        clinic = random.choice(clinics)
        age = random.choice(age_brackets)

        readiness_score = random.choices([1, 2, 3, 4, 5], weights=[0.15, 0.20, 0.30, 0.25, 0.10])[0]
        proxy_score = random.choices([1, 2, 3, 4, 5], weights=[0.25, 0.25, 0.20, 0.20, 0.10])[0]
        audit_importance = random.choices([1, 2, 3, 4, 5], weights=[0.02, 0.05, 0.13, 0.35, 0.45])[0]
        notification_sat = random.choices([1, 2, 3, 4, 5], weights=[0.10, 0.15, 0.25, 0.35, 0.15])[0]
        nps = random.choices(list(range(11)), weights=[0.05, 0.05, 0.05, 0.05, 0.08, 0.10, 0.12, 0.15, 0.15, 0.10, 0.10])[0]

        readiness_comment = random.choice(readiness_qual_templates[readiness_score])
        proxy_comment = random.choice(proxy_privacy_qual_templates[proxy_score])
        clinical_comment = random.choice(clinical_evidence_templates)

        if lang == "es":
            readiness_comment = f"[ES] {readiness_comment} (La aplicacion necesita instrucciones mas claras en espanol)."
            proxy_comment = f"[ES] {proxy_comment} (Los permisos de privacidad deben ser transparentes para la familia)."
        elif lang == "pt-BR":
            readiness_comment = f"[PT-BR] {readiness_comment} (O sistema precisa de confirmacao medica clara em portugues)."
            proxy_comment = f"[PT-BR] {proxy_comment} (Minha familia cuida das consultas mas nao deve ver prontuarios intimos)."

        answers = [
            {
                "question": "How clearly did CareNav explain why an appointment was ready or not ready?",
                "rating": readiness_score,
                "answer": readiness_comment,
            },
            {
                "question": "What is your primary concern regarding caregiver proxy access to your clinical notes?",
                "rating": proxy_score,
                "answer": proxy_comment,
            },
            {
                "question": "How important is seeing the verbatim clinical note behind an appointment readiness flag?",
                "rating": audit_importance,
                "answer": clinical_comment,
            },
            {
                "question": "How satisfied are you with the frequency of SMS and portal appointment readiness notifications?",
                "rating": notification_sat,
                "answer": f"Satisfaction rating {notification_sat}/5 for notification pacing.",
            },
            {
                "question": "Overall, how likely are you to recommend CareNav to another patient or caregiver?",
                "rating": nps,
                "answer": f"NPS rating {nps}/10.",
            },
        ]

        responses.append({
            "response_id": resp_id,
            "participant_id": part_id,
            "demographics": {
                "role": role,
                "language": lang,
                "clinic": clinic,
                "age_bracket": age,
            },
            "metrics": {
                "readiness_clarity": readiness_score,
                "caregiver_proxy_comfort": proxy_score,
                "audit_trail_importance": audit_importance,
                "notification_satisfaction": notification_sat,
                "nps_rating": nps,
            },
            "answers": answers,
        })

    return responses


def generate_usability_testing_20() -> list[dict]:
    """Generate 20 comprehensive usability lab session records."""
    random.seed(1337)

    personas = [
        {"name": "Eleanor (78yo, Cardiology Patient, low tech literacy)", "tech": "200% Zoom", "device": "iPad Safari"},
        {"name": "Carlos (46yo, Caregiver for elderly father, bilingual)", "tech": "None", "device": "iPhone Safari"},
        {"name": "Marcus (34yo, Tech worker, first-time oncology visit)", "tech": "None", "device": "Desktop Chrome"},
        {"name": "Beatrice (62yo, Low vision, post-hip replacement)", "tech": "Screen Reader (VoiceOver)", "device": "iPhone Safari"},
        {"name": "Devon (29yo, Pediatric caregiver for toddler)", "tech": "None", "device": "Android Chrome"},
        {"name": "Helena (53yo, Chronic autoimmune patient)", "tech": "High Contrast Mode", "device": "Desktop Firefox"},
        {"name": "George (82yo, Heart failure patient, caregiver-managed)", "tech": "200% Zoom", "device": "iPad Safari"},
        {"name": "Sofia (39yo, Healthcare proxy for two aging parents)", "tech": "None", "device": "Desktop Chrome"},
        {"name": "Amir (41yo, Diabetic neuropathy patient)", "tech": "None", "device": "Android Chrome"},
        {"name": "Grace (71yo, Mild cognitive impairment, cardiology)", "tech": "Large Text", "device": "iPad Safari"},
        {"name": "Liam (25yo, Sports medicine patient)", "tech": "None", "device": "iPhone Safari"},
        {"name": "Valerie (58yo, Post-mastectomy surgical follow-up)", "tech": "None", "device": "Desktop Safari"},
        {"name": "Raul (67yo, Spanish-dominant, cataract pre-op)", "tech": "High Contrast Mode", "device": "Android Chrome"},
        {"name": "Chloe (31yo, Caregiver for brother with Down syndrome)", "tech": "None", "device": "Desktop Chrome"},
        {"name": "Dennis (75yo, Hearing impaired, prostate care)", "tech": "Large Text", "device": "iPad Safari"},
        {"name": "Mei-Ling (48yo, Orthopedic surgery patient)", "tech": "None", "device": "iPhone Safari"},
        {"name": "Frank (69yo, Hypertension & kidney disease)", "tech": "None", "device": "Desktop Chrome"},
        {"name": "Patricia (84yo, Assisted living resident, palliative)", "tech": "Screen Reader (NVDA)", "device": "Desktop Chrome"},
        {"name": "Tariq (36yo, Outpatient endoscopy prep)", "tech": "None", "device": "Android Chrome"},
        {"name": "Ingrid (60yo, Rheumatology patient, dexterity tremor)", "tech": "High Contrast + Large Buttons", "device": "iPad Safari"},
    ]

    sessions = []
    for idx, p in enumerate(personas, start=1):
        sess_id = f"US-150s-{idx:02d}"
        part_id = f"P-LAB-{idx:02d}"

        t1_success = random.random() > 0.30
        t1_time = round(random.uniform(45.0, 160.0), 1)
        t1_errors = random.randint(0, 4) if t1_success else random.randint(3, 7)

        t2_success = random.random() > 0.25
        t2_time = round(random.uniform(30.0, 130.0), 1)
        t2_errors = random.randint(0, 3) if t2_success else random.randint(2, 6)

        t3_success = random.random() > 0.40
        t3_time = round(random.uniform(50.0, 190.0), 1)
        t3_errors = random.randint(1, 5) if t3_success else random.randint(4, 8)

        sus_items = [
            random.choice([3, 4, 5]),
            random.choice([1, 2, 3]),
            random.choice([3, 4, 5]),
            random.choice([1, 2, 3]),
            random.choice([3, 4, 5]),
            random.choice([1, 2, 4]),
            random.choice([3, 4, 5]),
            random.choice([1, 2, 3]),
            random.choice([3, 4, 5]),
            random.choice([1, 2, 3]),
        ]

        odd_sum = sum(sus_items[i] - 1 for i in range(0, 10, 2))
        even_sum = sum(5 - sus_items[i] for i in range(1, 10, 2))
        sus_score = round((odd_sum + even_sum) * 2.5, 1)

        umux_q1 = random.choice([4, 5, 6, 7])
        umux_q2 = random.choice([3, 4, 5, 6])
        umux_score = round(((umux_q1 - 1 + umux_q2 - 1) / 12.0) * 100.0, 1)

        critical_incidents = []
        if not t1_success or t1_errors > 2:
            critical_incidents.append({
                "task": "Task 1: Caregiver Proxy Restriction",
                "severity": 3,
                "heuristic": "Flexibility and Efficiency of Use / User Control",
                "observation": "Participant clicked 'Share Profile' expecting permission toggles, but received an immediate all-access confirmation without granular redaction choices.",
            })
        if not t2_success or t2_errors > 2:
            critical_incidents.append({
                "task": "Task 2: Diagnose Not-Ready Flag",
                "severity": 4 if not t2_success else 2,
                "heuristic": "Visibility of System Status / Error Prevention",
                "observation": "Red status icon was displayed without a tooltip or hyperlinked clinician note. Participant tried clicking the icon 5 times without response.",
            })
        if p["tech"] != "None":
            critical_incidents.append({
                "task": "Global Navigation",
                "severity": 3,
                "heuristic": "Accessibility / WCAG 2.2 AA Contrast",
                "observation": f"Assistive technology ({p['tech']}) failed to identify the secondary action button due to 2.8:1 contrast ratio against gray card background.",
            })

        sessions.append({
            "session_id": sess_id,
            "participant_id": part_id,
            "persona": p["name"],
            "assistive_tech": p["tech"],
            "device": p["device"],
            "tasks": [
                {
                    "task_id": "T1",
                    "name": "Configure Caregiver Proxy Access",
                    "success": t1_success,
                    "duration_seconds": t1_time,
                    "errors": t1_errors,
                    "verbatim": "Where do I uncheck the therapy records? I don't want my sister reading my depression history.",
                },
                {
                    "task_id": "T2",
                    "name": "Diagnose Appointment Not-Ready Flag",
                    "success": t2_success,
                    "duration_seconds": t2_time,
                    "errors": t2_errors,
                    "verbatim": "It says fasting required, but which doctor wrote that? My cardiologist or the surgeon?",
                },
                {
                    "task_id": "T3",
                    "name": "Reconcile Conflicting Preparation Advice",
                    "success": t3_success,
                    "duration_seconds": t3_time,
                    "errors": t3_errors,
                    "verbatim": "The text message said stop blood thinners 3 days before, but the app says 5 days. Who do I believe?",
                },
            ],
            "metrics": {
                "sus_items": sus_items,
                "sus_score": sus_score,
                "umux_items": [umux_q1, umux_q2],
                "umux_score": umux_score,
                "total_duration_seconds": round(t1_time + t2_time + t3_time, 1),
                "total_errors": t1_errors + t2_errors + t3_errors,
            },
            "critical_incidents": critical_incidents,
        })

    return sessions


def generate_codebook_lifecycle() -> dict:
    """Generate the 3-stage evolutionary codebook definition."""
    v1_0 = [
        {
            "code_id": "cb1-01",
            "name": "caregiver-privacy",
            "definition": "Boundaries, controls, and restrictions governing family caregiver access to patient health data.",
            "inclusion_criteria": "Mentions of proxy access, shared vs private clinical records, redaction of sensitive notes, or permission delegation.",
            "exclusion_criteria": "General portal login password resets or basic account creation.",
            "anchor_quotes": [
                "My daughter needs to see appointment dates, but not my psychiatric notes.",
                "Caregiver access must have explicit boundaries.",
            ],
        },
        {
            "code_id": "cb1-02",
            "name": "audit-trail-visibility",
            "definition": "Requirement that automated status transitions display verifiable clinical evidence trails.",
            "inclusion_criteria": "Mentions of queue verification, source trail, doctor signature, lab link, or audit logs.",
            "exclusion_criteria": "General complaints about page loading latency.",
            "anchor_quotes": [
                "I will not trust a green badge without seeing the doctor's verified note.",
                "The queue is useful only when the source trail is visible.",
            ],
        },
        {
            "code_id": "cb1-03",
            "name": "clinical-oversight",
            "definition": "Physician and nurse verification protocols safeguarding AI-assisted triage decisions.",
            "inclusion_criteria": "Mentions of clinician review of automated recommendations, liability, or nurse sign-off.",
            "exclusion_criteria": "Front desk administrative room scheduling.",
            "anchor_quotes": [
                "Physicians don't trust an AI summary that doesn't let them click straight to the patient quote.",
            ],
        },
        {
            "code_id": "cb1-04",
            "name": "notification-fatigue",
            "definition": "Cognitive overload and frustration resulting from repetitive or conflicting SMS and portal reminders.",
            "inclusion_criteria": "Mentions of redundant texts, alerts sent during work hours, or conflicting prep instructions.",
            "exclusion_criteria": "Desire for additional phone calls.",
            "anchor_quotes": [
                "I received four text messages in one morning for the same routine blood draw.",
            ],
        },
    ]

    v1_1 = list(v1_0[1:]) + [
        {
            "code_id": "cb11-01",
            "name": "caregiver-proxy-scheduling",
            "definition": "Positive collaborative coordination where caregivers manage logistics, transport, and calendars.",
            "inclusion_criteria": "Mentions of booking visits, transportation coordination, calendar syncing, or check-in assistance.",
            "exclusion_criteria": "Access to medical consultation notes or diagnostic test results.",
            "anchor_quotes": [
                "My son helps with my prescriptions and driving me to clinic.",
            ],
        },
        {
            "code_id": "cb11-02",
            "name": "caregiver-confidential-notes",
            "definition": "Patient resistance and anxiety regarding proxy visibility into sensitive psychiatric, reproductive, or oncological diagnoses.",
            "inclusion_criteria": "Mentions of privacy boundaries, behavioral health isolation, or desire to withhold notes from family.",
            "exclusion_criteria": "Administrative scheduling permissions.",
            "anchor_quotes": [
                "My mother wants me to manage her logistics, but does not want me reading her counseling notes.",
            ],
        },
        {
            "code_id": "cb11-03",
            "name": "multilingual-disparity",
            "definition": "Discrepancies in clarity, cultural appropriateness, or completeness between English and non-English communications.",
            "inclusion_criteria": "Mentions of machine-translated Spanish/Portuguese copy, mistranslated medical terms, or untranslated warning flags.",
            "exclusion_criteria": "Grammar typos in English documents.",
            "anchor_quotes": [
                "Spanish translations use clinical jargon nobody in our community understands.",
            ],
        },
        {
            "code_id": "cb11-04",
            "name": "clinical-provenance",
            "definition": "Explicit requirement that automated flags display the authoring clinician, timestamp, and EHR reference ID.",
            "inclusion_criteria": "Mentions of clinician credentials, author verification, or timestamped audit ledger.",
            "exclusion_criteria": "Generic system timestamps without clinical author.",
            "anchor_quotes": [
                "Show me the date, laboratory name, and the doctor's electronic signature.",
            ],
        },
    ]

    v2_0 = list(v1_1) + [
        {
            "code_id": "cb2-01",
            "name": "accessibility-contrast-deficiency",
            "definition": "Violations of WCAG 2.2 AA contrast standards impeding elderly and low-vision patients.",
            "inclusion_criteria": "Mentions of unreadable gray text, low contrast status indicators, small touch targets, or screen reader failures.",
            "exclusion_criteria": "Aesthetic feedback on branding colors.",
            "anchor_quotes": [
                "The light gray text on white background makes it impossible for my 84-year-old eyes to read pre-op instructions.",
            ],
        },
        {
            "code_id": "cb2-02",
            "name": "cognitive-load-reduction",
            "definition": "Design interventions that simplify complex multi-step clinical readiness into actionable, chunked checklists.",
            "inclusion_criteria": "Mentions of progressive disclosure, single-page summaries, visual progress meters, or plain-language translations.",
            "exclusion_criteria": "General visual layout preferences.",
            "anchor_quotes": [
                "Group the blood tests into one pre-op card instead of five separate warning banners.",
            ],
        },
        {
            "code_id": "cb2-03",
            "name": "audit-immutability-governance",
            "definition": "Cryptographic and database governance ensuring historical readiness evidence cannot be retroactively altered.",
            "inclusion_criteria": "Mentions of append-only audit ledgers, compliance verification, tamper-evident logs, or regulatory auditability.",
            "exclusion_criteria": "Temporary session caching.",
            "anchor_quotes": [
                "If a readiness status changes from ready to blocked, the audit record must preserve the previous clinician sign-off.",
            ],
        },
    ]

    return {
        "project": "CareNav Renewal",
        "lifecycle_description": "Qualitative codebook evolution across 150-turn research sprint",
        "stages": {
            "v1_0_initial": {
                "version": "1.0.0",
                "active_turns": "Turns 1-45 (Discover)",
                "codes": v1_0,
            },
            "v1_1_steered": {
                "version": "1.1.0",
                "active_turns": "Turns 46-90 (Define - Post Steering)",
                "codes": v1_1,
            },
            "v2_0_consolidated": {
                "version": "2.0.0",
                "active_turns": "Turns 91-150 (Develop & Deliver)",
                "codes": v2_0,
            },
        },
    }


def generate_trajectory_150_turns() -> list[dict]:
    """Generate the complete 150-turn conversational UX researcher trajectory."""
    turns = []

    # Phase 1: DISCOVER (Turns 1-40)
    for i in range(1, 41):
        steering = None
        if i == 5:
            steering = {
                "type": "scope_narrowing",
                "injection_text": "Steering: Do not generalize across all clinics yet. Focus specifically on the Cardiology and Oncology outpatient cohorts where missed prep tasks trigger same-day cancellations.",
                "verification_criterion": "Assistant confines analysis to cardiology and oncology outpatient prep.",
            }
        elif i == 10:
            steering = {
                "type": "hypothesis_challenge",
                "injection_text": "Steering: Wait. Participant P-02 mentioned that SMS reminders were confusing rather than helpful. Check if text message reminders are actually causing more clinic inbound calls.",
                "verification_criterion": "Assistant checks inbound call drivers related to SMS reminder confusion.",
            }
        elif i == 15:
            steering = {
                "type": "demographic_pivot",
                "injection_text": "Steering: Let's explicitly separate elderly patients (65+) managed by adult children from self-managing tech-literate patients.",
                "verification_criterion": "Assistant splits participant findings into self-managing vs caregiver-assisted cohorts.",
            }
        elif i == 20:
            steering = {
                "type": "competitor_crosscheck",
                "injection_text": "Steering: Check our Epic MyChart and Cerner HealtheLife benchmark notes (CR-125, CR-126). Does Epic allow fine-grained proxy redaction or is it all-or-nothing?",
                "verification_criterion": "Assistant verifies competitor proxy access is all-or-nothing without granular redaction.",
            }
        elif i == 25:
            steering = {
                "type": "multilingual_alert",
                "injection_text": "Steering: In CR-002 and CR-003, notice how Spanish and Portuguese copy caused confusion in cardiology pre-op. Flag multilingual disparity as a high-risk finding.",
                "verification_criterion": "Assistant flags multilingual copy discrepancy as high-risk qualitative finding.",
            }
        elif i == 30:
            steering = {
                "type": "methodological_challenge",
                "injection_text": "Steering: We cannot accept synthesized claims about patient readiness without reviewing the raw transcript spans. Search CR-004 specifically for verbatim quotes on fasting.",
                "verification_criterion": "Assistant quotes exact verbatim spans from CR-004 regarding fasting confusion.",
            }
        elif i == 35:
            steering = {
                "type": "privacy_boundary_drilldown",
                "injection_text": "Steering: The patient in CR-001 strongly demanded that psychiatric notes be hidden from family caregivers. Let's make this our primary privacy design inquiry.",
                "verification_criterion": "Assistant elevates psychiatric record compartmentalization to primary design inquiry.",
            }
        elif i == 40:
            steering = {
                "type": "phase_transition_gate",
                "injection_text": "Steering: Discover phase is concluding. Before we transition to Define, summarize the top 4 empirical themes supported by at least 3 distinct source documents.",
                "verification_criterion": "Assistant lists 4 grounded empirical themes citing at least 3 source IDs each.",
            }

        discover_prompts = [
            "Hello Cleo. We are beginning a comprehensive multi-week research sprint on the CareNav Renewal program for Northstar Health. Let's start by listing the available project documents and files to understand our corpus.",
            "Great. Now inspect the first interview transcript CR-001 with the pediatric care coordinator. What were their main operational frustrations regarding patient readiness verification?",
            "Look at CR-002, the interview with the urban specialty clinic administrator in Sao Paulo/Portuguese cohort. What unique friction points did they report regarding multilingual reminders?",
            "Examine CR-003, the Spanish-speaking patient interview. How did they describe their experience trying to determine if their laboratory blood work had arrived?",
            "Now review CR-004, the family caregiver interview for an elderly cardiology patient. How does the caregiver describe the handoff between appointment scheduling and clinical lab notes?",
            "Let's look into CR-005, the nurse manager interview. Why do the triage nurses distrust the automated green status indicator?",
            "Inspect CR-006, the operations analyst interview. What data do they provide on appointment cancellation rates when patients arrive without pre-visit labs?",
            "Examine participant profile CR-025. What is their digital health literacy profile, and how do they manage appointment notifications?",
            "Review participant profile CR-026. What assistive devices or screen reader accommodations does this patient rely on?",
            "Inspect participant profile CR-027. What are their chronic conditions and why do they require frequent caregiver proxy check-ins?",
            "Look at diary study CR-037. Over the 7-day pre-appointment log, on which days did the patient experience the highest anxiety?",
            "Examine diary study CR-038. Did the patient receive duplicate or conflicting messages between the automated SMS and phone calls?",
            "Review diary study CR-039. How did the family caregiver document their attempt to verify whether fasting was required for the ultrasound?",
            "Inspect diary study CR-040. What happened when the patient's appointment was rescheduled at the last minute?",
            "Let's look at field observation notes CR-099 from the community health center waiting room. What behaviors were observed at the self-service check-in kiosk?",
            "Examine field notes CR-100 from the cardiology waiting area. How often did front-desk staff have to intervene to resolve check-in errors?",
            "Review patient journey map CR-093 covering pre-visit lab completion. Where does the steepest drop-off in patient task completion occur?",
            "Inspect journey map CR-094 on caregiver invitation and consent. What are the key friction steps where caregivers abandon the proxy setup?",
            "Let's create a formal Kanban task to track our discovery findings on caregiver proxy consent friction. Title it 'Analyze Caregiver Proxy Consent Drop-Off'.",
            "Examine competitor benchmark CR-125 for Epic MyChart. How does MyChart handle proxy access permissions for family members?",
            "Inspect competitor benchmark CR-126 for Cerner HealtheLife. What audit trail mechanisms does Cerner provide to patients verifying triage status?",
            "Review competitor benchmark CR-127 for Zocdoc. How does Zocdoc communicate pre-visit readiness checklists compared to hospital portals?",
            "Now review heuristic evaluation CR-130 conducted on CareNav v1.0. Which Nielsen-Norman heuristics were violated most severely?",
            "Inspect heuristic evaluation CR-131 regarding error prevention. What specific design flaw allowed patients to check in without completing required fasting labs?",
            "Review accessibility audit CR-135. What were the critical WCAG 2.2 AA non-compliance issues identified on the mobile check-in view?",
            "Examine accessibility audit CR-136 focusing on screen reader compatibility. What accessibility barriers did VoiceOver users encounter on the readiness modal?",
            "Inspect Laws of UX evaluation CR-140. How does CareNav currently violate Hick's Law and Cognitive Load principles on the preparation dashboard?",
            "Review Laws of UX evaluation CR-141 regarding Fitts's Law. Are the primary action buttons appropriately sized and positioned for elderly arthritic patients?",
            "Examine stakeholder memo CR-148 from the Chief Medical Officer. What are the CMO's core governance requirements for AI-assisted readiness triage?",
            "Look at stakeholder memo CR-149 from the VP of Patient Experience. What are their priorities for reducing patient anxiety and improving NPS scores?",
            "Let's check our active tasks on the Kanban board. List all current tasks and their priority levels.",
            "Create another research task: 'Synthesize Multi-Source Privacy Requirements for Family Proxies' with high priority.",
            "Inspect the support ticket summary in CR-107. What percentage of inbound patient support calls are driven by confusing readiness status alerts?",
            "Look at the support ticket log CR-108. What are the recurring complaints regarding automated SMS notification frequency?",
            "Let's search memory for previous insights on 'caregiver privacy' across all indexed transcripts.",
            "Search documents for references to 'blood draw' or 'fasting instructions' across interviews and diary studies.",
            "Examine executive research report CR-171 from the previous quarter's pilot. What baseline metrics did they establish for check-in completion?",
            "Review the initial project brief in CR-153. What were the original success criteria defined for the CareNav renewal program?",
            "Check if there are any unassigned tasks on our board, and assign 'Analyze Caregiver Proxy Consent Drop-Off' to istara-main.",
            "We are ready to wrap up Discover. Summarize the key findings from our 35-document review before we dive into codebook definition and survey analysis.",
        ]

        turns.append({
            "turn_index": i,
            "phase": "discover",
            "step_title": f"Discover Step {i}: {discover_prompts[i-1][:40]}...",
            "user_prompt": discover_prompts[i-1],
            "steering": steering,
            "expected_tool": "list_project_files" if i == 1 else ("create_task" if "create" in discover_prompts[i-1].lower() else ("list_tasks" if "list" in discover_prompts[i-1].lower() else "get_document_content")),
            "expected_tool_params": {},
            "context_dependencies": [i-1] if i > 1 else [],
            "research_spine_milestone": "source_ingestion_and_exploration",
        })

    # Phase 2: DEFINE (Turns 41-80)
    for i in range(41, 81):
        steering = None
        if i == 44:
            steering = {
                "type": "codebook_exclusion_refinement",
                "injection_text": "Steering: Refine codebook v1.0. Exclude password resets, forgotten PINs, and general portal login problems from 'caregiver-privacy'. Keep it strictly focused on clinical data disclosure.",
                "verification_criterion": "Assistant updates inclusion/exclusion rules for caregiver-privacy code.",
            }
        elif i == 48:
            steering = {
                "type": "codebook_split",
                "injection_text": "Steering: 'caregiver-privacy' is too broad. Split it into two distinct codes: 'caregiver-proxy-scheduling' (logistics, transport) and 'caregiver-confidential-notes' (psychiatric/oncology privacy).",
                "verification_criterion": "Assistant promotes codebook v1.1 with split codes.",
            }
        elif i == 52:
            steering = {
                "type": "survey_subgroup_focus",
                "injection_text": "Steering: In the survey responses, filter specifically for family caregivers aged 50-64. How do their privacy ratings compare to younger patients?",
                "verification_criterion": "Assistant compares survey responses across age subgroups.",
            }
        elif i == 56:
            steering = {
                "type": "contradiction_uncovered",
                "injection_text": "Steering: Notice a contradiction! While overall NPS is relatively high (avg 7.4), the satisfaction with automated readiness explanations is very low (2.3/5). Why this divergence?",
                "verification_criterion": "Assistant investigates gap between high brand loyalty and low feature satisfaction.",
            }
        elif i == 60:
            steering = {
                "type": "reliability_rigor",
                "injection_text": "Steering: We need multi-model intercoder reliability. Run the coding verification on the 10 core interview quotes across Luna, Qwen, and GLM. Calculate Cohen's Kappa.",
                "verification_criterion": "Assistant verifies multi-model coding with Cohen's Kappa score >= 0.65.",
            }
        elif i == 64:
            steering = {
                "type": "clinical_provenance_mandate",
                "injection_text": "Steering: In our codebook, add 'clinical-provenance'. Over 80% of survey respondents insist on seeing the clinician's electronic signature and timestamp.",
                "verification_criterion": "Assistant adds clinical-provenance code with strict criteria.",
            }
        elif i == 68:
            steering = {
                "type": "sharon_atomic_elevation",
                "injection_text": "Steering: Elevate these accepted atomic nuggets into structured Sharon Facts. Ensure every fact links directly to at least 2 raw evidence unit spans.",
                "verification_criterion": "Assistant constructs Facts with dual evidence unit links.",
            }
        elif i == 72:
            steering = {
                "type": "discard_ungrounded_theme",
                "injection_text": "Steering: Discard the candidate theme that patients want gamified check-in badges. Survey responses indicate patients find gamification condescending for serious illnesses.",
                "verification_criterion": "Assistant rejects gamification hypothesis based on survey comments.",
            }
        elif i == 76:
            steering = {
                "type": "reconciliation_protocol",
                "injection_text": "Steering: For quote span Q-104 where Luna coded 'clinical-oversight' and Qwen coded 'audit-trail-visibility', reconcile under 'clinical-provenance' with human sign-off.",
                "verification_criterion": "Assistant applies governed reconciliation decision with rationale.",
            }
        elif i == 80:
            steering = {
                "type": "define_gate_verification",
                "injection_text": "Steering: Define phase is complete. Verify that all candidate nuggets have been reconciled into accepted atoms and elevated to verified Facts before we test solutions in Develop.",
                "verification_criterion": "Assistant confirms 0 unreconciled candidate atoms remain.",
            }

        define_prompts = [
            "Cleo, what's in the codebook now? Inspect the active qualitative codebook and display all registered codes and their definitions.",
            "Let's review the code 'caregiver-privacy'. What are its inclusion criteria, and which interview quotes have been tagged with it so far?",
            "Examine 'audit-trail-visibility'. Does our current definition account for both patient-facing and clinician-facing audit trails?",
            "Now inspect 'clinical-oversight'. How does this code distinguish between automated rule checks and human clinician sign-off?",
            "Let's ingest the 100 new patient and caregiver survey responses from simulated_surveys_100.json into our project's survey integration.",
            "Query the survey dataset: What is the mean rating for 'readiness_clarity' across all 100 participants?",
            "Break down the 'caregiver_proxy_comfort' survey metric by participant role (patient vs family caregiver vs healthcare proxy). What is the spread?",
            "Let's analyze the qualitative survey comments for question 2 regarding proxy privacy. What are the most frequent words and recurring fears?",
            "Review the qualitative comments regarding clinical note visibility. How many respondents explicitly stated they do not trust an ungrounded green status badge?",
            "Let's inspect the survey respondents from the Oncology Infusion Center. What specific concerns do cancer patients express about family proxy access?",
            "Now look at survey responses from the Cardiology Specialty Clinic. How do cardiology patients describe their confusion over fasting instructions?",
            "Compare survey sentiment between English-speaking respondents and Spanish/Portuguese respondents. Is there a statistically meaningful difference in readiness clarity?",
            "Let's segment our survey responses into evidence units. How many discrete sentiment atoms can we extract from the 100 survey comments?",
            "Create a new Kanban task: 'Reconcile Qualitative Interview Themes with Quantitative Survey Metrics' with high priority.",
            "Let's check the current status of the codebook. Has CodebookVersion 1.1 been officially recorded in the database?",
            "Let's run multi-coder thematic analysis on the top 15 interview quote spans using our updated codebook v1.1.",
            "Inspect the intercoder agreement matrix across our coders. What is the observed agreement percentage on 'caregiver-confidential-notes'?",
            "Calculate Cohen's Kappa for the coding run. Does our agreement meet the research validity threshold of kappa >= 0.65?",
            "What about Krippendorff's Alpha? Display the alpha coefficient for our multi-model qualitative coding run.",
            "Review the coding discrepancies where the models differed. Which quote spans had split decisions between coders?",
            "Let's resolve the split decision on Quote span 7 from CR-001. Did the participant mean logistics or medical privacy?",
            "Now review Quote span 12 from CR-004. Reconcile this span under 'caregiver-confidential-notes'.",
            "Check the reconciliation ledger. Are all 15 quote spans now resolved with human-approved decisions?",
            "Let's elevate these 15 reconciled spans into Sharon Accepted Atomic Nuggets. Display the resulting nugget IDs.",
            "Now synthesize our first Sharon Fact: 'Patients demand strict boundary separation between caregiver scheduling logistics and confidential psychiatric/reproductive notes.'",
            "Synthesize our second Sharon Fact: 'Automated appointment readiness flags trigger patient distrust and phone triage spikes unless backed by verbatim clinician notes.'",
            "Synthesize our third Sharon Fact: 'Multilingual reminders exhibit terminology discrepancies that increase prep failure rates in Spanish and Portuguese cohorts.'",
            "Synthesize our fourth Sharon Fact: 'Over 78% of family caregivers report anxiety when proxy permissions do not clearly display what is shared vs what is withheld.'",
            "Link each of these 4 Facts to their supporting Sharon Nuggets in the research evidence graph.",
            "Verify the graph integrity: Do all 4 Facts have bidirectional edges to accepted nuggets and underlying source spans?",
            "Search findings for all facts tagged with 'caregiver' to ensure our DAG is properly structured.",
            "Search findings for all facts tagged with 'audit-trail' and display their supporting evidence counts.",
            "Let's inspect the distribution of our findings: How many nuggets, facts, and candidate insights exist right now?",
            "Create a new Kanban task: 'Formulate Evidence-Grounded Design Principles for Caregiver Proxy Controls'.",
            "Move task 'Analyze Caregiver Proxy Consent Drop-Off' to IN_REVIEW status on the Kanban board.",
            "Let's attempt to move the task directly to DONE. (Notice whether the system enforces our human review gate!).",
            "The system appropriately blocked the transition with an HTTP 409 guard! Let's record the human review sign-off with evidence verification.",
            "Now approve the task transition to DONE with authorized researcher credentials.",
            "Verify that the Kanban board reflects the approved DONE status and logs the review side effects.",
            "Summarize the complete Sharon Atomic DAG created in the Define phase before we proceed to Develop.",
        ]

        turns.append({
            "turn_index": i,
            "phase": "define",
            "step_title": f"Define Step {i}: {define_prompts[i-41][:40]}...",
            "user_prompt": define_prompts[i-41],
            "steering": steering,
            "expected_tool": "get_codebook" if "codebook" in define_prompts[i-41].lower() else ("query_survey_responses" if "survey" in define_prompts[i-41].lower() else ("create_task" if "create" in define_prompts[i-41].lower() else ("move_task" if "move" in define_prompts[i-41].lower() else "search_findings"))),
            "expected_tool_params": {},
            "context_dependencies": [i-1],
            "research_spine_milestone": "thematic_coding_and_fact_elevation",
        })

    # Phase 3: DEVELOP (Turns 81-115)
    for i in range(81, 116):
        steering = None
        if i == 85:
            steering = {
                "type": "error_taxonomy_focus",
                "injection_text": "Steering: In usability session analysis, do not just calculate average task times. Categorize errors into: slip, rule-based mistake, and knowledge-based mistake.",
                "verification_criterion": "Assistant classifies usability errors into cognitive taxonomy.",
            }
        elif i == 89:
            steering = {
                "type": "assistive_tech_priority",
                "injection_text": "Steering: Participant Beatrice and Patricia used screen readers (VoiceOver/NVDA) and suffered catastrophic task failures on the readiness modal. Prioritize screen reader aria-live announcements over visual redesign.",
                "verification_criterion": "Assistant prioritizes screen reader accessibility fixes.",
            }
        elif i == 93:
            steering = {
                "type": "sus_score_drilldown",
                "injection_text": "Steering: The mean SUS score is 68.2 (marginal grade C). Breakdown the SUS scores by participant tech literacy. What is the SUS for elderly patients (65+)?",
                "verification_criterion": "Assistant isolates elderly participant SUS score (showing drop to ~54.0).",
            }
        elif i == 97:
            steering = {
                "type": "contrast_ratio_enforcement",
                "injection_text": "Steering: Check the color contrast of our secondary warning text. It measures 2.8:1, violating WCAG AA 4.5:1. Require all text to meet 4.5:1 and 7:1 for headers.",
                "verification_criterion": "Assistant specifies WCAG 2.2 AA contrast remediation rules.",
            }
        elif i == 101:
            steering = {
                "type": "progressive_disclosure_pivot",
                "injection_text": "Steering: To resolve Task 2 fasting confusion, do not show 5 separate warning cards. Design a single progressive disclosure drawer that expands to reveal Dr. Vance's signed order.",
                "verification_criterion": "Assistant applies progressive disclosure design pattern.",
            }
        elif i == 105:
            steering = {
                "type": "proxy_toggle_refinement",
                "injection_text": "Steering: For Task 1 (Caregiver setup), test a three-tiered permission model: Tier 1 (Appointments & Transport), Tier 2 (+ Medication & Preparation Instructions), Tier 3 (+ Full Clinical Notes).",
                "verification_criterion": "Assistant outlines 3-tiered proxy permissions architecture.",
            }
        elif i == 109:
            steering = {
                "type": "benchmark_comparison",
                "injection_text": "Steering: How does our 3-tiered permission model compare to Epic MyChart? Note that Epic only offers binary all-or-nothing, giving CareNav a distinct competitive advantage.",
                "verification_criterion": "Assistant highlights competitive advantage over Epic's binary proxy model.",
            }
        elif i == 113:
            steering = {
                "type": "develop_gate_check",
                "injection_text": "Steering: Develop phase is nearing completion. Verify that all 20 usability testing session logs and UMUX-Lite metrics have been synthesized into Sharon Insights.",
                "verification_criterion": "Assistant confirms all 20 usability sessions ground subsequent insights.",
            }

        develop_prompts = [
            "Now we enter the Develop phase. Ingest the 20 usability lab testing sessions from usability_testing_20.json.",
            "Calculate the overall task completion rate for Task 1: Configure Caregiver Proxy Access across all 20 participants.",
            "What was the mean duration in seconds for participants to complete Task 1, and what was the maximum time observed?",
            "Inspect the error log for Task 1. Why did 6 participants fail to restrict clinical notes on their first attempt?",
            "Examine Task 2: Diagnose Appointment Not-Ready Flag. What was the task completion rate across the 20 participants?",
            "What were the primary navigation paths taken by participants who succeeded on Task 2 versus those who failed?",
            "Look at Task 3: Reconcile Conflicting Preparation Advice. How many participants noticed the conflict between SMS (3 days) and portal (5 days)?",
            "What were the verbal reactions recorded during Task 3 when participants encountered conflicting fasting timelines?",
            "Let's compute the System Usability Scale (SUS) scores across all 20 lab sessions. What is the mean SUS score?",
            "Display the distribution of SUS scores: What is the highest SUS recorded, the lowest, and the standard deviation?",
            "Now calculate the UMUX-Lite score across the 20 participants. How does our UMUX-Lite correlate with our SUS score?",
            "Let's examine participant Eleanor (78yo, Cardiology). Walk through her step-by-step experience and friction points during the lab session.",
            "Look at participant Beatrice (62yo, Screen Reader user). What specific accessibility blocker caused her task failure on Task 2?",
            "Inspect participant Carlos (Bilingual caregiver). What were his observations regarding the clarity of Spanish proxy permission options?",
            "Review participant Sofia (Healthcare proxy for aging parents). Why did she spend 160 seconds configuring proxy permissions?",
            "Synthesize our first Sharon Insight: 'Elderly patients and low-vision users experience severe task failure due to low-contrast status banners and unannounced modal updates.'",
            "Synthesize our second Sharon Insight: 'Binary proxy permissions force patients into an unacceptable tradeoff between caregiver support and medical privacy.'",
            "Synthesize our third Sharon Insight: 'Conflicting cross-channel preparation reminders create clinical confusion and erode patient trust in automated readiness.'",
            "Synthesize our fourth Sharon Insight: 'Plain-language progressive disclosure of clinician notes improves task completion speed by over 40% in usability trials.'",
            "Link each of these 4 Sharon Insights to their supporting Sharon Facts and Usability metrics in the research graph.",
            "Check our active tasks on the Kanban board. What tasks are currently in progress for Develop?",
            "Create a new Kanban task: 'Specify Three-Tiered Caregiver Proxy Authorization Architecture' with urgent priority.",
            "Create another Kanban task: 'Remediate WCAG 2.2 AA Contrast Deficiencies and Screen Reader Aria-Live Announcements'.",
            "Attach usability test log usability_testing_20.json to the task 'Specify Three-Tiered Caregiver Proxy Authorization Architecture'.",
            "Move task 'Specify Three-Tiered Caregiver Proxy Authorization Architecture' to IN_REVIEW status.",
            "Let's review the evidence attached to 'Specify Three-Tiered Caregiver Proxy Authorization Architecture'. Are all usability quotes properly cited?",
            "Record human review approval and transition 'Specify Three-Tiered Caregiver Proxy Authorization Architecture' to DONE.",
            "Now examine the second task: 'Remediate WCAG 2.2 AA Contrast Deficiencies'. Move it to IN_REVIEW.",
            "Verify the accessibility audit evidence (CR-135, CR-136) and approve the task to DONE.",
            "Search findings for all Insights created so far. Display their IDs, titles, and supporting Fact counts.",
            "Check if any Insights lack backward links to Sharon Facts or Evidence Units.",
            "Search memory for design recommendations related to 'progressive disclosure' in clinical workflows.",
            "Review the updated codebook v2.0. Are 'accessibility-contrast-deficiency' and 'cognitive-load-reduction' registered?",
            "Verify that our qualitative codebook v2.0 has been synchronized with the Research Spine database.",
            "Summarize the key accomplishments of the Develop phase before we move into Deliver and Final Governance.",
        ]

        turns.append({
            "turn_index": i,
            "phase": "develop",
            "step_title": f"Develop Step {i}: {develop_prompts[i-81][:40]}...",
            "user_prompt": develop_prompts[i-81],
            "steering": steering,
            "expected_tool": "calculate_usability_metrics" if "sus" in develop_prompts[i-81].lower() or "task completion" in develop_prompts[i-81].lower() else ("create_task" if "create" in develop_prompts[i-81].lower() else ("move_task" if "move" in develop_prompts[i-81].lower() else ("attach_document" if "attach" in develop_prompts[i-81].lower() else "search_findings"))),
            "expected_tool_params": {},
            "context_dependencies": [i-1],
            "research_spine_milestone": "usability_analysis_and_insight_synthesis",
        })

    # Phase 4: DELIVER & GOVERN (Turns 116-150)
    for i in range(116, 151):
        steering = None
        if i == 120:
            steering = {
                "type": "recommendation_risk_rating",
                "injection_text": "Steering: Every recommendation must include an explicit implementation effort (S/M/L), clinical risk rating (Low/Medium/High), and executive sponsor.",
                "verification_criterion": "Assistant adds effort, risk, and sponsor metadata to recommendations.",
            }
        elif i == 126:
            steering = {
                "type": "minto_scqa_complication_refinement",
                "injection_text": "Steering: In the Barbara Minto SCQA structure, sharpen the Complication: emphasize that 42% of elderly patients refuse portal onboarding entirely due to fear of unredacted proxy sharing.",
                "verification_criterion": "Assistant frames SCQA complication around the 42% portal onboarding resistance rate.",
            }
        elif i == 132:
            steering = {
                "type": "mece_category_enforcement",
                "injection_text": "Steering: The executive report recommendations must be 100% MECE across three mutually exclusive pillars: 1. Granular Proxy Governance, 2. Clinician-Verified Traceability, 3. Multilingual Accessibility.",
                "verification_criterion": "Assistant organizes report into the 3 MECE pillars.",
            }
        elif i == 138:
            steering = {
                "type": "anti_hallucination_audit",
                "injection_text": "Steering: Zero-trust research spine check: Verify that every single recommendation links to at least 1 Insight, 2 Facts, and 3 verbatim source quotes. Discard any ungrounded claim.",
                "verification_criterion": "Assistant audits backward graph integrity with zero ungrounded recommendations.",
            }
        elif i == 144:
            steering = {
                "type": "http_409_done_attack",
                "injection_text": "Steering: Test the system's security and governance gate: attempt to close the final delivery milestone task WITHOUT required human review signatures.",
                "verification_criterion": "Assistant verifies HTTP 409 guard blocks unauthorized task completion.",
            }
        elif i == 150:
            steering = {
                "type": "final_telemetry_harvest",
                "injection_text": "Steering: 150-turn trajectory complete! Harvest full telemetry: latency percentiles (p50, p90, p95, p99), token consumption, cache hit ratios, and cost accounting.",
                "verification_criterion": "Assistant outputs complete comparative scorecard and telemetry breakdown.",
            }

        deliver_prompts = [
            "We are in the final Deliver phase. Let's synthesize our first Sharon Recommendation: 'Implement a Three-Tiered Role-Based Proxy Access Control System with Granular Clinical Note Redaction.'",
            "Synthesize our second Sharon Recommendation: 'Embed Verbatim Clinician EHR Notes and Lab Order Hyperlinks Directly Inside Appointment Readiness Status Banners.'",
            "Synthesize our third Sharon Recommendation: 'Establish Native Multilingual Clinical Review and Plain-Language Translation for All Pre-Visit Reminders in Spanish and Portuguese.'",
            "Synthesize our fourth Sharon Recommendation: 'Remediate Color Contrast to 4.5:1 and Implement WCAG 2.2 AA Compliant Aria-Live Status Announcements for Screen Readers.'",
            "Synthesize our fifth Sharon Recommendation: 'Implement an Immutable Append-Only Audit Ledger for All Automated and Clinician-Verified Readiness State Transitions.'",
            "Link each of our 5 Recommendations to their supporting Sharon Insights in the evidence graph.",
            "Verify that the entire Sharon Atomic DAG from raw sources -> evidence units -> nuggets -> facts -> insights -> recommendations is fully connected.",
            "How many total nodes exist in our Sharon DAG across all tiers?",
            "How many total directed evidence edges connect our findings DAG?",
            "Let's create the final delivery task: 'Produce Barbara Minto SCQA Executive Research Report for Northstar Health Executive Committee'.",
            "Formulate the Barbara Minto Situation statement based on our Discover and Define empirical data.",
            "Formulate the Barbara Minto Complication statement incorporating the 42% caregiver privacy hesitation rate.",
            "Formulate the Barbara Minto Question: 'How can Northstar Health scale automated appointment readiness while ensuring clinical trust, privacy compliance, and equitable access?'",
            "Formulate the Barbara Minto Answer: 'By deploying governed three-tiered proxy boundaries, source-verified clinician audit trails, and accessible multilingual workflows.'",
            "Organize our findings into MECE Pillar 1: Granular Proxy Governance (covering recommendations 1 and 5).",
            "Organize our findings into MECE Pillar 2: Clinician-Verified Traceability (covering recommendation 2 and audit trails).",
            "Organize our findings into MECE Pillar 3: Multilingual & Accessible Patient Communication (covering recommendations 3 and 4).",
            "Verify that these three pillars are completely Mutually Exclusive and Collectively Exhaustive (100% MECE).",
            "Generate the full ProjectReport model in the database linked to our project and findings DAG.",
            "Inspect the generated report summary: Does it cite verbatim quotes and exact source IDs for every claim?",
            "Check if any report claim relies on ungrounded model hallucinations or unverified assumptions.",
            "Verify that report_allowed is set to True only because all prerequisite Done tasks and human reviews were satisfied.",
            "Move task 'Produce Barbara Minto SCQA Executive Research Report' to IN_REVIEW status.",
            "Attempt to close the task directly to test the HTTP 409 guard.",
            "Confirm that the 409 guard prevented premature completion without human approval.",
            "Apply authorized human researcher approval to the executive report task.",
            "Transition the executive report task to DONE status.",
            "Verify on the Kanban board that all sprint tasks are in DONE status with recorded review side effects.",
            "Perform a final integrity audit of the Research Spine evidence graph.",
            "Confirm that 100% of recommendations trace backward through insights, facts, and nuggets to canonical source documents.",
            "Calculate total sprint token usage and estimate operational cost in USD.",
            "Examine prompt cache hit ratios across all turns in the session.",
            "Review tool execution latency percentiles: What was the p50 and p95 latency for system actions?",
            "Check for any unhandled tool errors or rate limits encountered during the 150-turn trajectory.",
            "Generate the final comprehensive executive research summary and comparative agentic scorecard!",
        ]

        turns.append({
            "turn_index": i,
            "phase": "deliver",
            "step_title": f"Deliver Step {i}: {deliver_prompts[i-116][:40]}...",
            "user_prompt": deliver_prompts[i-116],
            "steering": steering,
            "expected_tool": "create_task" if "create" in deliver_prompts[i-116].lower() else ("move_task" if "move" in deliver_prompts[i-116].lower() else ("generate_minto_report" if "report" in deliver_prompts[i-116].lower() else "search_findings")),
            "expected_tool_params": {},
            "context_dependencies": [i-1],
            "research_spine_milestone": "recommendation_elevation_and_minto_report",
        })

    return turns


def main() -> None:
    print(f"Generating 150-Turn Stress Test Data Package in {OUTPUT_DIR}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("  Generating corpus_manifest.json...")
    corpus_manifest = generate_corpus_manifest()
    with open(OUTPUT_DIR / "corpus_manifest.json", "w", encoding="utf-8") as f:
        json.dump(corpus_manifest, f, indent=2)
    print(f"    -> {corpus_manifest['total_selected']} canonical documents indexed.")

    print("  Generating simulated_surveys_100.json...")
    surveys = generate_simulated_surveys_100()
    with open(OUTPUT_DIR / "simulated_surveys_100.json", "w", encoding="utf-8") as f:
        json.dump(surveys, f, indent=2)
    print(f"    -> {len(surveys)} survey responses generated.")

    print("  Generating usability_testing_20.json...")
    usability = generate_usability_testing_20()
    with open(OUTPUT_DIR / "usability_testing_20.json", "w", encoding="utf-8") as f:
        json.dump(usability, f, indent=2)
    print(f"    -> {len(usability)} usability lab sessions generated.")

    print("  Generating codebook_lifecycle.json...")
    codebook = generate_codebook_lifecycle()
    with open(OUTPUT_DIR / "codebook_lifecycle.json", "w", encoding="utf-8") as f:
        json.dump(codebook, f, indent=2)
    print(f"    -> 3 codebook stages (v1.0: {len(codebook['stages']['v1_0_initial']['codes'])}, v1.1: {len(codebook['stages']['v1_1_steered']['codes'])}, v2.0: {len(codebook['stages']['v2_0_consolidated']['codes'])} codes).")

    print("  Generating trajectory_150_turns.json...")
    trajectory = generate_trajectory_150_turns()
    with open(OUTPUT_DIR / "trajectory_150_turns.json", "w", encoding="utf-8") as f:
        json.dump(trajectory, f, indent=2)
    steering_count = sum(1 for t in trajectory if t.get("steering") is not None)
    print(f"    -> {len(trajectory)} turns generated ({steering_count} dynamic steering interventions).")

    print("\nSuccessfully generated all 150-turn stress test data files!")


if __name__ == "__main__":
    main()
