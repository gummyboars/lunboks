class GateCard:
  def __init__(self, name, colors, encounter_creators):
    assert "Other" in encounter_creators
    self.name = name
    self.colors = colors
    self.encounters = {}
    for world, encounter_creator in encounter_creators.items():
      self.add_encounter(world, encounter_creator)

  def add_encounter(self, world, encounter_creator):
    self.encounters[world] = encounter_creator

  def encounter_event(self, character, world_name):
    if world_name not in self.encounters:
      world_name = "Other"
    return self.encounters[world_name](character)
