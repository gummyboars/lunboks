from eldritch.mythos import base
from eldritch.mythos import core


def CreateMythos(expansions):  # pylint: disable=unused-argument
  return base.CreateMythos() + [core.ShuffleMythos()]
