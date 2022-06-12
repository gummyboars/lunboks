ws = null;
players = [];

function init() {
  let params = new URLSearchParams(window.location.search);
  if (!params.has("game_id")) {
    throw new Error("No game id specified.");
  }
  let gameId = params.get("game_id");
  let promise = loadImages();
  promise.then(function() { continueInit(gameId); });
}

function continueInit(gameId) {
  ws = new WebSocket("ws://" + window.location.hostname + ":8081/" + gameId);
  ws.onmessage = onmsg;
  for (let div of document.getElementsByClassName("room")) {
    let name = div.id;
    renderAssetToDiv(div, name);
    if (name == "balcony") {
      name = "gallery";
    }
    div.onclick = function() { moveTo(name) };
  }
}

function start(e) {
  ws.send(JSON.stringify({"type": "start"}));
}

function endTurn(e) {
  ws.send(JSON.stringify({"type": "end"}));
}

function moveTo(shortName) {
  ws.send(JSON.stringify({"type": "move", "name": shortName}));
}

function onmsg(e) {
  let data = JSON.parse(e.data);
  if (data.type == "error") {
    console.log(data.message);
    document.getElementById("error").innerText = data.message;
    setTimeout(function() { document.getElementById("error").innerText = ""; }, 3000);
    return;
  }
  for (let room of document.getElementsByClassName("room")) {
    let roomId = room.id == "balcony" ? "gallery" : room.id;
    room.reachable = data.reachable.includes(roomId);
    room.visible = data.visible.includes(roomId);
  }
  for (let [idx, player] of data.players.entries()) {
    if (idx >= players.length) {
      let div = document.createElement("DIV");
      div.classList.add("player");
      div.style.background = player.color;
      players.push(div);
    }
    let div = players[idx];
    document.getElementById(player.room).appendChild(div);
  }
  let doctor = document.getElementById("doctor");
  if (doctor == null) {
    doctor = document.createElement("DIV");
    doctor.classList.add("player");
    doctor.style.background = "black";
    doctor.id = "doctor";
  }
  document.getElementById(data.doctor).appendChild(doctor);
}

function showVisible(e) {
  for (let room of document.getElementsByClassName("room")) {
    room.classList.toggle("shown", !!room.visible);
  }
  document.getElementById("overlay").classList.add("shown");
}
function showReachable(e) {
  for (let room of document.getElementsByClassName("room")) {
    room.classList.toggle("shown", !!room.reachable);
  }
  document.getElementById("overlay").classList.add("shown");
}
function hide(e) {
  for (let room of document.getElementsByClassName("room")) {
    room.classList.remove("shown");
  }
  document.getElementById("overlay").classList.remove("shown");
}
