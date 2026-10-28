undefined

def test_selection_parser_recovers_common_roman_hindi_stt_number_errors():
    parser = executor.intent_engine
    cases = {
        "number van": "1",
        "number wan": "1",
        "number won": "1",
        "number one": "1",
        "number 1 vala not kaise kholen": "1",
        "option one open": "1",
        "number do kholo": "2",
        "number tree": "3",
    }
    for spoken_text, expected in cases.items():
        assert parser._detect_selection(spoken_text) == expected


def test_selection_parser_does_not_treat_arbitrary_number_mentions_as_choices():
    parser = executor.intent_engine
    assert parser._detect_selection("please explain number theory") is None
    assert parser._detect_selection("what is the number of districts in Rajasthan") is None
