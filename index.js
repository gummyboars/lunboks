ws = null;
map = {};
function changeval(e) {
  let val = document.getElementById("gamechoice").value;
  document.getElementById("gametype").value = val;
}
function createGame(gameData) {
  let table = document.getElementById("table");
  let tr = document.createElement("TR");
  tr.gameId = gameData.game_id;
  let name = document.createElement("TD");
  name.innerText = tr.gameId;
  tr.appendChild(name);
  let gameStatus = document.createElement("TD");
  gameStatus.innerText = gameData.status;
  tr.appendChild(gameStatus);
  let gameLink = document.createElement("TD");
  let link = document.createElement("A");
  link.target = "_blank";
  link.href = gameData.url;
  link.innerText = "Launch";
  gameLink.appendChild(link);
  tr.appendChild(gameLink);
  table.appendChild(tr);
  map[tr.gameId] = tr;
}
function updateGame(tr, gameData) {
  let gameStatus = tr.children[1];
  if (gameStatus.innerText != gameData.status) {
    gameStatus.innerText = gameData.status;
  }
}
function deleteMissingGames(allIds) {
  let table = document.getElementById("table");
  let toRemove = [];
  for (child of table.children) {
    if (!allIds[child.gameId]) {
      toRemove.push(child);
    }
  }
  for (child of toRemove) {
    table.removeChild(child);
  }
}
function updateGames(gamesData) {
  let allIds = {};
  for (game of gamesData) {
    allIds[game.game_id] = true;
    if (map[game.game_id] != undefined) {
      updateGame(map[game.game_id], game);
      continue;
    }
    createGame(game);
  }
  deleteMissingGames(allIds);
}
function onmsg(e) {
  let data = JSON.parse(e.data);
  if (data.type == "error") {
    document.getElementById("error").innerText = data.message;
    document.getElementById("error").display = "block";
    return;
  }
  updateGames(data.games);
}
function init() {
  let l = window.location;
  ws = new WebSocket("ws://" + l.hostname + ":8081/");
  ws.onmessage = onmsg;
}
