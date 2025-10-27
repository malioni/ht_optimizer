import math
from age import Age
import logging

def calculate_training(age, level, training, coach=5, assistant=10, intensity=100, stamina=10, minutes=90):
    """
    Calculate the training effect based on various parameters.

    Parameters
    ----------
    age : Age
        Player's age.
    level : float
        The current level of the player skill.
    training : string 
        Type of training
    coach : int
        Level of the head coach (1-5).
    assistant : int
        Level of the assistant coaches (0-10).
    intensity : int
        The intensity of the training as percentage.
    stamina : int
        Stamina portion of training as percentage.
    minutes : int 
        Minutes the player played in the trainable position.

    Returns
    -------
    float
        The calculated training effect.
    """
    adj_level = level - 1
    f_lvl = level_factor(adj_level)
    K_coach = coach_factor(coach)
    K_assistant = assistant_factor(assistant)
    K_intensity = intensity / 100.0
    K_stamina = 1 - stamina / 100.0
    K_training = training_factor(training)
    K_age = age_factor(age.get_age())
    K_time = minutes / 90.0
    #logging.log(f"Factors - Level: {f_lvl:.4f}, Coach: {K_coach:.4f}, Assistant: {K_assistant:.4f}, Intensity: {K_intensity:.4f}, Stamina: {K_stamina:.4f}, Training: {K_training:.4f}, Age: {K_age:.4f}, Time: {K_time:.4f}")

    training_amount = f_lvl * K_coach * K_assistant * K_intensity * K_stamina * K_training * K_age * K_time
    # logging.log(f"Pre-drop Training Amount: {training_amount:.4f}")
    training_drop = get_training_level_drop(adj_level)
    if training_drop > training_amount:
        return 0.
    # logging.log(f"Skill: {training}, Level: {level:.2f}, Age: {age.years}.{age.days}, Final: {training_amount - training_drop:.4f}")
    return training_amount - training_drop

def get_training_level_drop(level):
    if level < 14:
        return 0.
    if level > 20:
        level += 0.39
    a = 0.000006111
    b = 0.000808
    c = -0.026017
    d = 0.192775
    return a * level**3 + b * level**2 + c * level + d


def level_factor(level):
    if level < 9:
        return level_factor_under_9(level)
    else:
        return level_factor_over_9(level)

def level_factor_under_9(level):
    return 16.289 * (math.e ** (-0.1396 * level))

def level_factor_over_9(level):
    if level == 0:
        return 0.
    return 54.676 / level - 1.438

def coach_factor(coach):
    if coach == 1:
        return 0.7343
    elif coach == 2:
        return 0.8324
    elif coach == 3:
        return 0.9200
    elif coach == 4:
        return 1.000
    elif coach ==5:
        return 1.0375
    else:
        return 0

def assistant_factor(assistant):
    return 1 + 0.035 * assistant

def training_factor(training):
    if training == "Goalkeeping":
        return 0.0510
    elif training == "Defending":
        return 0.0288 
    elif training == "Playmaking":
        return 0.0336
    elif training == "Winger":
        return 0.048
    elif training == "Passing":
        return 0.036
    elif training == "Scoring":
        return 0.0324
    elif training == "Set Pieces":
        return 0.147
    else:
        return 0.

def age_factor(age):
    return 54 / (age + 37.)
