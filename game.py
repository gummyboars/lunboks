import abc
import asyncio
import collections
import dataclasses
import enum
from http import HTTPStatus
import json
import sys
import traceback


class GameException(Exception):  # noqa: N818
  pass


class InvalidInput(GameException):
  pass


class NotYourTurn(GameException):
  pass


class UnknownMove(GameException):
  pass


class InvalidMove(GameException):
  pass


class InvalidPlayer(GameException):
  pass


class TooManyPlayers(GameException):
  pass


def ValidatePlayer(playerdata):
  if not isinstance(playerdata, dict):
    raise InvalidPlayer("Player data should be a dictionary.")
  if "name" not in playerdata:
    raise InvalidPlayer("Player data should have a name.")
  if not isinstance(playerdata["name"], str):
    raise InvalidPlayer("Player name must be a string.")
  if not playerdata["name"].strip():
    raise InvalidPlayer("Player name cannot be empty.")
  if not playerdata["name"].isprintable():
    raise InvalidPlayer("Player name must be printable.")


class CustomEncoder(json.JSONEncoder):
  def default(self, o):
    if isinstance(o, enum.Enum):
      return o.value
    if dataclasses.is_dataclass(o):
      return dataclasses.asdict(o)
    if hasattr(o, "json_repr"):
      return o.json_repr()
    return json.JSONEncoder.default(self, o)


class BaseGame(metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def game_url(self, game_id):
    pass

  def game_status(self):
    return self.__class__.__name__ + " game"

  @abc.abstractmethod
  def connect_user(self, session):
    pass

  @abc.abstractmethod
  def disconnect_user(self, session):
    pass

  @abc.abstractmethod
  def json_str(self):
    return "{}"

  @abc.abstractmethod
  def for_player(self, session):
    pass

  @abc.abstractmethod
  def handle(self, session, data):
    pass

  @classmethod
  @abc.abstractmethod
  def parse_json(cls, data):
    return None


class GameHandler:
  def __init__(self, game_id, game_class):
    self.game_id = game_id
    self.game = game_class()
    self.game_class = game_class
    self.websockets = collections.defaultdict(set)

  def game_url(self):
    return self.game.game_url(self.game_id)

  def game_status(self):
    return self.game.game_status()

  def get_urls(self):
    return {"/dump", "/save", "/json"}

  def post_urls(self):
    return {"/load"}

  def handle_get(self, event_loop, http_handler, path, args):  # pylint: disable=unused-argument
    if path not in ["/dump", "/save", "/json"]:
      http_handler.send_error(HTTPStatus.NOT_FOUND.value, f"Unknown path {path}")
      return
    value = self.game.json_str().encode("ascii")
    http_handler.send_response(HTTPStatus.OK.value)
    http_handler.end_headers()
    http_handler.wfile.write(value)

  def handle_post(self, event_loop, http_handler, path, args, data):  # pylint: disable=unused-argument
    if path not in ["/load"]:
      http_handler.send_error(HTTPStatus.NOT_FOUND.value, f"Unknown path {path}")
      return
    try:
      new_game = self.game_class.parse_json(data)
    except Exception as err:  # pylint: disable=broad-except # noqa: BLE001
      print(sys.exc_info()[0])
      print(sys.exc_info()[1])
      traceback.print_tb(sys.exc_info()[2])
      http_handler.send_error(HTTPStatus.BAD_REQUEST.value, str(err))
      return
    self.game = new_game
    for session in self.websockets:
      self.game.connect_user(session)
    http_handler.send_response(HTTPStatus.NO_CONTENT.value)
    http_handler.end_headers()
    fut = asyncio.run_coroutine_threadsafe(self.push(), event_loop)
    fut.result(10)

  async def connect_user(self, session, websocket):
    is_new_user = not self.websockets[session]
    self.websockets[session].add(websocket)
    if is_new_user:
      print(f"added {session} to the game {self.game_id}")
      self.game.connect_user(session)
    # Need to push, since the new connection needs data too.
    await self.push()

  async def disconnect_user(self, session, websocket):
    self.websockets[session].remove(websocket)
    if not self.websockets[session]:
      print(f"{session} has left game {self.game_id}")
      del self.websockets[session]
      self.game.disconnect_user(session)
      await self.push()

  async def handle(self, websocket, session, raw_data):
    try:
      data = json.loads(raw_data, object_pairs_hook=collections.OrderedDict)
    except Exception as err:  # pylint: disable=broad-except # noqa: BLE001
      await self.push_error(websocket, str(err))
      return
    pushed = False
    try:
      result = self.game.handle(session, data)
      if isinstance(result, collections.abc.Iterable):
        # TODO: investigate what happens when one of these websockets disconnects or throws an
        # error in the middle of handling this input.
        for _ in result:
          await self.push()
        # Avoid pushing the last state twice.
        pushed = True
    except (GameException, AssertionError) as err:
      if not str(err):
        await self.push_error(websocket, "Unknown error")
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        traceback.print_tb(sys.exc_info()[2])
      else:
        await self.push_error(websocket, str(err))
      # Intentionally fall through so that we can push the new state.
    except Exception:  # pylint: disable=broad-except # noqa: BLE001
      print(sys.exc_info()[0])
      print(sys.exc_info()[1])
      traceback.print_tb(sys.exc_info()[2])
      await self.push_error(
        websocket, f"unexpected error of type {sys.exc_info()[0]}: {sys.exc_info()[1]}"
      )
    if not pushed:
      await self.push()

  async def push(self):
    callbacks = []
    for session, ws_list in self.websockets.items():
      data = self.game.for_player(session)
      callbacks.extend([websocket.send(data) for websocket in ws_list])
    await asyncio.gather(*callbacks)

  async def push_error(self, websocket, err):
    await websocket.send(json.dumps({"type": "error", "message": err}))
