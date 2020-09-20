#!/usr/bin/env python3

import asyncio
import collections
from http import HTTPStatus
from http.server import HTTPServer,BaseHTTPRequestHandler
import json
import os
import random
import sys
import threading
import time
import traceback
import urllib
import uuid
import websockets

import catan
import game

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
GAME_STATE = None
GLOBAL_WS = collections.OrderedDict([])
GLOBAL_LOOP = None


class MyHandler(BaseHTTPRequestHandler):

  # TODO: Try SimpleHTTPRequestHandler
  def do_GET(self):
    start = time.time()
    self_path = urllib.parse.urlparse(self.path).path
    if self_path.rstrip("/") in ("/dump", "/json", "/save"):
      value = GAME_STATE.json_str().encode('ascii')
      self.send_response(HTTPStatus.OK.value)
      self.end_headers()
      self.wfile.write(value)
      return
    if self_path == "/":
      path = "/".join([ROOT_DIR, "catan.html"])
    else:
      path = "/".join([ROOT_DIR, self_path])
    path = os.path.abspath(path)
    if os.path.dirname(path) != ROOT_DIR:
      print("dirname is %s but root is %s" % (os.path.dirname(path), ROOT_DIR))
      self.send_error(HTTPStatus.FORBIDDEN.value, "Access to %s forbidden" % self_path)
      return
    if not os.path.exists(path):
      self.send_error(HTTPStatus.NOT_FOUND.value, "File %s not found" % self_path)
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

    self.end_headers()
    end = time.time()

    with open(path, 'rb') as w:
      self.wfile.write(w.read())

  def do_POST(self):
    global GAME_STATE
    req = urllib.parse.urlparse(self.path)
    self_path = req.path
    if self_path.rstrip("/") == "/reset":
      GAME_STATE.init_normal()
      self.send_response(HTTPStatus.NO_CONTENT.value)
      self.end_headers()
      fut = asyncio.run_coroutine_threadsafe(PushState(), GLOBAL_LOOP)
      fut.result(10)
    elif self_path.rstrip("/") == "/dice":
      params = urllib.parse.parse_qs(req.query)
      try:
        count = int(params["count"][0])
      except:
        count = 1
      GAME_STATE.handle_force_dice(count)
      self.send_response(HTTPStatus.NO_CONTENT.value)
      self.end_headers()
      fut = asyncio.run_coroutine_threadsafe(PushState(), GLOBAL_LOOP)
      fut.result(10)
    elif self_path.rstrip("/") == "/load":
      data = self.rfile.read(int(self.headers["content-length"]))
      try:
        cstate = catan.CatanState.parse_json(data)
      except Exception as e:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        traceback.print_tb(sys.exc_info()[2])
        self.send_error(HTTPStatus.BAD_REQUEST.value, str(e))
        return
      GAME_STATE = cstate
      self.send_response(HTTPStatus.NO_CONTENT.value)
      self.end_headers()
      fut = asyncio.run_coroutine_threadsafe(PushState(), GLOBAL_LOOP)
      fut.result(10)
    else:
      self.send_error(HTTPStatus.NOT_FOUND.value, "bruh, what is %s?" % self_path)


async def PushState():
  for session, ws_list in GLOBAL_WS.items():
    for ws in ws_list:
      await ws.send(GAME_STATE.for_player(session))


async def PushError(ws, e):
  await ws.send(json.dumps({"type": "error", "message": e}))


async def WebLoop(websocket, path):
  # TODO: possible cross-site request forgery of websocket data
  # https://christian-schneider.net/CrossSiteWebSocketHijacking.html
  cookie_str = websocket.request_headers["Cookie"]
  cookies = dict([x.strip().split("=", 1) for x in cookie_str.split(";")])
  session = cookies.get("session")
  missing_cookie = False
  if not session:
    session = str(uuid.uuid4())
    missing_cookie = True
  # Add this user to the global registry.
  if session not in GLOBAL_WS:
    GLOBAL_WS[session] = set([])
  GLOBAL_WS[session].add(websocket)
  print("added %s to the global registry" % session)

  if missing_cookie:
    await PushError(websocket, "Session cookie not set; you will not be able to resume if you close this tab.")
  GAME_STATE.connect_user(session)
  await PushState()
  try:
    async for raw in websocket:
      try:
        data = json.loads(raw, object_pairs_hook=collections.OrderedDict)
      except Exception as e:
        await PushError(websocket, str(e))
        continue
      try:
        GAME_STATE.handle(session, data)
      except (game.InvalidMove, game.InvalidPlayer, game.TooManyPlayers, AssertionError) as e:
        await PushError(websocket, str(e))
        # Intentionally fall through so that we can push the new state.
      except Exception as e:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        traceback.print_tb(sys.exc_info()[2])
        await PushError(websocket, "unexpected error of type %s: %s" % (sys.exc_info()[0], sys.exc_info()[1]))
        continue

      await PushState()
  finally:
    print("removing %s from the global registry" % session)
    GLOBAL_WS[session].remove(websocket)
    if not GLOBAL_WS[session]:
      del GLOBAL_WS[session]
      GAME_STATE.disconnect_user(session)
      await PushState()


def ws_main(loop):
  asyncio.set_event_loop(loop)
  ws_port = 8081
  start_server = websockets.serve(WebLoop, '127.0.0.1', ws_port)
  loop.run_until_complete(start_server)
  print("Websocket server started on port %d" % ws_port)
  loop.run_forever()


def main():
  try:
    port = 8080
    server = HTTPServer(('127.0.0.1', port), MyHandler)
    print('Started server on port %d' % port)
    server.serve_forever()
  except KeyboardInterrupt:
    print('keyboard interrupt received; shutting down')
    server.socket.close()
    return
  except Exception as e:
    print('%s (%s) occurred; shutting down' % (e, e.__class__))
    server.socket.close()
    return


if __name__ == '__main__':
  loop = asyncio.get_event_loop()
  GLOBAL_LOOP = loop
  t2 = threading.Thread(target=ws_main, args=(loop,))
  t2.daemon = True
  t2.start()
  GAME_STATE = catan.CatanState()
  main()
  loop.stop()
