import eldritch.events as events


class MythosCard(object):

  def __init__(
      self, name, mythos_type, gate_location, clue_location, white_dimensions, black_dimensions,
      event, environment_type=None,
    ):
    assert mythos_type in {"headline", "environment", "rumor"}
    if mythos_type == "environment":
      assert environment_type in {"urban", "mystic", "weather"}
    else:
      assert environment_type is None
    self.name = name
    self.mythos_type = mythos_type
    self.gate_location = gate_location
    self.clue_location = clue_location
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions
    self.environment_type = environment_type

  def create_event(self, state):
    return events.Sequence([
      events.OpenGate(self.gate_location),
      events.SpawnClue(self.clue_location),
      # TODO: monster movement
    ])
