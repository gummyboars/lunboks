from enum import Enum


class Resource(str, Enum):
  COAL = "coal"
  OIL = "oil"
  GAS = "gas"
  URANIUM = "uranium"
  GREEN = "green"
  HYBRID = "hybrid"
