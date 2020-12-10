import abc
import asyncio
import collections
from http import HTTPStatus
import json
import sys
import traceback


class GameException(Exception):
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


class BaseGame(metaclass=abc.ABCMeta):

  def get_urls(self):
    return []

  def post_urls(self):
    return []

  def handle_get(self, http_handler, path, args):
    http_handler.send_error(HTTPStatus.NOT_FOUND.value, "Unknown path %s" % path)

  def handle_post(self, http_handler, path, args, data):
    http_handler.send_error(HTTPStatus.NOT_FOUND.value, "Unknown path %s" % path)

  @abc.abstractmethod
  def game_url(self, game_id):
    pass

  def game_status(self):
    return self.__class__.__name__ + " game"

  @abc.abstractmethod
  def connect_user(self):
    pass

  @abc.abstractmethod
  def disconnect_user(self):
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

  @abc.abstractclassmethod
  def parse_json(cls, data):
    return None


class GameHandler(object):

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
    valid = set(self.game.get_urls())
    valid.update(["/dump", "/save", "/json"])
    return valid

  def post_urls(self):
    valid = set(self.game.post_urls())
    valid.update(["/load"])
    return valid

  def handle_get(self, event_loop, http_handler, path, args):
    if path in ["/dump", "/save", "/json"]:
      value = self.game.json_str().encode('ascii')
      http_handler.send_response(HTTPStatus.OK.value)
      http_handler.end_headers()
      http_handler.wfile.write(value)
      return
    self.game.handle_get(http_handler, path, args)

  def handle_post(self, event_loop, http_handler, path, args, data):
    if path in ["/load"]:
      try:
        new_game = self.game_class.parse_json(data)
      except Exception as e:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        traceback.print_tb(sys.exc_info()[2])
        http_handler.send_error(HTTPStatus.BAD_REQUEST.value, str(e))
        return
      self.game = new_game
      for session in self.websockets:
        self.game.connect_user(session)
      http_handler.send_response(HTTPStatus.NO_CONTENT.value)
      http_handler.end_headers()
    else:
      self.game.handle_post(http_handler, path, args, data)
    fut = asyncio.run_coroutine_threadsafe(self.push(), event_loop)
    fut.result(10)

  async def connect_user(self, session, websocket):
    is_new_user = not self.websockets[session]
    self.websockets[session].add(websocket)
    if is_new_user:
      print("added %s to the game %s" % (session, self.game_id))
      self.game.connect_user(session)
    # Need to push, since the new connection needs data too.
    await self.push()

  async def disconnect_user(self, session, websocket):
    self.websockets[session].remove(websocket)
    if not self.websockets[session]:
      print("%s has left game %s" % (session, self.game_id))
      del self.websockets[session]
      self.game.disconnect_user(session)
      await self.push()

  async def handle(self, ws, session, raw_data):
    try:
      data = json.loads(raw_data, object_pairs_hook=collections.OrderedDict)
    except Exception as e:
      await self.push_error(ws, str(e))
      return
    try:
      self.game.handle(session, data)
    except (GameException, AssertionError) as e:
      await self.push_error(ws, str(e))
      # Intentionally fall through so that we can push the new state.
    except Exception as e:
      print(sys.exc_info()[0])
      print(sys.exc_info()[1])
      traceback.print_tb(sys.exc_info()[2])
      await self.push_error(ws, "unexpected error of type %s: %s" % (sys.exc_info()[0], sys.exc_info()[1]))
    await self.push()

  async def push(self):
    callbacks = []
    for session, ws_list in self.websockets.items():
      data = self.game.for_player(session)
      for ws in ws_list:
        callbacks.append(ws.send(data))
    await asyncio.gather(*callbacks)

  async def push_error(self, ws, e):
    await ws.send(json.dumps({"type": "error", "message": e}))
