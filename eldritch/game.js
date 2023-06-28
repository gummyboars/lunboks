ws = null;
dragged = null;
characterMarkers = {};
characterSheets = {};
portraits = {};
monsters = {};
allAncients = {};
chosenAncient = null;
allCharacters = {};
availableChars = [];
pendingName = null;
monsterChoice = {};
charChoice = null;
ancientChoice = null;
oldCurrent = null;
oldVisuals = {};
runningAnim = [];
messageQueue = [];
statTimeout = null;
cardsStyle = "flex";
stepping = false;
statNames = {"stamina": "Stamina", "sanity": "Sanity", "clues": "Clue", "dollars": "Dollar"};

function toggleStepping(e) {
  if (stepping) {
    stepping = false;
    updateStepButton();
    if (messageQueue.length && !runningAnim.length) {
      let msg = messageQueue.shift();
      updateStepButton();
      handleData(msg);
    }
  } else {
    stepping = true;
    updateStepButton();
  }
}

function step(e) {
  if (messageQueue.length && !runningAnim.length) {
    let msg = messageQueue.shift();
    updateStepButton();
    handleData(msg);
  }
}

function updateStepButton() {
  let btn = document.getElementById("stepbutton");
  if (!stepping) {
    btn.style.display = "none";
  } else if (messageQueue.length) {
    btn.style.display = "inline-block";
    btn.disabled = false;
  } else {
    btn.style.display = "inline-block";
    btn.disabled = true;
  }
}

function addOptionToSelect(id, val) {
  let opt = document.createElement("OPTION");
  opt.value = val;
  opt.text = val;
  document.getElementById(id).appendChild(opt);
}

function removeOptionFromSelect(id, val) {
  for (let elem of document.getElementById(id).getElementsByTagName("OPTION")) {
    if (elem.value == val) {
      document.getElementById(id).removeChild(elem);
      break;
    }
  }
}

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
      monstersDiv.onclick = function(e) { toggleMonsters(monstersDiv, name); };
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
      let innerSelect = document.createElement("DIV");
      innerSelect.id = "place" + name + "innerselect";
      innerSelect.classList.add("placeinnerselect", placeType);
      innerSelect.onclick = function(e) { clickPlace(name); };
      select.appendChild(innerSelect);
      details.appendChild(select);
      cont.appendChild(div);

      addOptionToSelect("placechoice", name);
    }
  }
  placeLocations();
  for (let name of monsterNames) {
    addOptionToSelect("monsterchoice", name);
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

    addOptionToSelect("gatechoice", name);
  }
  for (let extra of ["Lost", "Sky", "Outskirts"]) {
    renderAssetToDiv(document.getElementById("place" + extra), extra);
    if (extra != "Lost") {
      let box = document.getElementById("place" + extra + "box");
      let monstersDiv = box.getElementsByClassName("placemonsters")[0];
      monstersDiv.onclick = function(e) { toggleMonsters(monstersDiv, extra); };
    }
  }
  let outskirtsBox = document.getElementById("placeOutskirtsbox");
  outskirtsBox.ondragenter = dragEnter;
  outskirtsBox.ondragover = dragOver;
  outskirtsBox.ondrop = drop;
  let cupBox = document.getElementById("monsterchoices");
  cupBox.onclick = function(e) { toggleMonsters(cupBox, "Monster Cup"); };
  cupBox.ondrop = drop;
  cupBox.ondragenter = dragEnter;
  cupBox.ondragover = dragOver;

  // Debug menu stuff
  changeOtherChoice(null);
  changePlaceChoice(null);
  for (let arr of [commonNames, uniqueNames, spellNames, skillNames, allyNames, abilityNames, otherNames]) {
    for (let name of arr) {
      addOptionToSelect("itemchoice", name);
    }
  }
  for (let name of monsterNames) {
    addOptionToSelect("trophychoice", name);
  }
  for (let i = 1; i < 67; i++) {
    addOptionToSelect("nextmythoschoice", "Mythos" + i);
  }
  for (let i = 1; i < 50; i++) {
    addOptionToSelect("nextgatechoice", "Gate" + i);
  }

  window.addEventListener("resize", function() {
    clearTimeout(statTimeout);
    statTimeout = setTimeout(redrawCustomCanvases, 255);
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

function replacer(match, p1) {
  if (serverNames[p1] != null) {
    return serverNames[p1];
  }
  if (!isNaN(parseInt(p1))) {
    return match;
  }
  return p1;
};

function formatServerString(str) {
  let regex = new RegExp("\\[([^\\]]*)\\]", "g");
  return str.replace(regex, replacer);
}

function onmsg(e) {
  let data = JSON.parse(e.data);
  if (data.type == "error") {
    document.getElementById("errorText").holdSeconds = 3;
    document.getElementById("errorText").style.opacity = 1.0;
    document.getElementById("errorText").innerText = formatServerString(data.message);
    setTimeout(clearError, 100);
    return;
  }
  if (stepping || runningAnim.length || messageQueue.length) {
    messageQueue.push(data);
    updateStepButton();
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
  if (!stepping && messageQueue.length && !runningAnim.length) {
    let msg = messageQueue.shift();
    handleData(msg);
    updateStepButton();
  } else {
    updateStats();  // TODO: this is hacky
  }
}
function handleData(data) {
  allCharacters = data.all_characters;
  allAncients = data.all_ancients;
  pendingName = data.pending_name;
  chosenAncient = (data.ancient_one == null) ? null : data.ancient_one.name;
  let myChoice = data.chooser == data.player_idx ? data.choice : null;
  let mySpendables = data.chooser == data.player_idx ? data.spendables : null;
  updateAvailableCharacters(data.characters, data.pending_chars);
  updateCharacterSelect(data.characters, data.player_idx);
  updateAncientSelect(data.game_stage, data.host);
  updateAncientOne(data.ancient_one, data.terror);
  updateCharacterSheets(data.characters, data.pending_chars, data.player_idx, data.first_player, myChoice);
  updateBottomText(data.game_stage, data.turn_phase, data.characters, data.turn_idx, data.player_idx, data.host);
  updateGlobals(data.environment, data.rumor, data.other_globals);
  updatePlaces(data.places, data.activity);
  updateCharacters(data.characters);
  updateSliderButton(data.sliders, data.chooser == data.player_idx);
  markVisualsForDeletion();
  updateChoices(data.choice, data.current, data.chooser == data.player_idx, data.characters[data.chooser]);
  updateMonsters(data.monsters);
  updateMonsterChoices(myChoice, data.monsters);
  updatePlaceBoxes(data.places, data.activity);
  updateUsables(data.usables, mySpendables, myChoice);
  updateDice(data.dice, data.player_idx, data.monsters);
  updateCurrentCard(data.current);
  deleteUnusedVisuals();
  updateEventLog(data.event_log);
  if (!stepping && messageQueue.length && !runningAnim.length) {
    let msg = messageQueue.shift();
    updateStepButton();
    handleData(msg);
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

function changePlaceChoice(e) {
  let name = document.getElementById("placechoice").value;
  for (let elem of document.getElementsByClassName("placetext")) {
    elem.innerText = name;
  }
  let nextCardChoice = document.getElementById("nextcardchoice");
  while (nextCardChoice.children.length) {
    nextCardChoice.removeChild(nextCardChoice.firstChild);
  }
  for (let i = 1; i <= 7; i++) {
    let opt = document.createElement("OPTION");
    opt.value = name + i;
    opt.label = name + i;
    nextCardChoice.appendChild(opt);
  }
}

function changeOtherChoice(e) {
  let name = document.getElementById("gatechoice").value;
  for (let elem of document.getElementsByClassName("othertext")) {
    elem.innerText = name;
  }
  for (let elem of document.getElementsByClassName("othertext1")) {
    elem.innerText = name + " 1";
  }
  for (let elem of document.getElementsByClassName("othertext2")) {
    elem.innerText = name + " 2";
  }
}

function changePlayerChoice(e) {
  let name = document.getElementById("playerchoice").value;
  let sheet = characterSheets[name];
  if (sheet == null) {
    return;
  }
  for (let stat of ["stamina", "sanity", "clues", "dollars"]) {
    let statDiv = sheet.getElementsByClassName(stat)[0];
    if (statDiv == null) {
      continue;
    }
    document.getElementById(stat + "choice").value = statDiv.statValue;
  }
  let handleChoice = document.getElementById("handlechoice");
  while (handleChoice.children.length) {
    handleChoice.removeChild(handleChoice.firstChild);
  }
  for (let elem of sheet.getElementsByClassName("possession")) {
    addOptionToSelect("handlechoice", elem.handle);
  }
  let trophyHandleChoice = document.getElementById("trophyhandlechoice");
  while (trophyHandleChoice.children.length) {
    trophyHandleChoice.removeChild(trophyHandleChoice.firstChild);
  }
  for (let elem of sheet.getElementsByClassName("trophy")) {
    addOptionToSelect("trophyhandlechoice", elem.handle);
  }
  for (let elem of document.getElementsByClassName("playertext")) {
    elem.innerText = name;
  }
}

function addDoom(e) {
  ws.send(JSON.stringify({"type": "add_doom"}));
}

function removeDoom(e) {
  ws.send(JSON.stringify({"type": "remove_doom"}));
}

function awaken(e) {
  ws.send(JSON.stringify({"type": "awaken"}));
}

function spawnClue(e) {
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "clue", "place": place}));
}

function removeClue(e) {
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "remove_clue", "place": place}));
}

function removeGate(e) {
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "remove_gate", "place": place}));
}

function toggleSeal(e) {
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "seal", "place": place}));
}

function spawnMonster(e) {
  let monster = document.getElementById("monsterchoice").value;
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "monster", "place": place, "monster": monster}));
}

function removeMonster(e) {
  let monster = document.getElementById("monsterchoice").value;
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "remove_monster", "place": place, "monster": monster}));
}

function spawnGate(e) {
  let gate = document.getElementById("gatechoice").value;
  let place = document.getElementById("placechoice").value;
  ws.send(JSON.stringify({"type": "gate", "gate": gate, "place": place}));
}

function setStats(e) {
  let name = document.getElementById("playerchoice").value;
  let msg = {
    "type": "set_stats",
    "name": name,
  };
  for (let stat of ["stamina", "sanity", "clues", "dollars"]) {
    msg[stat] = parseInt(document.getElementById(stat + "choice").value);
  }
  ws.send(JSON.stringify(msg));
}

function goInsane(e) {
  let name = document.getElementById("playerchoice").value;
  ws.send(JSON.stringify({"type": "insane", "char": name}));
}

function goUnconscious(e) {
  let name = document.getElementById("playerchoice").value;
  ws.send(JSON.stringify({"type": "unconscious", "char": name}));
}

function beDevoured(e) {
  let name = document.getElementById("playerchoice").value;
  ws.send(JSON.stringify({"type": "devoured", "char": name}));
}

function moveChar(e, suffix) {
  let place;
  let name = document.getElementById("playerchoice").value;
  if (suffix == null) {
    place = document.getElementById("placechoice").value;
  } else {
    place = document.getElementById("gatechoice").value + suffix;
  }
  ws.send(JSON.stringify({"type": "move_char", "char": name, "place": place}));
}

function giveItem(e) {
  let charName = document.getElementById("playerchoice").value;
  let itemName = document.getElementById("itemchoice").value;
  ws.send(JSON.stringify({"type": "give_item", "char": charName, "item": itemName}));
}

function removeItem(e) {
  let charName = document.getElementById("playerchoice").value;
  let handle = document.getElementById("handlechoice").value;
  ws.send(JSON.stringify({"type": "remove_item", "char": charName, "handle": handle}));
}

function exhaustItem(e) {
  let charName = document.getElementById("playerchoice").value;
  let handle = document.getElementById("handlechoice").value;
  ws.send(JSON.stringify({"type": "exhaust_item", "char": charName, "handle": handle}));
}

function refreshItem(e) {
  let charName = document.getElementById("playerchoice").value;
  let handle = document.getElementById("handlechoice").value;
  ws.send(JSON.stringify({"type": "refresh_item", "char": charName, "handle": handle}));
}

function giveTrophy(e, isMonster) {
  let charName = document.getElementById("playerchoice").value;
  let trophyName;
  if (isMonster) {
    trophyName = document.getElementById("trophychoice").value;
  } else {
    trophyName = document.getElementById("gatechoice").value;
  }
  ws.send(JSON.stringify({"type": "give_trophy", "char": charName, "trophy": trophyName}));
}

function removeTrophy(e) {
  let charName = document.getElementById("playerchoice").value;
  let handle = document.getElementById("trophyhandlechoice").value;
  ws.send(JSON.stringify({"type": "remove_trophy", "char": charName, "handle": handle}));
}

function redoSliders(e) {
  let charName = document.getElementById("playerchoice").value;
  ws.send(JSON.stringify({"type": "redo_sliders", "char": charName}));
}

function setEncounter(e) {
  let encName = document.getElementById("nextcardchoice").value;
  ws.send(JSON.stringify({"type": "set_encounter", "card": encName}));
}

function setMythos(e) {
  let mythName = document.getElementById("nextmythoschoice").value;
  ws.send(JSON.stringify({"type": "set_mythos", "card": mythName}));
}

function setGate(e) {
  let gateName = document.getElementById("nextgatechoice").value;
  ws.send(JSON.stringify({"type": "set_gate", "card": gateName}));
}

function bringTop(e) {
  let node = e.currentTarget;
  node.style.zIndex = 5;
}

function returnBottom(e) {
  let node = e.currentTarget;
  node.style.removeProperty("z-index");
}

function makeChoice(val) {
  ws.send(JSON.stringify({"type": "choice", "choice": val}));
}

function chooseItems(e) {
  ws.send(JSON.stringify({"type": "choice", "choice": "done"}));
}

function doneUsing(e) {
  ws.send(JSON.stringify({"type": "done_using"}));
}

function clickAsset(assetDiv, assetHandle) {
  if (assetDiv.classList.contains("usable")) {
    useAsset(assetHandle);
    return;
  }
  chooseAsset(assetHandle);
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
  let monsterDivList = [];
  for (let monsterDiv of document.getElementsByClassName("monster")) {
    monsterDivList.push(monsterDiv);
  }
  for (let monsterDiv of monsterDivList) {
    if (monsterDiv.monsterIdx != null && monsterDiv.draggable) {
      document.getElementById("monsterchoices").appendChild(monsterDiv);
    }
  }
  monsterChoice = {};
}

function toOutskirts(e) {
  let monsterDivList = [];
  let choicesDiv = document.getElementById("monsterchoices");
  for (let monsterDiv of choicesDiv.getElementsByClassName("monster")) {
    monsterDivList.push(monsterDiv);
  }
  for (let monsterDiv of monsterDivList) {
    if (monsterDiv.monsterIdx != null && monsterDiv.draggable && monsterChoice[monsterDiv.monsterIdx] == null) {
      document.getElementById("placeOutskirtsmonsters").appendChild(monsterDiv);
      monsterChoice[monsterDiv.monsterIdx] = "Outskirts";
    }
  }
}

function defaultSpend(spendDict, choice) {
  let knownSpends = ["sanity", "stamina", "clues", "dollars"];
  for (let key in spendDict) {
    if (spendDict[key] && !knownSpends.includes(key)) {
      makeChoice(choice);  // Try to make the choice anyway; let the backend throw an error.
      return;
    }
  }
  for (let spendType of knownSpends) {
    for (let i = 0; i < spendDict[spendType] || 0; i++) {
      spend(spendType);
    }
    for (let i = 0; i < -spendDict[spendType] || 0; i++) {
      unspend(spendType);
    }
  }
}

function spend(spendType) {
  ws.send(JSON.stringify({"type": "spend", "spend_type": spendType}));
}

function unspend(spendType) {
  ws.send(JSON.stringify({"type": "unspend", "spend_type": spendType}));
}

function chooseAsset(handle) {
  ws.send(JSON.stringify({"type": "choice", "choice": handle}));
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
  if (e.currentTarget.id == "monsterchoices") {
    e.preventDefault();
    e.currentTarget.appendChild(dragged);
    delete monsterChoice[dragged.monsterIdx];
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

function prevAncient(e) {
  let sortedKeys = Object.keys(allAncients).sort();
  let currentIdx = sortedKeys.indexOf(ancientChoice);
  if (currentIdx <= 0) {
    ancientChoice = sortedKeys[sortedKeys.length-1];
  } else {
    ancientChoice = sortedKeys[currentIdx-1];
  }
  updateAncientSelect("setup", true);
}

function nextAncient(e) {
  let sortedKeys = Object.keys(allAncients).sort();
  let currentIdx = sortedKeys.indexOf(ancientChoice);
  if (currentIdx >= sortedKeys.length - 1) {
    ancientChoice = sortedKeys[0];
  } else {
    ancientChoice = sortedKeys[currentIdx+1];
  }
  updateAncientSelect("setup", true);
}

function prevChar(e) {
  let sortedKeys = Object.keys(allCharacters).sort();
  let currentIdx = sortedKeys.indexOf(charChoice);
  if (currentIdx <= 0) {
    charChoice = sortedKeys[sortedKeys.length-1];
  } else {
    charChoice = sortedKeys[currentIdx-1];
  }
  drawChosenChar(allCharacters[charChoice]);
  updateStats();
}

function nextChar(e) {
  let sortedKeys = Object.keys(allCharacters).sort();
  let currentIdx = sortedKeys.indexOf(charChoice);
  if (currentIdx >= sortedKeys.length - 1) {
    charChoice = sortedKeys[0];
  } else {
    charChoice = sortedKeys[currentIdx+1];
  }
  drawChosenChar(allCharacters[charChoice]);
  updateStats();
}

function selectAncient(e) {
  ws.send(JSON.stringify({"type": "ancient", "ancient": ancientChoice}));
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
      if (characterMarkers[character.name] != null) {
        characterMarkers[character.name].parentNode.removeChild(characterMarkers[character.name]);
        delete characterMarkers[character.name];
      }
      updatePortraitDiv(character.name, "Lost");  // Anything that is not an otherworld will do.
      continue;
    }
    updatePortraitDiv(character.name, character.place);
    if (characterMarkers[character.name] == null) {
      characterMarkers[character.name] = createCharacterDiv(character.name);
      place.appendChild(characterMarkers[character.name]);
      renderAssetToDiv(characterMarkers[character.name].getElementsByClassName("cnvcontainer")[0], character.name);
    } else {
      animateMovingDiv(characterMarkers[character.name], place);
    }
    if (character.delayed_until != null || character.lose_turn_until != null || character.arrested_until != null) {
      characterMarkers[character.name].getElementsByClassName("markercontainer")[0].classList.add("delayed");
    } else {
      characterMarkers[character.name].getElementsByClassName("markercontainer")[0].classList.remove("delayed");
    }
  }
}

function toggleMonsters(placeDiv, name) {
  let details = document.getElementById("monsterdetails");
  if (details.style.display != "flex") {
    showMonsters(placeDiv, name);
    return;
  }
  let sname = serverNames[name] ?? name;
  if (document.getElementById("monsterdetailsname").innerText != sname) {
    showMonsters(placeDiv, name);
    return;
  }
  hideMonsters(null);
}

function showMonsters(placeDiv, name) {
  let box = document.getElementById("monsterdetailsbox");
  while (box.children.length) {
    box.removeChild(box.firstChild);
  }
  let sname = serverNames[name] ?? name;
  document.getElementById("monsterdetailsname").innerText = sname;
  document.getElementById("monsterdetails").style.display = "flex";
  for (let monsterDiv of placeDiv.getElementsByClassName("monster")) {
    let container = document.createElement("DIV");
    let handle = monsterDiv.monsterInfo.handle;
    container.onclick = function(e) { makeChoice(handle) };
    let frontDiv = createMonsterDiv(monsterDiv.monsterInfo, false, "big");
    container.appendChild(frontDiv);
    let backDiv = createMonsterDiv(monsterDiv.monsterInfo, true, "big");
    container.appendChild(backDiv);
    box.appendChild(container);
    renderAssetToDiv(frontDiv.getElementsByClassName("cnvcontainer")[0], monsterDiv.monsterInfo.name);
    renderMonsterBackToDiv(backDiv.getElementsByClassName("monsterback")[0], monsterDiv.monsterInfo);
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
      monsters[i] = createMonsterDiv(monster);
      monsters[i].monsterIdx = i;
      place.appendChild(monsters[i]);
      renderAssetToDiv(monsters[i].getElementsByClassName("cnvcontainer")[0], monster.name);
    } else {
      monsters[i].monsterInfo = monster;
      animateMovingDiv(monsters[i], place);
    }
  }
}

function updateSliderButton(sliders, isMySliders) {
  if (sliders) {
    document.getElementById("uiprompt").innerText = formatServerString(sliders.prompt);
  }
  if (sliders && isMySliders) {
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
  document.getElementById("cardchoicescroll").style.display = cardsStyle;
  setCardButtonText();
}

function setCardButtonText() {
  if (cardsStyle == "flex") {
    document.getElementById("togglecards").innerText = "Hide Info";
  } else {
    document.getElementById("togglecards").innerText = "Show Info";
  }
}

function scrollCards(e, dir) {
  let container = e.currentTarget.parentNode;
  let cardScroller = container.getElementsByClassName("cardscroller")[0];
  let rect = cardScroller.getBoundingClientRect();
  let width = rect.right - rect.left;
  let amount = dir * Math.ceil(width / 4);
  cardScroller.scrollLeft = cardScroller.scrollLeft + amount;
}

function markVisualsForDeletion() {
  oldVisuals = {};
  let uicardchoice = document.getElementById("uicardchoice");
  for (let holder of uicardchoice.getElementsByClassName("cardholder")) {
    holder.classList.add("todelete");
    let found = false;
    for (let className of ["fightchoice", "monsterchoice", "cardchoice", "bigmythoscard"]) {
      for (let child of holder.children) {
        if (child.classList.contains(className)) {
          if (oldVisuals[className] == null) {
            oldVisuals[className] = {};
          }
          oldVisuals[className][holder.handle] = holder;
          found = true;
          break;
        }
      }
      if (found) {
        break;
      }
    }
  }
}

function deleteUnusedVisuals() {
  let uicardchoice = document.getElementById("uicardchoice");
  while (uicardchoice.getElementsByClassName("todelete").length) {
    uicardchoice.removeChild(uicardchoice.getElementsByClassName("todelete")[0]);
  }
  oldVisuals = {};
}

function updateChoices(choice, current, isMyChoice, chooser) {
  let btn = document.getElementById("doneitems");
  let uichoice = document.getElementById("uichoice");
  let uicardchoice = document.getElementById("uicardchoice");
  let cardtoggle = document.getElementById("togglecards");
  let monsterBox = document.getElementById("monsterdetailsbox");
  let pDiv;
  if (!document.getElementsByClassName("you").length) {
    pDiv = document.createElement("DIV");  // Dummy div.
  } else {
    pDiv = document.getElementsByClassName("you")[0].getElementsByClassName("possessions")[0];
  }
  for (let place of document.getElementsByClassName("placeinnerselect")) {
    place.classList.remove("selectable");
    place.classList.remove("hoverable");
    place.classList.remove("unselectable");
    place.innerText = "";
  }
  for (let pos of pDiv.getElementsByClassName("possession")) {
    pos.classList.remove("choosable");
  }
  uichoice.style.display = "none";
  document.getElementById("cardchoicescroll").style.display = "none";
  btn.style.display = "none";
  cardtoggle.style.display = "none";
  if (choice != null && choice.board_monster != null && isMyChoice) {
    monsterBox.classList.add("choosable");
  } else {
    monsterBox.classList.remove("choosable");
  }
  if (choice == null || choice.to_spawn != null || choice.board_monster != null) {
    document.getElementById("charoverlay").classList.remove("shown");
    return;
  }
  // Set display style for uichoice div.
  if (choice.items == null && isMyChoice) {
    uichoice.style.display = "flex";
  }
  if (choice.cards != null || choice.monster != null || choice.monsters != null) {
    document.getElementById("cardchoicescroll").style.display = cardsStyle;
    cardtoggle.style.display = "inline-block";
    setCardButtonText();
  }
  // Clean out any old choices it may have.
  while (uichoice.getElementsByClassName("choice").length) {
    uichoice.removeChild(uichoice.getElementsByClassName("choice")[0]);
  }
  // Set prompt.
  let promptText = formatServerString(choice.prompt);
  let chooserName = serverNames[chooser.name] ?? chooser.name;
  if (!isMyChoice) {
    if (promptText.startsWith("Choose")) {
      promptText = chooserName + " must " + promptText.charAt(0).toLowerCase() + promptText.slice(1);
    } else if (promptText.startsWith(chooserName)) {
      // Do nothing: the name of the player is already in the text.
    } else {
      promptText = chooserName + " must choose: " + promptText;
    }
  }
  document.getElementById("uiprompt").innerText = promptText;
  let showOverlay = isMyChoice && (choice.items != null || choice.spendable != null);
  document.getElementById("charoverlay").classList.toggle("shown", showOverlay);
  if (choice.spell != null && choice.cards == null) {
    showActionSource(document.getElementById("uicardchoice"), choice.spell);
  }
  if (choice.items != null) {
    if (isMyChoice) {
      for (let pos of pDiv.getElementsByClassName("possession")) {
        pos.classList.toggle("choosable", choice.items.includes(pos.handle));
      }
      btn.style.display = "inline-block";
    }
    if (choice.monster != null) {
      showMonster(uicardchoice, choice.monster);  // TODO: update show/hide button text
    }
  } else {  // choice.items == null
    if (choice.places != null) {
      updatePlaceChoices(uichoice, choice.places, choice.annotations, isMyChoice);
    } else if (choice.cards != null) {
      addCardChoices(uichoice, uicardchoice, choice.cards, choice.invalid_choices, choice.remaining_spend, choice.annotations, choice.sort_uniq, current, isMyChoice);
    } else if (choice.monsters != null) {
      addMonsterChoices(uichoice, uicardchoice, choice.monsters, choice.invalid_choices, choice.annotations, current, isMyChoice);
    } else if (choice.monster != null) {
      addFightOrEvadeChoices(uichoice, uicardchoice, choice.monster, choice.choices, choice.invalid_choices, choice.annotations, current, isMyChoice);
    } else {
      if (isMyChoice) {
        addChoices(uichoice, choice.choices, choice.invalid_choices, choice.remaining_spend);
      }
    }
  }
}

function updateMonsterChoices(choice, monsterList) {
  // TODO: indicate how many monsters each location should receive.
  let uiprompt = document.getElementById("uiprompt");
  let uimonsterchoice = document.getElementById("uimonsterchoice");
  let choicesBox = document.getElementById("monsterchoices");
  if (choice == null || choice.to_spawn == null) {
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
  for (let monsterIdx of choice.to_spawn) {
    if (monsters[monsterIdx] == null) {
      monsters[monsterIdx] = createMonsterDiv(monsterList[monsterIdx]);
      monsters[monsterIdx].monsterIdx = monsterIdx;
      monsters[monsterIdx].draggable = true;
      monsters[monsterIdx].ondragstart = dragStart;
      monsters[monsterIdx].ondragend = dragEnd;
      choicesBox.appendChild(monsters[monsterIdx]);
      renderAssetToDiv(monsters[monsterIdx].getElementsByClassName("cnvcontainer")[0], monsterList[monsterIdx].name);
    }
  }
}

function addMonsterChoices(uichoice, cardChoice, monsters, invalidChoices, annotations, current, isMyChoice) {
  let otherChoices = [];
  for (let [idx, monster] of monsters.entries()) {
    if (typeof(monster) == "string") {
      otherChoices.push(monster);
      continue;
    }
    let [holder, div] = addVisual(cardChoice, monster.handle, monster.name, "monster", isMyChoice ? monster.handle : null, null, monster, annotations && annotations[idx]);
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      holder.classList.add("unchoosable");
      holder.style.order = 1;
    } else {
      holder.style.order = 0;
    }
  }
  let scrollParent = cardChoice.parentNode;
  if (monsters.length > 4) {
    scrollParent.classList.add("overflowing");
  } else {
    scrollParent.classList.remove("overflowing");
  }
  if (isMyChoice) {
    addChoices(uichoice, otherChoices, [], []);
  }
}

function showMonster(cardChoice, monster) {
  addVisual(cardChoice, monster.handle, monster.name, "fight", null, null, monster, null);
}

function showActionSource(cardChoice, name) {
  addVisual(cardChoice, name, name, "card", null, null, null, null);
}

function addVisual(cardChoice, handle, name, visualType, choice, backName, monster, descText) {
  let classNames = {
    "fight": "fightchoice",
    "monster": "monsterchoice",
    "card": "cardchoice",
    "mythos": "bigmythoscard",
  };
  let className = classNames[visualType];
  let holder = null;
  let div = null;
  let cnv = null;
  if (oldVisuals[className] != null && oldVisuals[className][handle] != null) {
    holder = oldVisuals[className][handle];
    div = holder.getElementsByClassName(className)[0];
    cnv = div.getElementsByClassName("markercnv")[0];
    div.classList.toggle("visualchoice", choice != null);
  }
  if (holder == null) {  // Does not exist - create a new one.
    holder = document.createElement("DIV");
    holder.classList.add("cardholder");
    div = document.createElement("DIV");
    div.classList.toggle("visualchoice", choice != null);
    div.classList.add(classNames[visualType]);
    cnv = document.createElement("CANVAS");
    cnv.classList.add("markercnv");  // TODO: use a better class name for this
    div.appendChild(cnv);
    holder.appendChild(div);
    cardChoice.appendChild(holder);
  }

  let backDiv = null;
  let backCnv = null;
  let desc = null;
  if (backName != null && holder.getElementsByClassName("visualback").length == 0) {
    backDiv = document.createElement("DIV");
    backDiv.classList.add(classNames[visualType], "visualback", "cnvcontainer");
    backCnv = document.createElement("CANVAS");
    backCnv.classList.add("markercnv");
    backDiv.appendChild(backCnv);
    holder.appendChild(backDiv);
  } else if (backName == null && holder.getElementsByClassName("visualback").length > 0) {
    holder.removeChild(holder.getElementsByClassName("visualback")[0]);
  }
  if (descText != null && holder.getElementsByClassName("desc").length == 0) {
    desc = document.createElement("DIV");
    desc.classList.add("desc");
    holder.appendChild(desc);
  } else if (descText == null && holder.getElementsByClassName("desc").length > 0) {
    holder.removeChild(holder.getElementsByClassName("desc")[0]);
  }

  if (descText != null) {
    holder.getElementsByClassName("desc")[0].innerText = formatServerString(descText);
  }
  if (choice != null) {
    div.onclick = function(e) { makeChoice(choice); };
  } else {
    div.onclick = null;
  }

  div.classList.remove("monsterback", "cnvcontainer");  // reset
  if (className == "monsterchoice") {
    while (div.children.length > 0) {
      div.removeChild(div.firstChild);
    }
    let frontDiv = document.createElement("DIV");
    frontDiv.classList.add("fightchoice", "cnvcontainer");
    let backDiv = document.createElement("DIV");
    backDiv.classList.add("fightchoice", "monsterback");
    backDiv.monsterInfo = monster;
    let frontCnv = document.createElement("CANVAS");
    frontCnv.classList.add("markercnv");  // TODO: use a better class name for this
    frontDiv.appendChild(frontCnv);
    let backCnv = document.createElement("CANVAS");
    backCnv.classList.add("markercnv");  // TODO: use a better class name for this
    backDiv.appendChild(backCnv);
    div.appendChild(frontDiv);
    div.appendChild(backDiv);
    renderAssetToDiv(frontDiv, monster.name);
    renderMonsterBackToDiv(backDiv, monster);
  } else if (monster != null) {
    div.classList.add("monsterback");
    div.monsterInfo = monster;
    renderMonsterBackToDiv(div, monster);
  } else {
    div.classList.add("cnvcontainer");
    renderAssetToDiv(div, name);
  }
  if (backName != null) {
    renderAssetToDiv(holder.getElementsByClassName("visualback")[0], backName);
  }
  holder.classList.remove("todelete");
  holder.handle = handle;
  return [holder, div];
}

function addFightOrEvadeChoices(uichoice, cardChoice, monster, choices, invalidChoices, annotations, current, isMyChoice) {
  for (let [idx, choice] of choices.entries()) {
    let descText = choice;
    if (annotations && annotations[idx] != null) {
      descText += " (" + formatServerString(annotations[idx]) + ")";
    }
    let holder, div, cnv;
    [holder, div] = addVisual(cardChoice, monster.handle + choice, monster.name, "fight", isMyChoice ? choice : null, null, choice == "Fight" ? monster : null, descText);
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      holder.classList.add("unchoosable");
    }
  }
}

function addCardChoices(uichoice, cardChoice, cards, invalidChoices, remainingSpend, annotations, sortUniq, current, isMyChoice) {
  if (!cards) {
    return;
  }
  let count = 0;
  let uniqueCards = new Set(cards);
  let sortedCards = [...uniqueCards];
  sortedCards.sort();
  let cardToOrder = {};
  for (let [idx, card] of sortedCards.entries()) {
    cardToOrder[card] = idx;
  }
  uniqueCards = new Set([]);
  let notFound = [];
  let newInvalid = [];
  let newRemainingSpend = [];
  for (let [idx, card] of cards.entries()) {
    if (!assetNames.includes(card)) {
      if (invalidChoices != null && invalidChoices.includes(idx)) {
        newInvalid.push(notFound.length);
      }
      if (remainingSpend != null && remainingSpend.length > idx) {
        newRemainingSpend.push(remainingSpend[idx]);
      }
      notFound.push(card);
      continue;
    }
    if (sortUniq && uniqueCards.has(card)) {
      continue;
    }
    uniqueCards.add(card);
    count++;
    let match = card.match(/(.*[^0-9])([0-9]*)$/);
    let backName = null;
    let shouldAnimate = false;
    if (match != null && assetNames.includes(match[1] + " Card")) {
      shouldAnimate = true;
      backName = match[1] + " Card";
    }
    let [holder, div] = addVisual(cardChoice, card, card, "card", isMyChoice ? card : null, backName, null, annotations && annotations[idx]);
    if (sortUniq) {
      holder.style.order = cardToOrder[card];
    }
    if ((oldVisuals["cardchoice"] != null && oldVisuals["cardchoice"][card] != null) || card == oldCurrent) {
      shouldAnimate = false;
    }
    if (shouldAnimate) {
      holder.classList.add("entering");
      runningAnim.push(true);
      let lastAnim = function() { doneAnimating(holder); finishAnim(); };
      let firstAnim = function() {
        holder.ontransitionend = lastAnim;
        holder.ontransitioncancel = lastAnim;
        holder.classList.remove("rotated");
      };
      holder.ontransitionend = firstAnim;
      holder.ontransitioncancel = firstAnim;
      setTimeout(function() { holder.classList.add("rotated"); holder.classList.remove("entering"); }, 10);
    }
    if (holder.getElementsByClassName("desc").length > 0) {
      holder.getElementsByClassName("desc")[0].style.removeProperty("background-position");
    }
    holder.classList.remove("unchoosable", "mustspend");
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      holder.classList.add("unchoosable");
    } else if (remainingSpend != null && remainingSpend.length > idx && remainingSpend[idx]) {
      let rem = remainingSpend[idx];
      holder.classList.add("mustspend");
      if (isMyChoice) {
        div.onclick = function(e) { defaultSpend(rem, card); };
      }
    }
  }
  let scrollParent = cardChoice.parentNode;
  if (count > 4) {
    scrollParent.classList.add("overflowing");
  } else {
    scrollParent.classList.remove("overflowing");
  }
  if (isMyChoice) {
    addChoices(uichoice, notFound, newInvalid, newRemainingSpend);
  }
}

function addChoices(uichoice, choices, invalidChoices, remainingSpend) {
  for (let [idx, c] of choices.entries()) {
    let div = document.createElement("DIV");
    div.classList.add("choice");
    div.innerText = serverNames[c] ?? c;
    if (c == "Pass") {
      div.classList.add("success");
    }
    if (c == "Fail") {
      div.classList.add("fail");
    }
    div.onclick = function(e) { makeChoice(c); };
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      div.classList.add("unchoosable");
    } else if (remainingSpend != null && remainingSpend.length > idx && remainingSpend[idx]) {
      let rem = remainingSpend[idx];
      div.classList.add("mustspend");
      div.onclick = function(e) { defaultSpend(rem, c); };
    } else {
      div.classList.add("choosable");
    }
    uichoice.appendChild(div);
  }
}

function updateUsables(usables, spendables, choice) {
  let uiuse = document.getElementById("uiuse");
  let pDiv, tDiv, pTab, tTab;
  if (!document.getElementsByClassName("you").length) {
    pDiv = document.createElement("DIV");  // Dummy div.
    tDiv = pDiv;
    pTab = pDiv;
    tTab = pDiv;
  } else {
    [pDiv, tDiv] = document.getElementsByClassName("you")[0].getElementsByClassName("possessions");
    [pTab, tTab] = document.getElementsByClassName("you")[0].getElementsByClassName("bagtab");
  }
  let posList = pDiv.getElementsByClassName("possession");
  let trophyList = tDiv.getElementsByClassName("trophy");
  let usableList = usables || [];
  usableList.concat(spendables || []);
  let anyPosUsable = false;
  let anyTrophyUsable = false;
  for (let pos of posList) {
    let isUsable = usableList.includes(pos.handle);
    pos.classList.toggle("usable", isUsable);
    anyPosUsable = anyPosUsable || isUsable;
  }
  for (let pos of trophyList) {
    let isUsable = usableList.includes(pos.handle);
    pos.classList.toggle("usable", isUsable);
    anyTrophyUsable = anyTrophyUsable || isUsable;
  }
  pTab.classList.toggle("usable", anyPosUsable);
  tTab.classList.toggle("usable", anyTrophyUsable);
  uiuse.style.display = "none";
  if (usables == null && spendables == null) {
    if (choice == null) {
      document.getElementById("charoverlay").classList.remove("shown");
    }
    return;
  }
  document.getElementById("charoverlay").classList.add("shown");
  if (choice == null) {
    uiuse.style.display = "flex";
  }
  let tradeOnly = true;
  for (let val of usableList) {
    if (val != "trade") {
      tradeOnly = false;
      break;
    }
  }
  document.getElementById("usetext").innerText = "Use Items or Abilities";
  document.getElementById("doneusing").innerText = "Done Using";
  if (tradeOnly) {
    document.getElementById("usetext").innerText = "Trade?";
    document.getElementById("doneusing").innerText = "Done Trading";
  }
}

function updateSpendList(spendable, spent) {
  let spendDiv = document.getElementById("uispend");
  for (let stat in statNames) {
    let count = spent[stat] || 0;

    // Remove elements from the spend list.
    while (spendDiv.getElementsByClassName(stat).length > count) {
      spendDiv.removeChild(spendDiv.getElementsByClassName(stat)[0]);
    }

    // Add elements to the spend list.
    while (spendDiv.getElementsByClassName(stat).length < count) {
      let statDiv = document.createElement("DIV");
      statDiv.classList.add("stats", "cnvcontainer", stat, "spendable");
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("cluecnv");
      statDiv.appendChild(cnv);
      spendDiv.appendChild(statDiv);
      renderAssetToDiv(statDiv, statNames[stat]);
      statDiv.onclick = function(e) { unspend(stat); };
    }
  }
}

function updateStatSpending(spendable) {
  let yourSheets = document.getElementsByClassName("you");
  if (!yourSheets.length) {
    return;
  }
  let yourSheet = yourSheets[0];
  if (spendable == null) {
    for (let div of yourSheet.getElementsByClassName("stats")) {
      div.classList.remove("spendable");
    }
    return;
  }
  for (let stat in statNames) {
    for (let div of yourSheet.getElementsByClassName(stat)) {
      if (spendable.includes(stat)) {
        div.classList.add("spendable");
      } else {
        div.classList.remove("spendable");
      }
    }
  }
}

function createMonsterDiv(monsterInfo, isBack, classPrefix) {
  classPrefix = classPrefix || "";
  let div = document.createElement("DIV");
  div.classList.add(classPrefix + "monster");
  let cnvContainer = document.createElement("DIV");
  let containerClass = isBack ? "monsterback" : "cnvcontainer";
  cnvContainer.classList.add(classPrefix + "monstercontainer", containerClass);
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("monstercnv");
  cnvContainer.appendChild(cnv);
  div.appendChild(cnvContainer);
  div.monsterInfo = monsterInfo;
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

function moveAndTranslateNode(div, destParent, classToggle) {
  let oldRect = div.getBoundingClientRect();
  div.parentNode.removeChild(div);
  if (classToggle != null) {
    div.classList.toggle(classToggle);
  }
  destParent.appendChild(div);
  let newRect = div.getBoundingClientRect();
  let diffX = Math.floor(oldRect.left - newRect.left);
  let diffY = Math.floor(oldRect.top - newRect.top);
  // TODO: also transition the destination characters.
  div.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px)";
}

function getNodeTranslation(div, destParent) {
  let oldRect = div.getBoundingClientRect();
  let newRect = destParent.getBoundingClientRect();
  let diffX = Math.floor(newRect.left - oldRect.left);
  let diffY = Math.floor(newRect.top - oldRect.top);
  return "translateX(" + diffX + "px) translateY(" + diffY + "px)";
}

function updatePlaces(places, activity) {
  let oldGates = [];
  for (let gateCont of document.getElementsByClassName("gatecontainer")) {
    if (gateCont.handle != null) {
      oldGates.push(gateCont.handle);
    }
  }
  for (let placeName in places) {
    let place = places[placeName];
    let handle = place.gate != null ? place.gate.handle : "nothing";
    let gateDiv = document.getElementById("place" + placeName + "gate");
    if (gateDiv != null) {  // Some places cannot have gates.
      updateGate(place, gateDiv, !oldGates.includes(handle));
    }
    if (place.sealed != null) {
      updateSeal(place);
    }
    if (place.clues != null) {
      updateClues(place);
    }
    if (place.closed != null) {
      updateClosed(place);
    }
    updateActivity(placeName, activity[placeName]);
  }
}

function updatePlaceBoxes(places, activity) {
  for (let placeName in places) {
    let place = places[placeName];
    let placeBox = document.getElementById("place" + placeName + "box");
    if (placeBox == null) {
      continue;
    }
    let placeChars = document.getElementById("place" + placeName + "chars");
    let placeMonsters = document.getElementById("place" + placeName + "monsters");
    placeBox.classList.toggle("withmonsters", placeMonsters && placeMonsters.children.length > 0);
    placeBox.classList.toggle("withdetails", placeChars && placeChars.children.length > 0);
    placeBox.classList.toggle("withgate", place.gate != null);
  }
}

function updateClues(place) {
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

function updateClosed(place) {
  let charsDiv = document.getElementById("place" + place.name + "chars");
  if (charsDiv == null) {  // The sky is a special case.
    return;
  }
  let isClosed = charsDiv.getElementsByClassName("closed").length;
  if (!place.closed && isClosed) {
    charsDiv.removeChild(charsDiv.getElementsByClassName("closed")[0]);
  } else if (place.closed && !isClosed) {
    let closedDiv = document.createElement("DIV");
    closedDiv.classList.add("closed");
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("closedcontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnvContainer.appendChild(cnv);
    closedDiv.appendChild(cnvContainer);
    charsDiv.appendChild(closedDiv);
    renderAssetToDiv(cnvContainer, "Closed");
  }
}

function updateActivity(placeName, activity) {
  if (activity == null) {
    activity = [];
  }
  let toRemove = {};
  let charsDiv = document.getElementById("place" + placeName + "chars");
  if (charsDiv == null) {  // e.g. outskirts
    return;
  }
  for (let act of charsDiv.getElementsByClassName("activity")) {
    toRemove[act.name] = act;
  }
  for (let [cardName, number] of activity) {
    if (toRemove[cardName]) {
      delete toRemove[cardName];
      continue;
    }
    let actDiv = document.createElement("DIV");
    actDiv.name = cardName;
    actDiv.classList.add("activity");
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("actcontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnvContainer.appendChild(cnv);
    actDiv.appendChild(cnvContainer);
    charsDiv.appendChild(actDiv);
    renderAssetToDiv(cnvContainer, "Activity", number);
    actDiv.onclick = function(e) { toggleGlobals(null, cardName) };
  }
  for (let cardName in toRemove) {
    charsDiv.removeChild(toRemove[cardName]);
  }
}

function updateGate(place, gateDiv, shouldAnimate) {
  let gateCont = gateDiv.getElementsByClassName("gatecontainer")[0];
  if (place.gate) {
    let gateName = place.gate.name;
    gateDiv.classList.add("placegatepresent");
    gateCont.handle = place.gate.handle;
    if (shouldAnimate) {
      let [holder, div] = addVisual(document.getElementById("enteringscroll"), place.gate.handle, place.gate.name, "fight", null, "Gate Back", null, null);
      holder.classList.add("entering");
      runningAnim.push(true);
      let lastAnim = function() { 
        doneAnimating(holder);
        renderAssetToDiv(gateCont, gateName);
        holder.parentNode.removeChild(holder);
        finishAnim();
      };
      let moveToBoard = function() {
        doneAnimating(holder);
        holder.style.transformOrigin = "top left";
        let oldRect = holder.getBoundingClientRect();
        let newRect = gateCont.getBoundingClientRect();
        let diffX = Math.floor(newRect.left - oldRect.left);
        let diffY = Math.floor(newRect.top - oldRect.top);
        let scaleFactor = (newRect.right - newRect.left) / (oldRect.right - oldRect.left);
        setTimeout(function() { 
          holder.ontransitionend = lastAnim;
          holder.ontransitioncancel = lastAnim;
          holder.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px) scale(" + scaleFactor+ ")";
        }, 10);
      };
      let turnAround = function() {
        doneAnimating(holder);
        holder.ontransitionend = moveToBoard;
        holder.ontransitioncancel = moveToBoard;
        holder.classList.remove("rotated");
      };
      holder.ontransitionend = turnAround;
      holder.ontransitioncancel = turnAround;
      setTimeout(function() { holder.classList.remove("entering"); holder.classList.add("rotated"); }, 10);

    } else {
      renderAssetToDiv(gateCont, gateName);
    }
  } else {
    let dest = null;
    for (let trophy of document.getElementsByClassName("trophy")) {
      if (trophy.handle == gateCont.handle) {
        dest = trophy;
        break;
      }
    }
    gateCont.handle = null;
    if (dest != null) {
      runningAnim.push(true);
      let lastAnim = function() {
        doneAnimating(gateCont);
        gateCont.style.transform = "none";
        clearAssetFromDiv(gateCont);
        gateDiv.classList.remove("placegatepresent");
        finishAnim();
      };
      gateCont.style.transformOrigin = "top left";
      let oldRect = gateCont.getBoundingClientRect();
      let newRect = dest.getBoundingClientRect();
      let diffX = Math.floor(newRect.left - oldRect.left);
      let diffY = Math.floor(newRect.top - oldRect.top);
      let scaleFactor = (newRect.right - newRect.left) / (oldRect.right - oldRect.left);
      gateCont.ontransitionend = lastAnim;
      gateCont.ontransitioncancel = lastAnim;
      gateCont.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px) scale(" + scaleFactor+ ")";
    } else {
      clearAssetFromDiv(gateCont);
      gateDiv.classList.remove("placegatepresent");
    }
  }
}

function updatePlaceChoices(uichoice, places, annotations, isMyChoice) {
  let notFound = [];
  for (let place of document.getElementsByClassName("placeinnerselect")) {
    place.classList.remove("selectable");
    place.classList.remove("hoverable");
    place.classList.add("unselectable");
    place.innerText = "❌";
  }
  for (let [idx, placeName] of places.entries()) {
    let place = document.getElementById("place" + placeName + "innerselect");
    if (place == null) {
      notFound.push(placeName);
      continue;
    }
    if (isMyChoice) {
      place.classList.add("selectable");
    } else {
      place.classList.add("hoverable");
    }
    place.classList.remove("unselectable");
    place.innerText = "Choose";
    if (annotations != null && annotations.length > idx) {
      place.innerText = formatServerString(annotations[idx]);
    } else {
      place.innerText = "Choose";
    }
  }
  if (isMyChoice && notFound.length) {
    addChoices(uichoice, notFound);
  }
}

function updateBottomText(gameStage, turnPhase, characters, turnIdx, playerIdx, host) {
  let uiprompt = document.getElementById("uiprompt");
  let btn = document.getElementById("start");
  uiprompt.innerText = "";
  btn.style.display = "none";
  if (gameStage == "setup") {
    if (host) {
      btn.style.display = "inline-block";
    }
    return;
  }
  if (turnIdx != null) {
    let name = serverNames[characters[turnIdx].name] ?? characters[turnIdx].name;
    uiprompt.innerText = name + "'s " + turnPhase + " phase";
  }
}

function updateGlobals(env, rumor, otherGlobals) {
  let envDiv = document.getElementById("environment");
  let envCnt = envDiv.getElementsByClassName("mythoscard")[0];
  let rumorDiv = document.getElementById("rumor");
  let rumorCnt = rumorDiv.getElementsByClassName("mythoscard")[0];
  if (env == null) {
    clearAssetFromDiv(envCnt);
    envDiv.classList.add("missing");
    envDiv.name = null;
    envDiv.annotation = null;
  } else {
    envDiv.classList.remove("missing");
    envDiv.name = env.name;
    envDiv.annotation = "Environment";
    renderAssetToDiv(envCnt, envDiv.name);
  }
  if (rumor == null) {
    clearAssetFromDiv(rumorCnt);
    rumorDiv.classList.add("missing");
    rumorDiv.name = null;
    rumorDiv.annotation = null;
  } else {
    rumorDiv.classList.remove("missing");
    rumorDiv.name = rumor.name;
    rumorDiv.annotation = "Rumor: " + rumor.progress + "/" + rumor.max_progress;
    renderAssetToDiv(rumorCnt, rumorDiv.name);
  }
  let toRemove = {};
  for (let node of document.getElementById("globals").getElementsByClassName("mythoscontainer")) {
    if (node.id == "environment" || node.id == "rumor") {
      continue;
    }
    toRemove[node.name] = node;
  }
  for (let glob of otherGlobals) {
    let globName = typeof(glob) == "string" ? glob : glob.name;
    if (toRemove[globName] != null) {
      delete toRemove[globName];
      continue;
    }
    let globDiv = document.createElement("DIV");
    globDiv.classList.add("mythoscontainer");
    globDiv.name = globName;
    globDiv.annotation = typeof(glob) == "string" ? null : glob.annotation;
    let globCont = document.createElement("DIV");
    globCont.classList.add("mythoscard", "cnvcontainer");
    let globCnv = document.createElement("CANVAS");
    globCnv.classList.add("mythoscnv");
    globCont.appendChild(globCnv);
    globDiv.appendChild(globCont);
    document.getElementById("globals").appendChild(globDiv);
    renderAssetToDiv(globCont, globName);
  }
  for (let name in toRemove) {
    toRemove[name].parentNode.removeChild(toRemove[name]);
  }
  let globalBox = document.getElementById("globals");
  if (globalBox.classList.contains("zoomed")) {
    globalBox.classList.remove("zoomed");
    toggleGlobals(null);
  }
}

function updateCurrentCard(current) {
  oldCurrent = current;
  let currDiv = document.getElementById("currentcard");
  if (current == null) {
    // TODO: because rendering happens in a promise, clearing the asset from the div can
    // actually happen before the promise is fulfilled. ugh.
    clearAssetFromDiv(currDiv);
    currDiv.classList.add("missing");
    return;
  }
  currDiv.classList.remove("missing");
  currDiv.cnvScale = 2;
  renderAssetToDiv(currDiv, current);
}

function toggleGlobals(e, frontCard) {
  let globalBox = document.getElementById("globals");
  let globalScroll = document.getElementById("globalscroll");
  let globalCards = document.getElementById("globalcards");
  if (globalBox.classList.contains("zoomed")) {
    globalBox.classList.remove("zoomed");
    globalScroll.style.display = "none";
    return;
  }
  globalBox.classList.add("zoomed");
  globalScroll.style.display = "flex";
  while (globalCards.getElementsByClassName("cardholder").length) {
    globalCards.removeChild(globalCards.getElementsByClassName("cardholder")[0]);
  }
  let count = 0;
  let toDisplay = null;
  for (let cont of document.getElementById("globals").getElementsByClassName("mythoscontainer")) {
    if (!cont.name) {
      continue;
    }
    count++;
    let [holder, container] = addVisual(globalCards, cont.name, cont.name, "mythos", null, null, null, cont.annotation);
    if (frontCard != null) {
      if (cont.name == frontCard) {
        toDisplay = holder;
      } else {
        holder.classList.add("unchoosable");
      }
    }
  }
  if (count > 4) {
    globalScroll.classList.add("overflowing");
    if (toDisplay != null) {
      // toDisplay.scrollIntoView({"inline": "center"}); TODO: this scrolls the entire document
      // instead, use scrollTo() after calculating the coords using getBoundingClientRect()
    }
  } else {
    globalScroll.classList.remove("overflowing");
  }
}

function updateDice(dice, playerIdx, monsterList) {
  let uidice = document.getElementById("uidice");
  if (dice == null) {
    uidice.style.display = "none";
    return;
  }
  if (dice.name != null) {  // Show the monster/card that is causing this dice roll.
    document.getElementById("cardchoicescroll").style.display = cardsStyle;
    document.getElementById("togglecards").style.display = "inline-block";
    setCardButtonText();
    if (monsterNames.includes(dice.name) && dice.check_type != "evade") {
      for (let m of monsterList) {
        if (m.name == dice.name) {
          showMonster(document.getElementById("uicardchoice"), m);
          break;
        }
      }
    } else {
      showActionSource(document.getElementById("uicardchoice"), dice.name);
    }
  }
  if (dice.prompt) {
    document.getElementById("uiprompt").innerText = formatServerString(dice.prompt);
  }

  let roll = dice.roll || [];
  let diceDiv = document.getElementById("dice");
  let btn = document.getElementById("dicebutton");
  uidice.style.display = "flex";
  while (diceDiv.getElementsByClassName("die").length > Math.max(dice.count, 0)) {
    diceDiv.removeChild(diceDiv.getElementsByClassName("die")[0])
  }
  while (diceDiv.getElementsByClassName("die").length < dice.count) {
    let die = document.createElement("DIV");
    die.classList.add("die");
    diceDiv.appendChild(die);
  }

  let allDice = diceDiv.getElementsByClassName("die");
  for (let die of allDice) {
    die.innerText = "?";
    die.classList.remove("success", "fail");
  }

  let remaining = dice.roll == null || roll.length < dice.count;
  for (let [idx, val] of roll.entries()) {
    if (idx >= allDice.length) {
      console.log("too many dice rolls");
      return;
    }
    if (dice.bad != null && dice.bad.includes(val)) {
      allDice[idx].classList.add("fail");
    }
    if (dice.success != null && idx < dice.success.length && dice.success[idx]) {
      allDice[idx].classList.add("success");
    }
    if (val != null) {
      allDice[idx].innerText = val;
    } else {
      remaining = true;
    }
  }
  if (dice.roller == playerIdx && remaining) {
    btn.style.display = "inline-block";
  } else {
    btn.style.display = "none";
  }
  if (dice.bad != null) {
    runningAnim.push(true);  // let the user see the dice for a moment
    setTimeout(finishAnim, 1000);
  }
}

function updateEventLog(eventLog) {
  let logDiv = document.getElementById("eventlog");
  if (eventLog.length < 1) {
    return;
  }
  if (logDiv.children.length == eventLog.length) {
    logDiv.removeChild(logDiv.lastChild);
  }
  while (logDiv.children.length < eventLog.length) {
    if (logDiv.lastChild != null) {
      logDiv.lastChild.classList.add("collapsed");
    }
    createLogDiv(eventLog[logDiv.children.length], logDiv, 0);
    logDiv.lastChild.onclick = function(e) {
      let theDiv = e.target;
      while (theDiv != null && theDiv.tagName != "DIV") {
        theDiv = theDiv.parentNode;
      }
      if (theDiv != null) {
        theDiv.classList.toggle("collapsed");
      }
    };
  }
  logDiv.scrollTop = logDiv.scrollHeight;
}

function createLogDiv(logEvent, parentNode, depth) {
  let logDiv = document.createElement("DIV");
  let textSpan = document.createElement("SPAN");
  textSpan.innerText = formatServerString(logEvent.text);
  textSpan.style.marginLeft = depth + "ch";
  logDiv.append(textSpan);
  logDiv.classList.add("logevent");
  for (let childLog of logEvent.sub_events) {
    createLogDiv(childLog, logDiv, depth+1);
  }
  parentNode.appendChild(logDiv);
}

function updateAvailableCharacters(characters, pendingChars) {
  let keys = Object.keys(allCharacters);
  // Ignore all characters that are already in the game.
  for (let character of characters) {
    let idx = keys.indexOf(character.name);
    if (idx >= 0) {
      keys.splice(idx, 1);
    }
  }
  // Ignore all characters that have been chosen by someone else.
  for (let name in pendingChars) {
    if (name == pendingName) {
      continue;
    }
    let idx = keys.indexOf(name);
    if (idx >= 0) {
      keys.splice(idx, 1);
    }
  }
  // Ignore all characters that have been devoured or retired.
  for (let name in allCharacters) {
    if (allCharacters[name].gone) {
      let idx = keys.indexOf(name);
      if (idx >= 0) {
        keys.splice(idx, 1);
      }
    }
  }
  keys.sort();
  availableChars = keys;
}

function updateAncientSelect(gameStage, host) {
  let ancientSelect = document.getElementById("ancientselect");
  if (gameStage != "setup" || !host) {
    ancientSelect.style.display = "none";
    return;
  }
  ancientSelect.style.display = "flex";
  if (ancientChoice == null) {
    let keys = Object.keys(allAncients);
    keys.sort();
    ancientChoice = (chosenAncient == null) ? keys[0] : chosenAncient;
  }

  let ancientSheet = document.getElementById("ancientchoice");
  renderAssetToDiv(ancientSheet, ancientChoice);
  let choiceButton = document.getElementById("chooseancientbutton");
  if (ancientChoice == chosenAncient) {
    choiceButton.innerText = "Chosen";
  } else if (chosenAncient != null) {
    choiceButton.innerText = "Change Choice";
  } else {
    choiceButton.innerText = "Choose";
  }
}

function updateAncientOne(ancientOne, terror) {
  renderAssetToDiv(document.getElementById("terror"), "Terror" + (terror || 0));
  let doom = document.getElementById("doom");
  if (ancientOne == null) {
    doom.maxValue = null;
    renderAssetToDiv(doom, "Doom");
    return;
  }
  doom.maxValue = ancientOneDoomMax[ancientOne.name];
  doom.statValue = ancientOne.doom;
  renderAssetToDiv(doom, ancientOne.name + " max");
  let worshippers = document.getElementById("worshippers");
  renderAssetToDiv(worshippers, ancientOne.name + " worshippers");
  let slumber = document.getElementById("slumber");
  renderAssetToDiv(slumber, ancientOne.name + " slumber");
}

function updateCharacterSelect(characters, playerIdx) {
  let selectors = document.getElementById("selectors");
  if (playerIdx != null && !characters[playerIdx].gone) {
    selectors.style.display = "none";
    return;
  }
  selectors.style.display = "flex";
  if (charChoice == null) {
    charChoice = availableChars[0];
  }
  drawChosenChar(allCharacters[charChoice]);
}

function drawChosenChar(character) {
  let sheet = document.getElementById("charchoicesheet");
  if (sheet == null) {
    let charChoiceDiv = document.getElementById("charchoice");
    sheet = createCharacterSheet(null, character.name, charChoiceDiv, false);
    sheet.id = "charchoicesheet";
    sheet.classList.remove("collapsed");
    sheet.getElementsByClassName("bagtabs")[0].classList.add("hidden");
    sheet.getElementsByClassName("playertop")[0].onclick = null;
  }
  let charMarker = sheet.getElementsByClassName("picture")[0];
  renderAssetToDiv(charMarker, character.name + " picture");
  let charName = sheet.getElementsByClassName("playername")[0];
  renderAssetToDiv(charName, character.name + " title");
  updateInitialStats(sheet, character);
  let sliders = sheet.getElementsByClassName("sliders")[0];
  renderAssetToDiv(sliders, character.name + " sliders");
  let focus = sheet.getElementsByClassName("focus")[0];
  renderAssetToDiv(focus, character.name + " focus");
  let home = sheet.getElementsByClassName("home")[0];
  renderAssetToDiv(home, character.name + " home");

  updateInitialPossessions(sheet, character);

  let choiceButton = document.getElementById("choosecharbutton");
  if (!availableChars.includes(character.name)) {
    sheet.classList.add("nochoose");
    choiceButton.innerText = "Not Available";
    choiceButton.disabled = true;
    return;
  }
  sheet.classList.remove("nochoose");
  choiceButton.disabled = false;
  if (character.name == pendingName) {
    choiceButton.innerText = "Chosen";
  } else if (pendingName != null) {
    choiceButton.innerText = "Change Choice";
  } else {
    choiceButton.innerText = "Choose";
  }
}

function updateCharacterSheets(characters, pendingCharacters, playerIdx, firstPlayer, choice) {
  // We're going to fix the visibility of the spendDiv first so that animations of the player
  // (un)spending their stats works correctly.
  let spendable = null;
  let spent = {};
  if (choice != null) {
    spendable = choice.spendable;
    for (let key in choice.spent) {
      for (let handle in choice.spent[key]) {
        spent[handle] = (spent[handle] || 0) + choice.spent[key][handle];
      }
    }
  }
  let spendDiv = document.getElementById("uispend");
  spendDiv.style.display = spendable == null ? "none" : "flex";

  let rightUI = document.getElementById("uichars");
  let toKeep = Object.keys(pendingCharacters);
  // If no characters have been chosen yet, draw the characters players have selected.
  if (!characters.length) {
    for (let charName in pendingCharacters) {
      let sheet = characterSheets[charName];
      if (sheet == null) {
        sheet = createCharacterSheet(null, allCharacters[charName], rightUI, false);
        characterSheets[charName] = sheet;
        addOptionToSelect("playerchoice", charName);
      }
      updateInitialStats(sheet, allCharacters[charName]);
      updateFocusHome(sheet, allCharacters[charName]);
      updateSliders(sheet, allCharacters[charName], false);
      updateInitialPossessions(sheet, allCharacters[charName]);
      // TODO: some characters may start with trophies.
    }
  }

  // Draw the characters currently in the game.
  for (let [idx, character] of characters.entries()) {
    if (character.gone) {
      continue;
    }
    toKeep.push(character.name);
    let sheet = characterSheets[character.name];
    if (sheet == null) {
      sheet = createCharacterSheet(idx, character, rightUI, playerIdx == idx);
      characterSheets[character.name] = sheet;
      addOptionToSelect("playerchoice", character.name);
    }
    // If this sheet is left over from before the game started, destroy and recreate it so that
    // it gets the proper onclick, ondrag, etc. handlers.
    if (sheet.getElementsByClassName("playertop")[0].idx == null) {
      rightUI.removeChild(sheet);
      sheet = createCharacterSheet(idx, character, rightUI, playerIdx == idx);
      characterSheets[character.name] = sheet;
    }
    let order = idx - firstPlayer;
    if (order < 0) {
      order += characters.length;
    }
    updateCharacterSheet(sheet, character, order, playerIdx == idx, choice, spent);
  }

  // Remove any sheets that are no longer needed.
  let toDestroy = [];
  for (let charName in characterSheets) {
    if (!toKeep.includes(charName)) {
      toDestroy.push(charName);
    }
  }
  for (let charName of toDestroy) {
    rightUI.removeChild(characterSheets[charName]);
    delete characterSheets[charName];
    removeOptionFromSelect("playerchoice", charName);
  }

  // Finally, if all character sheets are currently collapsed, uncollapse the player's own sheet.
  let unCollapsed = false;
  for (let sheet of rightUI.getElementsByClassName("player")) {
    if (!sheet.classList.contains("collapsed")) {
      unCollapsed = true;
      break;
    }
  }
  if (!unCollapsed && document.getElementsByClassName("you").length) {
    document.getElementsByClassName("you")[0].classList.remove("collapsed");
  }
  // Fix any spending.
  updateSpendList(spendable, spent);
  updateStatSpending(spendable);
  // Debug menu
  changePlayerChoice(null);
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
  charTop.onclick = function(e) { expandSheet(div) };
  if (idx != null) {
    charTop.idx = idx;
    charTop.ondrop = drop;
    charTop.ondragenter = dragEnter;
    charTop.ondragover = dragOver;
  }

  let charPic = document.createElement("DIV");
  charPic.classList.add("picture", "cnvcontainer");
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
  for (let stat in statNames) {
    let statDiv = document.createElement("DIV");
    statDiv.classList.add("stats", stat);  // intentionally omit cnvcontainer; see updateStats()
    let cnv = document.createElement("CANVAS");
    statDiv.appendChild(cnv);
    charStats.appendChild(statDiv);
    if (isPlayer) {
      statDiv.onclick = function(e) { spend(stat); };
      if (stat == "dollars") {
        statDiv.draggable = true;
        statDiv.ondragstart = dragStart;
        statDiv.ondragend = dragEnd;
      }
    }
  }
  charTop.appendChild(charStats);

  let focusHome = document.createElement("DIV");
  focusHome.classList.add("focushome");
  let focus = document.createElement("DIV");
  focus.classList.add("focus", "cnvcontainer");
  let focusCnv = document.createElement("CANVAS");
  focusCnv.classList.add("worldcnv");
  focus.appendChild(focusCnv);
  focusHome.appendChild(focus);
  let home = document.createElement("DIV");
  home.classList.add("home", "cnvcontainer");
  let homeCnv = document.createElement("CANVAS");
  homeCnv.classList.add("worldcnv");
  home.appendChild(homeCnv);
  focusHome.appendChild(home);
  div.appendChild(focusHome);

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

  let bag = document.createElement("DIV");
  bag.classList.add("bag");
  let bagTabs = document.createElement("DIV");
  bagTabs.classList.add("bagtabs");
  let posTab = document.createElement("DIV");
  posTab.classList.add("bagtab");
  posTab.innerText = "POSSESSIONS";
  posTab.onclick = function(e) { showPossessions(bag); };
  let trophyTab = document.createElement("DIV");
  trophyTab.classList.add("bagtab", "inactive");
  trophyTab.innerText = "TROPHIES";
  trophyTab.onclick = function(e) { showTrophies(bag); };
  bagTabs.appendChild(posTab);
  bagTabs.appendChild(trophyTab);
  bag.appendChild(bagTabs);
  let possessions = document.createElement("DIV");
  possessions.classList.add("possessions");
  bag.appendChild(possessions);
  let trophies = document.createElement("DIV");
  trophies.classList.add("possessions", "hidden");
  bag.appendChild(trophies);
  div.appendChild(bag);

  rightUI.appendChild(div);
  renderAssetToDiv(charPic, character.name + " picture");
  renderAssetToDiv(charName, character.name + " title");
  renderAssetToDiv(statsBg, "statsbg");
  for (let sliderDiv of sliders.getElementsByClassName("slider")) {
    renderAssetToDiv(sliderDiv, "Slider");
  }
  return div;
}

function expandSheet(sheetDiv) {
  for (let sheet of document.getElementById("uichars").getElementsByClassName("player")) {
    if (sheet == sheetDiv) {
      sheet.classList.remove("collapsed");
    } else {
      sheet.classList.add("collapsed");
    }
  }
}

function showPossessions(bag) {
  let possessions = bag.getElementsByClassName("possessions")[0];
  let trophies = bag.getElementsByClassName("possessions")[1];
  let posTab = bag.getElementsByClassName("bagtab")[0];
  let trophyTab = bag.getElementsByClassName("bagtab")[1];
  possessions.classList.remove("hidden");
  trophies.classList.add("hidden");
  posTab.classList.remove("inactive");
  trophyTab.classList.add("inactive");
}

function showTrophies(bag) {
  let possessions = bag.getElementsByClassName("possessions")[0];
  let trophies = bag.getElementsByClassName("possessions")[1];
  let posTab = bag.getElementsByClassName("bagtab")[0];
  let trophyTab = bag.getElementsByClassName("bagtab")[1];
  possessions.classList.add("hidden");
  trophies.classList.remove("hidden");
  posTab.classList.add("inactive");
  trophyTab.classList.remove("inactive");
}

function switchTab(tabName) {
  for (let elem of document.getElementsByClassName("rightelem")) {
    elem.classList.remove("shown");
    elem.classList.add("notshown");
  }
  for (let elem of document.getElementsByClassName("righttab")) {
    elem.classList.remove("shown");
  }
  if (tabName == "players") {
    document.getElementById("uichars").classList.add("shown");
    document.getElementById("uichars").classList.remove("notshown");
    document.getElementById("tabplayers").classList.add("shown");
  } else if (tabName == "log") {
    document.getElementById("eventlog").classList.add("shown");
    document.getElementById("eventlog").classList.remove("notshown");
    document.getElementById("tablog").classList.add("shown");
  } else {
    document.getElementById("admin").classList.add("shown");
    document.getElementById("admin").classList.remove("notshown");
    document.getElementById("tabadmin").classList.add("shown");
  }
}

function updateCharacterSheet(sheet, character, order, isPlayer, choice, spent) {
  sheet.style.order = order;
  let chosen = [];
  let spendable = null;
  let selectType = null;
  if (choice != null) {
    chosen = choice.chosen || [];
    spendable = choice.spendable;
    selectType = choice.select_type;
  }
  updateCharacterStats(sheet, character, isPlayer, spent, spendable);
  updateFocusHome(sheet, character);
  updateSliders(sheet, character, isPlayer);
  updatePossessions(sheet, character.possessions, isPlayer, spent, chosen, selectType);
  updateTrophies(sheet, character, isPlayer, spent);
  fixTransformOrigins(sheet);
}

function fixTransformOrigins(sheet) {
  let toFix = [];
  for (let pos of sheet.getElementsByClassName("possession")) {
    toFix.push(pos);
  }
  for (let trophy of sheet.getElementsByClassName("trophy")) {
    toFix.push(trophy);
  }
  for (let elem of toFix) {
    let totalWidth = elem.offsetParent.offsetWidth;
    let offsetCenter = elem.offsetLeft + (elem.offsetWidth / 2);
    if (offsetCenter / totalWidth < 0.3) {
      elem.style.transformOrigin = "left center";
    } else if (offsetCenter / totalWidth > 0.7) {
      elem.style.transformOrigin = "right center";
    } else {
      elem.style.transformOrigin = "center";
    }
  }
}

function updateInitialStats(sheet, character) {
  let stats = sheet.getElementsByClassName("playerstats")[0];
  let cfgs = [
    ["Stamina", "stamina", "white", "max_stamina"], ["Sanity", "sanity", "white", "max_sanity"],
  ];
  for (let cfg of cfgs) {
    let statDiv = sheet.getElementsByClassName(cfg[1])[0];
    renderAssetToDiv(statDiv, cfg[0]);
    statDiv.statValue = character[cfg[3]];
    statDiv.textColor = cfg[2];
  }
  cfgs = [["Clue", "clues", "white"], ["Dollar", "dollars", "black"]];
  for (let cfg of cfgs) {
    let statDiv = sheet.getElementsByClassName(cfg[1])[0];
    renderAssetToDiv(statDiv, cfg[0]);
    statDiv.statValue = character.initial[cfg[1]] || 0;
    statDiv.textColor = cfg[2];
  }
  // updateStats() will get called to render numbers at the end of handleData()
}

function updateCharacterStats(sheet, character, isPlayer, spent, spendable) {
  let spendDiv = document.getElementById("uispend");
  let stats = sheet.getElementsByClassName("playerstats")[0];
  let cfgs = [
    ["Stamina", "stamina", "white", "max_stamina"], ["Sanity", "sanity", "white", "max_sanity"],
    ["Clue", "clues", "white", null], ["Dollar", "dollars", "black", null],
  ];
  for (let [assetName, name, color, maxName] of cfgs) {
    let statDiv = sheet.getElementsByClassName(name)[0];
    renderAssetToDiv(statDiv, assetName);
    let oldValue = statDiv.statValue;
    let statSpent = isPlayer ? (spent[name] || 0) : 0;
    let newValue = character[name] - statSpent;
    statDiv.statValue = newValue;
    statDiv.textColor = color;
    statDiv.maxValue = maxName == null ? null : character[maxName];
    if (isPlayer && spendable != null) {
      for (let i = 0; i < oldValue - newValue; i++) {
        let movingStat = document.createElement("DIV");
        movingStat.classList.add("stats", "cnvcontainer", name, "spendable", "abs");
        let cnv = document.createElement("CANVAS");
        cnv.classList.add("cluecnv");
        movingStat.appendChild(cnv);
        movingStat.onclick = function(e) { unspend(name); };
        statDiv.appendChild(movingStat);
        renderAssetToDiv(movingStat, assetName);
        moveAndTranslateNode(movingStat, spendDiv, "abs");
        runningAnim.push(true);
        movingStat.ontransitionend = function() { movingStat.classList.remove("moving"); doneAnimating(movingStat); finishAnim(); };
        movingStat.ontransitioncancel = function() { movingStat.classList.remove("moving"); doneAnimating(movingStat); finishAnim(); };
        setTimeout(function() { movingStat.classList.add("moving"); movingStat.style.transform = "none"; }, 10);
      }
      let removable = [];
      let maxRemovable = spendDiv.getElementsByClassName(name).length;
      for (let i = 0; (i < newValue - oldValue) && (i < maxRemovable); i++) {
        removable.push(spendDiv.getElementsByClassName(name)[i]);
      }
      for (let toRemove of removable) {
        // TODO: find some way to make it visible for the whole journey
        moveAndTranslateNode(toRemove, statDiv, "abs");
        runningAnim.push(true);
        toRemove.ontransitionend = function() { toRemove.parentNode.removeChild(toRemove); finishAnim(); };
        toRemove.ontransitioncancel = function() { toRemove.parentNode.removeChild(toRemove); finishAnim(); };
        setTimeout(function() { toRemove.classList.add("moving"); toRemove.style.transform = "none"; }, 10);
      }
    }
  }
  // updateStats() will get called to render numbers at the end of handleData()
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
  let doom = document.getElementById("doom");
  renderAssetToDiv(doom, doom.assetName, doom.variant).then(function() {
    if (!doom.maxValue) {
      return;
    }
    let pct = doom.statValue / doom.maxValue;
    let cnv = doom.getElementsByTagName("CANVAS")[0];
    let ctx = cnv.getContext("2d");
    ctx.save();
    ctx.globalAlpha = 0.7; 
    ctx.globalCompositeOperation = "source-atop";
    ctx.fillStyle = "black";
    let rotation = 2 * Math.PI * pct - Math.PI / 2; 
    ctx.beginPath();
    ctx.arc(cnv.width / 2, cnv.height / 2, cnv.width / 2, rotation, 3 * Math.PI / 2, false);
    ctx.lineTo(cnv.width / 2, cnv.height / 2);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  });
}

function updateFocusHome(sheet, character) {
  let focus = sheet.getElementsByClassName("focus")[0];
  renderAssetToDiv(focus, character.name + " focus");
  let home = sheet.getElementsByClassName("home")[0];
  renderAssetToDiv(home, character.name + " home");
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

function updateInitialPossessions(sheet, character) {
  let pDiv = sheet.getElementsByClassName("possessions")[0];
  // Clearing out existing children is not strictly necessary, but makes the ordering look better.
  while (pDiv.children.length) {
    pDiv.removeChild(pDiv.firstChild);
  }
  let possessions = [];
  for (let ability of character.abilities) {
    possessions.push({name: ability, active: false, exhausted: false, handle: ability});
  }
  for (let [idx, pos] of character.fixed.entries()) {
    possessions.push({name: pos, active: false, exhausted: false, handle: pos + idx});
  }
  for (let deck in character.random) {
    for (let i = 0; i < character.random[deck]; i++) {
      possessions.push({name: deck, active: false, exhausted: false, handle: deck + i});
    }
  }
  updatePossessions(sheet, possessions, false, {}, [], null);
}

function updatePossessions(sheet, possessions, isPlayer, spent, chosen, selectType) {
  let pDiv = sheet.getElementsByClassName("possessions")[0];
  let handleToInfo = {};
  let toRemove = [];
  for (let pos of possessions) {
    handleToInfo[pos.handle] = pos;
  }
  for (let div of pDiv.getElementsByClassName("possession")) {
    if (handleToInfo[div.handle] == null) {
      toRemove.push(div);
      continue;
    }
    updatePossession(div, handleToInfo[div.handle], spent, chosen, selectType);
    delete handleToInfo[div.handle];
  }
  for (let div of toRemove) {
    pDiv.removeChild(div);
  }
  for (let handle in handleToInfo) {
    let div = createPossession(handleToInfo[handle], isPlayer, pDiv);
    updatePossession(div, handleToInfo[div.handle], spent, chosen, selectType);
  }
}

function createPossession(info, isPlayer, sheet) {
  let div = document.createElement("DIV");
  div.classList.add("possession", "cnvcontainer");
  div.cnvScale = 2.5;
  div.handle = info.handle;
  if (abilityNames.includes(info.handle)) {
    div.classList.add("big");
    div.cnvScale = 2;
  }
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("poscnv");
  div.appendChild(cnv);
  let chosenDiv = document.createElement("DIV");
  chosenDiv.classList.add("chosencheck");
  chosenDiv.innerText = "✔️";
  div.appendChild(chosenDiv);
  div.onmouseenter = bringTop;
  div.onmouseleave = returnBottom;
  let handle = info.handle;
  if (isPlayer) {
    div.onclick = function(e) { clickAsset(div, handle); };
    div.draggable = true;
    div.ondragstart = dragStart;
    div.ondragend = dragEnd;
  }
  sheet.appendChild(div);
  renderAssetToDiv(div, info.name);
  return div;
}

function updatePossession(div, info, spent, chosen, selectType) {
  // Note that the hands must be recomputed every time (e.g. for the axe).
  let handsText = "✔️";
  if (info.hands_used) {
    handsText = "✋".repeat(info.hands_used);
  } else if (info.hands_used != null) {
    handsText = "✊";
  }
  let selectText = "✔️";
  if (selectType == "x") {
    selectText = "❌";
  } else if (selectType == "hands") {
    selectText = handsText;
  }
  // If there is an item choice active, then selectType should not be null. When selectType is not
  // null, show the items being selected. If the selectType is hands, then also show any active
  // items. Otherwise, do not confuse the player by showing the active items as well.
  // If there is no item choice, then show the active items. When showing the
  // active items, show the hands text. Possessions that do not use hands (e.g. the voice spell)
  // will continue to show a checkmark.
  // Always show spent items with a checkmark.
  let showText = "✔️";
  if (selectType != null) {
    showText = selectText;
  } else if (info.active || info.in_use) {
    showText = handsText;
  }
  let chosenDiv = div.getElementsByClassName("chosencheck")[0];
  chosenDiv.innerText = showText;
  div.classList.toggle("chosen", chosen.includes(info.handle));
  if (selectType == "hands" || selectType == null) {
    div.classList.toggle("active", Boolean(info.active));
  } else {
    div.classList.remove("active");
  }
  div.classList.toggle("spent", spent[info.handle] != null);
  div.classList.toggle("exhausted", Boolean(info.exhausted));
}

function updateTrophies(sheet, character, isPlayer, spent) {
  let tDiv = sheet.getElementsByClassName("possessions")[1];
  let handleToInfo = {};
  let toRemove = [];
  for (let trophy of character.trophies) {
    handleToInfo[trophy.handle] = trophy;
  }
  for (let div of tDiv.getElementsByClassName("trophy")) {
    if (handleToInfo[div.handle] == null) {
      toRemove.push(div);
      continue;
    }
    updateTrophy(div, spent);
    delete handleToInfo[div.handle];
  }
  for (let div of toRemove) {
    tDiv.removeChild(div);
  }
  for (let handle in handleToInfo) {
    let div = createTrophy(handleToInfo[handle], isPlayer, tDiv);
    updateTrophy(div, spent);
  }
}

function createTrophy(info, isPlayer, tDiv) {
  let assetName = info.name;
  let handle = info.handle;
  let div = document.createElement("DIV");
  let containerClass = monsterNames.includes(assetName) ? "monsterback" : "cnvcontainer";
  div.classList.add("trophy", containerClass);
  div.cnvScale = 2.5;
  div.handle = handle;
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("poscnv");
  div.appendChild(cnv);
  div.onmouseenter = bringTop;
  div.onmouseleave = returnBottom;
  tDiv.appendChild(div);
  let chosenDiv = document.createElement("DIV");
  chosenDiv.classList.add("chosencheck");
  chosenDiv.innerText = "✔️";
  div.appendChild(chosenDiv);
  if (isPlayer) {
    div.onclick = function(e) { useAsset(handle); };
  }
  if (monsterNames.includes(assetName)) {
    div.monsterInfo = info;
  } else {
    renderAssetToDiv(div, assetName);
  }
  return div;
}

function updateTrophy(div, spent) {
  div.classList.toggle("spent", spent[div.handle] != null);
  if (div.monsterInfo != null) {
    renderMonsterBackToDiv(div, div.monsterInfo);
  }
}

function renderMonsterBackToDiv(div, monsterData) {
  let cnv = div.getElementsByTagName("CANVAS")[0];
  let cnvScale = div.cnvScale || 1;
  cnv.width = div.offsetWidth * cnvScale;
  cnv.height = div.offsetHeight * cnvScale;

  // Movement type border & white center box.
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "whitesmoke";
  let colors = {
    "unique": "olivedrab",
    "flying": "lightblue",
    "stalker": "purple",
    "aquatic": "orange",
    "fast": "red",
    "stationary": "gold",
    "normal": "black",
  };
  if (colors[monsterData.movement] != null) {
    ctx.fillStyle = colors[monsterData.movement];
  }
  ctx.fillRect(0, 0, cnv.width, cnv.height);
  ctx.fillStyle = "#e5dada";
  ctx.fillRect(cnv.width / 20, cnv.height / 20, 9 * cnv.width / 10, 9 * cnv.height / 10);

  // Render any special card text. TODO: can we reuse code from assets.js?
  ctx.save();
  let imgData = imageInfo[monsterData.name + " text"];
  if (imgData != null && imgData.srcnum != null && imgData.filternum != null) {
    let img = document.getElementById("img" + imgData.srcnum);
    let mask = document.getElementById("img" + imgData.filternum);
    if (img != null & mask != null) {
      let renderWidth, renderHeight, origWidth, origHeight;
      origWidth = mask.naturalWidth || mask.width;
      origHeight = mask.naturalHeight || mask.height;
      renderWidth = cnv.width * 9 / 10;
      renderHeight = renderWidth / origWidth * origHeight;
      let scale = (imgData.scale || 1) * (cnv.width * 9 / 10) / origWidth;
      let renderBottom = cnv.height * 13 / 20;
      let renderCenter = renderBottom - (renderHeight / 2);
      ctx.translate(cnv.width/2, renderCenter);
      ctx.beginPath();
      ctx.moveTo(-renderWidth/2, -renderHeight/2);
      ctx.lineTo(renderWidth/2, -renderHeight/2);
      ctx.lineTo(renderWidth/2, renderHeight/2);
      ctx.lineTo(-renderWidth/2, renderHeight/2);
      ctx.closePath();
      ctx.clip();

      ctx.save();
      ctx.rotate(Math.PI * (imgData.rotation || 0) / 180);
      ctx.scale(scale, scale);
      ctx.drawImage(img, (-imgData.xoff || 0), (-imgData.yoff || 0));
      ctx.restore();
    }
  }
  ctx.restore();
  // End special card text.

  let fontSize;

  // Monster attributes.
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillStyle = "black";
  let attributes = {
    "spawn": "Spawn",
    "mask": "Mask",
    "endless": "Endless",
    "ambush": "Ambush",
    "elusive": "Elusive",
    "undead": "Undead",
    "physical resistance": "Physical Resistance",
    "magical resistance": "Magical Resistance",
    "physical immunity": "Physical Immunity",
    "magical immunity": "Magical Immunity",
  };

  let offsetHeight = cnv.height / 10;
  for (let name in attributes) {
    if (monsterData.attributes.includes(name)) {
      fontSize = getTextSize(ctx, attributes[name], 4 * cnv.width / 5, cnv.height / 13);
      ctx.font = /*"bold " +*/ fontSize + "px serif";
      ctx.fillText(attributes[name], cnv.width / 10, offsetHeight);
      offsetHeight += cnv.height / 13;
    }
  }

  let attrs = [["nightmarish", "Nightmarish", "horror_bypass"], ["overwhelming", "Overwhelming", "combat_bypass"]];
  for (let [name, text, attr] of attrs) {
    if (monsterData.attributes.includes(name) && monsterData[attr] != null) {
      let displayText = text + " " + monsterData[attr];
      fontSize = getTextSize(ctx, displayText, 4 * cnv.width / 5, cnv.height / 13);
      ctx.font = /*"bold " +*/ fontSize + "px serif";
      ctx.fillText(displayText, cnv.width / 10, offsetHeight);
      offsetHeight += cnv.height / 13;
    }
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  // Horror modifier
  let horrorModifier;
  if (monsterData.horror_difficulty == null) {
    horrorModifier = "-";
  } else if (monsterData.horror_difficulty >= 0) {
    horrorModifier = "+" + monsterData.horror_difficulty;
  } else {
    horrorModifier = "" + monsterData.horror_difficulty;
  }
  fontSize = getTextSize(ctx, horrorModifier, 2 * cnv.width / 9, 3 * cnv.height / 20);
  ctx.font = fontSize + "px sans-serif";
  ctx.fillStyle = "#3366aa";
  ctx.fillText(horrorModifier, cnv.width / 6, 29 * cnv.height / 40);

  // Combat modifier
  let combatModifier;
  if (monsterData.combat_difficulty == null) {
    combatModifier = "-";
  } else if (monsterData.combat_difficulty >= 0) {
    combatModifier = "+" + monsterData.combat_difficulty;
  } else {
    combatModifier = "" + monsterData.combat_difficulty;
  }
  fontSize = getTextSize(ctx, combatModifier, 2 * cnv.width / 9, 3 * cnv.height / 20);
  ctx.font = fontSize + "px sans-serif";
  ctx.fillStyle = "#dd0000";
  ctx.fillText(combatModifier, 5 * cnv.width / 6, 29 * cnv.height / 40);

  // Toughness
  fontSize = getTextSize(ctx, "💧", cnv.width / 3, 3 * cnv.height / 20);
  ctx.font = fontSize + "px sans-serif";
  ctx.fillStyle = "black";
  ctx.filter = "hue-rotate(135deg)";
  let increment = (cnv.width / 3) / Math.max(monsterData.toughness+1, 6);
  let center = cnv.width / 2;
  for (let i = monsterData.toughness; i >= 1; i--) {
    let count = i - (monsterData.toughness+1) / 2;
    ctx.fillText("💧", cnv.width / 2 + count * increment, 17 * cnv.height / 20);
  }
  ctx.restore();

  renderDamage(ctx, monsterData.horror_damage, "horror", "#3366aa", cnv.width, cnv.height);
  renderDamage(ctx, monsterData.combat_damage, "combat", "#dd0000", cnv.width, cnv.height);
}

function renderDamage(ctx, damage, damageType, color, cnvWidth, cnvHeight) {
  if (damage == null || damage <= 0) {
    return;
  }
  let xCenter = (damageType == "horror") ? cnvWidth / 6 : 5 * cnvWidth / 6;
  let yCenter = 7 * cnvHeight / 8;
  if (damage == 1) {
    renderSingleDamage(ctx, damageType, color, xCenter, yCenter, cnvWidth / 5, cnvHeight / 8);
    return;
  }
  if (damage == 2) {
    renderSingleDamage(ctx, damageType, color, xCenter + cnvWidth / 22, yCenter, cnvWidth / 10, cnvHeight / 8);
    renderSingleDamage(ctx, damageType, color, xCenter - cnvWidth / 22, yCenter, cnvWidth / 10, cnvHeight / 8);
    return;
  }
  if (damage == 3) {
    renderSingleDamage(ctx, damageType, color, xCenter + cnvWidth / 25, yCenter + cnvHeight / 33, cnvWidth / 10, cnvHeight / 16);
    renderSingleDamage(ctx, damageType, color, xCenter - cnvWidth / 25, yCenter + cnvHeight / 33, cnvWidth / 10, cnvHeight / 16);
    renderSingleDamage(ctx, damageType, color, xCenter, yCenter - cnvHeight / 33, cnvWidth / 10, cnvHeight / 16);
    return;
  }
  if (damage == 4) {
    renderSingleDamage(ctx, damageType, color, xCenter + cnvWidth / 18, yCenter, cnvWidth / 10, cnvHeight / 16);
    renderSingleDamage(ctx, damageType, color, xCenter - cnvWidth / 18, yCenter, cnvWidth / 10, cnvHeight / 16);
    renderSingleDamage(ctx, damageType, color, xCenter, yCenter - cnvHeight / 25, cnvWidth / 10, cnvHeight / 16);
    renderSingleDamage(ctx, damageType, color, xCenter, yCenter + cnvHeight / 25, cnvWidth / 10, cnvHeight / 16);
    return;
  }
  // All others: just render one, but put a number in it.
  renderSingleDamage(ctx, damageType, color, xCenter, yCenter, cnvWidth / 5, cnvHeight / 8);
  ctx.save();
  ctx.fillStyle = "white";
  let fontSize = getTextSize(ctx, damage, 3 * cnvWidth / 20, 3 * cnvHeight / 32);
  ctx.font = "bold " + fontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(damage, xCenter, yCenter);
  ctx.restore();
}

function renderSingleDamage(ctx, damageType, color, xCenter, yCenter, maxWidth, maxHeight) {
  let width = Math.min(maxWidth, 4 * maxHeight / 3);
  let height = 3 * width / 4;
  ctx.save();
  ctx.fillStyle = color;
  if (damageType == "horror") {
    ctx.beginPath();
    ctx.ellipse(xCenter, yCenter, 2 * width / 5, 2 * height / 5, 2 * Math.PI, 0, 2 * Math.PI);
    ctx.fill();
  } else {
    let fontSize = getTextSize(ctx, "❤️", maxWidth, maxHeight);
    ctx.font = fontSize + "px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("❤️", xCenter, yCenter);
  }
  ctx.restore();
}

function redrawMonsterBacks() {
  for (let elem of document.getElementsByClassName("monsterback")) {
    let monsterInfo = elem.monsterInfo || elem.parentNode.monsterInfo;
    if (monsterInfo == null) {
      continue;
    }
    renderMonsterBackToDiv(elem, monsterInfo);
  }
}

function redrawCustomCanvases() {
  updateStats();
  redrawMonsterBacks();
}
