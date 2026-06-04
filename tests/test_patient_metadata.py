import pytest
from core.patient_metadata import extract_patient_metadata


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Patient Name: Ahmed\nAge: 45\nGender: Male", {"gender": "male", "age": 45}),
        ("Sex: F\n28 Years", {"gender": "female", "age": 28}),
        ("Age/Sex: 32/M", {"gender": "male", "age": 32}),
        ("DOB: 1990-05-15\nSex: Femaie", {"gender": "female", "age": None}),
        ("No patient info here", {"gender": None, "age": None}),
    ],
)
def test_extract_patient_metadata(text, expected):
    md = extract_patient_metadata(text)
    # Age from DOB depends on current year; when DOB provided we only assert gender for that case
    if "DOB" in text:
        assert md["gender"] == expected["gender"]
    else:
        assert md == expected
