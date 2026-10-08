from app.utils.txt_import import parse_txt


def test_parse_valid_questions():
    text = '''1. Savol?\nA: A\nB: B\nC: C\nD: D\nANSWER: C\nEXPLANATION: X\n\n2. Ikkinchi?\nA: A\nB: B\nC: C\nD: D\nANSWER: A\n'''
    parsed, errors, duplicates = parse_txt(text, 100)
    assert len(parsed) == 2
    assert not errors
    assert duplicates == 0


def test_parse_duplicate():
    text = '''1. Bir xil savol?\nA: A\nB: B\nC: C\nD: D\nANSWER: A\n\n2. Bir xil savol?\nA: A\nB: B\nC: C\nD: D\nANSWER: A\n'''
    parsed, errors, duplicates = parse_txt(text, 100)
    assert len(parsed) == 1
    assert duplicates == 1
    assert len(errors) == 1
