"""
Generated Knowledge base for Clinical Insight Engine.
"""

FALLBACK_INSIGHTS = {
    "high": {
        "causes": [
            "Inflammation or infection",
            "Dehydration",
            "Medication effects",
            "Organ stress"
        ],
        "next_steps": [
            "Review full clinical picture",
            "Repeat test to confirm",
            "Routine medical evaluation"
        ],
        "age_context": {},
        "gender_context": {}
    },
    "low": {
        "causes": [
            "Nutritional deficiency",
            "Dilution/overhydration",
            "Decreased production",
            "Medication effects"
        ],
        "next_steps": [
            "Review full clinical picture",
            "Repeat test to confirm",
            "Routine medical evaluation"
        ],
        "age_context": {},
        "gender_context": {}
    }
}

INSIGHTS_KB = {
    "hemoglobin": {
        "high": {
            "causes": [
                "Dehydration",
                "Smoking",
                "Lung disease",
                "High altitude living",
                "Polycythemia vera"
            ],
            "next_steps": [
                "Ensure adequate hydration",
                "Repeat CBC",
                "Evaluate respiratory function"
            ],
            "age_context": {
                "elderly": "In older adults, chronic lung conditions (like COPD) are common causes."
            },
            "gender_context": {
                "male": "Testosterone therapy in males can frequently cause elevated hemoglobin."
            }
        },
        "low": {
            "causes": [
                "Iron deficiency",
                "Blood loss",
                "B12/Folate deficiency",
                "Chronic disease",
                "Bone marrow suppression"
            ],
            "next_steps": [
                "Iron panel and Ferritin",
                "B12 and Folate levels",
                "Evaluate for source of blood loss"
            ],
            "age_context": {
                "young": "In young adults, poor dietary intake or acute blood loss are primary concerns.",
                "elderly": "In the elderly, anemia of chronic disease or occult gastrointestinal blood loss must be ruled out."
            },
            "gender_context": {
                "female": "In premenopausal females, menstrual blood loss is the leading cause.",
                "male": "In adult males, gastrointestinal blood loss is a primary concern."
            }
        }
    },
    "rbc": {
        "high": {
            "causes": [
                "Dehydration",
                "Pulmonary disease",
                "Congenital heart disease",
                "Polycythemia vera"
            ],
            "next_steps": [
                "Repeat CBC",
                "Ensure hydration",
                "Evaluate for hypoxia"
            ],
            "age_context": {
                "elderly": "Age-related lung diseases are a common cause."
            },
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Anemia",
                "Bleeding",
                "Nutritional deficiency",
                "Bone marrow failure"
            ],
            "next_steps": [
                "Iron studies",
                "Check reticulocyte count",
                "Evaluate for bleeding"
            ],
            "age_context": {
                "elderly": "Bone marrow response often blunts with age."
            },
            "gender_context": {
                "female": "Menstruation increases risk of low RBC."
            }
        }
    },
    "wbc": {
        "high": {
            "causes": [
                "Bacterial or viral infection",
                "Inflammation",
                "Physical or emotional stress",
                "Corticosteroid use"
            ],
            "next_steps": [
                "Review WBC differential",
                "Assess for clinical signs of infection",
                "Repeat testing"
            ],
            "age_context": {
                "young": "Often a robust response to acute infections.",
                "elderly": "May indicate underlying occult infection."
            },
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Viral infections",
                "Autoimmune conditions",
                "Medication side effects",
                "Bone marrow disorders"
            ],
            "next_steps": [
                "Review WBC differential",
                "Monitor for signs of illness",
                "Review current medications"
            ],
            "age_context": {
                "elderly": "Can reflect decreased bone marrow reserve."
            },
            "gender_context": {}
        }
    },
    "platelets": {
        "high": {
            "causes": [
                "Reactive thrombocytosis (infection, inflammation)",
                "Iron deficiency",
                "Post-surgery recovery",
                "Myeloproliferative disorders"
            ],
            "next_steps": [
                "Check iron studies",
                "Review CRP/ESR for inflammation",
                "Repeat in 2-4 weeks"
            ],
            "age_context": {},
            "gender_context": {
                "female": "May be reactive to iron deficiency anemia, which is more common in females."
            }
        },
        "low": {
            "causes": [
                "Viral infections",
                "Medication effects",
                "Autoimmune thrombocytopenia (ITP)",
                "Liver disease"
            ],
            "next_steps": [
                "Repeat to rule out clumping",
                "Review medications",
                "Evaluate liver function"
            ],
            "age_context": {
                "elderly": "Medication-induced thrombocytopenia is a more common consideration."
            },
            "gender_context": {
                "female": "Autoimmune causes (like ITP) occur more frequently in females."
            }
        }
    },
    "neutrophils": {
        "high": {
            "causes": [
                "Bacterial infection",
                "Acute inflammation",
                "Physical stress",
                "Tissue necrosis"
            ],
            "next_steps": [
                "Check for localized infection",
                "Review inflammatory markers"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Viral infection",
                "Severe bacterial infection",
                "Medication effect",
                "Autoimmune disease"
            ],
            "next_steps": [
                "Monitor for fever",
                "Review recent viral exposures"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "lymphocytes": {
        "high": {
            "causes": [
                "Viral infection",
                "Chronic bacterial infection",
                "Lymphoproliferative disorder"
            ],
            "next_steps": [
                "Monitor symptoms",
                "Consider peripheral blood smear if persistent"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Acute stress",
                "Corticosteroids",
                "Immunodeficiency",
                "Viral illness (e.g., HIV)"
            ],
            "next_steps": [
                "Review medical history",
                "Monitor immune status"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "monocytes": {
        "high": {
            "causes": [
                "Chronic infection",
                "Autoimmune disease",
                "Recovery phase of acute infection"
            ],
            "next_steps": [
                "Correlate with clinical history",
                "Check inflammatory markers"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Acute stress",
                "Bone marrow suppression"
            ],
            "next_steps": [
                "Usually not clinically significant in isolation, monitor trends"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "eosinophils": {
        "high": {
            "causes": [
                "Allergic reaction",
                "Asthma",
                "Parasitic infection",
                "Autoimmune disease"
            ],
            "next_steps": [
                "Review allergy history",
                "Consider stool ova/parasite if travel history"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Cushing syndrome",
                "Stress",
                "Corticosteroid use"
            ],
            "next_steps": [
                "Review medication list"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "basophils": {
        "high": {
            "causes": [
                "Allergic reaction",
                "Chronic inflammation",
                "Myeloproliferative disorders"
            ],
            "next_steps": [
                "Review allergy history",
                "Monitor trends"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Acute allergic reaction",
                "Hyperthyroidism"
            ],
            "next_steps": [
                "Usually not clinically significant in isolation"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "hematocrit": {
        "high": {
            "causes": [
                "Dehydration",
                "Hypoxia",
                "Polycythemia vera"
            ],
            "next_steps": [
                "Hydration status assessment",
                "Correlate with RBC and Hemoglobin"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Anemia",
                "Bleeding",
                "Hemodilution",
                "Nutritional deficiency"
            ],
            "next_steps": [
                "Investigate for anemia causes",
                "Check Iron/B12/Folate"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "mcv": {
        "high": {
            "causes": [
                "B12 or Folate deficiency",
                "Alcoholism",
                "Liver disease",
                "Hypothyroidism"
            ],
            "next_steps": [
                "Check B12 and Folate levels",
                "Evaluate liver function"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Iron deficiency anemia",
                "Thalassemia trait",
                "Anemia of chronic disease"
            ],
            "next_steps": [
                "Iron panel including Ferritin",
                "Hemoglobin electrophoresis if suspected thalassemia"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "mch": {
        "high": {
            "causes": [
                "Macrocytic anemia",
                "B12/Folate deficiency"
            ],
            "next_steps": [
                "Check B12/Folate",
                "Correlate with MCV"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Microcytic anemia",
                "Iron deficiency",
                "Thalassemia"
            ],
            "next_steps": [
                "Iron panel",
                "Correlate with MCV"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "mchc": {
        "high": {
            "causes": [
                "Hereditary spherocytosis",
                "Autoimmune hemolytic anemia"
            ],
            "next_steps": [
                "Peripheral blood smear",
                "Reticulocyte count"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Iron deficiency anemia",
                "Thalassemia"
            ],
            "next_steps": [
                "Iron panel",
                "Review MCV/MCH"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "rdw": {
        "high": {
            "causes": [
                "Mixed nutritional deficiency",
                "Recent blood transfusion",
                "Early iron deficiency"
            ],
            "next_steps": [
                "Nutritional panel (Iron, B12, Folate)",
                "Review previous CBC"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Uniform cell size (not typically concerning)"
            ],
            "next_steps": [
                "No specific action required for low RDW"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "rdw_sd": {
        "high": {
            "causes": [
                "Iron deficiency (early stage)",
                "B12 or Folate deficiency",
                "Recent blood loss or hemolysis",
                "Mixed anemia"
            ],
            "next_steps": [
                "Check iron panel (Ferritin, TIBC, serum iron)",
                "Check B12 and Folate levels",
                "Correlate with MCV and MCH"
            ],
            "age_context": {
                "young": "In young adults, iron deficiency from diet or blood loss is common."
            },
            "gender_context": {
                "female": "Menstrual blood loss is a common cause of iron deficiency in premenopausal females."
            }
        },
        "low": {
            "causes": [
                "Normal variant (uniform cell size)"
            ],
            "next_steps": [
                "No specific action required"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "mpv": {
        "high": {
            "causes": [
                "Increased platelet destruction (e.g., ITP)",
                "Inflammatory conditions",
                "Recovery from bone marrow suppression",
                "Bleeding"
            ],
            "next_steps": [
                "Review platelet count trend",
                "Assess for inflammatory markers (CRP/ESR)",
                "Peripheral smear if persistent"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Bone marrow disorders (e.g., aplastic anemia)",
                "Chemotherapy or radiation",
                "Chronic inflammation"
            ],
            "next_steps": [
                "Review full CBC with platelet parameters",
                "Assess bone marrow function if persistent",
                "Correlate with platelet count"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "pdw": {
        "high": {
            "causes": [
                "Increased platelet turnover",
                "Inflammatory conditions",
                "Iron deficiency",
                "Correlates with high MPV"
            ],
            "next_steps": [
                "Repeat CBC with platelet parameters",
                "Check iron studies",
                "Review clinical signs of inflammation"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Normal variant (uniform platelet size)"
            ],
            "next_steps": [
                "No specific action required"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "esr": {
        "high": {
            "causes": [
                "Systemic inflammation",
                "Infection",
                "Autoimmune disease (e.g., Rheumatoid Arthritis)"
            ],
            "next_steps": [
                "Assess alongside CRP",
                "Autoimmune screening if indicated"
            ],
            "age_context": {
                "elderly": "ESR naturally increases with age. Persistent high levels warrant investigation for conditions like temporal arteritis."
            },
            "gender_context": {
                "female": "Females naturally tend to have slightly higher ESR values."
            }
        },
        "low": {
            "causes": [
                "Polycythemia",
                "Sickle cell anemia",
                "Congestive heart failure"
            ],
            "next_steps": [
                "Correlate with full clinical picture"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "crp": {
        "high": {
            "causes": [
                "Bacterial infection",
                "Acute inflammation",
                "Tissue injury",
                "Smoking/Obesity"
            ],
            "next_steps": [
                "Repeat CRP in 2 weeks",
                "Check CBC and ESR"
            ],
            "age_context": {
                "young": "Often acute infections.",
                "elderly": "Chronic elevation is highly correlated with cardiovascular disease."
            },
            "gender_context": {
                "male": "Correlates with cardiovascular risk.",
                "female": "Associated with autoimmune conditions."
            }
        },
        "low": {
            "causes": [
                "Low systemic inflammation (optimal)"
            ],
            "next_steps": [
                "No action required for low CRP"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "procalcitonin": {
        "high": {
            "causes": [
                "Severe bacterial infection",
                "Sepsis",
                "Severe trauma"
            ],
            "next_steps": [
                "Immediate infectious disease evaluation",
                "Blood cultures",
                "Initiate antibiotics if septic"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Viral infection (rather than bacterial)"
            ],
            "next_steps": [
                "Supports viral etiology or absence of severe bacterial infection"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "glucose_fasting": {
        "high": {
            "causes": [
                "Insulin resistance",
                "Pre-diabetes or Diabetes",
                "Stress response"
            ],
            "next_steps": [
                "Check HbA1c",
                "Evaluate diet and exercise"
            ],
            "age_context": {
                "elderly": "Age-related changes in insulin sensitivity increase prevalence."
            },
            "gender_context": {
                "male": "Correlates with central adiposity.",
                "female": "Consider PCOS in younger females."
            }
        },
        "low": {
            "causes": [
                "Excess diabetes medication",
                "Prolonged fasting",
                "Liver disease"
            ],
            "next_steps": [
                "Review diabetes medications",
                "Ensure regular meals"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "hba1c": {
        "high": {
            "causes": [
                "Poorly controlled diabetes",
                "Undiagnosed diabetes",
                "Pre-diabetes",
                "Insulin resistance"
            ],
            "next_steps": [
                "Consult endocrinologist",
                "Dietary review",
                "Medication adjustment"
            ],
            "age_context": {
                "elderly": "Targets may be slightly higher to avoid hypoglycemia."
            },
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Recent blood loss",
                "Hemolytic anemia",
                "Excess diabetes medication"
            ],
            "next_steps": [
                "Review medications",
                "Rule out anemia affecting RBC lifespan"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "glucose": {
        "high": {
            "causes": [
                "Insulin resistance",
                "Pre-diabetes or Diabetes",
                "Recent carbohydrate-heavy meal"
            ],
            "next_steps": [
                "Check fasting glucose",
                "Check HbA1c",
                "Evaluate diet"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Prolonged fasting",
                "Excess insulin/medication",
                "Reactive hypoglycemia"
            ],
            "next_steps": [
                "Review meal timing",
                "Check medications"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "creatinine": {
        "high": {
            "causes": [
                "Dehydration",
                "Kidney impairment",
                "High muscle mass",
                "Medications"
            ],
            "next_steps": [
                "Ensure hydration and repeat",
                "Check eGFR and BUN",
                "Urinalysis"
            ],
            "age_context": {
                "elderly": "Small increases can represent significant kidney function decline due to lower muscle mass."
            },
            "gender_context": {
                "male": "Males generally have higher baseline due to muscle mass."
            }
        },
        "low": {
            "causes": [
                "Low muscle mass",
                "Severe liver disease",
                "Inadequate dietary protein"
            ],
            "next_steps": [
                "Ensure adequate protein intake",
                "Review overall nutritional status"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "urea": {
        "high": {
            "causes": [
                "Dehydration",
                "Kidney impairment",
                "High protein diet",
                "Heart failure"
            ],
            "next_steps": [
                "Assess hydration",
                "Check Creatinine",
                "Calculate BUN/Creatinine ratio"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Liver disease",
                "Low protein diet",
                "Overhydration",
                "Pregnancy"
            ],
            "next_steps": [
                "Review diet",
                "Check liver function"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "bun": {
        "high": {
            "causes": [
                "Dehydration",
                "Kidney impairment",
                "Gastrointestinal bleeding",
                "High protein diet"
            ],
            "next_steps": [
                "Check hydration",
                "Correlate with Creatinine",
                "Check for GI bleeding signs"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Liver disease",
                "Malnutrition",
                "Overhydration"
            ],
            "next_steps": [
                "Review nutrition and liver health"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "sodium": {
        "high": {
            "causes": [
                "Dehydration",
                "High salt diet",
                "Diabetes insipidus",
                "Kidney disease"
            ],
            "next_steps": [
                "Increase free water intake",
                "Review medications (diuretics)",
                "Monitor fluid balance"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Overhydration",
                "Heart failure",
                "Liver disease",
                "SIADH",
                "Medications (thiazides)"
            ],
            "next_steps": [
                "Fluid restriction",
                "Review medications",
                "Evaluate volume status"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "potassium": {
        "high": {
            "causes": [
                "Kidney disease",
                "Medications (ACE inhibitors, ARBs)",
                "Acidosis",
                "Hemolysis of sample"
            ],
            "next_steps": [
                "Repeat test to rule out hemolysis",
                "Review medications",
                "ECG if severely elevated"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Diuretic use",
                "Vomiting/Diarrhea",
                "Inadequate intake",
                "Alkalosis"
            ],
            "next_steps": [
                "Potassium supplementation",
                "Review medications",
                "ECG if severely low"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "calcium": {
        "high": {
            "causes": [
                "Hyperparathyroidism",
                "Vitamin D toxicity",
                "Malignancy",
                "Prolonged immobilization"
            ],
            "next_steps": [
                "Check PTH level",
                "Review supplements",
                "Check Vitamin D"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Vitamin D deficiency",
                "Hypoparathyroidism",
                "Renal failure",
                "Magnesium deficiency"
            ],
            "next_steps": [
                "Check Albumin",
                "Check Vitamin D and Magnesium",
                "Consider calcium supplementation"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "magnesium": {
        "high": {
            "causes": [
                "Kidney failure",
                "Excessive antacid/laxative use containing magnesium"
            ],
            "next_steps": [
                "Review medications and supplements",
                "Check kidney function"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Poor diet",
                "Alcohol abuse",
                "Gastrointestinal loss",
                "Diuretic use"
            ],
            "next_steps": [
                "Magnesium supplementation",
                "Review alcohol intake",
                "Check potassium and calcium levels"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "phosphorus": {
        "high": {
            "causes": [
                "Kidney failure",
                "Hypoparathyroidism",
                "Excessive vitamin D"
            ],
            "next_steps": [
                "Check kidney function",
                "Check Calcium and PTH"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Hyperparathyroidism",
                "Vitamin D deficiency",
                "Alcoholism",
                "Antacid abuse"
            ],
            "next_steps": [
                "Check Calcium, Vitamin D, and PTH",
                "Review diet"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "alt": {
        "high": {
            "causes": [
                "Fatty liver disease",
                "Alcohol consumption",
                "Medication toxicity",
                "Viral hepatitis"
            ],
            "next_steps": [
                "Avoid alcohol and hepatotoxic meds",
                "Ultrasound of liver",
                "Hepatitis panel"
            ],
            "age_context": {
                "young": "Often metabolic syndrome or acute viral infections."
            },
            "gender_context": {
                "male": "Higher incidence of alcoholic liver disease."
            }
        },
        "low": {
            "causes": [
                "Normal physiological variant",
                "Vitamin B6 deficiency"
            ],
            "next_steps": [
                "Typically no clinical concern"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "ast": {
        "high": {
            "causes": [
                "Liver damage",
                "Alcohol use",
                "Muscle injury",
                "Heart muscle stress"
            ],
            "next_steps": [
                "Compare AST/ALT ratio",
                "Limit alcohol",
                "Review medications"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Normal physiological variant",
                "Vitamin B6 deficiency"
            ],
            "next_steps": [
                "Typically no clinical concern"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "alp": {
        "high": {
            "causes": [
                "Bile duct obstruction",
                "Bone disease (Paget's, metastatic)",
                "Liver disease",
                "Pregnancy"
            ],
            "next_steps": [
                "Check GGT or 5'-nucleotidase to confirm liver vs bone origin",
                "Ultrasound"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Zinc deficiency",
                "Malnutrition",
                "Hypothyroidism",
                "Pernicious anemia"
            ],
            "next_steps": [
                "Evaluate nutritional status"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "bilirubin": {
        "high": {
            "causes": [
                "Liver disease",
                "Bile duct obstruction",
                "Hemolysis",
                "Gilbert's syndrome"
            ],
            "next_steps": [
                "Fractionate bilirubin (direct/indirect)",
                "Check AST/ALT and Alk Phos",
                "CBC for hemolysis"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Caffeine intake",
                "Medications (e.g., phenobarbital)"
            ],
            "next_steps": [
                "Typically indicates lower risk of cardiovascular disease, no action needed"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "albumin": {
        "high": {
            "causes": [
                "Dehydration"
            ],
            "next_steps": [
                "Encourage fluid intake",
                "Repeat testing if persistent"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Liver disease",
                "Kidney disease (nephrotic syndrome)",
                "Malnutrition",
                "Severe inflammation"
            ],
            "next_steps": [
                "Check liver and kidney function",
                "Urinalysis for protein",
                "Nutritional assessment"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "cholesterol": {
        "high": {
            "causes": [
                "Diet high in saturated fats",
                "Genetics",
                "Hypothyroidism",
                "Obesity"
            ],
            "next_steps": [
                "Fasting lipid panel",
                "Dietary modification",
                "Consider statins"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Hyperthyroidism",
                "Severe liver disease",
                "Malnutrition"
            ],
            "next_steps": [
                "Evaluate thyroid and liver function"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "ldl": {
        "high": {
            "causes": [
                "Diet high in saturated fats",
                "Genetics",
                "Hypothyroidism",
                "Obesity"
            ],
            "next_steps": [
                "Dietary modifications",
                "Consider statin therapy if risk is high",
                "Check thyroid function"
            ],
            "age_context": {
                "senior": "Cumulative exposure to high LDL strongly increases risk for cardiovascular events."
            },
            "gender_context": {
                "female": "LDL levels often increase significantly after menopause."
            }
        },
        "low": {
            "causes": [
                "Statin therapy",
                "Malnutrition",
                "Hyperthyroidism"
            ],
            "next_steps": [
                "Maintain current healthy lifestyle if not on medication"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "hdl": {
        "high": {
            "causes": [
                "Regular vigorous exercise",
                "Moderate alcohol consumption",
                "Genetics (beneficial variant)"
            ],
            "next_steps": [
                "Maintain healthy lifestyle"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Sedentary lifestyle",
                "Smoking",
                "Poor diet",
                "Metabolic syndrome"
            ],
            "next_steps": [
                "Increase cardiovascular exercise",
                "Smoking cessation",
                "Dietary improvements"
            ],
            "age_context": {},
            "gender_context": {
                "male": "Males typically have lower baseline HDL compared to premenopausal females."
            }
        }
    },
    "triglycerides": {
        "high": {
            "causes": [
                "High carbohydrate/sugar intake",
                "Alcohol consumption",
                "Obesity",
                "Poorly controlled diabetes",
                "Hypothyroidism"
            ],
            "next_steps": [
                "Reduce sugar and alcohol intake",
                "Increase exercise",
                "Evaluate fasting glucose"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Low-fat diet",
                "Hyperthyroidism",
                "Malabsorption"
            ],
            "next_steps": [
                "Maintain healthy balanced diet"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "tsh": {
        "high": {
            "causes": [
                "Hypothyroidism (underactive thyroid)",
                "Hashimoto's thyroiditis",
                "Inadequate medication"
            ],
            "next_steps": [
                "Check Free T4 and Free T3",
                "Test for thyroid antibodies",
                "Consider starting/adjusting levothyroxine"
            ],
            "age_context": {
                "elderly": "Mild TSH elevation is common with aging; aggressive treatment may not always be necessary."
            },
            "gender_context": {
                "female": "Autoimmune hypothyroidism is significantly more common in females."
            }
        },
        "low": {
            "causes": [
                "Hyperthyroidism (overactive thyroid)",
                "Too much thyroid medication",
                "Graves' disease"
            ],
            "next_steps": [
                "Check Free T4 and Free T3",
                "Evaluate for palpitations",
                "Adjust thyroid meds"
            ],
            "age_context": {
                "elderly": "Low TSH in older adults increases risk of atrial fibrillation and osteoporosis."
            },
            "gender_context": {
                "female": "Autoimmune hyperthyroidism is more common in females."
            }
        }
    },
    "t3": {
        "high": {
            "causes": [
                "Hyperthyroidism",
                "High dose of thyroid medication",
                "Graves' disease"
            ],
            "next_steps": [
                "Check TSH and Free T4",
                "Endocrinology consult"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Hypothyroidism",
                "Non-thyroidal illness (Euthyroid sick syndrome)",
                "Starvation"
            ],
            "next_steps": [
                "Check TSH",
                "Evaluate overall health status"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "t4": {
        "high": {
            "causes": [
                "Hyperthyroidism",
                "Excessive thyroid medication replacement",
                "Thyroiditis"
            ],
            "next_steps": [
                "Check TSH",
                "Review medication dose"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Hypothyroidism",
                "Pituitary disorder",
                "Iodine deficiency"
            ],
            "next_steps": [
                "Check TSH",
                "Consider thyroid autoantibodies"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "vitamin_d": {
        "high": {
            "causes": [
                "Excessive vitamin D supplementation"
            ],
            "next_steps": [
                "Reduce or stop supplements",
                "Check serum calcium levels"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Lack of sun exposure",
                "Inadequate dietary intake",
                "Malabsorption",
                "Obesity"
            ],
            "next_steps": [
                "Start Vitamin D3 supplementation",
                "Increase safe sun exposure",
                "Check calcium levels"
            ],
            "age_context": {
                "elderly": "Older adults have reduced capacity to synthesize Vitamin D in the skin."
            },
            "gender_context": {
                "female": "Adequate Vitamin D is critical in females for maintaining bone density."
            }
        }
    },
    "vitamin_b12": {
        "high": {
            "causes": [
                "Liver disease",
                "Kidney disease",
                "Myeloproliferative disorders",
                "Excessive supplementation"
            ],
            "next_steps": [
                "Review supplements",
                "Check liver and kidney function"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Pernicious anemia",
                "Vegan/vegetarian diet",
                "Malabsorption",
                "Certain medications (PPIs, Metformin)"
            ],
            "next_steps": [
                "B12 supplementation",
                "Check MCV for macrocytic anemia",
                "Evaluate diet"
            ],
            "age_context": {
                "elderly": "Age-related decrease in stomach acid heavily impairs B12 absorption."
            },
            "gender_context": {}
        }
    },
    "ferritin": {
        "high": {
            "causes": [
                "Hemochromatosis",
                "Inflammation",
                "Liver disease",
                "Alcohol abuse",
                "Frequent transfusions"
            ],
            "next_steps": [
                "Check iron and TIBC",
                "Check CRP/ESR to rule out inflammation",
                "Liver function tests"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Iron deficiency anemia",
                "Chronic blood loss",
                "Inadequate dietary iron",
                "Pregnancy"
            ],
            "next_steps": [
                "Check CBC for anemia",
                "Iron supplementation",
                "Evaluate for source of blood loss"
            ],
            "age_context": {},
            "gender_context": {
                "female": "Common in menstruating females or during pregnancy."
            }
        }
    },
    "iron": {
        "high": {
            "causes": [
                "Hemochromatosis",
                "Excessive iron supplements",
                "Multiple blood transfusions",
                "Liver damage"
            ],
            "next_steps": [
                "Check Ferritin and TIBC",
                "Stop iron supplements",
                "Liver function tests"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Iron deficiency",
                "Chronic blood loss",
                "Poor absorption",
                "Poor diet"
            ],
            "next_steps": [
                "Check Ferritin",
                "Check CBC",
                "Evaluate for GI bleeding"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "tibc": {
        "high": {
            "causes": [
                "Iron deficiency",
                "Pregnancy",
                "Oral contraceptive use"
            ],
            "next_steps": [
                "Check Iron and Ferritin",
                "Correlate with CBC"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Hemochromatosis",
                "Malnutrition",
                "Inflammation",
                "Liver disease"
            ],
            "next_steps": [
                "Check Iron and Ferritin",
                "Evaluate liver function"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "psa": {
        "high": {
            "causes": [
                "Prostate enlargement (BPH)",
                "Prostatitis",
                "Prostate cancer",
                "Recent ejaculation or bike riding"
            ],
            "next_steps": [
                "Consult urologist",
                "Consider free PSA ratio",
                "Digital rectal exam"
            ],
            "age_context": {
                "elderly": "PSA naturally rises with age due to prostate growth."
            },
            "gender_context": {
                "male": "Only applicable to males."
            }
        },
        "low": {
            "causes": [
                "Medications (e.g., 5-alpha reductase inhibitors)",
                "Healthy prostate"
            ],
            "next_steps": [
                "No action required"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "d_dimer": {
        "high": {
            "causes": [
                "Deep vein thrombosis (DVT)",
                "Pulmonary embolism (PE)",
                "Recent surgery or trauma",
                "Pregnancy",
                "Severe inflammation"
            ],
            "next_steps": [
                "Ultrasound for DVT",
                "CT angiogram if PE suspected",
                "Correlate with clinical risk score (Wells score)"
            ],
            "age_context": {
                "elderly": "D-Dimer naturally increases with age; age-adjusted cutoffs may be needed."
            },
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Normal coagulation status"
            ],
            "next_steps": [
                "Rules out significant clotting in low-risk patients"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "troponin": {
        "high": {
            "causes": [
                "Myocardial infarction (heart attack)",
                "Myocarditis",
                "Heart failure",
                "Pulmonary embolism",
                "Severe kidney disease"
            ],
            "next_steps": [
                "Immediate ECG",
                "Cardiology consult",
                "Serial troponin testing"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Normal heart muscle status"
            ],
            "next_steps": [
                "No action required"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "pt": {
        "high": {
            "causes": [
                "Liver disease",
                "Vitamin K deficiency",
                "Warfarin therapy",
                "DIC"
            ],
            "next_steps": [
                "Review medications",
                "Liver function tests",
                "Check Vitamin K status"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Vitamin K supplementation",
                "High intake of Vitamin K-rich foods"
            ],
            "next_steps": [
                "Review diet and supplements"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "inr": {
        "high": {
            "causes": [
                "Warfarin overdose",
                "Liver failure",
                "Severe Vitamin K deficiency"
            ],
            "next_steps": [
                "Withhold Warfarin if applicable",
                "Consider Vitamin K or FFP if bleeding",
                "Immediate medical evaluation"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Subtherapeutic Warfarin dose",
                "High Vitamin K diet"
            ],
            "next_steps": [
                "Adjust anticoagulant dose if applicable"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "aptt": {
        "high": {
            "causes": [
                "Heparin therapy",
                "Hemophilia",
                "Von Willebrand disease",
                "Lupus anticoagulant",
                "Liver disease"
            ],
            "next_steps": [
                "Review anticoagulants",
                "Coagulation factor assays",
                "Mixing study"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Acute phase reaction",
                "Extensive cancer"
            ],
            "next_steps": [
                "Monitor for thrombotic risk"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "lactate": {
        "high": {
            "causes": [
                "Sepsis",
                "Hypoxia",
                "Severe anemia",
                "Heart failure",
                "Intense exercise"
            ],
            "next_steps": [
                "Assess oxygenation and perfusion",
                "Treat underlying cause immediately",
                "Serial lactate measurements"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Normal physiological state"
            ],
            "next_steps": [
                "No action required"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "lipase": {
        "high": {
            "causes": [
                "Acute pancreatitis",
                "Pancreatic duct obstruction",
                "Kidney failure",
                "Gallbladder disease"
            ],
            "next_steps": [
                "Abdominal ultrasound or CT",
                "NPO (fasting)",
                "Pain management and IV fluids"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Chronic pancreatitis (advanced)",
                "Cystic fibrosis"
            ],
            "next_steps": [
                "Evaluate pancreatic exocrine function"
            ],
            "age_context": {},
            "gender_context": {}
        }
    },
    "amylase": {
        "high": {
            "causes": [
                "Acute pancreatitis",
                "Salivary gland inflammation (e.g., mumps)",
                "Peptic ulcer",
                "Gallbladder disease"
            ],
            "next_steps": [
                "Check Lipase for pancreas specificity",
                "Abdominal imaging"
            ],
            "age_context": {},
            "gender_context": {}
        },
        "low": {
            "causes": [
                "Pancreatic insufficiency",
                "Liver disease",
                "Advanced cystic fibrosis"
            ],
            "next_steps": [
                "Evaluate pancreatic and liver function"
            ],
            "age_context": {},
            "gender_context": {}
        }
    }
}
