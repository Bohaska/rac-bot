import random
import enum
from functools import total_ordering

"""
An exact implementation of http://scoresim.ilya.online
"""


@total_ordering
class OrderedEnum(enum.Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented


def random_picker(weights):
    total_weight = sum(weights.values())
    random_value = random.uniform(0, total_weight)

    cumulative_weight = 0
    for item, weight in weights.items():
        cumulative_weight += weight
        if random_value <= cumulative_weight:
            return item


class PlayerPosition(OrderedEnum):
    GOALKEEPER = 1
    DEFENDER = 2
    MIDFIELDER = 3
    FORWARD = 4


class CardColour(OrderedEnum):
    YELLOW = 1
    RED = 2


class Half(OrderedEnum):
    FIRST_HALF = 1
    SECOND_HALF = 2
    EXTRA_TIME = 3
    PENALTIES = 4
    MATCH_END = 5

@total_ordering
class Time:
    __slots__ = ("half", "minute", "time_added_h1", "time_added_h2")

    def __init__(self, half: Half, minute: int):
        self.minute = minute
        self.time_added_h1 = None  # ignore added time for now
        self.time_added_h2 = None
        self.half = half

    def __str__(self):
        if self.half == Half.FIRST_HALF:
            if self.minute > 45:
                return f"45+{self.minute - 45}'"
            else:
                return str(self.minute) + "'"
        elif self.half == Half.SECOND_HALF:
            if self.minute > 90:
                return f"90+{self.minute - 90}'"
            else:
                return str(self.minute) + "'"
        elif self.half == Half.EXTRA_TIME:
            if self.minute > 120:
                return f"120+{self.minute - 120}'"
            else:
                return str(self.minute) + "'"
        elif self.half == Half.MATCH_END:
            return str(self.minute) + "'"

    def __eq__(self, other):
        return self.half == other.half and self.minute == other.minute

    def __gt__(self, other):
        if not self.half == other.half:
            return self.half > other.half
        else:
            return self.minute > other.minute


class Shot:
    __slots__ = ("player", "time", "on_target", "goal", "team", "penalty", "assister", "blocker")

    def __init__(self, player: str, time: Time, on_target: bool, goal: bool, team: str, penalty: bool = None, assister: str = None, blocker: str = None):
        self.player = player
        self.time = time
        self.on_target = on_target
        self.goal = goal
        self.team = team
        self.penalty = False if penalty is None else penalty
        self.assister = assister
        self.blocker = blocker


class Card:
    __slots__ = ("player", "colour", "time", "team")

    def __init__(self, player, colour: CardColour, time: Time, team: str):
        self.player = player
        self.colour = colour
        self.time = time
        self.team = team


class Player:
    __slots__ = ("name", "goals", "yellow_card", "red_card", "position")

    def __init__(self, name: str, position: PlayerPosition):
        self.name = name
        self.goals = 0
        self.yellow_card = None
        self.red_card = None
        self.position = position


class TeamIdentifier(enum.Enum):
    TEAM_1 = 1
    TEAM_2 = 2


class Team:
    __slots__ = ("name", "players", "goals", "relative_strength", "shot_accuracy", "possession", "potential_fouls",
                 "potential_shots", "tactic", "morale", "crowd_support", "fouls", "sent_off_players", "shots",
                 "shots_on_target", "goal_objects", "cards", "shootout_goals", "penalty_objects", "first_leg_goals")

    TACTICS = {"Very defensive": 0.6, "Defensive": 0.8, "Balanced": 1, "Attacking (recommended)": 1.2,
               "Very attacking": 1.4}
    MORALES = {"Extremely low": 0, "Very low": 1, "Low": 2, "Average": 3, "High": 4, "Very high": 5, "Extremely high": 6}
    CROWD_SUPPORTS = {"No support": 0, "Weak support": 2, "Average support": 3, "Good support": 4, "Great Support": 6,
                      "Outstanding support": 8, "Away team (no support)": 0}
    STRENGTHS = {
        "Team 1 much weaker than Team 2": 30,
        "Team 1 weaker than Team 2": 40,
        "Team 1 a bit weaker than Team 2": 45,
        "Team 1 and Team 2 equal in class": 50,
        "Team 1 a bit stronger than Team 2": 55,
        "Team 1 stronger than Team 2": 60,
        "Team 1 much stronger than Team 2": 70,
    }

    def __init__(self, name: str, players: list[Player], goals: int = None, relative_strength: int = None,
                 tactic: str = None,
                 opponent_tactic: str = None, morale: str = None, crowd_support=None):
        self.name = name
        self.players = players
        self.first_leg_goals = goals
        self.goals = 0 if goals is None else goals
        self.shootout_goals = 0
        self.relative_strength = 50 if relative_strength is None else relative_strength
        self.relative_strength += round((random.random() - self.relative_strength / 100) * 10)
        # self.shot_accuracy = random.random() * 0.4 + 0.1 Original
        self.shot_accuracy = random.random() * 0.25 + 0.3
        self.possession = 50
        self.potential_fouls = round(round(20 + random.random() * 7) * relative_strength / 100)
        tactic = "Balanced" if tactic is None else tactic
        self.tactic = self.TACTICS[tactic]
        opponent_tactic = "Balanced" if opponent_tactic is None else opponent_tactic
        opponent_tactic = self.TACTICS[opponent_tactic]
        if self.tactic > opponent_tactic:
            self.potential_shots = 8 * (self.tactic + opponent_tactic)
        elif self.tactic == opponent_tactic:
            if self.tactic >= 1:
                self.potential_shots = 12 * (self.tactic + opponent_tactic)
            if self.tactic < 1:
                self.potential_shots = 8 * (self.tactic + opponent_tactic)
        elif self.tactic < opponent_tactic:
            self.potential_shots = 6 * (self.tactic + opponent_tactic)
        print(self.potential_shots)
        morale = "Average" if morale is None else morale
        self.morale = self.MORALES[morale]
        crowd_support = "No support" if crowd_support is None else crowd_support
        self.crowd_support = self.CROWD_SUPPORTS[crowd_support]
        self.relative_strength += self.crowd_support
        if self.relative_strength < 60 and opponent_tactic < 1:
            self.potential_shots *= opponent_tactic * max(self.relative_strength, 25) / 50
        self.potential_shots = round(
            self.potential_shots * ((self.relative_strength + self.morale + self.crowd_support) * 1.2 - 20) / 90) + 3
        print(self.potential_shots)
        self.fouls = 0
        self.shots = 0
        self.shots_on_target = 0
        self.sent_off_players = []
        self.goal_objects = []
        self.penalty_objects = []
        self.cards = []


def possession_change(team_1: Team, team_2: Team):
    possession_adjust = 0
    if team_1.relative_strength < team_2.relative_strength:
        if team_1.relative_strength <= 40:
            possession_adjust = random.random() * 5
        elif team_1.relative_strength >= 45:
            possession_adjust = random.random() * 3
    elif team_1.relative_strength > team_2.relative_strength:
        if team_2.relative_strength <= 40:
            possession_adjust = random.random() * -5
        elif team_2.relative_strength >= 45:
            # This is the original code, where possession is for some reason not symmetrical
            # possession_adjust = random.random() * -2
            possession_adjust = random.random() * -3
    morale_from_possession = random.random() * 0.02
    if random.random() < (team_1.relative_strength + possession_adjust) / 100:
        if abs(team_1.possession - team_2.possession) > 20:
            team_1.possession = team_1.possession + round(random.random() * 0.75)
        else:
            team_1.possession = team_1.possession + round(random.random() * 1.4)
        team_1.morale += morale_from_possession
        team_2.morale -= morale_from_possession
        team_2.possession = 100 - team_1.possession
    else:
        if abs(team_1.possession - team_2.possession) > 20:
            team_2.possession = team_2.possession + round(random.random() * 0.75)
        else:
            team_2.possession = team_2.possession + round(random.random() * 1.4)
        team_2.morale += morale_from_possession
        team_1.morale -= morale_from_possession
        team_1.possession = 100 - team_2.possession
    # extreme cases
    if team_1.possession - team_2.possession > 70:
        team_1.possession = 85
        team_2.possession = 15
    elif team_2.possession - team_1.possession > 70:
        team_2.possession = 85
        team_1.possession = 15
    return team_1, team_2


def foul_change(team_1: Team, team_2: Team, half: Half, minute: int, minute_events: list):
    factor = 2 if half == Half.EXTRA_TIME else 1  # double events during extra time
    team_1_foul = team_1.potential_fouls / 90 * factor - random.random()
    team_2_foul = team_2.potential_fouls / 90 * factor - random.random()
    if team_1_foul > 0 and team_1_foul > team_2_foul:
        team_1.fouls += 1
        # Yellow card
        if random.random() < 1 / 7:
            bad_player = random.randint(0, len(team_1.players) - 1)
            if team_1.players[bad_player].yellow_card:
                if random.random() < 0.66:
                    bad_player = random.randint(0, len(team_1.players) - 1)
            yellow_card = Card(team_1.players[bad_player].name, CardColour.YELLOW, Time(half, minute), team_1.name)
            red_card = Card(team_1.players[bad_player].name, CardColour.RED, Time(half, minute), team_1.name)
            # Is it a second yellow?
            print(f"{team_1.players[bad_player].name} {str(team_1.players[bad_player].yellow_card)} {minute}")
            if team_1.players[bad_player].yellow_card:
                team_1.cards.append(yellow_card)
                team_1.cards.append(red_card)
                minute_events.append(yellow_card)
                minute_events.append(red_card)
                team_1.sent_off_players.append(team_1.players[bad_player])
                del team_1.players[bad_player]
                # Decrease relative strength due to man disadvantage
                team_1.relative_strength *= 0.91
                # Morale changes
                if random.random() > 0.5:
                    team_1.morale *= 0.85
                else:
                    team_1.morale *= 1.15
            else:
                team_1.players[bad_player].yellow_card = yellow_card
                team_1.cards.append(yellow_card)
                minute_events.append(yellow_card)
        # Red card
        elif random.random() < 1 / 500:
            bad_player = random.randint(0, len(team_1.players) - 1)
            red_card = Card(team_1.players[bad_player].name, CardColour.RED, Time(half, minute), team_1.name)
            team_1.cards.append(red_card)
            minute_events.append(red_card)
            team_1.sent_off_players.append(team_1.players[bad_player])
            del team_1.players[bad_player]
            # Decrease relative strength due to man disadvantage
            team_1.relative_strength *= 0.91
            # Morale changes
            if random.random() > 0.5:
                team_1.morale *= 0.8
            else:
                team_1.morale *= 1.2
    # Team 2
    if team_2_foul > 0 and team_2_foul > team_1_foul:
        team_2.fouls += 1
        # Yellow card
        if random.random() < 1 / 7:
            bad_player = random.randint(0, len(team_2.players) - 1)
            if team_2.players[bad_player].yellow_card:
                if random.random() < 0.66:
                    bad_player = random.randint(0, len(team_2.players) - 1)
            # Is it a second yellow?
            yellow_card = Card(team_2.players[bad_player].name, CardColour.YELLOW, Time(half, minute), team_2.name)
            red_card = Card(team_2.players[bad_player].name, CardColour.RED, Time(half, minute), team_2.name)
            print(f"{team_2.players[bad_player].name} {str(team_2.players[bad_player].yellow_card)} {minute}")
            if team_2.players[bad_player].yellow_card:
                team_2.cards.append(yellow_card)
                team_2.cards.append(red_card)
                minute_events.append(yellow_card)
                minute_events.append(red_card)
                team_2.sent_off_players.append(team_2.players[bad_player])
                del team_2.players[bad_player]
                # Decrease relative strength due to man disadvantage
                team_2.relative_strength *= 0.91
                # Morale changes
                if random.random() > 0.5:
                    team_2.morale *= 0.85
                else:
                    team_2.morale *= 1.15
            else:
                team_2.players[bad_player].yellow_card = yellow_card
                team_2.cards.append(yellow_card)
                minute_events.append(yellow_card)
        # Red card
        elif random.random() < 1 / 500:
            bad_player = random.randint(0, len(team_2.players) - 1)
            red_card = Card(team_2.players[bad_player].name, CardColour.RED, Time(half, minute), team_2.name)
            team_2.cards.append(red_card)
            minute_events.append(red_card)
            team_2.sent_off_players.append(team_2.players[bad_player])
            del team_2.players[bad_player]
            # Decrease relative strength due to man disadvantage
            team_2.relative_strength *= 0.91
            # Morale changes
            if random.random() > 0.5:
                team_2.morale *= 0.8
            else:
                team_2.morale *= 1.2
    return team_1, team_2, minute_events


def goal_scorer(team: Team):
    weights = {
        PlayerPosition.FORWARD: 0.6,
        PlayerPosition.MIDFIELDER: 0.35,
        PlayerPosition.DEFENDER: 0.05,
    }
    player_position = random_picker(weights)
    valid_players = [index for index, scorer in enumerate(team.players) if scorer.position == player_position]
    if valid_players:
        player = random.choice(valid_players)
    else:
        player = random.randint(0, len(team.players) - 1)
    return player


def assist_player(team: Team, scorer: int):
    weights = {
        PlayerPosition.FORWARD: 0.43,
        PlayerPosition.MIDFIELDER: 0.35,
        PlayerPosition.DEFENDER: 0.1,
        PlayerPosition.GOALKEEPER: 0.02,
        None: 0.1
    }
    player_position = random_picker(weights)
    valid_players = [index for index, scorer in enumerate(team.players) if scorer.position == player_position]
    try:
        valid_players.remove(scorer)
    except ValueError:
        pass
    if valid_players:
        player = random.choice(valid_players)
    else:
        player = random.randint(0, len(team.players) - 1)
    if not scorer == player:
        return player
    else:
        return


def block_player(team: Team):
    weights = {
        PlayerPosition.FORWARD: 0.05,
        PlayerPosition.MIDFIELDER: 0.15,
        PlayerPosition.DEFENDER: 0.80,
    }
    player_position = random_picker(weights)
    valid_players = [index for index, scorer in enumerate(team.players) if scorer.position == player_position]
    if valid_players:
        player = random.choice(valid_players)
    else:
        player = random.randint(0, len(team.players) - 1)
    return player


def goal_change(team_1: Team, team_2: Team, half: Half, minute: int, minute_events: list):
    #  Did they get a shot?
    factor = 2 if half == Half.EXTRA_TIME else 1  # double events during extra time
    team_1_shot = team_1.potential_shots / 90 * factor - random.random()
    team_2_shot = team_2.potential_shots / 90 * factor - random.random()
    if team_1_shot > 0 and team_1_shot > team_2_shot:
        team_1.shots += 1
        player = goal_scorer(team_1)
        assister = assist_player(team_1, player)
        if assister is not None:
            assister = team_1.players[assister].name
        #  Was it on target?
        if random.random() < team_1.shot_accuracy:
            team_1.shots_on_target += 1
            team_1.morale += 0.2
            #  Was it a goal?
            goal_chance = (team_1.relative_strength + team_1.morale * 2 + team_1.crowd_support) / 100 / (
                        1.5 + random.random())
            if random.random() < goal_chance:
                #  Congratulations!
                shot = Shot(team_1.players[player].name, Time(half, minute), on_target=True, goal=True,
                            team=team_1.name, assister=assister)
                team_1.goals += 1
                team_1.goal_objects.append(shot)
                minute_events.append(shot)
                team_1.players[player].goals += 1
                team_1.morale += 1
            else:
                shot = Shot(team_1.players[player].name, Time(half, minute), on_target=True, goal=False,
                            team=team_1.name, assister=assister)
                minute_events.append(shot)
        else:
            blocker = team_2.players[block_player(team_2)].name
            shot = Shot(team_1.players[player].name, Time(half, minute), on_target=False, goal=False,
                        team=team_1.name, assister=assister, blocker=blocker)
            minute_events.append(shot)
    elif team_2_shot > 0 and team_2_shot > team_1_shot:
        team_2.shots += 1
        player = goal_scorer(team_2)
        assister = assist_player(team_2, player)
        if assister is not None:
            assister = team_2.players[assister].name
        #  Was it on target?
        if random.random() < team_2.shot_accuracy:
            team_2.shots_on_target += 1
            team_2.morale += 0.2
            #  Was it a goal?
            goal_chance = (team_2.relative_strength + team_2.morale * 2 + team_2.crowd_support) / 100 / (
                        1.5 + random.random())
            if random.random() < goal_chance:
                #  Congratulations!
                shot = Shot(team_2.players[player].name, Time(half, minute), on_target=True, goal=True,
                            team=team_2.name, assister=assister)
                team_2.goals += 1
                team_2.goal_objects.append(shot)
                minute_events.append(shot)
                team_2.players[player].goals += 1
                team_2.morale += 1
            else:
                shot = Shot(team_2.players[player].name, Time(half, minute), on_target=True, goal=False,
                            team=team_2.name, assister=assister)
                minute_events.append(shot)
        else:
            blocker = team_1.players[block_player(team_1)].name
            shot = Shot(team_2.players[player].name, Time(half, minute), on_target=False, goal=False,
                        team=team_2.name, assister=assister, blocker=blocker)
            minute_events.append(shot)
    return team_1, team_2, minute_events


def new_minute(team_1: Team, team_2: Team, half: Half, minute: int, extra_time: bool = None):
    """Simulates a minute of football"""
    minute_events = []
    # 1. Possession changes
    team_1, team_2 = possession_change(team_1, team_2)
    # 2. Fouls
    team_1, team_2, minute_events = foul_change(team_1, team_2, half, minute, minute_events)
    # 3. Goals
    team_1, team_2, minute_events = goal_change(team_1, team_2, half, minute, minute_events)
    if minute == 45 and half == Half.FIRST_HALF:
        half = Half.SECOND_HALF
    if minute == 90 and half == Half.SECOND_HALF:
        if extra_time is True and team_1.goals == team_2.goals:
            half = Half.EXTRA_TIME
        else:
            half = Half.MATCH_END
    if minute == 120 and half == Half.EXTRA_TIME:
        half = Half.MATCH_END
    return team_1, team_2, half, minute_events


def penalty_winner(team_1_goals, team_2_goals, penalty_turn, team_shooting):
    penalty_turn += 1
    if penalty_turn <= 5:
        if team_shooting == TeamIdentifier.TEAM_1:
            team_1_chances = 5 - penalty_turn
            team_2_chances = 5 - penalty_turn + 1
            if team_1_goals + team_1_chances < team_2_goals:
                return TeamIdentifier.TEAM_2
            elif team_2_goals + team_2_chances < team_1_goals:
                return TeamIdentifier.TEAM_1
        if team_shooting == TeamIdentifier.TEAM_2:
            chances = 5 - penalty_turn
            if team_2_goals + chances < team_1_goals:
                return TeamIdentifier.TEAM_1
            elif team_1_goals + chances < team_2_goals:
                return TeamIdentifier.TEAM_2
    else:
        if team_shooting == TeamIdentifier.TEAM_2:
            if team_2_goals < team_1_goals:
                return TeamIdentifier.TEAM_1
            elif team_1_goals < team_2_goals:
                return TeamIdentifier.TEAM_2
    return False


async def penalty_shootout(team_1: Team, team_2: Team):
    team_1_players = team_1.players
    team_2_players = team_2.players
    team_1_players.sort(key=lambda player: player.position, reverse=True)
    team_2_players.sort(key=lambda player: player.position, reverse=True)
    if len(team_1_players) > len(team_2_players):
        team_1_players = team_1_players[:len(team_2_players)-len(team_1_players)]
    elif len(team_1_players) < len(team_2_players):
        team_2_players = team_2_players[:len(team_1_players)-len(team_2_players)]
    shootout_winner = False
    team_shooting = TeamIdentifier.TEAM_1
    penalty_turn = 0
    while not shootout_winner:
        player = penalty_turn % len(team_1_players)
        penalty_scored = random.random() < 0.75
        if team_shooting == TeamIdentifier.TEAM_1:
            penalty_shot = Shot(
                team_1_players[player].name,
                Time(Half.PENALTIES, penalty_turn),
                True,
                penalty_scored,
                team_1.name,
                penalty=True
            )
            team_1.penalty_objects.append(penalty_shot)
            if penalty_scored:
                team_1.shootout_goals += 1
        elif team_shooting == TeamIdentifier.TEAM_2:
            penalty_shot = Shot(
                team_2_players[player].name,
                Time(Half.PENALTIES, penalty_turn),
                True,
                penalty_scored,
                team_2.name,
                penalty=True
            )
            team_2.penalty_objects.append(penalty_shot)
            if penalty_scored:
                team_2.shootout_goals += 1
        yield penalty_shot, team_1, team_2
        shootout_winner = penalty_winner(team_1.shootout_goals, team_2.shootout_goals, penalty_turn, team_shooting)
        if not shootout_winner:
            if team_shooting == TeamIdentifier.TEAM_1:
                team_shooting = TeamIdentifier.TEAM_2
            elif team_shooting == TeamIdentifier.TEAM_2:
                team_shooting = TeamIdentifier.TEAM_1
                penalty_turn += 1


async def start_match(team_1: Team, team_2: Team, extra_time: bool = None, penalties: bool = None):
    minute = 1
    half = Half.FIRST_HALF
    extra_time = False if extra_time is None else extra_time
    penalties = False if penalties is None else penalties
    for player in team_1.players:
        print(f"{player.name}, {player.yellow_card}")
    for player in team_2.players:
        print(f"{player.name}, {player.yellow_card}")
    while not half == Half.MATCH_END:
        team_1, team_2, half, minute_events = new_minute(team_1, team_2, half, minute, extra_time)
        yield team_1, team_2, Time(half, minute), minute_events
        minute += 1


def default_players():
    return [
        Player("Goalkeeper", PlayerPosition.GOALKEEPER),
        Player("Defender1", PlayerPosition.DEFENDER),
        Player("Defender2", PlayerPosition.DEFENDER),
        Player("Defender3", PlayerPosition.DEFENDER),
        Player("Defender4", PlayerPosition.DEFENDER),
        Player("Midfielder1", PlayerPosition.MIDFIELDER),
        Player("Midfielder2", PlayerPosition.MIDFIELDER),
        Player("Midfielder3", PlayerPosition.MIDFIELDER),
        Player("Midfielder4", PlayerPosition.MIDFIELDER),
        Player("Forward1", PlayerPosition.FORWARD),
        Player("Forward2", PlayerPosition.FORWARD),
    ]
