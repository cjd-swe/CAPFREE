"""
Tests for the pick parser — verifies regex patterns correctly extract
structured pick data from raw OCR text.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ocr.parser import parse_picks


# ── Spread formats ──────────────────────────────────────────────

class TestSpreadFormats:
    def test_basic_spread_with_units(self):
        picks = parse_picks("Lakers -5.5 2u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Lakers -5.5"
        assert picks[0]["units_risked"] == 2.0

    def test_positive_spread(self):
        picks = parse_picks("Celtics +3.5 1u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Celtics +3.5"
        assert picks[0]["units_risked"] == 1.0

    def test_whole_number_spread(self):
        picks = parse_picks("Chiefs -7 3u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Chiefs -7"
        assert picks[0]["units_risked"] == 3.0

    def test_fractional_units(self):
        picks = parse_picks("Bucks -4.5 1.5u")
        assert len(picks) == 1
        assert picks[0]["units_risked"] == 1.5

    def test_uppercase_U(self):
        picks = parse_picks("Nuggets -3 2U")
        assert len(picks) == 1
        assert picks[0]["units_risked"] == 2.0


# ── Spread with opponent (v./vs) ───────────────────────────────

class TestSpreadWithOpponent:
    def test_spread_vs_opponent_with_units(self):
        picks = parse_picks("Indiana -6.5 (-110) v. Northwestern 10u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Indiana -6.5"
        assert picks[0]["units_risked"] == 10.0
        assert picks[0]["match_key"] == "Indiana v. Northwestern"
        assert picks[0].get("odds") == -110

    def test_spread_vs_opponent_potd(self):
        picks = parse_picks("Florida State -3.5 (-110) v. California 10u POTD")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Florida State -3.5"
        assert picks[0]["units_risked"] == 10.0
        assert picks[0]["match_key"] == "Florida State v. California"

    def test_positive_spread_vs(self):
        picks = parse_picks("Pelicans +2.5 (-110) v. Raptors 10u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Pelicans +2.5"
        assert picks[0]["sport"] == "Basketball"
        assert picks[0]["match_key"] == "Pelicans v. Raptors"

    def test_odds_extracted(self):
        picks = parse_picks("Clippers -1.5 (-110) v. Timberwolves 10u")
        assert picks[0].get("odds") == -110


# ── Moneyline formats ──────────────────────────────────────────

class TestMoneylineFormats:
    def test_basic_moneyline_ml(self):
        picks = parse_picks("ChiefsML 1.5u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Chiefs ML"
        assert picks[0]["units_risked"] == 1.5

    def test_moneyline_lowercase(self):
        picks = parse_picks("Lakersml 2u")
        assert len(picks) == 1
        assert picks[0]["units_risked"] == 2.0

    def test_moneyline_full_word(self):
        """'Capitals Moneyline' with context units from header."""
        text = "NHL: 1 Unit ( 7:30 PM EST )\nCapitals Moneyline"
        picks = parse_picks(text)
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Capitals ML"
        assert picks[0]["units_risked"] == 1.0
        assert picks[0]["sport"] == "Hockey"

    def test_moneyline_full_word_nba(self):
        text = "NBA: 1 Unit (10:30 PM EST )\nClippers Moneyline"
        picks = parse_picks(text)
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Clippers ML"
        assert picks[0]["sport"] == "Basketball"


# ── Over/Under formats ─────────────────────────────────────────

class TestOverUnderFormats:
    def test_over_with_units(self):
        picks = parse_picks("Over 225.5 3u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Over 225.5"
        assert picks[0]["units_risked"] == 3.0

    def test_under_with_units(self):
        picks = parse_picks("Under 210 2u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Under 210"
        assert picks[0]["units_risked"] == 2.0

    def test_teams_under_no_units(self):
        """'Clemson/Wake Forest Under 143' with context units."""
        text = "NCAAB: 1 Unit ( 9:30 PM EST )\nClemson/Wake Forest Under 143"
        picks = parse_picks(text)
        assert len(picks) == 1
        assert "Under 143" in picks[0]["pick_text"]
        assert picks[0]["units_risked"] == 1.0


# ── Player props ───────────────────────────────────────────────

class TestPlayerProps:
    def test_player_over_pra(self):
        picks = parse_picks("Kevin Durant O34.5 PRA -110 1u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Kevin Durant O34.5 PRA"
        assert picks[0]["units_risked"] == 1.0
        assert picks[0].get("odds") == -110

    def test_player_over_rebounds(self):
        picks = parse_picks("Rudy Gobert O11.5 Rebounds +106 1u")
        assert len(picks) == 1
        assert picks[0]["pick_text"] == "Rudy Gobert O11.5 Rebounds"
        assert picks[0]["units_risked"] == 1.0

    def test_player_prop_ocr_zero_for_O(self):
        """OCR often reads 'O' as '0' — parser should handle both."""
        picks = parse_picks("Kevin Durant 034.5 PRA -110 1u")
        assert len(picks) == 1
        assert "O34.5" in picks[0]["pick_text"]

    def test_player_prop_detects_nba(self):
        picks = parse_picks("Kevin Durant O34.5 PRA -110 1u")
        assert picks[0]["sport"] == "Basketball"


# ── Context headers ────────────────────────────────────────────

class TestContextHeaders:
    def test_sport_header_sets_context(self):
        text = "NHL: 1 Unit ( 7:30 PM EST )\nCapitals Moneyline"
        picks = parse_picks(text)
        assert picks[0]["league"] == "NHL"
        assert picks[0]["sport"] == "Hockey"

    def test_nba_header_units(self):
        text = "NBA: 1 Unit (10:00 PM EST )\nNuggets -5 Alternate Line"
        picks = parse_picks(text)
        assert len(picks) == 1
        assert picks[0]["units_risked"] == 1.0
        assert picks[0]["sport"] == "Basketball"

    def test_main_card_header(self):
        text = "Main Card: NCAAB & NBA\nIndiana -6.5 (-110) v. Northwestern 10u"
        picks = parse_picks(text)
        assert len(picks) == 1
        assert picks[0]["league"] == "NCAAB"

    def test_plays_header(self):
        text = "3/11 nba plays\nLakers -5.5 2u"
        picks = parse_picks(text)
        assert len(picks) == 1
        assert picks[0]["sport"] == "Basketball"


# ── Parenthesis format ─────────────────────────────────────────

class TestParenthesisFormat:
    def test_parens_with_spread(self):
        picks = parse_picks("(LAKERS -3.5)")
        assert len(picks) == 1
        assert "LAKERS" in picks[0]["pick_text"]
        assert picks[0]["units_risked"] == 1.0

    def test_parens_positive_spread(self):
        picks = parse_picks("(CELTICS +7)")
        assert len(picks) == 1
        assert picks[0]["units_risked"] == 1.0


# ── Multi-line parsing ─────────────────────────────────────────

class TestMultiLineParsing:
    def test_multiple_picks(self):
        text = "Lakers -5.5 2u\nCeltics +3 1u\nOver 220 3u"
        picks = parse_picks(text)
        assert len(picks) == 3

    def test_skips_empty_lines(self):
        text = "\nLakers -5.5 2u\n\nCeltics +3 1u\n"
        picks = parse_picks(text)
        assert len(picks) == 2

    def test_skips_short_lines(self):
        text = "ab\nLakers -5.5 2u"
        picks = parse_picks(text)
        assert len(picks) == 1

    def test_full_yourdailycapper_format(self):
        """Simulates the yourdailycapper format from test1.jpg."""
        text = (
            "NHL: 1 Unit ( 7:30 PM EST )\n"
            "Capitals Moneyline\n\n"
            "NCAAB: 1 Unit ( 9:30 PM EST )\n"
            "Clemson/Wake Forest Under 143\n\n"
            "NBA: 1 Unit (10:00 PM EST )\n"
            "Nuggets -5 Alternate Line\n\n"
            "NBA: 1 Unit (10:30 PM EST )\n"
            "Clippers Moneyline\n"
        )
        picks = parse_picks(text)
        assert len(picks) == 4
        assert picks[0]["pick_text"] == "Capitals ML"
        assert picks[0]["sport"] == "Hockey"
        assert picks[1]["pick_text"] == "Clemson/Wake Forest Under 143"
        assert picks[2]["pick_text"] == "Nuggets -5"
        assert picks[2]["sport"] == "Basketball"
        assert picks[3]["pick_text"] == "Clippers ML"

    def test_full_analyticscapper_format(self):
        """Simulates the AnalyticsCapper format from test2.jpg."""
        text = (
            "Main Card: NCAAB & NBA\n\n"
            "Indiana -6.5 (-110) v. Northwestern 10u\n\n"
            "Florida State -3.5 (-110) v. California 10u POTD\n"
            "Pelicans +2.5 (-110) v. Raptors 10u\n\n"
            "Clippers -1.5 (-110) v. Timberwolves 10u\n"
        )
        picks = parse_picks(text)
        assert len(picks) == 4
        assert picks[0]["match_key"] == "Indiana v. Northwestern"
        assert picks[1]["pick_text"] == "Florida State -3.5"
        assert picks[2]["sport"] == "Basketball"
        assert all(p["units_risked"] == 10.0 for p in picks)


# ── Edge cases ─────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_string(self):
        assert parse_picks("") == []

    def test_no_matches(self):
        assert parse_picks("Hello world\nNo picks here") == []

    def test_whitespace_only(self):
        assert parse_picks("   \n   \n   ") == []

    def test_raw_text_preserved(self):
        picks = parse_picks("Lakers -5.5 2u")
        assert picks[0]["raw_text"] == "Lakers -5.5 2u"

    def test_match_key_is_none_for_simple(self):
        picks = parse_picks("Lakers -5.5 2u")
        assert picks[0]["match_key"] is None

    def test_skips_noise_text(self):
        """Paragraphs of analysis should not produce picks."""
        text = (
            "KD has been really good on the second leg of\n"
            "back to backs. In 10 games with no rest he's hit\n"
            "this over 8 times. This game should be\n"
            "competitive and the Rockets have some weapons\n"
        )
        picks = parse_picks(text)
        assert len(picks) == 0

    def test_team_detection_from_opponent(self):
        """If the main team is unknown, detect sport from opponent."""
        picks = parse_picks("Florida State -3.5 (-110) v. California 10u")
        # Florida State is NCAAB
        assert picks[0]["sport"] == "Basketball"
