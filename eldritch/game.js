ws = null;
dragged = null;
characters = {};
monsters = {};
allCharacters = {};
scale = 1;
itemsToChoose = null;
itemChoice = [];
monsterChoice = {};
charChoice = null;
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
  let heights = {"location": Math.floor(2*radiusRatio*width), "street": Math.floor(width*heightRatio)};
  let widths = {"location": Math.floor(2*radiusRatio*width), "street": Math.floor(width*widthRatio)};
  for (let [placeType, places] of [["location", locations], ["street", streets]]) {
    for (let name in places) {
      let div = document.createElement("DIV");
      div.id = "place" + name;
      div.style.width = widths[placeType] + "px";
      div.style.height = heights[placeType] + "px";
      div.classList.add("place");
      div.style.top = Math.round(places[name].y*width) + "px";
      div.style.left = Math.round(places[name].x*width) + "px";
      div.onmouseenter = bringToTop;
      let box = document.createElement("DIV");
      box.id = "place" + name + "box";
      box.classList.add("placebox", "placeboxhover");  // FIXME
      box.ondrop = drop;
      box.ondragenter = dragEnter;
      box.ondragover = dragOver;
      div.appendChild(box);
      let monstersDiv = document.createElement("DIV");
      monstersDiv.id = "place" + name + "monsters";
      monstersDiv.classList.add("placemonsters");
      monstersDiv.style.height = div.style.height;
      monstersDiv.onclick = function(e) { showMonsters(monstersDiv, name); };
      let details = document.createElement("DIV");
      details.id = "place" + name + "details";
      details.classList.add("placedetails");
      details.style.height = div.style.height;
      if (places[name].y < 0.3) {
        box.classList.add("placeupper");
        box.appendChild(details);
        box.appendChild(monstersDiv);
      } else {
        box.classList.add("placelower");
        box.appendChild(monstersDiv);
        box.appendChild(details);
      }
      if (places[name].x < 0.5) {
        box.classList.add("placeleft");
      } else {
        box.classList.add("placeright");
      }

      let chars = document.createElement("DIV");
      chars.id = "place" + name + "chars";
      chars.classList.add("placechars");
      chars.style.height = div.style.height;
      chars.style.minWidth = div.style.width;
      details.appendChild(chars);
      let gateDiv = document.createElement("DIV");
      gateDiv.id = "place" + name + "gate";
      gateDiv.classList.add("placegate");
      gateDiv.style.height = div.style.height;
      gateDiv.style.width = div.style.width;
      details.appendChild(gateDiv);
      let gate = document.createElement("CANVAS");
      gate.classList.add("gate");
      gate.width = Math.floor(2*radiusRatio*width);
      gate.height = Math.floor(2*radiusRatio*width);
      gateDiv.appendChild(gate);
      let select = document.createElement("DIV");
      select.id = "place" + name + "select";
      select.classList.add("placeselect", placeType);
      select.style.height = div.style.height;
      select.style.width = div.style.width;
      select.onclick = function(e) { clickPlace(name); };
      details.appendChild(select);
      cont.appendChild(div);

      let opt = document.createElement("OPTION");
      opt.value = name;
      opt.text = name;
      document.getElementById("placechoice").appendChild(opt);
    }
  }
  for (let name of monsterNames) {
    let opt = document.createElement("OPTION");
    opt.value = name;
    opt.text = name;
    document.getElementById("monsterchoice").appendChild(opt);
  }
  for (let [idx, name] of otherWorlds.entries()) {
    let div = document.createElement("DIV");
    div.id = "world" + name;
    div.classList.add("world");
    div.style.width = Math.floor(width/8) + "px";
    div.style.maxHeight = Math.floor(width/8) + "px";
    let worldbox = document.createElement("DIV");
    worldbox.id = "world" + name + "box";
    worldbox.classList.add("worldbox");
    worldbox.style.width = Math.floor(width/8) + "px";
    worldbox.style.height = Math.floor(width/8) + "px";
    for (let [i, side] of [[1, "left"], [2, "right"]]) {
      let world = document.createElement("DIV");
      world.id = "place" + name + i + "chars";
      world.classList.add("world" + side, "worldchars");
      worldbox.appendChild(world);
    }
    div.appendChild(worldbox);
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("worldcnv");
    cnv.width = width / 8;
    cnv.height = width / 8;
    renderAssetToCanvas(cnv, name, "");
    div.appendChild(cnv);
    if (idx < otherWorlds.length / 2) {
      document.getElementById("worldstop").appendChild(div);
    } else {
      document.getElementById("worldsbottom").appendChild(div);
    }
  }
  let worlds = document.getElementById("worlds");
  worlds.style.height = Math.floor(width/16) + "px";
  worlds.style.maxHeight = Math.floor(width/16) + "px";
  for (let extra of ["Lost", "Sky", "Outskirts"]) {
    let div = document.getElementById("place" + extra);
    div.style.width = Math.floor(width/15) + "px";
    div.style.height = Math.floor(width/15) + "px";
    let box = document.getElementById("place" + extra + "box");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("worldcnv");
    cnv.width = width / 15;
    cnv.height = width / 15;
    renderAssetToCanvas(cnv, extra, "");
    box.appendChild(cnv);
    if (extra != "Lost") {
      let monstersDiv = box.getElementsByClassName("placemonsters")[0];
      monstersDiv.onclick = function(e) { showMonsters(monstersDiv, extra); };
    }
  }
  let outskirtsBox = document.getElementById("placeOutskirtsbox");
  outskirtsBox.ondragenter = dragEnter;
  outskirtsBox.ondragover = dragOver;
  outskirtsBox.ondrop = drop;

  let markerWidth = width * markerWidthRatio;
  let markerHeight = width * markerHeightRatio;
  let charChoice = document.getElementById("charchoice");
  let cnv = document.getElementById("charchoicecnv");
  charChoice.style.width = markerWidth + "px";
  charChoice.style.height = markerHeight + "px";
  cnv.width = markerWidth;
  cnv.height = markerHeight;
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
function doneAnimating(div) {
  div.ontransitionend = null;
  div.ontransitioncancel = null;
}
function finishAnim() {
  runningAnim.shift();
  if (messageQueue.length && !runningAnim.length) {
    handleData(messageQueue.shift());
  }
}
function handleData(data) {
  allCharacters = data.all_characters;
  updateCharacterSelect(data.characters, data.player_idx, data.pending_name, data.pending_chars);
  updateCharacterSheets(data.characters, data.player_idx, data.first_player);
  updateDone(data.game_stage, data.sliders);
  updatePlaces(data.places);
  updateCharacters(data.characters);
  updateChoices(data.choice);
  updateMonsters(data.monsters);
  updateMonsterChoices(data.choice, data.monsters);
  updateUsables(data.usables, data.choice);
  updateEventLog(data.event_log);
  if (messageQueue.length && !runningAnim.length) {
    handleData(messageQueue.shift());
  }
}

function clickPlace(place) {
  ws.send(JSON.stringify({"type": "choice", "choice": place}));
}

function setSlider(sliderName, sliderValue) {
  ws.send(JSON.stringify({"type": "set_slider", "name": sliderName, "value": sliderValue}));
}

function spawnMonster(e) {
  let monster = document.getElementById("monsterchoice").value;
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "monster", "place": place, "monster": monster}));
}

function spawnGate(e) {
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "gate", "place": place}));
}

function spawnClue(e) {
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "clue", "place": place}));
}

function bringToTop(e) {
  // It turns out that for siblings in the DOM, browsers give precedence to the sibling that
  // comes later in the dom when calculating which element is being hovered. So once the user
  // hovers over a box, we put that box last so that it gets priority over all the other boxes.
  // This is a convoluted way of doing it - it turns out that if you move the dom element that
  // you just moused over, firefox has trouble with applying the hover attributes. So instead
  // of moving the element to the end, we move all OTHER elements before it, and this makes
  // firefox happy.
  let board = e.currentTarget.parentNode;
  let divsToMove = [];
  let found = false;
  for (let i = 0; i < board.children.length; i++) {
    if (found && board.children[i].classList.contains("place")) {
      divsToMove.push(board.children[i]);
    }
    if (board.children[i] == e.currentTarget) {
      found = true;
    }
  }
  for (let other of divsToMove) {
    board.insertBefore(other, e.currentTarget);
  }
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

function clickAsset(assetDiv, assetHandle) {
  // TODO: we should change ItemChoice to choose items one by one.
  if (assetDiv.classList.contains("usable")) {
    useAsset(assetHandle);
    return;
  }
  let choiceIdx = itemChoice.indexOf(assetHandle);
  if (choiceIdx >= 0) {
    itemChoice.splice(choiceIdx, 1);
    assetDiv.classList.remove("chosen");
  } else {
    itemChoice.push(assetHandle);
    assetDiv.classList.add("chosen");
  }
}

function confirmMonsterChoice(e) {
  let choices = {};
  for (let idx in monsterChoice) {
    if (choices[monsterChoice[idx]] == null) {
      choices[monsterChoice[idx]] = [];
    }
    choices[monsterChoice[idx]].push(parseInt(idx));
  }
  ws.send(JSON.stringify({"type": "choice", "choice": choices}));
}

function resetMonsterChoice(e) {
  for (let monsterDiv of document.getElementsByClassName("monster")) {
    if (monsterDiv.monsterIdx != null && monsterDiv.draggable) {
      document.getElementById("monsterchoices").appendChild(monsterDiv);
    }
  }
  monsterChoice = {};
}

function useAsset(handle) {
  ws.send(JSON.stringify({"type": "use", "handle": handle}));
}

function dragStart(e) {
  dragged = e.target;
}

function dragEnd(e) {
  dragged = null;
}

function dragEnter(e) {
  e.preventDefault();
}

function dragOver(e) {
  e.preventDefault();
}

function drop(e) {
  if (dragged == null) {
    console.log("dropped elem that was not dragged");
    return;
  }
  if (dragged.classList.contains("monster")) {
    return dropMonster(e);
  }
  if (dragged.classList.contains("possession")) {
    return dropPossession(e);
  }
  if (dragged.classList.contains("dollars")) {
    return dropDollars(dragged, e);
  }
  console.log("dragged elem was neither a monster nor a possession nor dollars");
}

function dropMonster(e) {
  if (dragged.monsterIdx == null) {
    console.log("dragged monster did not have an id");
    return;
  }
  if (!e.currentTarget.id.startsWith("place") || !e.currentTarget.id.endsWith("box")) {
    console.log("dragged to something that's not a place");
    return;
  }
  let placeName = e.currentTarget.id.substring(5, e.currentTarget.id.length - 3)
  if (streets[placeName] == null && locations[placeName] == null && placeName != "Outskirts") {
    console.log("dragged to a place that's not a place");
    return;
  }
  if (!e.currentTarget.getElementsByClassName("placemonsters").length) {
    console.log("dragged to a place that has no monsters div");
    return;
  }
  e.preventDefault();
  e.currentTarget.getElementsByClassName("placemonsters")[0].appendChild(dragged);
  monsterChoice[dragged.monsterIdx] = placeName;
}

function dropPossession(e) {
  if (dragged.handle == null) {
    console.log("dragged elem did not have a handle");
    return;
  }
  if (!e.currentTarget.classList.contains("playertop")) {
    console.log("dragged to something that's not a player");
    return;
  }
  if (e.currentTarget.idx == null) {
    console.log("dragged to a player without an id");
    return;
  }
  e.preventDefault();
  ws.send(JSON.stringify({"type": "give", "recipient": e.currentTarget.idx, "handle": dragged.handle}));
}

function dropDollars(dragged, e) {
  if (!e.currentTarget.classList.contains("playertop")) {
    console.log("dragged to something that's not a player");
    return;
  }
  if (e.currentTarget.idx == null) {
    console.log("dragged to a player without an id");
    return;
  }
  let colonIdx = dragged.innerText.indexOf(":");
  let valueText = dragged.innerText.substring(colonIdx+1).trim();
  let maxAmount = parseInt(valueText, 10);
  if (isNaN(maxAmount)) {
    console.log("dragged a non-integer number of dollars");
    return;
  }
  e.preventDefault();
  showGive(maxAmount, e.currentTarget.idx);
}

function showGive(maxAmount, idx) {
  let datalist = document.getElementById("giveoptions");
  while (datalist.children.length) {
    datalist.removeChild(datalist.firstChild);
  }
  for (let i = 0; i <= maxAmount; i++) {
    let option = document.createElement("OPTION");
    option.value = i;
    option.label = i;
    datalist.appendChild(option);
  }
  document.getElementById("giveslider").max = maxAmount;
  document.getElementById("giveselect").style.display = "flex";
  document.getElementById("giveselect").idx = idx;
  updateGive(document.getElementById("giveslider").value);
}

function updateGive(value) {
  document.getElementById("givevalue").value = value;
}

function cancelGive(e) {
  document.getElementById("giveselect").style.display = "none";
}

function finishGive(e) {
  document.getElementById("giveselect").style.display = "none";
  let msg = {
    "type": "give",
    "recipient": document.getElementById("giveselect").idx,
    "idx": "dollars",
    "amount": parseInt(document.getElementById("giveslider").value, 10),
  };
  ws.send(JSON.stringify(msg));
}

function makeCheck(e) {
  let t = e.currentTarget;
  let check_type = t.value;
  let modifier = document.getElementById("modifier").value;
  ws.send(JSON.stringify({"type": "check", "modifier": modifier, "check_type": check_type}));
}

function prevChar(e) {
  let sortedKeys = Object.keys(allCharacters).sort();
  let currentIdx = sortedKeys.indexOf(charChoice);
  if (currentIdx <= 0) {
    charChoice = sortedKeys[sortedKeys.length-1];
  } else {
    charChoice = sortedKeys[currentIdx-1];
  }
  drawChosenChar(charChoice);
}

function nextChar(e) {
  let sortedKeys = Object.keys(allCharacters).sort();
  let currentIdx = sortedKeys.indexOf(charChoice);
  if (currentIdx >= sortedKeys.length - 1) {
    charChoice = sortedKeys[0];
  } else {
    charChoice = sortedKeys[currentIdx+1];
  }
  drawChosenChar(charChoice);
}

function selectChar(e) {
  ws.send(JSON.stringify({"type": "join", "char": charChoice}));
}

function start(e) {
  ws.send(JSON.stringify({"type": "start"}));
}

function done(e) {
  ws.send(JSON.stringify({"type": "choice", "choice": "done"}));
}

function doneSliders(e) {
  ws.send(JSON.stringify({"type": "set_slider", "name": "done"}));
}

function updateCharacters(newCharacters) {
  for (let character of newCharacters) {
    let place = document.getElementById("place" + character.place + "chars");
    if (place == null) {
      // TODO: may need to remove the character instead of letting them stay on the board.
      console.log("Unknown place " + character.place);
      continue;
    }
    if (characters[character.name] == null) {
      characters[character.name] = createCharacterDiv(character.name);
      place.appendChild(characters[character.name]);
    } else {
      animateMovingDiv(characters[character.name], place);
    }
  }
}

function showMonsters(placeDiv, name) {
  let box = document.getElementById("monsterdetailsbox");
  while (box.children.length) {
    box.removeChild(box.firstChild);
  }
  for (let monsterDiv of placeDiv.getElementsByClassName("monster")) {
    let container = document.createElement("DIV");
    container.appendChild(createMonsterDiv(monsterDiv.monsterName, 2, ""));
    container.appendChild(createMonsterDiv(monsterDiv.monsterName, 2, "back"));
    box.appendChild(container);
  }
  document.getElementById("monsterdetailsname").innerText = name;
  document.getElementById("monsterdetails").style.display = "flex";
}

function hideMonsters(e) {
  document.getElementById("monsterdetails").style.display = "none";
}

function updateMonsters(monster_list) {
  for (let i = 0; i < monster_list.length; i++) {
    let monster = monster_list[i];
    let monsterPlace = monsterChoice[i] || null;
    // If we're moving monsters, remember where the user has placed the monster.
    if (monsterPlace == null && monster != null && monster.place && monster.place != "cup") {
      monsterPlace = monster.place;
    }
    if (monsterPlace == null) {
      if (monsters[i] != null) {
        monsters[i].parentNode.removeChild(monsters[i]);  // TODO: animate
        monsters[i] = null;
      }
      continue;
    }
    let place = document.getElementById("place" + monsterPlace + "monsters");
    if (place == null) {
      console.log("Unknown place " + monster.place);
      continue;
    }
    if (monsters[i] == null) {
      monsters[i] = createMonsterDiv(monster.name, 1, "");
      monsters[i].monsterIdx = i;
      place.appendChild(monsters[i]);
    } else {
      animateMovingDiv(monsters[i], place);
    }
  }
}

function updateChoices(choice) {
  let uichoice = document.getElementById("uichoice");
  let uicardchoice = document.getElementById("uicardchoice");
  let pDiv;
  if (!document.getElementsByClassName("you").length) {
    pDiv = document.createElement("DIV");  // Dummy div.
  } else {
    pDiv = document.getElementsByClassName("you")[0].getElementsByClassName("possessions")[0];
  }
  for (let place of document.getElementsByClassName("placeselect")) {
    place.classList.remove("selectable");
    place.classList.remove("unselectable");
    place.innerText = "";
  }
  if (choice == null || choice.monsters != null) {
    uichoice.style.display = "none";
    itemsToChoose = null;
    itemChoice = [];
    pDiv.classList.remove("choose");
    return;
  }
  // Set display style for uichoice div.
  uichoice.style.display = "flex";
  if (choice.cards != null) {
    uichoice.style.maxWidth = "100%";
  } else {
    uichoice.style.maxWidth = "40%";
  }
  // Clean out any old choices it may have.
  while (uichoice.getElementsByClassName("choice").length) {
    uichoice.removeChild(uichoice.getElementsByClassName("choice")[0]);
  }
  while (uicardchoice.getElementsByClassName("cardholder").length) {
    uicardchoice.removeChild(uicardchoice.getElementsByClassName("cardholder")[0]);
  }
  // Set prompt.
  document.getElementById("uiprompt").innerText = choice.prompt;
  if (choice.items != null) {
    itemsToChoose = choice.items;
    pDiv.classList.add("choose");
    addChoices(uichoice, ["Done Choosing Items"]);
  } else {
    itemsToChoose = null;
    itemChoice = [];
    pDiv.classList.remove("choose");
    if (choice.places != null) {
      updatePlaceChoices(uichoice, choice.places, choice.annotations);
    } else if (choice.cards != null) {
      addCardChoices(uicardchoice, choice.cards, choice.invalid_choices, choice.annotations);
    } else {
      addChoices(uichoice, choice.choices, choice.invalid_choices);
    }
  }
}

function updateMonsterChoices(choice, monsterList) {
  // TODO: indicate how many monsters each location should receive.
  let uimonsterchoice = document.getElementById("uimonsterchoice");
  let choicesBox = document.getElementById("monsterchoices");
  if (choice == null || choice.monsters == null) {
    uimonsterchoice.style.display = "none";
    for (let monsterIdx in monsters) {
      if (monsters[monsterIdx] == null) {
        continue;
      }
      monsters[monsterIdx].draggable = false;
      monsters[monsterIdx].ondragstart = null;
      monsters[monsterIdx].ondragend = null;
    }
    monsterChoice = {};
    return;
  }
  uimonsterchoice.style.display = "flex";
  for (let monsterIdx of choice.monsters) {
    if (monsters[monsterIdx] == null) {
      monsters[monsterIdx] = createMonsterDiv(monsterList[monsterIdx].name, 1, "");
      monsters[monsterIdx].monsterIdx = monsterIdx;
      monsters[monsterIdx].draggable = true;
      monsters[monsterIdx].ondragstart = dragStart;
      monsters[monsterIdx].ondragend = dragEnd;
      choicesBox.appendChild(monsters[monsterIdx]);
    }
  }
}

function addCardChoices(cardChoice, cards, invalidChoices, annotations) {
  if (!cards) {
    return;
  }
  for (let [idx, card] of cards.entries()) {
    let holder = document.createElement("DIV");
    holder.classList.add("cardholder");
    let div = document.createElement("DIV");
    div.classList.add("cardchoice");
    div.onclick = function(e) { makeChoice(card); };
    let asset = getAsset(card, "");
    let elemWidth = asset.naturalWidth || asset.width;
    let elemHeight = asset.naturalHeight || asset.height;
    div.style.width = elemWidth + "px";
    div.style.height = elemHeight + "px";
    let cnv = document.createElement("CANVAS");
    cnv.width = elemWidth;
    cnv.height = elemHeight;
    cnv.classList.add("markercnv");  // TODO: use a better class name for this
    renderAssetToCanvas(cnv, card, "");
    div.appendChild(cnv);
    holder.appendChild(div);
    let desc = document.createElement("DIV");
    if (annotations != null && annotations.length > idx) {
      desc.innerText = annotations[idx];
    }
    holder.appendChild(desc);
    cardChoice.appendChild(holder);
    let spacer = document.createElement("DIV");
    spacer.style.height = "100%";
    spacer.style.width = 0.1 * elemWidth + "px";
    cardChoice.appendChild(spacer);
  }
  cardChoice.removeChild(cardChoice.lastChild);
}

function addChoices(uichoice, choices, invalidChoices) {
  for (let [idx, c] of choices.entries()) {
    let div = document.createElement("DIV");
    div.classList.add("choice");
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      div.classList.add("unchoosable");
    } else {
      div.classList.add("choosable");
    }
    div.innerText = c;
    div.onclick = function(e) { makeChoice(c); };
    uichoice.appendChild(div);
  }
}

function updateUsables(usables, choice) {
  let uiuse = document.getElementById("uiuse");
  let pDiv;
  if (!document.getElementsByClassName("you").length) {
    pDiv = document.createElement("DIV");  // Dummy div.
  } else {
    pDiv = document.getElementsByClassName("you")[0].getElementsByClassName("possessions")[0];
  }
  uiuse.style.display = "none";
  if (usables == null) {
    pDiv.classList.remove("use");
    return;
  }
  if (choice == null) {
    uiuse.style.display = "flex";
  }
  pDiv.classList.add("use");
  let posList = pDiv.getElementsByClassName("possession");
  for (let pos of posList) {
    if (usables.includes(pos.handle)) {
      pos.classList.add("usable");
      pos.classList.remove("unusable");
    } else {
      pos.classList.remove("usable");
      if (choice == null) {  // TODO: this is hacky.
        pos.classList.add("unusable");
      }
    }
  }
  let includesAbility = false;
  for (let val of usables) {
    if (val != "clues" && val != "trade") {
      includesAbility = true;
    }
  }
  document.getElementById("usetext").innerText = "Use Items or Abilities";
  document.getElementById("doneusing").innerText = "Done Using";
  if (!includesAbility) {
    if (usables.includes("trade")) {
      document.getElementById("usetext").innerText = "Trade?";
      document.getElementById("doneusing").innerText = "Done Trading";
    } else if (usables.includes("clues")) {
      document.getElementById("usetext").innerText = "Use clues?";
      document.getElementById("doneusing").innerText = "Done Using";
    }
  }
  // TODO: make clues change apperance when usable
}

function createMonsterDiv(name, scale, side) {
  let width = document.getElementById("boardcanvas").width;
  let markerHeight = width * markerHeightRatio;
  let div = document.createElement("DIV");
  div.style.width = + markerHeight * scale + "px";
  div.style.height = markerHeight * scale + "px";
  div.classList.add("monster");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("monstercnv");
  cnv.width = markerHeight * scale;
  cnv.height = markerHeight * scale;
  renderAssetToCanvas(cnv, name, side);
  div.appendChild(cnv);
  div.monsterName = name;
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

function animateMovingDiv(div, destParent) {
  if (div.parentNode == destParent) {
    return;
  }
  let divToShow = null;
  if (destParent.classList.contains("worldchars")) {
    divToShow = destParent.parentNode.parentNode;
  } else if (div.parentNode.classList.contains("worldchars")) {
    divToShow = div.parentNode.parentNode.parentNode;
  }
  if (divToShow == null) {
    // Moving from the board to the board. Just animate the marker's movement.
    moveAndTranslateNode(div, destParent);
    runningAnim.push(true);  // Doesn't really matter what we push.
    div.ontransitionend = function() { div.classList.remove("moving"); doneAnimating(div); finishAnim(); };
    div.ontransitioncancel = function() { div.classList.remove("moving"); doneAnimating(div); finishAnim(); };
    setTimeout(function() { div.classList.add("moving"); div.style.transform = "none"; }, 10);
    return;
  }

  // Moving from or to another world. Show the other world, then animate, then unshow.
  let lastAnim = function() {
    divToShow.ontransitionend = function() { doneAnimating(divToShow); finishAnim(); };
    divToShow.ontransitioncancel = function() { doneAnimating(divToShow); finishAnim(); };
    divToShow.classList.remove("shown");
  }
  let continueAnim = function() {
    doneAnimating(divToShow);
    moveAndTranslateNode(div, destParent);
    div.ontransitionend = function() { div.classList.remove("moving"); doneAnimating(div); setTimeout(lastAnim, 10); };
    div.ontransitioncancel = function() { div.classList.remove("moving"); doneAnimating(div); setTimeout(lastAnim, 10); };
    setTimeout(function() { div.classList.add("moving"); div.style.transform = "none"; }, 10);
  }
  runningAnim.push(true);
  divToShow.ontransitionend = continueAnim;
  divToShow.ontransitioncancel = continueAnim;
  divToShow.classList.add("shown");
}

function moveAndTranslateNode(div, destParent) {
  let oldRect = div.getBoundingClientRect();
  div.parentNode.removeChild(div);
  destParent.appendChild(div);
  let newRect = div.getBoundingClientRect();
  let diffX = Math.floor((oldRect.left - newRect.left) / scale);
  let diffY = Math.floor((oldRect.top - newRect.top) / scale);
  // TODO: also transition the destination characters.
  div.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px)";
}

function updatePlaces(places) {
  for (let placeName in places) {
    let place = places[placeName];
    let gateDiv = document.getElementById("place" + placeName + "gate");
    if (gateDiv != null) {  // Some places cannot have gates.
      updateGate(place, gateDiv);
    }
    if (place.clues != null) {
      updateClues(place);
    }
  }
}

function updateClues(place) {
  let boardWidth = document.getElementById("boardcanvas").width;
  let size = Math.floor(radiusRatio * boardWidth * 3 / 4);
  // TODO: maybe put them somewhere else?
  let charsDiv = document.getElementById("place" + place.name + "chars");
  let numClues = charsDiv.getElementsByClassName("clue").length;
  while (numClues > place.clues) {
    charsDiv.removeChild(charsDiv.getElementsByClassName("clue")[0]);
    numClues--;
  }
  while (numClues < place.clues) {
    let clueDiv = document.createElement("DIV");
    clueDiv.classList.add("clue");
    clueDiv.style.height = size + "px";
    clueDiv.style.width = size + "px";
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnv.width = size;
    cnv.height = size;
    renderAssetToCanvas(cnv, "Clue", "");
    clueDiv.appendChild(cnv);
    charsDiv.appendChild(clueDiv);
    numClues++;
  }
}

function updateGate(place, gateDiv) {
  let gateCnv = gateDiv.getElementsByTagName("CANVAS")[0];
  if (place.gate) {  // TODO: sealed
    renderAssetToCanvas(gateCnv, "Gate " + place.gate.name, "");
    gateDiv.classList.add("placegatepresent");
  } else {
    let ctx = gateCnv.getContext("2d");
    ctx.clearRect(0, 0, gateCnv.width, gateCnv.height);
    gateDiv.classList.remove("placegatepresent");
  }
}

function updatePlaceChoices(uichoice, places, annotations) {
  let notFound = [];
  for (let place of document.getElementsByClassName("placeselect")) {
    place.classList.remove("selectable");
    place.classList.add("unselectable");
    place.innerText = "❌";
  }
  for (let [idx, placeName] of places.entries()) {
    let place = document.getElementById("place" + placeName + "select");
    if (place == null) {
      notFound.push(placeName);
      continue;
    }
    place.classList.add("selectable");
    place.classList.remove("unselectable");
    place.innerText = "Choose";
    if (annotations != null && annotations.length > idx) {
      place.innerText = annotations[idx];
    } else {
      place.innerText = "Choose";
    }
  }
  if (notFound.length) {
    addChoices(uichoice, notFound);
  }
}

function updateDone(gameStage, sliders) {
  let btn = document.getElementById("done").firstChild;
  if (gameStage == "setup") {
    btn.innerText = "Start";
    btn.onclick = start;
    return;
  }
  btn.innerText = "Done";
  if (sliders) {
    btn.onclick = doneSliders;
  } else {
    btn.onclick = done;
  }
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

function updateCharacterSelect(characters, playerIdx, pendingName, pendingChars) {
  let charSelect = document.getElementById("charselect");
  if (playerIdx != null) {  // TODO: choosing a new character.
    charSelect.style.display = "none";
    return;
  }
  charSelect.style.display = "flex";
  // TODO: choosing a different character after picking a character.
  if (pendingName != null) {
    drawChosenChar(pendingName);
    document.getElementById("choosecharbutton").innerText = "Chosen";
    return;
  }
  document.getElementById("choosecharbutton").innerText = "Choose";
  if (charChoice == null) {
    let keys = Object.keys(allCharacters);
    for (let character of characters) {
      let idx = keys.indexOf(character.name);
      if (idx >= 0) {
        keys.splice(idx, 1);
      }
    }
    for (let name of pendingChars) {
      let idx = keys.indexOf(name);
      if (idx >= 0) {
        keys.splice(idx, 1);
      }
    }
    charChoice = keys.sort()[0];
  }
  drawChosenChar(charChoice);
}

function drawChosenChar(name) {
  let cnv = document.getElementById("charchoicecnv");
  renderAssetToCanvas(cnv, name, "");
}

function updateCharacterSheets(characters, playerIdx, firstPlayer) {
  let rightUI = document.getElementById("uiright");
  for (let [idx, character] of characters.entries()) {
    let sheet;
    if (rightUI.getElementsByClassName("player").length <= idx) {
      sheet = createCharacterSheet(idx, character, rightUI);
    } else {
      sheet = rightUI.getElementsByClassName("player")[idx];
    }
    let order = idx - firstPlayer;
    if (order < 0) {
      order += characters.length;
    }
    updateCharacterSheet(sheet, character, order, playerIdx == idx);
  }
  let unCollapsed = false;
  for (let sheet of document.getElementsByClassName("player")) {
    if (!sheet.classList.contains("collapsed")) {
      unCollapsed = true;
      break;
    }
  }
  if (!unCollapsed && document.getElementsByClassName("you").length) {
    document.getElementsByClassName("you")[0].classList.remove("collapsed");
  }
}

function createCharacterSheet(idx, character, rightUI) {
  let div = document.createElement("DIV");
  div.classList.add("player");
  div.classList.add("collapsed");

  let charTop = document.createElement("DIV");
  charTop.classList.add("playertop");
  charTop.idx = idx;
  charTop.ondrop = drop;
  charTop.ondragenter = dragEnter;
  charTop.ondragover = dragOver;
  let charPic = document.createElement("DIV");
  charPic.classList.add("playerpicouter");
  charPic.onclick = function(e) { expandSheet(div) };
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("playerpiccanvas");
  charPic.appendChild(cnv);
  charTop.appendChild(charPic);

  let charInfo = document.createElement("DIV");
  charInfo.classList.add("playerinfo");
  let charName = document.createElement("DIV");
  charName.classList.add("playername");
  charName.onclick = function(e) { expandSheet(div) };
  charInfo.appendChild(charName);
  let charStats = document.createElement("DIV");
  charStats.classList.add("playerstats");
  charInfo.appendChild(charStats);
  charTop.appendChild(charInfo);
  div.appendChild(charTop);

  let sliders = document.createElement("DIV");
  sliders.classList.add("sliders");
  let spacer = document.createElement("DIV");
  spacer.classList.add("sliderspacer");
  sliders.appendChild(spacer);
  div.appendChild(sliders);
  let possessions = document.createElement("DIV");
  possessions.classList.add("possessions");
  div.appendChild(possessions);
  let spacer2 = document.createElement("DIV");
  spacer2.classList.add("sliderspacer");
  div.appendChild(spacer2);

  rightUI.appendChild(div);
  return div;
}

function expandSheet(sheetDiv) {
  for (let sheet of document.getElementsByClassName("player")) {
    if (sheet == sheetDiv) {
      sheet.classList.remove("collapsed");
    } else {
      sheet.classList.add("collapsed");
    }
  }
}

function updateCharacterSheet(sheet, character, order, isPlayer) {
  let width = document.getElementById("boardcanvas").width;
  let markerWidth = width * markerWidthRatio;
  let markerHeight = width * markerHeightRatio;
  let picDiv = sheet.getElementsByClassName("playerpicouter")[0];
  let cnv = sheet.getElementsByClassName("playerpiccanvas")[0];
  picDiv.style.width = markerWidth + "px";
  picDiv.style.height = markerHeight + "px";
  cnv.width = markerWidth;
  cnv.height = markerHeight;
  renderAssetToCanvas(cnv, character.name, "");
  if (isPlayer) {
    sheet.classList.add("you");
  } else {
    sheet.classList.remove("you");
  }
  sheet.style.order = order;
  sheet.getElementsByClassName("playername")[0].innerText = character.name;
  let stats = sheet.getElementsByClassName("playerstats")[0];
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
    // TODO: make this nicer
    if (isPlayer && cfg[0] == "clues") {
      statDiv.classList.add("clue");
      statDiv.onclick = function(e) { useAsset("clues") };
    }
    if (isPlayer && cfg[0] == "dollars") {
      statDiv.classList.add("dollars");
      statDiv.draggable = true;
      statDiv.ondragstart = dragStart;
      statDiv.ondragend = dragEnd;
    }
    stats.appendChild(statDiv);
  }
  updateSliders(sheet, character, isPlayer);
  updatePossessions(sheet, character, isPlayer);
}

function updateSliders(sheet, character, isPlayer) {
  for (let sliderName in character.sliders) {
    let sliderDiv = sheet.getElementsByClassName("slider_" + sliderName)[0];
    if (sliderDiv == null) {
      sliderDiv = createSlider(sliderName, character.sliders[sliderName], isPlayer);
      sheet.getElementsByClassName("sliders")[0].appendChild(sliderDiv);
      let spacerDiv = document.createElement("DIV");
      spacerDiv.classList.add("sliderspacer");
      sheet.getElementsByClassName("sliders")[0].appendChild(spacerDiv);
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

function createSlider(sliderName, sliderInfo, isPlayer) {
  let firstName = sliderName.split("_")[0];
  let secondName = sliderName.split("_")[1];
  let sliderDiv = document.createElement("DIV");
  sliderDiv.classList.add("slider");
  sliderDiv.classList.add("slider_" + sliderName);
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
    if (isPlayer) {
      pairDiv.onclick = function(e) { setSlider(sliderName, idx); };
    }
    sliderDiv.appendChild(pairDiv);
  }
  return sliderDiv;
}

function updatePossessions(sheet, character, isPlayer) {
  let pDiv = sheet.getElementsByClassName("possessions")[0];
  while (pDiv.firstChild) {
    pDiv.removeChild(pDiv.firstChild);
  }
  for (let pos of character.possessions) {
    pDiv.appendChild(createPossession(pos, isPlayer));
  }
}

function createPossession(info, isPlayer) {
  let width = document.getElementById("boardcanvas").width;
  let posWidth = 3 * width * markerWidthRatio / 2;
  let posHeight = 3 * width * markerHeightRatio / 2;
  let div = document.createElement("DIV");
  div.classList.add("possession");
  if (info.active) {
    div.classList.add("active");
  }
  div.handle = info.handle;
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
  // TODO: show some information about bonuses that aren't active right now
  let handle = info.handle;
  if (isPlayer) {
    if (itemChoice.includes(handle)) {
      div.classList.add("chosen");
    }
    div.onclick = function(e) { clickAsset(div, handle); };
    div.draggable = true;
    div.ondragstart = dragStart;
    div.ondragend = dragEnd;
  }
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
