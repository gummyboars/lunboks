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
import websockets

import catan
import game

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
GAME_STATE = None
GLOBAL_WS = collections.OrderedDict([])
GLOBAL_LOOP = None


class MyHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    start = time.time()
    self_path = urllib.parse.urlparse(self.path).path
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

    end = time.time()

    self.send_response(HTTPStatus.OK.value)
    self.end_headers()

    with open(path, 'rb') as w:
      self.wfile.write(w.read())

  def do_POST(self):
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
    else:
      self.send_error(HTTPStatus.NOT_FOUND.value, "bruh, what is %s?" % self_path)


async def PushState():
  for name, ws in GLOBAL_WS.items():
    await ws.send(GAME_STATE.for_player(name))


async def PushError(player, e):
  await GLOBAL_WS[player].send(json.dumps({"type": "error", "message": e}))


async def WebLoop(websocket, path):
  name = None
  for i in range(len(GLOBAL_WS) + 1):
    name = "Player%s" % (i+1) 
    if name not in GLOBAL_WS:
      break
  else:
    await websocket.close()
    return
  GLOBAL_WS[name] = websocket
  GAME_STATE.add_player(name)
  print("added %s (%s) to the global registry" % (name, websocket))
  await PushState()
  try:
    async for raw in websocket:
      try:
        data = json.loads(raw, object_pairs_hook=collections.OrderedDict)
      except Exception as e:
        await PushError(str(e))
        continue
      if data.get("type") == "player":
        playerdata = data.get("player")
        if isinstance(playerdata, dict) and isinstance(playerdata.get("name"), str):
          if not playerdata["name"].isprintable():
            await PushError(name, "Player names must be printable.")
            continue
          if playerdata["name"] in GLOBAL_WS:
            await PushError(name, "There is already a player named %s. Nice try." % playerdata["name"])
            continue
          if len(playerdata["name"]) > 50:
            friend_names = ["Joey", "Ross", "Chandler", "Phoebe", "Rachel", "Monica"]
            random.shuffle(friend_names)
            new_name = None
            for some_name in friend_names:
              if some_name not in GLOBAL_WS:
                new_name = some_name
                break
            if new_name:
              await PushError(name, "Oh, is that how you want to play it? Well, you know what? I'm just gonna call you %s." % new_name)
              playerdata["name"] = new_name
          if len(playerdata["name"]) > 16:
            await PushError(name, "Max name length is 16.")
            continue
          del GLOBAL_WS[name]
          print("player %s changing name to %s" % (name, playerdata["name"]))
          GAME_STATE.rename_player(name, playerdata["name"])
          name = playerdata["name"]
          GLOBAL_WS[name] = websocket
        else:
          await PushError("invalid player data")
          continue
      else:
        try:
          GAME_STATE.handle(data, name)
        except game.InvalidMove as e:
          await PushError(name, str(e))
        except Exception as e:
          print(sys.exc_info()[0])
          print(sys.exc_info()[1])
          traceback.print_tb(sys.exc_info()[2])
          await PushError(name, "unexpected error of type %s: %s" % (sys.exc_info()[0], sys.exc_info()[1]))

      await PushState()
  finally:
    print("removing %s (%s) from the global registry" % (name, websocket))
    del GLOBAL_WS[name]
    GAME_STATE.remove_player(name)


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
  t2.start()
  GAME_STATE = catan.CatanState()
  GAME_STATE.init_normal()
  main()
  loop.stop()
  loop.close()
