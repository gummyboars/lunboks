class InvalidMove(Exception):
  pass


class InvalidPlayer(Exception):
  pass


class TooManyPlayers(Exception):
  pass


def ValidatePlayer(playerdata):
  if not isinstance(playerdata, dict):
    raise InvalidPlayer("Player data should be a dictionary.")
  if "name" not in playerdata:
    raise InvalidPlayer("Player data should have a name.")
  if not playerdata["name"].strip():
    raise InvalidPlayer("Player name cannot be empty.")
  if not playerdata["name"].isprintable():
    raise InvalidPlayer("Player name must be printable.")
