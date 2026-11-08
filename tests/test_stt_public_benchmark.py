from scripts.benchmark_stt_public import edit_distance, metric, normalize, region


def test_stt_metric_normalizes_vietnamese_without_hiding_word_errors():
    assert normalize("Đường huyết 126!") == ["duong", "huyet", "126"]
    assert edit_distance(["duong", "huyet"], ["duong", "viet"]) == 1
    wer, cer = metric("đường huyết", "đường viết")
    assert wer == 0.5 and 0 < cer < 0.5


def test_vietmed_regions_are_grouped_explicitly():
    assert region("North") == "north"
    assert region("North Central Coast") == "central"
    assert region("South Central Coast") == "central"
    assert region("Central Highland") == "central"
    assert region("South East") == "south"
    assert region("South West") == "south"
    assert region("other") == "unknown"
