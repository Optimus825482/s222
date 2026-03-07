"""Healthcare & Medical domain skill plugin."""

DOMAIN_CONFIG = {
    "domain_id": "healthcare",
    "name": "Healthcare & Medical",
    "name_tr": "Sağlık & Tıp",
    "description": "Medical terminology lookup, drug interaction checking, BMI calculation, and clinical reference tools",
    "capabilities": ["Drug interaction check", "BMI calculation", "Medical term lookup", "Dosage calculator"],
    "version": "1.0.0",
    "author": "community",
    "tools": [
        {"name": "calculate_bmi", "description": "Calculate Body Mass Index", "params": ["weight_kg", "height_cm"]},
        {"name": "check_drug_interaction", "description": "Check potential drug interactions", "params": ["drug_a", "drug_b"]},
        {"name": "lookup_medical_term", "description": "Look up medical terminology", "params": ["term"]},
        {"name": "calculate_dosage", "description": "Calculate medication dosage by weight", "params": ["medication", "weight_kg"]},
    ],
}


def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    """Calculate BMI and return category."""
    if height_cm <= 0 or weight_kg <= 0:
        return {"error": "Weight and height must be positive"}
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        category = "Underweight"
        category_tr = "Zayıf"
    elif bmi < 25:
        category = "Normal"
        category_tr = "Normal"
    elif bmi < 30:
        category = "Overweight"
        category_tr = "Fazla Kilolu"
    else:
        category = "Obese"
        category_tr = "Obez"
    return {
        "bmi": round(bmi, 1),
        "category": category,
        "category_tr": category_tr,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
    }


# Common drug interaction database (simplified)
_INTERACTIONS = {
    ("aspirin", "warfarin"): {"severity": "high", "effect": "Increased bleeding risk", "effect_tr": "Artmış kanama riski"},
    ("ibuprofen", "aspirin"): {"severity": "moderate", "effect": "Reduced aspirin efficacy", "effect_tr": "Aspirin etkinliğinde azalma"},
    ("metformin", "alcohol"): {"severity": "high", "effect": "Lactic acidosis risk", "effect_tr": "Laktik asidoz riski"},
    ("ssri", "maoi"): {"severity": "critical", "effect": "Serotonin syndrome risk", "effect_tr": "Serotonin sendromu riski"},
    ("ace_inhibitor", "potassium"): {"severity": "moderate", "effect": "Hyperkalemia risk", "effect_tr": "Hiperkalemi riski"},
    ("statin", "grapefruit"): {"severity": "moderate", "effect": "Increased statin levels", "effect_tr": "Artmış statin seviyeleri"},
}


def check_drug_interaction(drug_a: str, drug_b: str) -> dict:
    """Check for known drug interactions."""
    a, b = drug_a.lower().strip(), drug_b.lower().strip()
    interaction = _INTERACTIONS.get((a, b)) or _INTERACTIONS.get((b, a))
    if interaction:
        return {
            "drug_a": drug_a,
            "drug_b": drug_b,
            "interaction_found": True,
            **interaction,
        }
    return {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "interaction_found": False,
        "note": "No known interaction in database. Always consult a healthcare professional.",
        "note_tr": "Veritabanında bilinen etkileşim yok. Her zaman bir sağlık uzmanına danışın.",
    }


_MEDICAL_TERMS = {
    "hypertension": {"definition": "Persistently elevated arterial blood pressure", "definition_tr": "Kalıcı olarak yükselmiş arter kan basıncı", "category": "Cardiovascular"},
    "tachycardia": {"definition": "Heart rate exceeding 100 beats per minute", "definition_tr": "Dakikada 100'ü aşan kalp atış hızı", "category": "Cardiovascular"},
    "dyspnea": {"definition": "Difficulty breathing or shortness of breath", "definition_tr": "Nefes almada güçlük veya nefes darlığı", "category": "Respiratory"},
    "edema": {"definition": "Swelling caused by excess fluid in body tissues", "definition_tr": "Vücut dokularında aşırı sıvı birikmesinden kaynaklanan şişlik", "category": "General"},
    "anemia": {"definition": "Deficiency of red blood cells or hemoglobin", "definition_tr": "Kırmızı kan hücresi veya hemoglobin eksikliği", "category": "Hematology"},
    "arrhythmia": {"definition": "Irregular heartbeat rhythm", "definition_tr": "Düzensiz kalp atış ritmi", "category": "Cardiovascular"},
    "sepsis": {"definition": "Life-threatening organ dysfunction caused by infection", "definition_tr": "Enfeksiyonun neden olduğu yaşamı tehdit eden organ işlev bozukluğu", "category": "Infectious"},
    "ischemia": {"definition": "Inadequate blood supply to an organ or tissue", "definition_tr": "Bir organ veya dokuya yetersiz kan akışı", "category": "Cardiovascular"},
}


def lookup_medical_term(term: str) -> dict:
    """Look up a medical term."""
    key = term.lower().strip()
    info = _MEDICAL_TERMS.get(key)
    if info:
        return {"term": term, "found": True, **info}
    return {
        "term": term,
        "found": False,
        "suggestion": "Term not in database. Try common medical terms like: " + ", ".join(list(_MEDICAL_TERMS.keys())[:5]),
    }


_DOSAGE_TABLE = {
    "paracetamol": {"dose_per_kg": 15, "unit": "mg", "max_daily": 4000, "frequency": "every 4-6 hours"},
    "ibuprofen": {"dose_per_kg": 10, "unit": "mg", "max_daily": 2400, "frequency": "every 6-8 hours"},
    "amoxicillin": {"dose_per_kg": 25, "unit": "mg", "max_daily": 3000, "frequency": "every 8 hours"},
}


def calculate_dosage(medication: str, weight_kg: float) -> dict:
    """Calculate medication dosage based on weight."""
    med = medication.lower().strip()
    info = _DOSAGE_TABLE.get(med)
    if not info:
        return {
            "medication": medication,
            "error": f"Medication not in database. Available: {', '.join(_DOSAGE_TABLE.keys())}",
        }
    dose = info["dose_per_kg"] * weight_kg
    return {
        "medication": medication,
        "weight_kg": weight_kg,
        "single_dose": f"{round(dose)} {info['unit']}",
        "frequency": info["frequency"],
        "max_daily": f"{info['max_daily']} {info['unit']}",
        "note": "This is a general guideline. Always consult a healthcare professional.",
        "note_tr": "Bu genel bir kılavuzdur. Her zaman bir sağlık uzmanına danışın.",
    }
