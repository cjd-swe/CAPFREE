import re
from typing import List, Dict, Any

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
                    units = float(match.group(2))
                    pick_text = team
                else:
                    continue
                
                picks.append({
                    "pick_text": pick_text,
                    "units_risked": units,
                    "raw_text": line,
                    "sport": "Unknown",  # Could be enhanced with team name detection
                    "league": None,
                    "match_key": None,
                })
                break
    
    return picks

