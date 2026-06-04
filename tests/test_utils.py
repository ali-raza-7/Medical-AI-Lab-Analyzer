import pytest
import math
from core.utils import sanitize_for_json
from dataclasses import dataclass

@dataclass
class MockData:
    name: str
    value: float

def test_sanitize_primitives():
    assert sanitize_for_json(None) is None
    assert sanitize_for_json(True) is True
    assert sanitize_for_json(123) == 123
    assert sanitize_for_json("hello") == "hello"

def test_sanitize_floats():
    assert sanitize_for_json(1.23) == 1.23
    assert sanitize_for_json(float('nan')) is None
    assert sanitize_for_json(float('inf')) is None

def test_sanitize_dict():
    d = {"a": 1, "b": float('nan'), "c": {"d": float('inf')}}
    expected = {"a": 1, "b": None, "c": {"d": None}}
    assert sanitize_for_json(d) == expected

def test_sanitize_list():
    l = [1, float('nan'), [float('inf')]]
    expected = [1, None, [None]]
    assert sanitize_for_json(l) == expected

def test_sanitize_dataclass():
    obj = MockData(name="test", value=float('nan'))
    expected = {"name": "test", "value": None}
    assert sanitize_for_json(obj) == expected

def test_sanitize_unknown_type():
    class Unknown:
        def __str__(self): return "unknown"
    
    obj = Unknown()
    assert sanitize_for_json(obj) == "unknown"
