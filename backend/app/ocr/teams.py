"""
Team reference data for league/sport detection.
Maps team names (including variations) to their league and sport.
"""
from typing import Optional, Tuple


# NBA Teams - including common variations and OCR errors
NBA_TEAMS = {
    # Atlantic Division
    "CELTICS": "Boston Celtics",
    "NETS": "Brooklyn Nets",
    "KNICKS": "New York Knicks",
    "76ERS": "Philadelphia 76ers",
    "SIXERS": "Philadelphia 76ers",
    "RAPTORS": "Toronto Raptors",
    
    # Central Division
    "BULLS": "Chicago Bulls",
    "CAVALIERS": "Cleveland Cavaliers",
    "CAVS": "Cleveland Cavaliers",
    "PISTONS": "Detroit Pistons",
    "PACERS": "Indiana Pacers",
    "BUCKS": "Milwaukee Bucks",
    
    # Southeast Division
    "HAWKS": "Atlanta Hawks",
    "HORNETS": "Charlotte Hornets",
    "HEAT": "Miami Heat",
    "MAGIC": "Orlando Magic",
    "WIZARDS": "Washington Wizards",
    
    # Northwest Division
    "NUGGETS": "Denver Nuggets",
    "TIMBERWOLVES": "Minnesota Timberwolves",
    "WOLVES": "Minnesota Timberwolves",
    "THUNDER": "Oklahoma City Thunder",
    "OKC": "Oklahoma City Thunder",
    "BLAZERS": "Portland Trail Blazers",
    "TRAIL BLAZERS": "Portland Trail Blazers",
    "JAZZ": "Utah Jazz",
    
    # Pacific Division
    "WARRIORS": "Golden State Warriors",
    "CLIPPERS": "LA Clippers",
    "LAKERS": "Los Angeles Lakers",
    "SUNS": "Phoenix Suns",
    "KINGS": "Sacramento Kings",
    
    # Southwest Division
    "MAVERICKS": "Dallas Mavericks",
    "MAVS": "Dallas Mavericks",
    "ROCKETS": "Houston Rockets",
    "GRIZZLIES": "Memphis Grizzlies",
    "PELICANS": "New Orleans Pelicans",
    "SPURS": "San Antonio Spurs",
}

# NFL Teams
NFL_TEAMS = {
    # AFC East
    "BILLS": "Buffalo Bills",
    "DOLPHINS": "Miami Dolphins",
    "PATRIOTS": "New England Patriots",
    "JETS": "New York Jets",
    
    # AFC North
    "RAVENS": "Baltimore Ravens",
    "BENGALS": "Cincinnati Bengals",
    "BROWNS": "Cleveland Browns",
    "STEELERS": "Pittsburgh Steelers",
    
    # AFC South
    "TEXANS": "Houston Texans",
    "COLTS": "Indianapolis Colts",
    "JAGUARS": "Jacksonville Jaguars",
    "TITANS": "Tennessee Titans",
    
    # AFC West
    "BRONCOS": "Denver Broncos",
    "CHIEFS": "Kansas City Chiefs",
    "RAIDERS": "Las Vegas Raiders",
    "CHARGERS": "Los Angeles Chargers",
    
    # NFC East
    "COWBOYS": "Dallas Cowboys",
    "GIANTS": "New York Giants",
    "EAGLES": "Philadelphia Eagles",
    "COMMANDERS": "Washington Commanders",
    "WASHINGTON": "Washington Commanders",
    
    # NFC North
    "BEARS": "Chicago Bears",
    "LIONS": "Detroit Lions",
    "PACKERS": "Green Bay Packers",
    "VIKINGS": "Minnesota Vikings",
    
    # NFC South
    "FALCONS": "Atlanta Falcons",
    "PANTHERS": "Carolina Panthers",
    "SAINTS": "New Orleans Saints",
    "BUCCANEERS": "Tampa Bay Buccaneers",
    "BUCS": "Tampa Bay Buccaneers",
    
    # NFC West
    "CARDINALS": "Arizona Cardinals",
    "RAMS": "Los Angeles Rams",
    "49ERS": "San Francisco 49ers",
    "NINERS": "San Francisco 49ers",
    "SEAHAWKS": "Seattle Seahawks",
}

# MLB Teams
MLB_TEAMS = {
    # AL East
    "ORIOLES": "Baltimore Orioles",
    "RED SOX": "Boston Red Sox",
    "YANKEES": "New York Yankees",
    "RAYS": "Tampa Bay Rays",
    "BLUE JAYS": "Toronto Blue Jays",
    
    # AL Central
    "WHITE SOX": "Chicago White Sox",
    "GUARDIANS": "Cleveland Guardians",
    "INDIANS": "Cleveland Guardians",  # Legacy name
    "ROYALS": "Kansas City Royals",
    "TWINS": "Minnesota Twins",
    
    # AL West
    "ASTROS": "Houston Astros",
    "ANGELS": "Los Angeles Angels",
    "ATHLETICS": "Oakland Athletics",
    "A'S": "Oakland Athletics",
    "MARINERS": "Seattle Mariners",
    "RANGERS": "Texas Rangers",
    
    # NL East
    "BRAVES": "Atlanta Braves",
    "MARLINS": "Miami Marlins",
    "METS": "New York Mets",
    "PHILLIES": "Philadelphia Phillies",
    "NATIONALS": "Washington Nationals",
    
    # NL Central
    "CUBS": "Chicago Cubs",
    "REDS": "Cincinnati Reds",
    "BREWERS": "Milwaukee Brewers",
    "PIRATES": "Pittsburgh Pirates",
    "CARDINALS": "St. Louis Cardinals",
    
    # NL West
    "DIAMONDBACKS": "Arizona Diamondbacks",
    "DBACKS": "Arizona Diamondbacks",
    "ROCKIES": "Colorado Rockies",
    "DODGERS": "Los Angeles Dodgers",
    "PADRES": "San Diego Padres",
    "GIANTS": "San Francisco Giants",
}

# NHL Teams
NHL_TEAMS = {
    # Atlantic Division
    "BRUINS": "Boston Bruins",
    "SABRES": "Buffalo Sabres",
    "RED WINGS": "Detroit Red Wings",
    "PANTHERS": "Florida Panthers",
    "CANADIENS": "Montreal Canadiens",
    "SENATORS": "Ottawa Senators",
    "LIGHTNING": "Tampa Bay Lightning",
    "MAPLE LEAFS": "Toronto Maple Leafs",
    
    # Metropolitan Division
    "HURRICANES": "Carolina Hurricanes",
    "BLUE JACKETS": "Columbus Blue Jackets",
    "DEVILS": "New Jersey Devils",
    "ISLANDERS": "New York Islanders",
    "RANGERS": "New York Rangers",
    "FLYERS": "Philadelphia Flyers",
    "PENGUINS": "Pittsburgh Penguins",
    "CAPITALS": "Washington Capitals",
    
    # Central Division
    "BLACKHAWKS": "Chicago Blackhawks",
    "AVALANCHE": "Colorado Avalanche",
    "STARS": "Dallas Stars",
    "WILD": "Minnesota Wild",
    "PREDATORS": "Nashville Predators",
    "BLUES": "St. Louis Blues",
    "JETS": "Winnipeg Jets",
    
    # Pacific Division
    "DUCKS": "Anaheim Ducks",
    "COYOTES": "Arizona Coyotes",
    "FLAMES": "Calgary Flames",
    "OILERS": "Edmonton Oilers",
    "KINGS": "Los Angeles Kings",
    "SHARKS": "San Jose Sharks",
    "KRAKEN": "Seattle Kraken",
    "CANUCKS": "Vancouver Canucks",
    "GOLDEN KNIGHTS": "Vegas Golden Knights",
}

# Soccer Teams (Major leagues)
SOCCER_TEAMS = {
    # Premier League
    "ARSENAL": "Arsenal",
    "CHELSEA": "Chelsea",
    "LIVERPOOL": "Liverpool",
    "MAN CITY": "Manchester City",
    "MANCHESTER CITY": "Manchester City",
    "MAN UTD": "Manchester United",
    "MANCHESTER UNITED": "Manchester United",
    "TOTTENHAM": "Tottenham Hotspur",
    "SPURS": "Tottenham Hotspur",
    
    # La Liga
    "BARCELONA": "Barcelona",
    "BARCA": "Barcelona",
    "REAL MADRID": "Real Madrid",
    "ATLETICO": "Atletico Madrid",
    "ATLETICO MADRID": "Atletico Madrid",
    
    # MLS (sample)
    "LAFC": "Los Angeles FC",
    "LA GALAXY": "LA Galaxy",
    "GALAXY": "LA Galaxy",
    "ATLANTA UNITED": "Atlanta United",
    "INTER MIAMI": "Inter Miami",
}

# NCAAB Teams (major programs — expand as needed)
NCAAB_TEAMS = {
    "INDIANA": "Indiana Hoosiers",
    "HOOSIERS": "Indiana Hoosiers",
    "NORTHWESTERN": "Northwestern Wildcats",
    "FLORIDA STATE": "Florida State Seminoles",
    "SEMINOLES": "Florida State Seminoles",
    "CALIFORNIA": "California Golden Bears",
    "CLEMSON": "Clemson Tigers",
    "WAKE FOREST": "Wake Forest Demon Deacons",
    "DUKE": "Duke Blue Devils",
    "NORTH CAROLINA": "North Carolina Tar Heels",
    "UNC": "North Carolina Tar Heels",
    "KENTUCKY": "Kentucky Wildcats",
    "KANSAS": "Kansas Jayhawks",
    "VILLANOVA": "Villanova Wildcats",
    "GONZAGA": "Gonzaga Bulldogs",
    "UCLA": "UCLA Bruins",
    "MICHIGAN": "Michigan Wolverines",
    "MICHIGAN STATE": "Michigan State Spartans",
    "PURDUE": "Purdue Boilermakers",
    "IOWA": "Iowa Hawkeyes",
    "IOWA STATE": "Iowa State Cyclones",
    "BAYLOR": "Baylor Bears",
    "HOUSTON": "Houston Cougars",
    "UCONN": "UConn Huskies",
    "CONNECTICUT": "UConn Huskies",
    "TENNESSEE": "Tennessee Volunteers",
    "AUBURN": "Auburn Tigers",
    "ALABAMA": "Alabama Crimson Tide",
    "ARKANSAS": "Arkansas Razorbacks",
    "OREGON": "Oregon Ducks",
    "ARIZONA": "Arizona Wildcats",
    "CREIGHTON": "Creighton Bluejays",
    "MARQUETTE": "Marquette Golden Eagles",
    "TEXAS": "Texas Longhorns",
    "WISCONSIN": "Wisconsin Badgers",
    "ILLINOIS": "Illinois Fighting Illini",
    "OHIO STATE": "Ohio State Buckeyes",
    "SYRACUSE": "Syracuse Orange",
    "LOUISVILLE": "Louisville Cardinals",
    "VIRGINIA": "Virginia Cavaliers",
    "XAVIER": "Xavier Musketeers",
    "ST JOHNS": "St. John's Red Storm",
    "ST. JOHNS": "St. John's Red Storm",
    "MEMPHIS": "Memphis Tigers",
    "COLORADO": "Colorado Buffaloes",
    "FLORIDA": "Florida Gators",
    "PITTSBURGH": "Pittsburgh Panthers",
    "MARYLAND": "Maryland Terrapins",
    "GEORGIA": "Georgia Bulldogs",
    "PENN STATE": "Penn State Nittany Lions",
    "RUTGERS": "Rutgers Scarlet Knights",
    "NEBRASKA": "Nebraska Cornhuskers",
    "MINNESOTA": "Minnesota Golden Gophers",
    "OKLAHOMA": "Oklahoma Sooners",
    "BYU": "BYU Cougars",
    "BRIGHAM YOUNG": "BYU Cougars",
    "OKLAHOMA STATE": "Oklahoma State Cowboys",
    "OKLAHOMA ST": "Oklahoma State Cowboys",
    "OKLA ST": "Oklahoma State Cowboys",
    "OKLA STATE": "Oklahoma State Cowboys",
    "BOSTON UNIVERSITY": "Boston University Terriers",
    "BOSTON UNIV": "Boston University Terriers",
    "TCU": "TCU Horned Frogs",
    "TEXAS CHRISTIAN": "TCU Horned Frogs",
    "SMU": "SMU Mustangs",
    "LIBERTY": "Liberty Flames",
    "CAL POLY": "Cal Poly Mustangs",
    "WEST VIRGINIA": "West Virginia Mountaineers",
    "WVU": "West Virginia Mountaineers",
    "BUTLER": "Butler Bulldogs",
    "DAYTON": "Dayton Flyers",
    "SETON HALL": "Seton Hall Pirates",
    "NOTRE DAME": "Notre Dame Fighting Irish",
    "WAKE": "Wake Forest Demon Deacons",
    "MSU": "Michigan State Spartans",
}

# League mapping
LEAGUE_MAP = {
    **{team: ("NBA", "Basketball") for team in NBA_TEAMS},
    **{team: ("NFL", "Football") for team in NFL_TEAMS},
    **{team: ("MLB", "Baseball") for team in MLB_TEAMS},
    **{team: ("NHL", "Hockey") for team in NHL_TEAMS},
    **{team: ("Soccer", "Soccer") for team in SOCCER_TEAMS},
    **{team: ("NCAAB", "Basketball") for team in NCAAB_TEAMS},
}

def detect_league_from_team(team_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect league and sport from team name.
    Returns (league, sport) or (None, None) if not found.
    """
    # Normalize the team name
    team_upper = team_name.upper().strip()

    if not team_upper:
        return None, None

    # Direct lookup
    if team_upper in LEAGUE_MAP:
        return LEAGUE_MAP[team_upper]
    
    # Partial match - check if any known team is in the text
    for known_team, (league, sport) in LEAGUE_MAP.items():
        if known_team in team_upper or team_upper in known_team:
            return league, sport
    
    return None, None

def get_full_team_name(team_name: str) -> Optional[str]:
    """
    Get the full official team name from a partial or abbreviated name.
    """
    team_upper = team_name.upper().strip()
    
    # Check each league's team dictionary
    for team_dict in [NBA_TEAMS, NFL_TEAMS, MLB_TEAMS, NHL_TEAMS, SOCCER_TEAMS, NCAAB_TEAMS]:
        if team_upper in team_dict:
            return team_dict[team_upper]
        
        # Partial match
        for key, full_name in team_dict.items():
            if key in team_upper or team_upper in key:
                return full_name
    
    return None
