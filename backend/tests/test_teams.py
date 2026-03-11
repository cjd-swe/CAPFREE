"""
Tests for team name detection and league/sport mapping.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ocr.teams import detect_league_from_team, get_full_team_name


class TestDetectLeague:
    """Test league/sport detection from team names."""

    def test_nba_exact(self):
        assert detect_league_from_team("LAKERS") == ("NBA", "Basketball")

    def test_nba_lowercase(self):
        assert detect_league_from_team("lakers") == ("NBA", "Basketball")

    def test_nba_mixed_case(self):
        assert detect_league_from_team("Lakers") == ("NBA", "Basketball")

    def test_nba_variation(self):
        assert detect_league_from_team("CAVS") == ("NBA", "Basketball")
        assert detect_league_from_team("OKC") == ("NBA", "Basketball")

    def test_nfl(self):
        assert detect_league_from_team("CHIEFS") == ("NFL", "Football")
        assert detect_league_from_team("BUCS") == ("NFL", "Football")

    def test_mlb(self):
        assert detect_league_from_team("YANKEES") == ("MLB", "Baseball")
        assert detect_league_from_team("RED SOX") == ("MLB", "Baseball")

    def test_nhl(self):
        assert detect_league_from_team("BRUINS") == ("NHL", "Hockey")
        assert detect_league_from_team("GOLDEN KNIGHTS") == ("NHL", "Hockey")

    def test_soccer(self):
        assert detect_league_from_team("ARSENAL") == ("Soccer", "Soccer")
        assert detect_league_from_team("BARCA") == ("Soccer", "Soccer")

    def test_unknown_team(self):
        assert detect_league_from_team("NONEXISTENT") == (None, None)

    def test_empty_string(self):
        assert detect_league_from_team("") == (None, None)

    def test_partial_match(self):
        # "LAKER" should partial-match to LAKERS
        league, sport = detect_league_from_team("LAKER")
        assert league == "NBA"

    def test_whitespace_handling(self):
        assert detect_league_from_team("  LAKERS  ") == ("NBA", "Basketball")


class TestGetFullTeamName:
    """Test full team name resolution."""

    def test_exact_match(self):
        assert get_full_team_name("LAKERS") == "Los Angeles Lakers"

    def test_abbreviation(self):
        assert get_full_team_name("CAVS") == "Cleveland Cavaliers"
        assert get_full_team_name("MAVS") == "Dallas Mavericks"

    def test_nickname(self):
        assert get_full_team_name("SIXERS") == "Philadelphia 76ers"
        assert get_full_team_name("NINERS") == "San Francisco 49ers"

    def test_lowercase(self):
        assert get_full_team_name("lakers") == "Los Angeles Lakers"

    def test_unknown(self):
        assert get_full_team_name("NONEXISTENT") is None

    def test_soccer_team(self):
        assert get_full_team_name("BARCA") == "Barcelona"
        assert get_full_team_name("MAN CITY") == "Manchester City"
