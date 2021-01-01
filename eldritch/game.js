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
  if (data.player_idx != null) {
    updateYou(data.characters[data.player_idx]);
  } else {
    updateYou(null);
  }
  updateTurn(data.characters[data.turn_idx], data.turn_phase);
  updateCharacters(data.characters);
  updateDistances(data.distances);
  updateDice(data.check_result, data.dice_result);
}

function moveTo(place) {
  ws.send(JSON.stringify({"type": "move", "place": place}));
}

function setSlider(sliderName, sliderValue) {
  ws.send(JSON.stringify({"type": "set_slider", "name": sliderName, "value": sliderValue}));
}

function makeCheck(e) {
  let t = e.currentTarget;
  let check_type = t.value;
  let modifier = document.getElementById("modifier").value;
  ws.send(JSON.stringify({"type": "check", "modifier": modifier, "check_type": check_type}));
}

function endTurn(e) {
  ws.send(JSON.stringify({"type": "end_turn"}));
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
  for (let character of newCharacters) {
    let place = document.getElementById("place" + character.place);
    if (place == null) {
      console.log("Unknown place " + character.place);
      continue;
    }
    if (characters[character.name] == null) {
      characters[character.name] = createCharacterDiv(character.name);
      place.appendChild(characters[character.name]);
    } else {
      moveCharacter(character.name, place);
    }
  }
}

function createCharacterDiv(name) {
  let width = document.getElementById("boardcanvas").width;
  let markerWidth = width * markerWidthRatio;
  let markerHeight = width * markerHeightRatio;
  let div = document.createElement("DIV");
  div.style.width = + markerWidth + "px";
  div.style.height = markerHeight + "px";
  div.classList.add("marker");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("markercnv");
  cnv.width = markerWidth;
  cnv.height = markerHeight;
  renderAssetToCanvas(cnv, name, "");
  div.appendChild(cnv);
  return div;
}

function moveCharacter(name, destDiv) {
  let div = characters[name];
  if (div.parentNode == destDiv) {
    return;
  }
  let oldRect = div.getBoundingClientRect();
  div.parentNode.removeChild(div);
  destDiv.appendChild(div);
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

function updateTurn(character, phase) {
  let btn = document.getElementById("turn").firstChild;
  btn.innerText = character.name + "'s " + phase + " phase";
}

function updateYou(character) {
  // TODO handle null, since this may be an observer.
  let width = document.getElementById("boardcanvas").width;
  let pdata = document.getElementById("player");
  let markerWidth = width * markerWidthRatio;
  let markerHeight = width * markerHeightRatio;
  let picDiv = document.getElementById("playerpic");
  let cnv = document.getElementById("playerpiccanvas");
  picDiv.style.width = markerWidth + "px";
  picDiv.style.height = markerHeight + "px";
  cnv.width = markerWidth;
  cnv.height = markerHeight;
  renderAssetToCanvas(cnv, character.name, "");
  document.getElementById("playername").innerText = character.name + " " + character.focus_points + " / " + character.focus;
  updateSliders(character);
  // updatePossessions(character);
}

function updateSliders(character) {
  for (let sliderName in character.sliders) {
    let sliderDiv = document.getElementById("slider_" + sliderName);
    if (sliderDiv == null) {
      sliderDiv = createSlider(sliderName, character.sliders[sliderName]);
      document.getElementById("sliders").appendChild(sliderDiv);
      let spacerDiv = document.createElement("DIV");
      spacerDiv.classList.add("sliderspacer");
      document.getElementById("sliders").appendChild(spacerDiv);
    }
    let selection = character.sliders[sliderName].selection;
    let pairs = sliderDiv.getElementsByClassName("slidervaluepair");
    for (let idx = 0; idx < pairs.length; idx++) {
      let sliderPair = pairs[idx];
      if (idx == selection) {
        sliderPair.classList.add("sliderselected");
        sliderPair.classList.remove("sliderdeselected");
      } else {
        sliderPair.classList.remove("sliderselected");
        sliderPair.classList.add("sliderdeselected");
      }
    }
  }
}

function createSlider(sliderName, sliderInfo) {
  let firstName = sliderName.split("_")[0];
  let secondName = sliderName.split("_")[1];
  let sliderDiv = document.createElement("DIV");
  sliderDiv.classList.add("slider");
  sliderDiv.id = "slider_" + sliderName;
  let nameDiv = document.createElement("DIV");
  nameDiv.classList.add("sliderpair");
  nameDiv.classList.add("slidernames");
  let firstNameDiv = document.createElement("DIV");
  firstNameDiv.classList.add("slidername");
  firstNameDiv.innerText = firstName;
  let secondNameDiv = document.createElement("DIV");
  secondNameDiv.classList.add("slidername");
  secondNameDiv.innerText = secondName;
  nameDiv.appendChild(firstNameDiv);
  nameDiv.appendChild(secondNameDiv);
  sliderDiv.appendChild(nameDiv);
  for (let idx = 0; idx < sliderInfo.pairs.length; idx++) {
    let pair = sliderInfo.pairs[idx];
    let pairDiv = document.createElement("DIV");
    pairDiv.classList.add("sliderpair");
    pairDiv.classList.add("slidervaluepair");
    let firstDiv = document.createElement("DIV");
    firstDiv.classList.add("slidervalue");
    firstDiv.classList.add("slidertop");
    firstDiv.innerText = pair[0];
    let secondDiv = document.createElement("DIV");
    secondDiv.classList.add("slidervalue");
    secondDiv.classList.add("sliderbottom");
    secondDiv.innerText = pair[1];
    pairDiv.appendChild(firstDiv);
    pairDiv.appendChild(secondDiv);
    pairDiv.onclick = function(e) { setSlider(sliderName, idx); };
    sliderDiv.appendChild(pairDiv);
  }
  return sliderDiv;
}
