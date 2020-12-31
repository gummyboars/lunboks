class Result(object):
  """The result types are as follows:

  Adjustment: The player's sanity, stamina, money, or clues will be changed.
  Status: The player will be blessed, cursed, a lodge member, gain a retainer, be delayed,
    be arrested, be lost in time and space, or be devoured.
  Movement: The player will be moved to another location and have an encounter there, or they
    will move to the street.
  Multi: Multiple results will be grouped together.
  Check: has a check that the player must pass. It has two sub-results: pass and fail.
    Some Check results have additional sub-results for different numbers of successes.
  Conditional: Has two sub-results, with only one having a prerequisite. If the prerequisite is
    met, then the result with the prerequisite is applied. Otherwise, the other result applies.
  Choice: the player must make a binary choice. There is one sub-result for each choice.
    Additionally, one of the sub-results may have a prerequisite. If the player does not meet
    that prerequisite, the other sub-result is automatically applied.
  """

  # RESULT_TYPES = ["Choice", "Conditional", "Check", "Multi", "Movement", "Status", "Adjustment"]
  # 
  # def __init__(self, result_type):
  #   assert result_type in RESULT_TYPES
  #   self.result_type = result_type


class Adjustment(Result):

  def __init__(self, adjustments):
    assert not self.adjustments.keys() - {"stamina", "sanity", "money", "clues"}
    self.adjustments = adjustments

  def apply(self, character):
    for key, adjustment in self.adjustments.items():
      old_val = getattr(character, key)
      new_val = old_val + adjustment
      if new_val < 0:
        new_val = 0
      # TODO: this should be a call to the character, both to allow them to override the value
      # change via special abilities, and to allow them to go insane.
      setattr(character, key, new_val)


class Status(Result):

  def __init__(self, status, positive=True):
    assert status in {"bless_curse", "retainer", "lodge_membership", "delayed", "arrested"}
    self.status = status
    self.positive = positive

  def apply(self, character):
    if self.status in {"retainer", "lodge_membership", "delayed", "arrested"}:
      setattr(character, self.status, self.positive)
      return
    if self.status == "bless_curse":
      old_val = character.bless_curse
      new_val = old_val + (1 if self.positive else -1)
      if abs(new_val) > 1:
        new_val = new_val / abs(new_val)
      character.bless_curse = new_val
      return
    raise RuntimeError("unhandled status type %s" % self.status)


class Check(Result):

  def __init__(self, check_type, modifier, success_result=None, fail_result=None, succes_map=None):
    # TODO: assert on check type
    self.check_type = check_type
    self.modifier = modifier
    # Must specify either the success map or both results.
    assert success_map or (success_result and fail_result)
    # Cannot specify both at the same time.
    assert not succes_map and (success_result or fail_result)
    if success_map:
      assert min(success_map.keys()) == 0
      self.success_map = success_map
    else:
      self.success_map[0] = fail_result
      self.success_map[1] = success_result

  def apply(self, character):
    successes, dice = character.make_check(self.check_type, self.modifier)
    for min_successes in reversed(sorted(self.success_map)):
      if successes >= min_successes:
        self.success_map[min_successes].apply(character)
        break
    else:
      raise RuntimeError("success map without result for %s: %s" % (successes, self.success_map))
