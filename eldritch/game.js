ws = null;
characters = {};
scale = 1;
itemsToChoose = null;
itemChoice = [];
runningAnim = [];
messageQueue = [];

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
    let opt = document.createElement("OPTION");
    opt.value = name;
    opt.text = name;
    document.getElementById("placechoice").appendChild(opt);
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
    let opt = document.createElement("OPTION");
    opt.value = name;
    opt.text = name;
    document.getElementById("placechoice").appendChild(opt);
  }
  for (let name of monsterNames) {
    let opt = document.createElement("OPTION");
    opt.value = name;
    opt.text = name;
    document.getElementById("monsterchoice").appendChild(opt);
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
  if (runningAnim.length || messageQueue.length) {
    messageQueue.push(data);
  } else {
    handleData(data);
  }
}
function finishAnim(div) {
  div.ontransitionend = null;
  div.ontransitioncancel = null;
  runningAnim.shift();
  if (messageQueue.length && !runningAnim.length) {
    handleData(messageQueue.shift());
  }
}
function handleData(data) {
  if (data.player_idx != null) {
    updateYou(data.characters[data.player_idx]);
  } else {
    updateYou(null);
  }
  updateTurn(data.characters[data.turn_idx], data.turn_phase);
  updateDistances(data.distances);
  updateDice(data.check_result, data.dice_result);
  updateCharacters(data.characters);
  updateMonsters(data.places);
  if (messageQueue.length && !runningAnim.length) {
    handleData(messageQueue.shift());
  }
  updateChoices(data.choice);
  updateUsables(data.usables);
  updateEventLog(data.event_log);
}

function moveTo(place) {
  ws.send(JSON.stringify({"type": "move", "place": place}));
}

function setSlider(sliderName, sliderValue) {
  ws.send(JSON.stringify({"type": "set_slider", "name": sliderName, "value": sliderValue}));
}

function spawnMonster(e) {
  let monster = document.getElementById("monsterchoice").value;
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "monster", "place": place, "monster": monster}));
}

function makeChoice(val) {
  if (itemsToChoose == null) {
    ws.send(JSON.stringify({"type": "choice", "choice": val}));
    return;
  }
  if (itemsToChoose > 0 && itemChoice.length != itemsToChoose) {
    document.getElementById("errorText").holdSeconds = 3;
    document.getElementById("errorText").style.opacity = 1.0;
    document.getElementById("errorText").innerText = "Expected " + itemsToChoose + " items.";
    setTimeout(clearError, 100);
    return;
  }
  ws.send(JSON.stringify({"type": "choice", "choice": itemChoice}));
}

function doneUsing(e) {
  ws.send(JSON.stringify({"type": "done_using"}));
}

function clickAsset(assetDiv, assetIdx) {
  if (itemsToChoose == null) {
    useAsset(assetIdx);
    return;
  }
  let choiceIdx = itemChoice.indexOf(assetIdx);
  if (choiceIdx >= 0) {
    itemChoice.splice(choiceIdx, 1);
    assetDiv.classList.remove("chosen");
  } else {
    itemChoice.push(assetIdx);
    assetDiv.classList.add("chosen");
  }
}

function useAsset(idx) {
  ws.send(JSON.stringify({"type": "use", "idx": idx}));
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

function updateMonsters(places) {
  for (let name in places) {
    let pDiv = document.getElementById("place" + name);
    while (pDiv.getElementsByClassName("monster").length) {
      pDiv.removeChild(pDiv.getElementsByClassName("monster")[0]);
    }
    for (let monster of places[name].monsters) {
      pDiv.appendChild(createMonsterDiv(monster.name));
    }
  }
}

function updateChoices(choice) {
  let uichoice = document.getElementById("uichoice");
  let pDiv = document.getElementById("possessions");
  if (choice == null) {
    uichoice.style.display = "none";
    itemsToChoose = null;
    itemChoice = [];
    pDiv.classList.remove("choose");
    return;
  }
  uichoice.style.display = "flex";
  while (uichoice.getElementsByClassName("choice").length) {
    uichoice.removeChild(uichoice.getElementsByClassName("choice")[0]);
  }
  document.getElementById("uiprompt").innerText = choice.prompt;
  if (choice.items != null) {
    itemsToChoose = choice.items;
    pDiv.classList.add("choose");
    addChoices(uichoice, ["Done Choosing Items"]);
  } else {
    itemsToChoose = null;
    itemChoice = [];
    pDiv.classList.remove("choose");
    addChoices(uichoice, choice.choices);
  }
}

function addChoices(uichoice, choices) {
  for (let c of choices) {
    let div = document.createElement("DIV");
    div.classList.add("choice");
    div.innerText = c;
    div.onclick = function(e) { makeChoice(c); };
    uichoice.appendChild(div);
  }
}

function updateUsables(usables) {
  let uiuse = document.getElementById("uiuse");
  let pDiv = document.getElementById("possessions");
  if (usables == null) {
    uiuse.style.display = "none";
    pDiv.classList.remove("use");
    return;
  }
  uiuse.style.display = "flex";
  pDiv.classList.add("use");
  let posList = pDiv.getElementsByClassName("possession");
  for (let i = 0; i < posList.length; i++) {
    if (usables.includes(i)) {
      posList[i].classList.add("usable");
      posList[i].classList.remove("unusable");
    } else {
      posList[i].classList.remove("usable");
      posList[i].classList.add("unusable");
    }
  }
  // TODO: clues
}

function createMonsterDiv(name) {
  let width = document.getElementById("boardcanvas").width;
  let markerWidth = width * markerWidthRatio;
  let markerHeight = width * markerHeightRatio;
  let div = document.createElement("DIV");
  div.style.width = + markerWidth + "px";
  div.style.height = markerHeight + "px";
  div.classList.add("monster");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("monstercnv");
  cnv.width = markerWidth;
  cnv.height = markerHeight;
  renderAssetToCanvas(cnv, name, "");
  div.appendChild(cnv);
  return div;
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
  // TODO: also transition the destination characters.
  div.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px)";
  
  runningAnim.push(true);  // Doesn't really matter what we push.
  div.ontransitionend = function() { div.classList.remove("moving"); finishAnim(div); };
  div.ontransitioncancel = function() { div.classList.remove("moving"); finishAnim(div); };
  setTimeout(function() { div.classList.add("moving"); div.style.transform = "none"; }, 10);
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

function updateEventLog(eventLog) {
  let logDiv = document.getElementById("eventlog");
  while (logDiv.firstChild) {
    logDiv.removeChild(logDiv.firstChild);
  }
  for (let e of eventLog) {
    let textDiv = document.createElement("DIV");
    textDiv.classList.add("logevent");
    textDiv.innerText = e;
    logDiv.appendChild(textDiv);
  }
  logDiv.scrollTop = logDiv.scrollHeight;
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
  document.getElementById("playername").innerText = character.name;
  let stats = document.getElementById("playerstats");
  while (stats.firstChild) {
    stats.removeChild(stats.firstChild);
  }
  let cfgs = [  // TODO: speed is not the correct cap for movement points
    ["stamina", "stamina", "max_stamina"], ["sanity", "sanity", "max_sanity"],
    ["movement", "movement_points", "speed"], ["focus", "focus_points", "focus"],
    ["clues", "clues"], ["dollars", "dollars"],
  ];
  for (let cfg of cfgs) {
    let text = cfg[0] + ": " + character[cfg[1]];
    if (cfg.length > 2) {
      text += " / " + character[cfg[2]];
    }
    let statDiv = document.createElement("DIV");
    statDiv.classList.add("stat");
    statDiv.innerText = text;
    if (cfg[0] == "clues") {
      statDiv.classList.add("clue");
      // TODO: make this nicer
      statDiv.onclick = function(e) { useAsset(-1) };
    }
    stats.appendChild(statDiv);
  }
  updateSliders(character);
  updatePossessions(character);
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

function updatePossessions(character) {
  let pDiv = document.getElementById("possessions");
  while (pDiv.firstChild) {
    pDiv.removeChild(pDiv.firstChild);
  }
  for (let i = 0; i < character.possessions.length; i++) {
    pDiv.appendChild(createPossession(character.possessions[i], i));
  }
}

function createPossession(info, idx) {
  let width = document.getElementById("boardcanvas").width;
  let posWidth = 3 * width * markerWidthRatio / 2;
  let posHeight = 3 * width * markerHeightRatio / 2;
  let div = document.createElement("DIV");
  div.classList.add("possession");
  if (info.active) {
    div.classList.add("active");
  }
  let cnv = document.createElement("CANVAS");
  div.style.width = posWidth + "px";
  div.style.height = posHeight + "px";
  cnv.width = posWidth;
  cnv.height = posHeight;
  cnv.classList.add("markercnv");  // TODO: maybe these should be a different size/class.
  renderAssetToCanvas(cnv, info.name, "");
  div.appendChild(cnv);
  let cascade = {"sneak": "evade", "fight": "combat", "will": "horror", "lore": "spell"};
  for (let attr in info.bonuses) {
    if (!info.bonuses[attr]) {
      continue;
    }
    let highlightDiv = document.createElement("DIV");
    highlightDiv.classList.add("bonus");
    highlightDiv.classList.add("bonus" + attr);
    highlightDiv.innerText = (info.bonuses[attr] >= 0 ? "+" : "") + info.bonuses[attr];
    if (cascade[attr]) {
      highlightDiv.classList.add("bonus" + cascade[attr]);
    }
    div.appendChild(highlightDiv);
  }
  if (itemChoice.includes(idx)) {
    div.classList.add("chosen");
  }
  div.onclick = function(e) { clickAsset(div, idx); };
  // TODO: show some information about bonuses that aren't active right now
  return div;
}

function highlightCheck(e) {
  let check_type = e.currentTarget.value;
  for (let hDiv of document.getElementsByClassName("bonus" + check_type)) {
    hDiv.classList.add("shown");
  }
}

// TODO: figure out why this gets called when a button is clicked
function endHighlight(e) {
  for (let hDiv of document.getElementsByClassName("bonus")) {
    hDiv.classList.remove("shown");
  }
}
