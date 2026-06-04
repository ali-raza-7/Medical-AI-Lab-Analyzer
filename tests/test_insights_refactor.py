import unittest
from services.insights_service import LabResult, generate_insights

class TestInsightsLogicRefactor(unittest.TestCase):
    def test_anemia_pattern(self):
        results = [
            LabResult(test_key="hemoglobin", test_name="Hb", status="low", value=10.0, unit="g/dL"),
            LabResult(test_key="mcv", test_name="MCV", status="low", value=75.0, unit="fL"),
            LabResult(test_key="mchc", test_name="MCHC", status="low", value=30.0, unit="g/dL"),
        ]
        insights = generate_insights(results)
        self.assertTrue(any("Pattern: Low Hb + Low MCV + Low MCHC/MCH" in i for i in insights))

    def test_diabetes_pattern(self):
        results = [
            LabResult(test_key="glucose_fasting", test_name="Glucose", status="high", value=150.0, unit="mg/dL"),
            LabResult(test_key="hba1c", test_name="HbA1c", status="high", value=7.5, unit="%"),
        ]
        insights = generate_insights(results)
        self.assertTrue(any("Pattern: High fasting glucose + High HbA1c" in i for i in insights))

    def test_liver_pattern(self):
        results = [
            LabResult(test_key="alt", test_name="ALT", status="high", value=200.0, unit="U/L"),
            LabResult(test_key="ast", test_name="AST", status="high", value=180.0, unit="U/L"),
        ]
        insights = generate_insights(results)
        self.assertTrue(any("Pattern: Markedly elevated ALT + AST" in i for i in insights))

    def test_thyroid_pattern(self):
        results = [
            LabResult(test_key="tsh", test_name="TSH", status="high", value=10.0, unit="mIU/L"),
            LabResult(test_key="t4", test_name="T4", status="low", value=0.5, unit="ng/dL"),
        ]
        insights = generate_insights(results)
        self.assertTrue(any("Pattern: High TSH + Low Free T4" in i for i in insights))

    def test_no_pattern(self):
        results = [
            LabResult(test_key="hemoglobin", test_name="Hb", status="normal", value=14.0, unit="g/dL"),
        ]
        insights = generate_insights(results)
        self.assertTrue(any("No specific pattern detected" in i for i in insights))

if __name__ == "__main__":
    unittest.main()
