import pytest

from src.llm.json_utils import extract_json


def test_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_markdown_fences():
    text = '```json\n{"a": 1}\n```'
    assert extract_json(text) == {"a": 1}


def test_text_around_json():
    text = 'Aquí tienes el resultado:\n{"a": {"b": 2}}\nEspero que te sirva.'
    assert extract_json(text) == {"a": {"b": 2}}


def test_trailing_commas():
    text = '{"a": [1, 2,], "b": {"c": 3,},}'
    assert extract_json(text) == {"a": [1, 2], "b": {"c": 3}}


def test_nested_braces_after_json():
    # rfind("}") habría cogido la llave del texto posterior;
    # el balanceo de llaves debe coger la correcta.
    text = '{"a": 1} y luego {esto no es json'
    assert extract_json(text) == {"a": 1}


def test_empty_response_raises():
    with pytest.raises(ValueError):
        extract_json("")


def test_no_json_raises():
    with pytest.raises(ValueError):
        extract_json("no hay nada estructurado aquí")


def test_malformed_json_raises():
    with pytest.raises(ValueError):
        extract_json('{"a": 1')
