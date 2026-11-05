from voice.language import detect_text_language


def test_detect_text_language_identifies_urdu_script():
    assert detect_text_language("اردو میں بات کریں") == "ur"


def test_detect_text_language_leaves_english_undetected():
    assert detect_text_language("Speak to me in English") is None


def test_detect_text_language_handles_empty_text():
    assert detect_text_language("") is None
