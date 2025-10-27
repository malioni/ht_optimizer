import contributions

def calculate_sector_rating_contribution(skill_level: float, skill_type: str, sector: str, position: str, form: float = 1.) -> float:
    """Calculate the rating contribution of a specific skill level for a given sector and position.

    Args:
        skill_level (float): The level of the skill.
        skill_type (str): The type of skill (e.g., "Passing", "Scoring").
        sector (str): The sector for which the contribution is calculated.
        position (str): The player's position.
        form (float, optional): A multiplier representing the player's current form. Defaults to 1.0.

    Returns:
        float: The calculated rating contribution.
    """
    adjusted_skill = skill_level - 1.
    form_effect = form
    positional_factor = get_positional_factor(skill_type, sector, position)
    sector_factor = get_sector_factor(sector)

    return (adjusted_skill * form_effect * positional_factor * sector_factor)**1.2

def get_positional_factor(skill_type:str, sector: str, position: str) -> float:
    """Retrieve the positional factor for a given sector and position.

    Args:
        sector (str): The sector for which the factor is retrieved.
        position (str): The player's position.

    Returns:
        float: The positional factor.
    """
    return contributions.contributions.get((position, skill_type, sector), 0.)

def get_sector_factor(sector: str) -> float:
    """Retrieve the sector factor for a given sector.

    Args:
        sector (str): The sector for which the factor is retrieved.

    Returns:
        float: The sector factor.
    """
    if sector == "MB":
        return 0.6716368
    elif sector == "RB" or sector == "LB":
        return 0.78204
    elif sector == "M":
        return 1. 
    elif sector == "MF" or sector == "RF" or sector == "LF":
        return 0.628456
    return 0.
    
def calculate_team_ratings(players: dict[str, dict]) -> dict[str, float]:
    """Calculate the overall team ratings based on individual player contributions.

    Args:
        players (dict[str, dict]): A dictionary where keys are player names and values are dictionaries containing player attributes.

    Returns:
        dict[str, float]: A dictionary with overall team ratings for each sector.
    """
    team_ratings = {
        "LB": 0.,
        "MB": 0.,
        "RB": 0.,
        "M": 0.,
        "LF": 0.,
        "MF": 0.,
        "RF": 0.,
    }

    overcrowding = {
        "IM": 0,
        "CD": 0,
        "FW": 0,
    }

    for player in players.keys():
        if "IM" in player:
            overcrowding["IM"] += 1
        elif "CD" in player:
            overcrowding["CD"] += 1 
        elif "FW" in player or "FTW" in player or "DF" in player:
            overcrowding["FW"] += 1

    for sector in team_ratings.keys():
        rating = 0.
        sector_factor = get_sector_factor(sector)
        for position, skills in players.items():
            overcrowding_factor = get_overcowding_factor(position, overcrowding)
            for skill_type, skill_value in skills.items():
                adjusted_skill = skill_value - 1.
                positional_factor = get_positional_factor(skill_type, sector, position)
                rating += (adjusted_skill * positional_factor * sector_factor * overcrowding_factor)
        team_ratings[sector] = rating**1.2 / 4. + 1.
    
    return team_ratings

def get_overcowding_factor(position: str, overcrowding: dict[str, int]) -> float:
    """Calculate the overcrowding factor for a given position.

    Args:
        position (str): The player's position.
        overcrowding (dict[str, int]): A dictionary with counts of players in key positions.

    Returns:
        float: The overcrowding factor.
    """
    if "IM" in position:
        return get_im_overcrowding_factor(overcrowding["IM"])
    elif "CD" in position:
        return get_cd_overcrowding_factor(overcrowding["CD"])
    elif ("FW" in position or "FTW" in position or "DF" in position):
        return get_fw_overcrowding_factor(overcrowding["FW"])
    return 1.

def get_im_overcrowding_factor(count: int) -> float:
    if count == 3:
        return 0.8 
    elif count == 2:
        return 0.91 
    else:
        return 1.

def get_cd_overcrowding_factor(count: int) -> float:
    if count <= 3:
        return 0.88 
    elif count == 2:
        return 0.95 
    else:
        return 1.

def get_fw_overcrowding_factor(count: int) -> float:
    if count == 3:
        return 0.84 
    elif count == 2:
        return 0.93 
    else:
        return 1.
