from age import Age
import training
import contributions
import ratings
import logging
import copy
from pprint import pprint

rating_cache = {}

def calculate_optimal_skills(starting_age: Age, target_age: Age, starting_skills: dict, position: str, sector_weights: dict, min_target_skills: dict = None, max_skills: dict = None):
    """
    Greedy one-player training optimizer.

    Parameters
    ----------
    starting_age : Age
        The starting age of the player.
    target_age : Age
        The target age of the player.
    starting_skills : dict
        A dictionary of the player's starting skills.
    position : str
        The player's position.
    sector_weights : dict
        A dictionary of weights for each sector.
    min_target_skills : dict, optional
        A dictionary of minimum target skills (default is None).
    max_skills : dict, optional
        A dictionary of maximum skill levels (default is None).

    Returns
    -------
    dict
        A dictionary of the player's optimal skills at the target age.
    dict
        A dictionary of number of training sessions per skill.
    """
    final_skills = starting_skills.copy()
    training_sessions = {skill: 0 for skill in starting_skills.keys()}
    current_age = Age(starting_age.years, starting_age.days)

    current_age, training_sessions, final_skills = get_to_minimum_skills(
            current_age, training_sessions, final_skills, min_target_skills)

    position_contributions = relevant_contributions(position)

    while current_age.to_days() < target_age.to_days():
        best_skill, best_delta, training_effect = find_best_skill(
            current_age, final_skills, sector_weights, position_contributions, position, max_skills)

        if best_skill is None:
            break

        final_skills[best_skill] += training_effect
        training_sessions[best_skill] += 1
        current_age.add_days(7)
        #logging.log(f"Age: {current_age.to_days()}, Trained: {best_skill}, Effect: {training_effect:.3f}, New Level: {final_skills[best_skill]:.3f}, Delta Rating: {best_delta:.3f}")

    return final_skills, training_sessions

def find_best_skill(current_age, current_skills, sector_weights, position_contributions, position, max_skills):
    best_skill = None
    best_delta = 0.
    training_effect = 0.

    relevant_skills = {skill for (skill, _) in position_contributions.keys()}

    for skill in relevant_skills:
        current_level = current_skills[skill]
        skill_training = training.calculate_training(
            age=current_age,
            level=current_level,
            training=skill,
            )

        new_level = current_level + skill_training
        if max_skills is not None and skill in max_skills and new_level > max_skills[skill]:
            continue

        delta_rating = 0.
        for (s, sector), _ in position_contributions.items():
            if s == skill:
                before = get_cached_rating(current_level, skill, sector, position)
                after = get_cached_rating(new_level, skill, sector, position)
                delta_rating += sector_weights[sector] * (after - before)

        #logging.log(f"Skill: {skill}, Current Level: {current_level:.3f}, Delta Rating: {delta_rating:.3f}")
        if delta_rating > best_delta:
            best_delta = delta_rating
            best_skill = skill
            training_effect = skill_training

    return best_skill, best_delta, training_effect

def get_cached_rating(skill_level, skill_type, sector, position):
    """Return cached sector rating contribution if available, otherwise compute and store it."""
    key = (round(skill_level, 3), skill_type, sector, position)
    # rounding avoids cache bloat from floating-point quirks

    if key not in rating_cache:
        rating_cache[key] = ratings.calculate_sector_rating_contribution(
            skill_level=skill_level,
            skill_type=skill_type,
            sector=sector,
            position=position,
        )
    return rating_cache[key]

def relevant_contributions(position):
    return { (skill, sector): val for (pos, skill, sector), val in contributions.contributions.items() if pos == position }

def get_to_minimum_skills(current_age, training_sessions, final_skills, min_target_skils):
    if min_target_skils is None:
        return current_age, training_sessions, final_skills
    for skill, min_level in min_target_skils.items():
        while final_skills[skill] < min_level:
            training_effect = training.calculate_training(
                age=current_age,
                level=final_skills[skill],
                training=skill,
                )
            final_skills[skill] += training_effect
            training_sessions[skill] += 1
            current_age.add_days(7)
    return current_age, training_sessions, final_skills


def main():
    age = Age(17,0)
    skills = {
        "Goalkeeping": 5.,
        "Defending": 5.,
        "Playmaking": 5.,
        "Passing": 5.,
        "Scoring": 5.,
        "Winger": 5.,
        "Set Pieces": 5.,
    }
    target_age = Age(21,60)
    sector_weights = {
            "LB": 0.9 * 1.1,
            "MB": 1.2 * 1.1,
            "RB": 0.9 * 1.1,
            "M": 3.,
            "LF": 0.9,
            "MF": 1.2,
            "RF": 0.9,
    }
    position = "LWB"
    min_target_skills = {
            "Goalkeeping": 1.,
            "Defending": 14.,
            "Playmaking": 1.,
            "Passing": 1.,
            "Scoring": 1.,
            "Winger": 1.,
            "Set Pieces": 15.,
    }
    max_skills = {
            "Goalkeeping": 22.,
            "Defending": 22.,
            "Playmaking": 22.,
            "Passing": 22.,
            "Scoring": 18.,
            "Winger": 22.,
            "Set Pieces": 22.,
    }
    final_skills, training_sessions = calculate_optimal_skills(
        starting_age=age,
        target_age=target_age,
        starting_skills=skills,
        position=position,
        sector_weights=sector_weights,
        min_target_skills=min_target_skills,
        max_skills=max_skills
    )
    pprint(final_skills)

    sector_ratings = {}

    for skill, level in final_skills.items():
        for sector in sector_weights:
            contrib = ratings.calculate_sector_rating_contribution(
                skill_level=level,
                skill_type=skill,
                sector=sector,
                position=position,
                form=1.0,
            )
            if sector in sector_ratings:
                sector_ratings[sector] += contrib / 4.
            else:
                sector_ratings[sector] = contrib / 4.

    #pprint(sector_ratings)



def best_ratings_pos():
    age = Age(17,0)
    target_age = Age(29,61)
    skills = {
        "Goalkeeping": 5.,
        "Defending": 5.,
        "Playmaking": 5.,
        "Passing": 5.,
        "Scoring": 5.,
        "Winger": 5.,
        "Set Pieces": 1.,
    }
    sector_weights = {
            "LB": 1.,
            "MB": 1.,
            "RB": 1.,
            "M": 1.,
            "LF": 1.,
            "MF": 1.,
            "RF": 1.,
    }
    max_skills = {
            "Goalkeeping": 22.,
            "Defending": 22.,
            "Playmaking": 22.,
            "Passing": 22.,
            "Scoring": 22.,
            "Winger": 22.,
            "Set Pieces": 22.,
    }
    min_target_skills = {
            "Goalkeeping": 1.,
            "Defending": 1.,
            "Playmaking": 1.,
            "Passing": 1.,
            "Scoring": 1.,
            "Winger": 1.,
            "Set Pieces": 1.,
    }
    positions = ["GK", "CD", "CDTW", "OCD", "WB", "WBO", "WBD", "WBM", "W", "WTM", "WO", "WD", "IM", "IMD", "IMO", "IMTW", "DF", "FW", "FTW"]
    ratings_dict = {}

    for position in positions:
        final_skills, training_sessions = calculate_optimal_skills(
            starting_age=age,
            target_age=target_age,
            starting_skills=skills,
            position=position,
            sector_weights=sector_weights,
            min_target_skills=min_target_skills,
            max_skills=max_skills
        )

        rating = 0.
        # compute total weighted rating contribution
        total_rating = 0.0
        for skill, level in final_skills.items():
            for sector in sector_weights:
                contrib = ratings.calculate_sector_rating_contribution(
                    skill_level=level,
                    skill_type=skill,
                    sector=sector,
                    position=position,
                    form=1.0,
                )
                total_rating += sector_weights[sector] * contrib

        ratings_dict[position] = total_rating

    print(dict(sorted(ratings_dict.items(), key=lambda item: item[1], reverse=True)))

def main3():
    starting_skills = {
            "Goalkeeping": 5.,
            "Defending": 5.,
            "Playmaking": 5.,
            "Passing": 5.,
            "Scoring": 5.,
            "Winger": 5.,
            "Set Pieces": 5.,
    }
    sector_weights = {
            "LB": 0.9 * 1.1,
            "MB": 1.2 * 1.1,
            "RB": 0.9 * 1.1,
            "M": 3.,
            "LF": 0.9,
            "MF": 1.2,
            "RF": 0.9,
    }
    players = {
            "GK" : copy.deepcopy(starting_skills),
            "LOCD" : copy.deepcopy(starting_skills),
            "RWB" : copy.deepcopy(starting_skills),
            "RWTM" : copy.deepcopy(starting_skills),
            "LWTM" : copy.deepcopy(starting_skills),
            "IM" : copy.deepcopy(starting_skills),
            "RIM" : copy.deepcopy(starting_skills),
            "LIM" : copy.deepcopy(starting_skills),
            "RFW" : copy.deepcopy(starting_skills),
            "LFW" : copy.deepcopy(starting_skills),
            "FW" : copy.deepcopy(starting_skills),
    }

    current_age = Age(17,0)
    target_age = Age(29,61)

    while current_age.to_days() < target_age.to_days():
        for position, skills in players.items():
            best_delta = 0.
            best_skill = None
            best_training = 0.
            for skill_type, skill_value in skills.items():
                training_effect = training.calculate_training(
                    age=current_age,
                    level=skill_value,
                    training=skill_type,
                )
                new_players = copy.deepcopy(players)
                new_players[position][skill_type] += training_effect
                old_ratings = ratings.calculate_team_ratings(players)
                new_ratings = ratings.calculate_team_ratings(new_players)
                old_delta = 0.
                new_delta = 0.
                for sector in sector_weights:
                    old_delta += sector_weights[sector] * old_ratings[sector]
                    new_delta += sector_weights[sector] * new_ratings[sector]
                delta = new_delta - old_delta
                if delta > best_delta:
                    best_delta = delta
                    best_skill = skill_type
                    best_training = training_effect
            players[position][best_skill] += best_training
        current_age.add_days(7)
    pprint(players)

if __name__ == "__main__":
    main()
