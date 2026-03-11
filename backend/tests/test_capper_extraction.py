"""
Tests for capper name extraction from raw OCR text.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ocr.parser import extract_capper_name


class TestCapperExtraction:

    def test_simple_name_first_line(self):
        text = "MrBigBets\n\nKevin Durant O34.5 PRA -110 1u\n"
        assert extract_capper_name(text) == "MrBigBets"

    def test_name_after_icon_artifacts(self):
        """'~~ MrBigBets' — leading symbols stripped."""
        text = "~~ MrBigBets\n\nKevin Durant O34.5 PRA -110 1u\n"
        assert extract_capper_name(text) == "MrBigBets"

    def test_name_with_badge_prefix(self):
        """'AC AnalyticsCapper' — 2-letter all-caps badge skipped."""
        text = "AC AnalyticsCapper\n3/11/26\nIndiana -6.5 v. Northwestern 10u\n"
        assert extract_capper_name(text) == "AnalyticsCapper"

    def test_name_with_timestamp_and_hash_tag(self):
        """'€A Caleb #CPIK 2:30PM' — timestamp stripped, short artifact skipped."""
        text = "11 March 2026\n\n€A Caleb #CPIK 2:30PM\nZverev + Alcaraz -145 10U\n"
        assert extract_capper_name(text) == "Caleb"

    def test_name_at_first_line_no_noise(self):
        text = "yourdailycapper @\nNHL: 1 Unit\nCapitals Moneyline\n"
        assert extract_capper_name(text) == "yourdailycapper"

    def test_skips_date_line(self):
        """Dates like '11 March 2026' should not be returned as a name."""
        text = "11 March 2026\nCaleb\nsome pick\n"
        result = extract_capper_name(text)
        assert result == "Caleb"

    def test_skips_cappersfree_watermark(self):
        text = "@cappersfree\nMrBigBets\nLakers -5.5 2u\n"
        assert extract_capper_name(text) != "@cappersfree"
        assert extract_capper_name(text) == "MrBigBets"

    def test_returns_none_for_empty(self):
        assert extract_capper_name("") is None

    def test_returns_none_for_only_noise(self):
        text = "@cappersfree\n3/11\n@vip\n"
        assert extract_capper_name(text) is None

    def test_skips_sport_league_tokens(self):
        """Pure league/sport tokens (NBA, NHL) should not be treated as names."""
        text = "NBA\nLakers -5.5 2u\n"
        result = extract_capper_name(text)
        # Should not return NBA as a capper name
        assert result != "NBA"

    def test_camelcase_name(self):
        text = "SharpBettorPro\nChiefs -3 2u\n"
        assert extract_capper_name(text) == "SharpBettorPro"

    def test_looks_past_short_artifact_to_real_name(self):
        """When a line has a short leading artifact followed by a real name,
        it should find the real name within that line."""
        text = "YD SharpCapperDaily\nCapitals Moneyline\n"
        result = extract_capper_name(text)
        assert result == "SharpCapperDaily"
