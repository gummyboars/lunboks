ws = null;
dragged = null;
characters = {};
portraits = {};
monsters = {};
allCharacters = {};
scale = 1;
minItemsToChoose = null;
maxItemsToChoose = null;
itemChoice = [];
monsterChoice = {};
charChoice = null;
runningAnim = [];
messageQueue = [];
statTimeout = null;
cardsStyle = "flex";

function init() {
  let params = new URLSearchParams(window.location.search);
  if (!params.has("game_id")) {
    showError("No game id specified.");
    return;
  }
  let gameId = params.get("game_id");
  let promise = loadImages();
  promise.then(function() { continueInit(gameId); }, showError);
}

function continueInit(gameId) {
  ws = new WebSocket("ws://" + window.location.hostname + ":8081/" + gameId);
  ws.onmessage = onmsg;
  renderAssetToDiv(document.getElementById("board"), "board");
  let width = document.getElementById("boardcanvas").width;
  let cont = document.getElementById("board");
  for (let [placeType, places] of [["location", locations], ["street", streets]]) {
    for (let name in places) {
      let div = document.createElement("DIV");
      div.id = "place" + name;
      div.classList.add("place");
      div.onmouseenter = bringTop;
      div.onmouseleave = returnBottom;
      let box = document.createElement("DIV");
      box.id = "place" + name + "box";
      box.classList.add("placebox");
      box.ondrop = drop;
      box.ondragenter = dragEnter;
      box.ondragover = dragOver;
      div.appendChild(box);
      let monstersDiv = document.createElement("DIV");
      monstersDiv.id = "place" + name + "monsters";
      monstersDiv.classList.add("placemonsters");
      monstersDiv.onclick = function(e) { showMonsters(monstersDiv, name); };
      let details = document.createElement("DIV");
      details.id = "place" + name + "details";
      details.classList.add("placedetails");
      if (places[name].y < 0.5) {
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
      details.appendChild(chars);
      let gateDiv = document.createElement("DIV");
      gateDiv.id = "place" + name + "gate";
      gateDiv.classList.add("placegate");
      details.appendChild(gateDiv);
      let gateCont = document.createElement("DIV");
      gateCont.classList.add("gatecontainer", "cnvcontainer");
      gateDiv.appendChild(gateCont);
      let gate = document.createElement("CANVAS");
      gate.classList.add("gate");
      gateCont.appendChild(gate);
      let select = document.createElement("DIV");
      select.id = "place" + name + "select";
      select.classList.add("placeselect", placeType);
      select.onclick = function(e) { clickPlace(name); };
      details.appendChild(select);
      cont.appendChild(div);

      let opt = document.createElement("OPTION");
      opt.value = name;
      opt.text = name;
      document.getElementById("placechoice").appendChild(opt);
    }
  }
  placeLocations();
  for (let name of monsterNames) {
    let opt = document.createElement("OPTION");
    opt.value = name;
    opt.text = name;
    document.getElementById("monsterchoice").appendChild(opt);
  }
  for (let name of otherWorlds) {
    let div = document.createElement("DIV");
    div.id = "world" + name;
    div.classList.add("world");
    let worldbox = document.createElement("DIV");
    worldbox.id = "world" + name + "box";
    worldbox.classList.add("worldbox");
    for (let [i, side] of [[1, "left"], [2, "right"]]) {
      let world = document.createElement("DIV");
      world.id = "place" + name + i + "chars";
      world.classList.add("world" + side, "worldchars");
      worldbox.appendChild(world);
      let portrait = document.createElement("DIV");
      portrait.id = "place" + name + i + "portraits";
      portrait.classList.add("portrait" + side);
      worldbox.appendChild(portrait);
    }
    div.appendChild(worldbox);
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("worldcnvcontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("worldcnv");
    cnvContainer.appendChild(cnv);
    div.appendChild(cnvContainer);
    document.getElementById("worlds").appendChild(div);
    renderAssetToDiv(cnvContainer, name);
  }
  for (let extra of ["Lost", "Sky", "Outskirts"]) {
    renderAssetToDiv(document.getElementById("place" + extra), extra);
    if (extra != "Lost") {
      let box = document.getElementById("place" + extra + "box");
      let monstersDiv = box.getElementsByClassName("placemonsters")[0];
      monstersDiv.onclick = function(e) { showMonsters(monstersDiv, extra); };
    }
  }
  let outskirtsBox = document.getElementById("placeOutskirtsbox");
  outskirtsBox.ondragenter = dragEnter;
  outskirtsBox.ondragover = dragOver;
  outskirtsBox.ondrop = drop;
  window.addEventListener("resize", function() {
    clearTimeout(statTimeout);
    statTimeout = setTimeout(updateStats, 255);
  });
}

function placeLocations() {
  for (let [placeType, places] of [["location", locations], ["street", streets]]) {
    for (let name in places) {
      let div = document.getElementById("place" + name);
      if (!setDivXYPercent(div, "board", name)) {
        div.style.top = 100 * places[name].y + "%";
        div.style.left = 100 * places[name].x + "%";
      }
    }
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
function doneAnimating(div) {
  div.ontransitionend = null;
  div.ontransitioncancel = null;
}
function finishAnim() {
  runningAnim.shift();
  if (messageQueue.length && !runningAnim.length) {
    handleData(messageQueue.shift());
  } else {
    updateStats();  // TODO: this is hacky
  }
}
function handleData(data) {
  allCharacters = data.all_characters;
  updateCharacterSelect(data.characters, data.player_idx, data.pending_name, data.pending_chars);
  updateCharacterSheets(data.characters, data.player_idx, data.first_player);
  updateBottomText(data.game_stage, data.turn_phase, data.characters, data.turn_idx, data.player_idx);
  updateGlobals(data.environment, data.rumor);
  updatePlaces(data.places);
  updateCharacters(data.characters);
  updateSliderButton(data.sliders);
  updateChoices(data.choice);
  updateMonsters(data.monsters);
  updateMonsterChoices(data.choice, data.monsters);
  updateUsables(data.usables, data.choice);
  updateDice(data.dice, data.roll, data.roller == data.player_idx);
  updateEventLog(data.event_log);
  if (messageQueue.length && !runningAnim.length) {
    handleData(messageQueue.shift());
  } else {
    updateStats();  // TODO: this is hacky
  }
}

function clickPlace(place) {
  ws.send(JSON.stringify({"type": "choice", "choice": place}));
}

function setSlider(sliderName, sliderValue) {
  ws.send(JSON.stringify({"type": "set_slider", "name": sliderName, "value": sliderValue}));
}

function roll(e) {
  ws.send(JSON.stringify({"type": "roll"}));
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

function bringTop(e) {
  let node = e.currentTarget;
  node.origZ = node.style.zIndex;
  node.style.zIndex = 5;
}

function returnBottom(e) {
  let node = e.currentTarget;
  node.style.zIndex = node.origZ || 0;
}

function makeChoice(val) {
  ws.send(JSON.stringify({"type": "choice", "choice": val}));
}

function chooseItems(e) {
  if ((minItemsToChoose != null && itemChoice.length < minItemsToChoose) ||
      (maxItemsToChoose != null && itemChoice.length > maxItemsToChoose)) {
    document.getElementById("errorText").holdSeconds = 3;
    document.getElementById("errorText").style.opacity = 1.0;
    let errmsg = "Expected between " + minItemsToChoose + " and " + maxItemsToChoose + " items.";
    document.getElementById("errorText").innerText = errmsg;
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
  let maxAmount = parseInt(dragged.statValue, 10);
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
    "handle": "dollars",
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
    updatePortraitDiv(character.name, character.place);
    if (characters[character.name] == null) {
      characters[character.name] = createCharacterDiv(character.name);
      place.appendChild(characters[character.name]);
      renderAssetToDiv(characters[character.name].getElementsByClassName("cnvcontainer")[0], character.name);
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
  document.getElementById("monsterdetailsname").innerText = name;
  document.getElementById("monsterdetails").style.display = "flex";
  for (let monsterDiv of placeDiv.getElementsByClassName("monster")) {
    let container = document.createElement("DIV");
    let frontDiv = createMonsterDiv(monsterDiv.monsterName, "big");
    container.appendChild(frontDiv);
    let backDiv = createMonsterDiv(monsterDiv.monsterName, "big");
    container.appendChild(backDiv);
    box.appendChild(container);
    renderAssetToDiv(frontDiv, monsterDiv.monsterName);
    renderAssetToDiv(backDiv, monsterDiv.monsterName + " back");
  }
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
      monsters[i] = createMonsterDiv(monster.name);
      monsters[i].monsterIdx = i;
      place.appendChild(monsters[i]);
      renderAssetToDiv(monsters[i].getElementsByClassName("cnvcontainer")[0], monster.name);
    } else {
      animateMovingDiv(monsters[i], place);
    }
  }
}

function updateSliderButton(sliders) {
  if (sliders) {
    document.getElementById("uiprompt").innerText = sliders.prompt;
    document.getElementById("donesliders").style.display = "inline-block";
  } else {
    document.getElementById("donesliders").style.display = "none";
  }
}

function toggleCards(e) {
  if (cardsStyle == "flex") {
    cardsStyle = "none";
  } else {
    cardsStyle = "flex";
  }
  document.getElementById("uicardchoice").style.display = cardsStyle;
  setCardButtonText();
}

function setCardButtonText() {
  if (cardsStyle == "flex") {
    document.getElementById("togglecards").innerText = "Hide Cards";
  } else {
    document.getElementById("togglecards").innerText = "Show Cards";
  }
}

function updateChoices(choice) {
  let btn = document.getElementById("doneitems");
  let uichoice = document.getElementById("uichoice");
  let uicardchoice = document.getElementById("uicardchoice");
  let cardtoggle = document.getElementById("togglecards");
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
  uichoice.style.display = "none";
  uicardchoice.style.display = "none";
  btn.style.display = "none";
  cardtoggle.style.display = "none";
  if (choice == null || choice.monsters != null) {
    minItemsToChoose = null;
    maxItemsToChoose = null;
    itemChoice = [];
    pDiv.classList.remove("choose");
    return;
  }
  // Set display style for uichoice div.
  if (choice.cards != null) {
    uicardchoice.style.display = cardsStyle;
    cardtoggle.style.display = "inline-block";
    setCardButtonText();
  } else if (!choice.items) {
    uichoice.style.display = "flex";
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
  if (choice.items) {
    minItemsToChoose = choice.min_items;
    maxItemsToChoose = choice.max_items;
    pDiv.classList.add("choose");
    btn.style.display = "inline-block";
  } else {
    minItemsToChoose = null;
    maxItemsToChoose = null;
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
  let uiprompt = document.getElementById("uiprompt");
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
  uiprompt.innerText = "Drag Monsters to Gates";
  uimonsterchoice.style.display = "flex";
  for (let monsterIdx of choice.monsters) {
    if (monsters[monsterIdx] == null) {
      monsters[monsterIdx] = createMonsterDiv(monsterList[monsterIdx].name);
      monsters[monsterIdx].monsterIdx = monsterIdx;
      monsters[monsterIdx].draggable = true;
      monsters[monsterIdx].ondragstart = dragStart;
      monsters[monsterIdx].ondragend = dragEnd;
      choicesBox.appendChild(monsters[monsterIdx]);
      renderAssetToDiv(monsters[monsterIdx].getElementsByClassName("cnvcontainer")[0], monsterList[monsterIdx].name);
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
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      holder.classList.add("unchoosable");
    }
    let div = document.createElement("DIV");
    div.classList.add("cardchoice", "cnvcontainer");
    div.onclick = function(e) { makeChoice(card); };
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("markercnv");  // TODO: use a better class name for this
    div.appendChild(cnv);
    holder.appendChild(div);
    let desc = document.createElement("DIV");
    desc.classList.add("desc");
    if (annotations != null && annotations.length > idx) {
      desc.innerText = annotations[idx];
    }
    holder.appendChild(desc);
    cardChoice.appendChild(holder);
    renderAssetToDiv(div, card);
  }
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

function createMonsterDiv(name, classPrefix) {
  classPrefix = classPrefix || "";
  let div = document.createElement("DIV");
  div.classList.add(classPrefix + "monster");
  let cnvContainer = document.createElement("DIV");
  cnvContainer.classList.add(classPrefix + "monstercontainer", "cnvcontainer");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("monstercnv");
  cnvContainer.appendChild(cnv);
  div.appendChild(cnvContainer);
  div.monsterName = name;
  return div;
}

function createCharacterDiv(name) {
  let div = document.createElement("DIV");
  div.classList.add("marker");
  let cnvContainer = document.createElement("DIV");
  cnvContainer.classList.add("markercontainer", "cnvcontainer");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("markercnv");
  cnvContainer.appendChild(cnv);
  div.appendChild(cnvContainer);
  return div;
}

function createCharacterPortrait(name) {
  let div = document.createElement("DIV");
  div.classList.add("portrait", "cnvcontainer");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("markercnv");
  div.appendChild(cnv);
  return div;
}

function updatePortraitDiv(charName, destName) {
  let charsDiv = document.getElementById("place" + destName + "chars");
  if (charsDiv.classList.contains("worldchars")) {
    if (portraits[charName] == null) {
      portraits[charName] = createCharacterPortrait(charName);
    }
    let dest = document.getElementById("place" + destName + "portraits");
    dest.appendChild(portraits[charName]);
    renderAssetToDiv(portraits[charName], charName + " picture");
  } else {
    if (portraits[charName] != null) {
      portraits[charName].parentNode.removeChild(portraits[charName]);
      portraits[charName] = null;
    }
  }
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
    if (place.sealed != null) {
      updateSeal(place);
    }
    if (place.clues != null) {
      updateClues(place);
    }
  }
}

function updateClues(place) {
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
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("cluecontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnvContainer.appendChild(cnv);
    clueDiv.appendChild(cnvContainer);
    charsDiv.appendChild(clueDiv);
    renderAssetToDiv(cnvContainer, "Clue");
    numClues++;
  }
}

function updateSeal(place) {
  let charsDiv = document.getElementById("place" + place.name + "chars");
  let hasSeal = charsDiv.getElementsByClassName("seal").length;
  if (!place.sealed && hasSeal) {
    charsDiv.removeChild(charsDiv.getElementsByClassName("seal")[0]);
  } else if (place.sealed && !hasSeal) {
    let sealDiv = document.createElement("DIV");
    sealDiv.classList.add("seal");
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("cluecontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnvContainer.appendChild(cnv);
    sealDiv.appendChild(cnvContainer);
    charsDiv.appendChild(sealDiv);
    renderAssetToDiv(cnvContainer, "Seal");
  }
}

function updateGate(place, gateDiv) {
  let gateCont = gateDiv.getElementsByClassName("gatecontainer")[0];
  if (place.gate) {  // TODO: sealed
    gateDiv.classList.add("placegatepresent");
    renderAssetToDiv(gateCont, "Gate " + place.gate.name);
  } else {
    clearAssetFromDiv(gateCont);
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

function updateBottomText(gameStage, turnPhase, characters, turnIdx, playerIdx) {
  let uiprompt = document.getElementById("uiprompt");
  let btn = document.getElementById("start");
  uiprompt.innerText = "";
  if (gameStage == "setup") {
    btn.style.display = "inline-block";
    return;
  }
  btn.style.display = "none";
  if (turnIdx != null) {
    uiprompt.innerText = characters[turnIdx].name + "'s " + turnPhase + " phase";
  }
}

function updateGlobals(env, rumor) {
  let envDiv = document.getElementById("environment");
  let rumorDiv = document.getElementById("rumor");
  envDiv.cnvScale = 2;
  rumorDiv.cnvScale = 2;
  if (env == null) {
    clearAssetFromDiv(envDiv);
  } else {
    renderAssetToDiv(envDiv, env);
  }
  if (rumor == null) {
    clearAssetFromDiv(rumorDiv);
  } else {
    renderAssetToDiv(rumorDiv, rumor);
  }
}

function updateDice(numDice, roll, yours) {
  let uidice = document.getElementById("uidice");
  let diceDiv = document.getElementById("dice");
  let btn = document.getElementById("dicebutton");
  if (numDice == null) {
    uidice.style.display = "none";
    return;
  }
  uidice.style.display = "flex";
  if (yours && (roll == null || roll.length < numDice)) {
    btn.style.display = "inline-block";
  } else {
    btn.style.display = "none";
  }
  while (diceDiv.getElementsByClassName("die").length > Math.max(numDice, 0)) {
    diceDiv.removeChild(diceDiv.getElementsByClassName("die")[0])
  }
  while (diceDiv.getElementsByClassName("die").length < numDice) {
    let die = document.createElement("DIV");
    die.classList.add("die");
    diceDiv.appendChild(die);
  }

  let allDice = diceDiv.getElementsByClassName("die");
  for (let die of allDice) {
    die.innerText = "?";
  }

  if (roll == null) {
    return;
  }
  for (let [idx, val] of roll.entries()) {
    if (idx >= allDice.length) {
      console.log("too many dice rolls");
      return;
    }
    allDice[idx].innerText = val;
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
  renderAssetToDiv(document.getElementById("charchoice"), name);
}

function updateCharacterSheets(characters, playerIdx, firstPlayer) {
  let rightUI = document.getElementById("uiright");
  for (let [idx, character] of characters.entries()) {
    let sheet;
    if (rightUI.getElementsByClassName("player").length <= idx) {
      sheet = createCharacterSheet(idx, character, rightUI, playerIdx == idx);
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

function createCharacterSheet(idx, character, rightUI, isPlayer) {
  let div = document.createElement("DIV");
  div.classList.add("player");
  div.classList.add("collapsed");
  if (isPlayer) {
    div.classList.add("you");
  }

  let charTop = document.createElement("DIV");
  charTop.classList.add("playertop");
  charTop.idx = idx;
  charTop.ondrop = drop;
  charTop.ondragenter = dragEnter;
  charTop.ondragover = dragOver;
  let charPic = document.createElement("DIV");
  charPic.classList.add("picture", "cnvcontainer");
  charPic.onclick = function(e) { expandSheet(div) };
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("markercnv");
  charPic.appendChild(cnv);
  charTop.appendChild(charPic);

  let charName = document.createElement("DIV");
  charName.classList.add("playername", "cnvcontainer");
  cnv = document.createElement("CANVAS");
  charName.appendChild(cnv);
  charTop.appendChild(charName);
  div.appendChild(charTop);

  let charStats = document.createElement("DIV");
  charStats.classList.add("playerstats");
  let statsBg = document.createElement("DIV");
  statsBg.classList.add("statsbg", "cnvcontainer");
  let bgcnv = document.createElement("CANVAS");
  bgcnv.classList.add("markercnv");
  statsBg.appendChild(bgcnv);
  charStats.appendChild(statsBg);
  for (let stat of ["stamina", "sanity", "clues", "dollars"]) {
    let statDiv = document.createElement("DIV");
    statDiv.classList.add("stats", stat);  // intentionally omit cnvcontainer; see updateStats()
    let cnv = document.createElement("CANVAS");
    statDiv.appendChild(cnv);
    charStats.appendChild(statDiv);
    if (isPlayer && stat == "clues") {
      statDiv.onclick = function(e) { useAsset("clues") };
    }
    if (isPlayer && stat == "dollars") {
      statDiv.draggable = true;
      statDiv.ondragstart = dragStart;
      statDiv.ondragend = dragEnd;
    }
  }
  charTop.appendChild(charStats);

  let sliderCont = document.createElement("DIV");
  sliderCont.classList.add("slidercont");
  let sliders = document.createElement("DIV");
  sliders.classList.add("sliders", "cnvcontainer");
  sliderCont.appendChild(sliders);
  div.appendChild(sliderCont);
  let slidersCnv = document.createElement("CANVAS");
  slidersCnv.classList.add("worldcnv");  // TODO
  sliders.appendChild(slidersCnv);
  for (let i = 0; i < 3; i++) {  // TODO: fourth slider
    for (let j = 0; j < 4; j++) {
      let sliderDiv = document.createElement("DIV");
      sliderDiv.classList.add("slider", "slider" + i + "" + j, "cnvcontainer");
      let sliderCnv = document.createElement("CANVAS");
      sliderCnv.classList.add("worldcnv");
      sliderDiv.appendChild(sliderCnv);
      sliders.appendChild(sliderDiv);
      if (isPlayer) {
        let sliderName = Object.entries(character.sliders)[i][0];
        sliderDiv.onclick = function(e) { setSlider(sliderName, j); };
      }
      if (!setDivXYPercent(sliderDiv, "Nun sliders", "Slider " + i + " " + j, true)) {
        let xoff = (i % 2 == 0) ? 1 : 2;
        let xpct = (2 * (j+1) + xoff) * 9.09 + "%";
        sliderDiv.style.left = xpct;
        sliderDiv.style.bottom = (3 + 5 * (2-i)) * 100 / 16 + "%";
      }
    }
  }
  let possessions = document.createElement("DIV");
  possessions.classList.add("possessions");
  div.appendChild(possessions);

  rightUI.appendChild(div);
  renderAssetToDiv(statsBg, "statsbg");
  for (let sliderDiv of sliders.getElementsByClassName("slider")) {
    renderAssetToDiv(sliderDiv, "Slider");
  }
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
  let charMarker = sheet.getElementsByClassName("picture")[0];
  renderAssetToDiv(charMarker, character.name + " picture");
  let charName = sheet.getElementsByClassName("playername")[0];
  renderAssetToDiv(charName, character.name + " title");
  sheet.style.order = order;
  let stats = sheet.getElementsByClassName("playerstats")[0];
  let cfgs = [
    ["Stamina", "stamina", "white", "max_stamina"], ["Sanity", "sanity", "white", "max_sanity"],
    ["Clue", "clues", "white"], ["Dollar", "dollars", "black"],
  ];
  for (let cfg of cfgs) {
    let statDiv = sheet.getElementsByClassName(cfg[1])[0];
    renderAssetToDiv(statDiv, cfg[0]);
    statDiv.statValue = character[cfg[1]];
    statDiv.textColor = cfg[2];
    if (cfg.length > 3) {
      statDiv.maxValue = character[cfg[3]];
    } else {
      statDiv.maxValue = null;
    }
  }
  updateSliders(sheet, character, isPlayer);
  updatePossessions(sheet, character, isPlayer);
}

function updateStats() {
  for (let elem of document.getElementsByClassName("stats")) {
    if (elem.assetName == null) {
      continue;
    }
    renderAssetToDiv(elem, elem.assetName, elem.variant).then(function() {
      let cnv = elem.getElementsByTagName("CANVAS")[0];
      if (elem.maxValue != null) {
        let pct = (elem.maxValue - elem.statValue) / elem.maxValue;
        let ctx = cnv.getContext("2d");
        ctx.save();
        ctx.globalAlpha = 0.7;
        ctx.globalCompositeOperation = "source-atop";
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, cnv.width, cnv.height * pct);
        ctx.restore();
      }
      renderTextCircle(cnv, elem.statValue, "rgba(0, 0, 0, 0)", elem.textColor, 0.7);
    });
  }
}

function updateSliders(sheet, character, isPlayer) {
  let sliders = sheet.getElementsByClassName("sliders")[0];
  renderAssetToDiv(sliders, character.name + " sliders");
  for (let slider of sliders.getElementsByClassName("slider")) {
    slider.classList.remove("chosen");
  }
  for (let [idx, [sliderName, sliderInfo]] of Object.entries(character.sliders).entries()) {
    let chosen = sheet.getElementsByClassName("slider" + idx + "" + sliderInfo.selection)[0];
    chosen.classList.add("chosen");
  }
}

function updatePossessions(sheet, character, isPlayer) {
  let pDiv = sheet.getElementsByClassName("possessions")[0];
  while (pDiv.firstChild) {
    pDiv.removeChild(pDiv.firstChild);
  }
  for (let pos of character.possessions) {
    createPossession(pos, isPlayer, pDiv);
  }
}

function createPossession(info, isPlayer, sheet) {
  let div = document.createElement("DIV");
  div.classList.add("possession", "cnvcontainer");
  div.cnvScale = 2.5;
  if (info.active) {
    div.classList.add("active");
  }
  div.handle = info.handle;
  if (abilityNames.includes(info.handle)) {
    div.classList.add("big");
  }
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("poscnv");
  div.appendChild(cnv);
  let cascade = {"sneak": "evade", "fight": "combat", "will": "horror", "lore": "spell"};
  for (let attr in info.bonuses) {
    if (!info.bonuses[attr]) {
      continue;
    }
    let highlightDiv = document.createElement("DIV");
    highlightDiv.classList.add("bonus", "bonus" + attr);
    highlightDiv.innerText = (info.bonuses[attr] >= 0 ? "+" : "") + info.bonuses[attr];
    if (cascade[attr]) {
      highlightDiv.classList.add("bonus" + cascade[attr]);
    }
    div.appendChild(highlightDiv);
  }
  let chosenDiv = document.createElement("DIV");
  chosenDiv.classList.add("chosencheck");
  chosenDiv.innerText = "✔️";
  div.appendChild(chosenDiv);
  // TODO: show some information about bonuses that aren't active right now
  let handle = info.handle;
  div.onmouseenter = bringTop;
  div.onmouseleave = returnBottom;
  if (isPlayer) {
    if (itemChoice.includes(handle)) {
      div.classList.add("chosen");
    }
    div.onclick = function(e) { clickAsset(div, handle); };
    div.draggable = true;
    div.ondragstart = dragStart;
    div.ondragend = dragEnd;
  }
  sheet.appendChild(div);
  renderAssetToDiv(div, info.name);
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
