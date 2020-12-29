#!/usr/bin/env python3

import argparse
import asyncio
from http import HTTPStatus
from http.server import HTTPServer,BaseHTTPRequestHandler
import json
import os
import random
from socketserver import ThreadingMixIn
import string
import threading
import urllib
import uuid
import websockets

import catan
import game as game_handler


ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
GLOBAL_LOOP = asyncio.get_event_loop()
GLOBAL_WS_SERVER = None
INDEX_WEBSOCKETS = set()
GAMES = {}
GAME_TYPES = {"catan": catan.CatanGame}
# Check to make sure abstract base classes are satisfied.
[game_class() for game_class in GAME_TYPES.values()]


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
  pass


class MyHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    parsed_url = urllib.parse.urlparse(self.path)
    path = parsed_url.path
    args = urllib.parse.parse_qs(parsed_url.query)
    game_id_arg = args.get("game_id", [])
    game = GAMES.get(game_id_arg[0]) if game_id_arg else None

    if game_id_arg and not game:
      self.send_error(HTTPStatus.BAD_REQUEST.value, "Unknown game_id %s" % game_id_arg[0])
      return
    if game and path.rstrip("/") in game.get_urls():
      game.handle_get(GLOBAL_LOOP, self, path.rstrip("/"), args)
      return

    if path == "/":
      filepath = "/".join([ROOT_DIR, "index.html"])
    else:
      filepath = "/".join([ROOT_DIR, path])
    filepath = os.path.abspath(filepath)
    if os.path.dirname(filepath) != ROOT_DIR:
      print("dirname is %s but root is %s" % (os.path.dirname(filepath), ROOT_DIR))
      self.send_error(HTTPStatus.FORBIDDEN.value, "Access to %s forbidden" % path)
      return
    if not os.path.exists(filepath):
      self.send_error(HTTPStatus.NOT_FOUND.value, "File %s not found" % path)
      return

    self.send_response(HTTPStatus.OK.value)

    session = None
    cookie_str = self.headers["Cookie"]
    if cookie_str:
      cookies = dict([x.strip().split("=", 1) for x in cookie_str.split(";")])
      session = cookies.get("session")
      try:
        uuid.UUID(session)
      except (TypeError, ValueError):
        session = None
    if not session:
      new_session = "session=%s" % (uuid.uuid4())
      self.send_header("Set-Cookie", new_session)
      print("setting session cookie %s" % new_session)
    if filepath.endswith(".jpg") or filepath.endswith(".jpeg") or filepath.endswith(".png"):
      self.send_header("Cache-Control", "public, max-age=604800")

    self.end_headers()

    with open(filepath, 'rb') as w:
      self.wfile.write(w.read())

  def do_POST(self):
    parsed_url = urllib.parse.urlparse(self.path)
    path = parsed_url.path
    args = urllib.parse.parse_qs(parsed_url.query)
    data = b""
    if self.headers["content-length"]:
      data = self.rfile.read(int(self.headers["content-length"]))

    if path.rstrip("/") == "/new":
      # TODO: extract a content encoding from content-type header.
      CreateGame(self, urllib.parse.parse_qs(data.decode("ascii", "strict")))
      return

    game_id_arg = args.get("game_id", [])
    if not game_id_arg:
      self.send_error(HTTPStatus.BAD_REQUEST.value, "Missing required param game_id")
      return

    game = GAMES.get(game_id_arg[0])
    if not game:
      self.send_error(HTTPStatus.BAD_REQUEST.value, "Game not found: %s" % game_id_arg[0])
      return

    if path.rstrip("/") not in game.post_urls():
      self.send_error(HTTPStatus.NOT_FOUND.value, "Unknown path %s" % path)
      return

    game.handle_post(GLOBAL_LOOP, self, path.rstrip("/"), args, data)


def CreateGame(http_handler, data):
  if not data.get("type"):
    http_handler.send_error(HTTPStatus.BAD_REQUEST.value, "Missing game type")
    return
  game_type = data.get("type")[0]
  if game_type not in GAME_TYPES:
    http_handler.send_error(HTTPStatus.BAD_REQUEST.value, f"Unknown game type {game_type}")
    return
  generated_id = GenerateId(2)
  if not generated_id:
    http_handler.send_error(
        HTTPStatus.INTERNAL_SERVER_ERROR, "no unique game ids left. probably. i didn't try very hard")
    return
  GAMES[generated_id] = game_handler.GameHandler(generated_id, GAME_TYPES[game_type])
  http_handler.send_response(301)
  http_handler.send_header('Location', GAMES[generated_id].game_url())
  http_handler.end_headers()
  print("Created new game of type %s with id %s" % (game_type, generated_id))


def GenerateId(length):
  generated = None
  for attempt in range(5):
    chars = []
    for x in range(length):
      chars.append(random.choice(string.ascii_lowercase))
    generated = "".join(chars)
    # TODO: concurrency
    if generated not in GAMES:
      return generated
  return None


async def PushError(ws, e):
  await ws.send(json.dumps({"type": "error", "message": e}))


async def HandleWebsocket(websocket, path):
  game_id = path.rstrip("/").lstrip("/")
  if game_id == "":
    await SendGames(websocket)
    return
  game = GAMES.get(game_id)
  if game is None:
    await PushError(websocket, f"Unknown game {game_id}")
    return
  # TODO: possible cross-site request forgery of websocket data
  # https://christian-schneider.net/CrossSiteWebSocketHijacking.html
  cookie_str = websocket.request_headers["Cookie"]
  cookies = dict([x.strip().split("=", 1) for x in cookie_str.split(";")])
  session = cookies.get("session")
  if not session:
    session = str(uuid.uuid4())
    await PushError(websocket, "Session cookie not set; you will not be able to resume if you close this tab.")
  await GameLoop(websocket, session, game)


async def GameLoop(websocket, session, game):
  print("new websocket connection by %s from %s" % (session, websocket.remote_address))
  await game.connect_user(session, websocket)
  try:
    async for raw in websocket:
      await game.handle(websocket, session, raw)
  except websockets.exceptions.ConnectionClosed:
    print("connection for %s from %s closed unexpectedly" % (session, websocket.remote_address))
  finally:
    print("closed websocket connection for %s from %s" % (session, websocket.remote_address))
    await game.disconnect_user(session, websocket)


async def SendGames(websocket):
  INDEX_WEBSOCKETS.add(websocket)
  try:
    async for raw in websocket:
      pass
  except websockets.exceptions.ConnectionClosed:
    pass
  finally:
    INDEX_WEBSOCKETS.remove(websocket)


async def SendGameUpdates():
  while True:
    game_data = []
    for game_id, game in GAMES.items():
      game_data.append({
        "game_id": game_id,
        "status": game.game_status(),
        "url": game.game_url(),
      })
    coroutines = [ws.send(json.dumps({"games": game_data})) for ws in INDEX_WEBSOCKETS]
    asyncio.gather(*coroutines)
    await asyncio.sleep(1)


def ws_main(loop):
  port = 8081  # TODO: this is hard-coded into various .js files.
  global GLOBAL_WS_SERVER
  asyncio.set_event_loop(loop)
  asyncio.ensure_future(SendGameUpdates())
  start_server = websockets.serve(HandleWebsocket, '', port)
  GLOBAL_WS_SERVER = loop.run_until_complete(start_server)
  print("Websocket server started on port %d" % port)
  loop.run_forever()


def main(port):
  try:
    server = ThreadingHTTPServer(('', port), MyHandler)
    print('Started server on port %d' % port)
    server.serve_forever()
  except (KeyboardInterrupt, Exception) as e:
    if isinstance(e, KeyboardInterrupt):
      print('keyboard interrupt received; shutting down')
    else:
      print('%s (%s) occurred; shutting down' % (e, e.__class__))
    server.socket.close()
    GLOBAL_WS_SERVER.close()
    fut = asyncio.run_coroutine_threadsafe(GLOBAL_WS_SERVER.wait_closed(), GLOBAL_LOOP)
    fut.result(10)
    GLOBAL_LOOP.stop()


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--http-port", type=int, help="HTTP port", metavar="PORT", default=8001)
  args = parser.parse_args()
  t2 = threading.Thread(target=ws_main, args=(GLOBAL_LOOP,))
  t2.start()
  main(args.http_port)
  t2.join()
