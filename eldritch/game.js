ws = null;
characters = {};
scale = 1;

function init() {
  let params = new URLSearchParams(window.location.search);
  if (!params.has("game_id")) {
    showError("No game id specified.");
    return;
  }
  let gameId = params.get("game_id");
  initializeDefaults();
  let promise = renderImages();
  promise.then(function() { continueInit(gameId); }, showError);
}

function continueInit(gameId) {
  ws = new WebSocket("ws://" + window.location.hostname + ":8081/" + gameId);
  ws.onmessage = onmsg;
  document.getElementById("boardcanvas").width = document.getElementById("defaultboard").width;
  document.getElementById("boardcanvas").height = document.getElementById("defaultboard").height;
  renderAssetToCanvas(document.getElementById("boardcanvas"), "board", "");
  let width = document.getElementById("boardcanvas").width;
  let cont = document.getElementById("board");
  for (let name in locations) {
    let div = document.createElement("DIV");
    div.id = "place" + name;
    div.style.width = Math.floor(2*radiusRatio*width) + "px";
    div.style.height = Math.floor(2*radiusRatio*width) + "px";
    div.classList.add("place", "location");
    div.style.top = Math.round(locations[name].y*width) + "px";
    div.style.left = Math.round(locations[name].x*width) + "px";
    let desc = document.createElement("DIV");
    desc.id = "place" + name + "desc";
    div.appendChild(desc);
    div.onclick = function(e) { moveTo(name); };
    cont.appendChild(div);
  }
  for (let name in streets) {
    let div = document.createElement("DIV");
    div.id = "place" + name;
    div.style.width = Math.floor(width*widthRatio) + "px";
    div.style.height = Math.floor(width*heightRatio) + "px";
    div.classList.add("place");
    div.style.top = Math.round(streets[name].y*width) + "px";
    div.style.left = Math.round(streets[name].x*width) + "px";
    let desc = document.createElement("DIV");
    desc.id = "place" + name + "desc";
    div.appendChild(desc);
    div.onclick = function(e) { moveTo(name); };
    cont.appendChild(div);
  }
}

// TODO: dedup
function clearError() {
  etxt = document.getElementById("errorText")
  if (etxt.holdSeconds > 0) {
    etxt.holdSeconds -= 0.1;
    setTimeout(clearError, 100);
  } else {
    newOpac = etxt.style.opacity - 0.02;
    etxt.style.opacity = newOpac;
    if (newOpac <= 0.1) {
      etxt.innerText = null;
    } else {
      setTimeout(clearError, 50);
    }
  }
}

function showError(errText) {
  document.getElementById("errorText").holdSeconds = 0;
  document.getElementById("errorText").style.opacity = 1.0;
  document.getElementById("errorText").innerText = errText;
}

function onmsg(e) {
  let data = JSON.parse(e.data);
  if (data.type == "error") {
    document.getElementById("errorText").holdSeconds = 3;
    document.getElementById("errorText").style.opacity = 1.0;
    // document.getElementById("errorText").innerText = formatServerString(data.message);
    document.getElementById("errorText").innerText = data.message;
    setTimeout(clearError, 100);
    return;
  }
  updateCharacters(data.characters);
  updateDistances(data.distances);
  updateDice(data.check_result, data.dice_result);
}

function moveTo(place) {
  ws.send(JSON.stringify({"type": "move", "place": place}));
}

function makeCheck(e) {
  let t = e.currentTarget;
  let check_type = t.value;
  let modifier = document.getElementById("modifier").value;
  ws.send(JSON.stringify({"type": "check", "modifier": modifier, "check_type": check_type}));
}

function updateDice(checkResult, diceResult) {
  if (checkResult == null || diceResult == null) {
    document.getElementById("dice").innerText = "no dice";
    document.getElementById("result").innerText = "no check";
    return;
  }
  document.getElementById("dice").innerText = diceResult.join();
  document.getElementById("result").innerText = checkResult ? "pass" : "fail";
}

function updateCharacters(newCharacters) {
  let width = document.getElementById("boardcanvas").width;
  let markerWidth = width * markerWidthRatio;
  let markerHeight = width * markerHeightRatio;
  for (let character of newCharacters) {
    let place = document.getElementById("place" + character.place);
    if (place == null) {
      console.log("Unknown place " + character.place);
      continue;
    }
    if (characters[character.name] == null) {
      let div = document.createElement("DIV");
      div.style.width = + markerWidth + "px";
      div.style.height = markerHeight + "px";
      div.classList.add("marker");
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("markercnv");
      cnv.width = markerWidth;
      cnv.height = markerHeight;
      renderAssetToCanvas(cnv, character.name, "");
      div.appendChild(cnv);
      place.appendChild(div);
      characters[character.name] = div;
    } else {
      let div = characters[character.name];
      if (div.parentNode == place) {
        continue;
      }
      let oldRect = div.getBoundingClientRect();
      div.parentNode.removeChild(div);
      place.appendChild(div);
      let newRect = div.getBoundingClientRect();
      let diffX = Math.floor((oldRect.left - newRect.left) / scale);
      let diffY = Math.floor((oldRect.top - newRect.top) / scale);
      // TODO: multiple clicks in a row, also transition the destination characters.
      div.classList.remove("moving");  // In case a previous movement was interrupted.
      div.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px)";
      setTimeout(function() { div.classList.add("moving"); div.style.transform = ""; }, 5);
      div.addEventListener(
        "transitionend", function() { div.classList.remove("moving") }, {once: true});
    }
  }
}

function updateDistances(distances) {
  for (let place of document.getElementsByClassName("place")) {
    place.classList.remove("reachable");
    place.classList.add("unreachable");
    let divId = place.id;
    let desc = document.getElementById(divId + "desc");
    if (desc != null) {
      desc.innerText = "X";
    }
  }
  for (let placeName in distances) {
    let placeDiv = document.getElementById("place" + placeName);
    placeDiv.classList.remove("unreachable");
    placeDiv.classList.add("reachable");
    let textDiv = document.getElementById("place" + placeName + "desc");
    textDiv.innerText = distances[placeName];
  }
}
