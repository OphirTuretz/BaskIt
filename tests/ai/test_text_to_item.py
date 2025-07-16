"""Tests for the text-to-item parser."""
from ai.text_to_item import parse_text_to_item

def test_parse_text_to_item_basic():
    """Test basic text parsing with a simple Hebrew input."""
    text = "קניתי מלפפונים"
    result = parse_text_to_item(text)
    
    assert isinstance(result, dict)
    assert "item" in result
    assert "quantity" in result
    assert "unit" in result
    assert "confidence" in result
    assert "original_text" in result
    
    assert result["original_text"] == text
    assert isinstance(result["confidence"], float)
    assert 0 <= result["confidence"] <= 1

def test_parse_text_to_item_structure():
    """Test that the parser returns the expected data structure."""
    result = parse_text_to_item("test")
    
    expected_keys = {"item", "quantity", "unit", "confidence", "original_text"}
    assert set(result.keys()) == expected_keys
    
    assert isinstance(result["quantity"], int)
    assert isinstance(result["unit"], str)
    assert isinstance(result["item"], str) 