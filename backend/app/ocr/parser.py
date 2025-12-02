import re
from typing import List, Dict, Any
from .teams import detect_league_from_team, get_full_team_name


def parse_picks(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parse raw OCR text into structured picks.
    Handles various formats from OCR output.
    """
    picks = []
    lines = raw_text.split('\n')
    
    # Multiple regex patterns to handle different formats
    patterns = [
        # Format: "Lakers -5.5 2u" or "Lakers-55 2u"
        re.compile(r"(.+?)\s*([+-]?\d+\.?\d*)\s+(\d+\.?\d*)[uU]"),
        # Format: "ChiefsML 1.5u" (ML = moneyline)
        re.compile(r"(.+?ML)\s+(\d+\.?\d*)[uU]", re.IGNORECASE),
        # Format: "Over 225.5 3u" or "ver2255 Su"
        re.compile(r"(Over|Under|ver)\s*(\d+\.?\d*)\s+(\d+\.?\d*)[uU]", re.IGNORECASE),
        # Format: "(LAKERS -3.5)" without units - defaults to 1.0 units
        re.compile(r"\(?\s*([A-Z][A-Za-z\s]+?)\s*([+-]\d+\.?\d*)\s*\)?"),
    ]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # Skip header lines
        if 'PICK' in line.upper() or 'TODAY' in line.upper():
            continue
            
        # Try each pattern
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                if len(match.groups()) == 3:
                    team = match.group(1).strip()
                    line_val = match.group(2)
                    units = float(match.group(3))
                    pick_text = f"{team} {line_val}"
                elif len(match.groups()) == 2:
                    team = match.group(1).strip()
                    # Check if group 2 is a line value (starts with +/-) or units
                    group2 = match.group(2).strip()
                    if group2.startswith(('+', '-')) or '.' in group2:
                        # This is a line value, not units - default to 1.0 units
                        line_val = group2
                        units = 1.0
                        pick_text = f"{team} {line_val}"
                    else:
                        # This is units (from ML pattern)
                        units = float(group2)
                        pick_text = team
                else:
                    continue
                
                # Detect league and sport from team name
                league, sport = detect_league_from_team(team)
                full_team_name = get_full_team_name(team)
                
                picks.append({
                    "pick_text": pick_text,
                    "units_risked": units,
                    "raw_text": line,
                    "sport": sport if sport else "Unknown",
                    "league": league,
                    "match_key": None,
                    "team_name": full_team_name if full_team_name else team,
                })
                break
    
    return picks

