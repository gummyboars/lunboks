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
charChoice = null;
ancientChoice = null;
oldCurrent = null;
oldStage = null;
oldVisuals = {};
newVisuals = [];
gainedClues = [];
gainedCards = {};
lostCards = {};
runningAnim = [];
messageQueue = [];
statTimeout = null;
autoClickTimeout = null;
cardsShown = true;
stepping = false;
statNames = {"stamina": "Stamina", "sanity": "Sanity", "clues": "Clue", "dollars": "Dollar"};
cursorURLs = {};

isDragging = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;
boardRotate = 0;
boardScale = 1;

function onmove(event) {
  if (isDragging) {
    let changeX = event.clientX - startX;
    let changeY = event.clientY - startY;
    if (boardRotate == 0) {
      dX = changeX;
      dY = changeY;
    } else {
      dY = changeX;
      dX = -changeY;
    }
    moveBoard();
  }
}
function ondown(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  startX = event.clientX;
  startY = event.clientY;
  isDragging = true;
}
function onup(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  if (isDragging) {
    isDragging = false;
    offsetX += dX;
    offsetY += dY;
    dX = 0;
    dY = 0;
  }
}
function onout(event) {
  if (isDragging) {
    isDragging = false;
    offsetX += dX;
    offsetY += dY;
    dX = 0;
    dY = 0;
  }
}
function onwheel(event) {
  event.preventDefault();
  let oldScale = boardScale;
  if (event.deltaY < 0) {
    boardScale += 0.05;
  } else if (event.deltaY > 0) {
    boardScale -= 0.05;
  }
  boardScale = Math.min(Math.max(0.125, boardScale), 4);
  let board = document.getElementById("board");
  let rect = board.getBoundingClientRect();
  let centerX = (rect.left + rect.right) / 2;
  let centerY = (rect.top + rect.bottom) / 2;
  let mouseX = event.clientX - centerX;
  let mouseY = event.clientY - centerY;
  let mouseXScaled = mouseX * boardScale / oldScale;
  let mouseYScaled = mouseY * boardScale / oldScale;
  if (boardRotate == 0) {
    offsetX -= (mouseXScaled - mouseX);
    offsetY -= (mouseYScaled - mouseY);
  } else {
    offsetY -= (mouseXScaled - mouseX);
    offsetX += (mouseYScaled - mouseY);
  }
  moveBoard();
}
function flipBoard() {
  if (boardRotate == 0) {
    boardRotate = -90;
    for (let p of document.getElementsByClassName("place")) {
      p.style.transform = "translateX(-50%) translateY(-50%) rotate(90deg)";
    }
  } else {
    boardRotate = 0;
    for (let p of document.getElementsByClassName("place")) {
      p.style.transform = "translateX(-50%) translateY(-50%) rotate(0deg)";
    }
  }
  adjustLocationClasses();
  moveBoard();
}
function moveBoard() {
  document.getElementById("board").style.transform = "rotate(" + boardRotate + "deg) translate(" + (offsetX+dX) + "px, " + (offsetY+dY) + "px) scale(" + boardScale + ")";
}

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
    console.log("============================================");
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
  document.getElementById("board").cnvScale = 4;
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
      div.oncontextmenu = function(e) { rightClickPlace(e, name); };
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
      let chars = document.createElement("DIV");
      chars.id = "place" + name + "chars";
      chars.classList.add("placechars");
      box.appendChild(chars);
      box.appendChild(monstersDiv);
      if (places[name].y < 0.5) {
        box.classList.add("placeupper");
      } else {
        box.classList.add("placelower");
      }
      if (places[name].x < 0.5) {
        box.classList.add("placeleft");
      } else {
        box.classList.add("placeright");
      }

      let gateDiv = document.createElement("DIV");
      gateDiv.id = "place" + name + "gate";
      gateDiv.classList.add("placegate");
      monstersDiv.appendChild(gateDiv);
      let gateCont = document.createElement("DIV");
      gateCont.classList.add("gatecontainer", "cnvcontainer");
      gateDiv.appendChild(gateCont);
      let gate = document.createElement("CANVAS");
      gate.classList.add("gate");
      gateCont.appendChild(gate);
      let highlight = document.createElement("DIV");
      highlight.id = "place" + name + "highlight";
      highlight.classList.add("placehighlight", placeType);
      box.appendChild(highlight);
      let innerSelect = document.createElement("DIV");
      innerSelect.id = "place" + name + "innerselect";
      innerSelect.classList.add("placeinnerselect", placeType);
      innerSelect.onclick = function(e) { clickPlace(name); };
      box.appendChild(innerSelect);
      let monsterCount = document.createElement("DIV");
      monsterCount.classList.add("monstercount");
      let minus = document.createElement("DIV");
      minus.classList.add("minus");
      minus.onclick = function(e) { changeMonsterCount(name, false); };
      let minusText = document.createElement("DIV");
      minusText.innerText = "➖";
      minus.appendChild(minusText);
      let plus = document.createElement("DIV");
      plus.classList.add("plus");
      plus.onclick = function(e) { changeMonsterCount(name, true); };
      let plusText = document.createElement("DIV");
      plusText.innerText = "➕";
      plus.appendChild(plusText);
      let monsterCountText = document.createElement("DIV");
      monsterCountText.classList.add("monstercounttext");
      monsterCount.appendChild(minus);
      monsterCount.appendChild(plus);
      monsterCount.appendChild(monsterCountText);
      box.appendChild(monsterCount);
      cont.appendChild(div);

      addOptionToSelect("placechoice", name);
    }
  }
  placeLocations();
  adjustLocationClasses();
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

  document.getElementById("uicont").onmousemove = onmove;
  document.getElementById("uicont").onmousedown = ondown;
  document.getElementById("uicont").onmouseup = onup;
  document.getElementById("uicont").onmouseout = onout;
  document.getElementById("uicont").onwheel = onwheel;

  // Position the board.
  let contRect = document.getElementById("uicont").getBoundingClientRect();
  let boardRect = document.getElementById("board").getBoundingClientRect();
  offsetX = (contRect.right + contRect.left - boardRect.right - boardRect.left) / 2;
  moveBoard();

  createCursors();

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
      let parentCnv = document.getElementById("boardcanvas");
      if (!setDivXYPercent(div, parentCnv, "board", name)) {
        div.style.top = 100 * places[name].y + "%";
        div.style.left = 100 * places[name].x + "%";
        div.xpct = places[name].x;
        div.ypct = places[name].y;
      }
    }
  }
}

function adjustLocationClasses() {
  for (let [placeType, places] of [["location", locations], ["street", streets]]) {
    for (let name in places) {
      let div = document.getElementById("place" + name);
      let box = document.getElementById("place" + name + "box");
      if (boardRotate == 0) {
        box.classList.toggle("placeupper", div.ypct < 0.5);
        box.classList.toggle("placelower", div.ypct >= 0.5);
        box.classList.toggle("placeleft", div.xpct < 0.5);
        box.classList.toggle("placeright", div.xpct >= 0.5);
      } else {
        box.classList.toggle("placeupper", div.xpct >= 0.5);
        box.classList.toggle("placelower", div.xpct < 0.5);
        box.classList.toggle("placeleft", div.ypct < 0.5);
        box.classList.toggle("placeright", div.ypct >= 0.5);
      }
    }
  }
}

function createCursors() {
  let spendables = ["Stamina", "Sanity", "Clue", "Dollar"];
  for (let spendable of spendables) {
    for (let def of [true, false]) {
      let div = document.createElement("DIV");
      div.classList.add("cursordiv");
      div.id = (def ? "default" : "") + spendable + "cursor";
      let cnv = document.createElement("CANVAS");
      cnv.width = 26;
      cnv.height = 26;
      cnv.classList.add("markercnv");
      div.appendChild(cnv);
      document.getElementById("uimain").appendChild(div);
      if (!def) {
        renderAssetToDiv(div, spendable).then(function() {
          cnv.toBlob(function(blob) { storeBlobURL(blob, spendable, def); } );
        });
      } else {
        renderDefaultToCanvas(cnv, 26, 26, spendable);
        cnv.toBlob(function(blob) { storeBlobURL(blob, spendable, def); });
      }
    }
  }
}

function storeBlobURL(blob, spendable, isDefault) {
  let url = URL.createObjectURL(blob);
  if (!isDefault || cursorURLs[spendable] == null) {
    cursorURLs[spendable] = url;
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
  let submatch = p1.match(/(.*[^0-9])([0-9]*)$/);
  if (submatch != null && serverNames[submatch[1]] != null) {
    return serverNames[submatch[1]];
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
  if (!runningAnim.length) {
    let numVisuals = document.getElementById("uicardchoice").getElementsByClassName("cardholder").length;
    document.getElementById("cardchoicescroll").classList.toggle("hidden", numVisuals == 0 || !cardsShown);
    document.getElementById("togglecards").classList.toggle("hidden", numVisuals == 0);
    setCardButtonText();
  }
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
  removeDummyObjects();
  updateAvailableCharacters(data.characters, data.pending_chars);
  updateCharacterSelect(data.game_stage, data.characters, data.player_idx);
  updateAncientSelect(data.game_stage, data.host);
  updateOptions(data.options);
  updateCharacterSheets(data.characters, data.pending_chars, data.player_idx, data.first_player, myChoice, data.chooser == data.player_idx ? data.sliders : null);
  updateBottomText(data.game_stage, data.turn_phase, data.characters, data.turn_idx, data.player_idx, data.host);
  recordOldVisuals();
  updateGlobals(data.environment, data.rumor, data.other_globals);
  let gateCount = updatePlaces(data.places, data.activity, data.current);
  animateClues(data.current);
  updateAncientOne(data.game_stage, data.ancient_one, data.terror, gateCount, data.gate_limit, data.characters.length);
  updateCharacters(data.characters);
  updateSliderButton(data.sliders, data.chooser == data.player_idx);
  updateMonsters(data.choice, data.monsters);
  updateChoices(data.choice, data.current, data.chooser == data.player_idx, data.characters[data.chooser], data.autochoose);
  updateMonsterChoices(data.choice, data.monsters, data.chooser == data.player_idx, data.characters[data.chooser]);
  updatePlaceBoxes(data.places, data.activity);
  updateUsables(data.usables, data.log, mySpendables, myChoice, data.sliders, data.dice);  // TODO: Better name might be updateOverlay or updateDoneUsingButton
  updateDice(data.dice, data.player_idx, data.monsters);
  updateBottomCards(data.bottom);
  updateCurrentCard(data.current, data.visual, data.monster, data.choice);
  animateMissedGate(data.missed_gate);
  animateVisuals();
  animateVictory(data.game_stage);
  oldCurrent = data.current;
  oldStage = data.game_stage;
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

function rightClickPlace(event, place) {
  let rect = event.currentTarget.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right) {
    return;
  }
  if (event.clientY < rect.top || event.clientY > rect.bottom) {
    return;
  }
  event.preventDefault();
  clickPlace(place);
}

function changeMonsterCount(place, plus) {
  let choice = {};
  choice[place] = (plus ? 1 : -1);
  ws.send(JSON.stringify({"type": "choice", "choice": choice}));
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

function toggleExpansion(e, expansion) {
  let enabled = e.target.checked;
  ws.send(JSON.stringify({"type": "option", "expansion": expansion, "enabled": enabled}));
}

function toggleOption(e, expansion, option) {
  let enabled = e.target.checked;
  ws.send(JSON.stringify({"type": "option", "expansion": expansion, "option": option, "enabled": enabled}));
}

function doneUse(e) {
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
  ws.send(JSON.stringify({"type": "choice", "choice": "confirm"}));
}

function resetMonsterChoice(e) {
  ws.send(JSON.stringify({"type": "choice", "choice": "reset"}));
}

function toOutskirts(e) {  // TODO: just send the rest to outskirts if possible?
  let monsterDivList = [];
  let choicesDiv = document.getElementById("monsterchoices");
  for (let monsterDiv of choicesDiv.getElementsByClassName("monster")) {
    monsterDivList.push(monsterDiv);
  }
  monsterDivList.reverse();
  for (let monsterDiv of monsterDivList) {
    if (monsterDiv.monsterIdx != null && monsterDiv.draggable) {
      ws.send(JSON.stringify({"type": "choice", "choice": {"Outskirts": monsterDiv.monsterIdx}}));
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
    ws.send(JSON.stringify({"type": "choice", "choice": {"cup": dragged.monsterIdx}}));
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
  let choice = {};
  choice[placeName] = dragged.monsterIdx;
  ws.send(JSON.stringify({"type": "choice", "choice": choice}));
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

function resetSliders(e) {
  ws.send(JSON.stringify({"type": "set_slider", "name": "reset"}));
}

function removeDummyObjects() {
  let enterDiv = document.getElementById("enteringscroll");
  while (enterDiv.getElementsByClassName("dummy").length > 0) {
    enterDiv.removeChild(enterDiv.getElementsByClassName("dummy")[0]);
  }
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
  let gateCont = placeDiv.getElementsByClassName("gatecontainer")[0];
  if (gateCont != null && gateCont.handle != null) {
    let div = document.createElement("DIV");
    div.classList.add("biggate", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("monstercnv");
    div.appendChild(cnv);
    box.appendChild(div);
    renderAssetToDiv(div, gateCont.assetName);
  }
  for (let monsterDiv of placeDiv.getElementsByClassName("monster")) {
    let container = document.createElement("DIV");
    let handle = monsterDiv.monsterInfo.handle;
    container.onclick = function(e) { makeChoice(handle); };
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

function updateMonsters(choice, monster_list) {
  let moveFromBoard = [];
  for (let i = 0; i < monster_list.length; i++) {
    let monster = monster_list[i];
    let monsterPlace = null;
    if (monsterPlace == null && monster != null && monster.place && monster.place != "cup") {
      monsterPlace = monster.place;
    }
    if (monsterPlace == null) {
      if (monsters[i] != null) {
        let dest = null;
        for (let trophy of document.getElementsByClassName("trophy")) {
          if (trophy.handle == monsters[i].monsterInfo.handle) {
            dest = trophy;
            break;
          }
        }
        let sources = [];
        let box = document.getElementById("monsterdetailsbox");
        if (document.getElementById("monsterdetails").style.display == "flex") {
          for (let monsterDetails of box.getElementsByClassName("bigmonster")) {
            if (monsterDetails.monsterInfo.handle == monsters[i].monsterInfo.handle) {
              sources.push(monsterDetails);
            }
          }
        }
        if (!sources.length) {
          sources = [monsters[i]];
        }
        // Our priority order is cardholder -> monsterdetails -> monster on board
        // However, the cardholder can have monsters not on the board. So here, we choose to
        // animate only the monsters in the details box or on the board.
        for (let src of document.getElementsByClassName("cardholder")) {
          if (src.handle == monsters[i].monsterInfo.handle) {
            sources = [];
            break;
          }
        }
        let orig = monsters[i];
        if (dest != null && sources.length) {
          runningAnim.push(true);
          let callback = function() {
            if (sources.length > 1) {  // Not the monster on the board
              orig.parentNode.removeChild(orig);
              hideMonsters(null);
            }
          };
          for (let source of sources) {
            source.classList.add("movingslow");
            setTimeout(function() { translateNodeThenRemove(source, dest, callback); }, 10);
          }
        } else if (dest == null && sources.length == 1) {
          let holder = createVisual(document.getElementById("enteringscroll"), newVisual(monster.handle, "fight"));
          runningAnim.push(true);
          let lastAnim = function() {
            doneAnimating(holder);
            holder.parentNode.removeChild(holder);
            finishAnim();
          };
          let startLeaving = function() {
            doneAnimating(holder);
            setTimeout(function() {
              holder.ontransitionend = lastAnim;
              holder.ontransitioncancel = lastAnim;
              holder.classList.add("leaving");
            }, 10);
          };
          holder.ontransitionend = startLeaving;
          holder.ontransitioncancel = startLeaving;
          moveFromBoard.push([holder, sources[0]]);
        } else {
          monsters[i].parentNode.removeChild(monsters[i]);
        }
        monsters[i] = null;
      }
      continue;
    }
    let place = document.getElementById("place" + monsterPlace + "monsters");
    if (monsterPlace == "cup") {
      place = document.getElementById("monsterchoices");
    }
    if (place == null) {
      console.log("Unknown place " + monster.place);
      continue;
    }
    if (monsters[i] == null) {
      monsters[i] = createMonsterDiv(monster);
      monsters[i].monsterIdx = i;
      let container = monsters[i].getElementsByClassName("cnvcontainer")[0];
      place.appendChild(monsters[i]);
      if (document.getElementById("eventlog").children.length) {  // Hack to not do this on the first message.
        let holder = createVisual(document.getElementById("enteringscroll"), newVisual(monster.handle, "fight"));
        holder.classList.add("rising");
        runningAnim.push(true);
        let callback = function() { renderAssetToDiv(container, monster.name); };
        let moveToBoard = function() {
          doneAnimating(holder);
          setTimeout(function() { translateNodeThenRemove(holder, container, callback); }, 10);
        };
        holder.ontransitionend = moveToBoard;
        holder.ontransitioncancel = moveToBoard;
        setTimeout(function() { holder.classList.remove("rising"); }, 10);
      } else {
        renderAssetToDiv(container, monster.name);
      }
    } else {
      monsters[i].monsterInfo = monster;
      animateMovingDiv(monsters[i], place);
    }
  }
  for (let [holder, boardDiv] of moveFromBoard) {
    holder.classList.add("noanimate");
    translateNode(holder, boardDiv);
    setTimeout(function() {
      holder.classList.remove("noanimate");
      holder.style.removeProperty("transform");
    }, 10);
  }
  for (let [holder, boardDiv] of moveFromBoard) {
    boardDiv.parentNode.removeChild(boardDiv);
  }
}

function updateSliderButton(sliders, isMySliders) {
  if (sliders) {
    document.getElementById("uiprompt").innerText = formatServerString(sliders.prompt);
  }
  let sliderButtons = document.getElementById("sliderbuttons");
  if (sliderButtons != null) {
    sliderButtons.classList.toggle("hidden", !(sliders && isMySliders));
  }
}

function animateMissedGate(gate) {
  if (gate == null) {
    return;
  }
  let charsDiv = document.getElementById("place" + gate + "chars");
  let hasSeal = charsDiv.getElementsByClassName("seal").length;
  let toBlink = null;
  if (hasSeal) {
    toBlink = charsDiv.getElementsByClassName("seal")[0];
  } else {
    for (let charDiv of charsDiv.getElementsByClassName("marker")) {
      if (charDiv == characterMarkers["Scientist"]) {
        toBlink = charDiv;
        break;
      }
    }
  }
  if (toBlink != null) {
    runningAnim.push(true);
    toBlink.onanimationend = function() { toBlink.onanimationend = null; toBlink.onanimationcancel = null; toBlink.classList.remove("blinking"); finishAnim(); };
    toBlink.onanimationcancel = function() { toBlink.onanimationend = null; toBlink.onanimationcancel = null; toBlink.classList.remove("blinking"); finishAnim(); };
    toBlink.classList.add("blinking");
    return;
  }
  let gateDiv = document.getElementById("place" + gate + "gate");
  if (gateDiv == null || !gateDiv.classList.contains("placegatepresent")) {
    return;
  }
  if (!gateDiv.getElementsByClassName("gate").length) {
    return;
  }
  let gateCnv = gateDiv.getElementsByClassName("gate")[0];
  runningAnim.push(true);
  gateCnv.onanimationend = function() { gateCnv.onanimationend = null; gateCnv.onanimationcancel = null; gateCnv.classList.remove("shaking"); finishAnim(); };
  gateCnv.onanimationcancel = function() { gateCnv.onanimationend = null; gateCnv.onanimationcancel = null; gateCnv.classList.remove("shaking"); finishAnim(); };
  gateCnv.classList.add("shaking");
}

function animateVictory(gameStage) {
  if (oldStage == null || oldStage == "victory" || gameStage != "victory") {
    return;
  }
  let seals = document.getElementsByClassName("seal");
  let ancientDetails = document.getElementById("ancientdetails");
  if (seals.length < 6) {
    ancientDetails.ontransitionend = function() { doneAnimating(ancientDetails); finishAnim(); };
    ancientDetails.ontransitioncancel = function() { doneAnimating(ancientDetails); finishAnim(); };
    setTimeout(function() { ancientDetails.classList.add("fade"); document.getElementById("ancientone").classList.add("fade"); }, 2500);
    return;
  }
  // Animate the seals moving on top of the ancient one and making the ancient one fade away.
  let currentSeals = [];
  for (let i = 0; i < 6; i++) {
    currentSeals.push(seals[i]);
  }
  let destinations = [];
  let enterDiv = document.getElementById("ancientdetails");
  let theCenter = document.createElement("DIV");
  theCenter.classList.add("sealcenter");
  let centerSeal = document.createElement("DIV");
  centerSeal.classList.add("seal", "cnvcontainer");
  let cnv = document.createElement("CANVAS");
  cnv.classList.add("markercnv");
  centerSeal.appendChild(cnv);
  theCenter.appendChild(centerSeal);
  enterDiv.appendChild(theCenter);
  renderAssetToDiv(centerSeal, "Seal");
  destinations.push(centerSeal);
  let boxDiv = document.createElement("DIV");
  boxDiv.classList.add("sealbox");
  boxDiv.id = "sealbox0";
  theCenter.appendChild(boxDiv);
  for (let i = 0; i < 5; i++) {
    let arm = document.createElement("DIV");
    arm.classList.add("sealarm");
    arm.id = "sealarm" + i;
    let sealCnt = document.createElement("DIV");
    sealCnt.classList.add("seal");
    let newSeal = document.createElement("DIV");
    newSeal.classList.add("seal", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("markercnv");
    newSeal.appendChild(cnv);
    sealCnt.appendChild(newSeal);
    arm.appendChild(sealCnt);
    theCenter.appendChild(arm);
    renderAssetToDiv(newSeal, "Seal");
    destinations.push(newSeal);
  }
  for (let i = 1; i < 5; i++) {
    let box = document.createElement("DIV");
    box.classList.add("sealbox");
    box.id = "sealbox" + i;
    boxDiv.appendChild(box);
  }

  runningAnim.push(true);
  for (let i = 0; i < 6; i++) {
    translateNode(destinations[i], currentSeals[i]);
  }
  let fadeAncient = function() {
    doneAnimating(boxDiv);
    ancientDetails.ontransitionend = function() { doneAnimating(ancientDetails); finishAnim(); };
    ancientDetails.ontransitioncancel = function() { doneAnimating(ancientDetails); finishAnim(); };
    setTimeout(function() { ancientDetails.classList.add("fade"); document.getElementById("ancientone").classList.add("fade"); }, 5);
  };
  boxDiv.ontransitionend = fadeAncient;
  boxDiv.ontransitioncancel = fadeAncient;
  let showLines = function() {
    for (let box of document.getElementsByClassName("sealbox")) {
      box.classList.add("shown");
    }
  };
  destinations[0].ontransitionend = function() { doneAnimating(destinations[0]); showLines(); };
  destinations[0].ontransitioncancel = function() { doneAnimating(destinations[0]); showLines(); };
  setTimeout(function() {
    for (let i = 0; i < 6; i++) {
      destinations[i].classList.add("mover");
      destinations[i].style.removeProperty("transform");
    }
  }, 5);
}

function toggleCards(e) {
  cardsShown = !cardsShown;
  document.getElementById("cardchoicescroll").classList.toggle("hidden", !cardsShown);
  setCardButtonText();
}

function setCardButtonText() {
  document.getElementById("togglecards").classList.toggle("hide", cardsShown);
}

function scrollCards(e, dir) {
  let container = e.currentTarget.parentNode;
  let cardScroller = container.getElementsByClassName("cardscroller")[0];
  let rect = cardScroller.getBoundingClientRect();
  let width = rect.right - rect.left;
  let amount = dir * Math.ceil(width / 4);
  cardScroller.scrollLeft = cardScroller.scrollLeft + amount;
}

function getNameAndBack(handleOrName) {
  let stripped = handleOrName;
  let match = handleOrName.match(/(.*[^0-9])([0-9]*)$/);
  if (match != null) {
    stripped = match[1];
  }
  if (stripped != handleOrName && assetNames.includes(handleOrName)) {  // e.g. Northside1, Mythos12, Gate20
    if (assetNames.includes(stripped + " Card")) {
      return [handleOrName, stripped + " Card"];
    }
    return [handleOrName, null];
  }
  // Handles like Wither0, Zombie1, Dog, Flute
  let deckLists = {"common": commonNames, "unique": uniqueNames, "spells": spellNames, "skills": skillNames, "allies": allyNames};
  for (let deckName in deckLists) {
    if (deckLists[deckName].includes(stripped)) {
      return [stripped, deckName];
    }
  }
  return [stripped, null];
}

function recordOldVisuals() {
  oldVisuals = {};
  newVisuals = [];
  let uicardchoice = document.getElementById("uicardchoice");
  for (let holder of uicardchoice.getElementsByClassName("cardholder")) {
    if (oldVisuals[holder.handle] == null) {
      oldVisuals[holder.handle] = [holder];
    } else {
      oldVisuals[holder.handle].push(holder);
    }
  }
}

function animateVisuals() {
  let enteringVisuals = [];
  let movingVisuals = [];
  let leavingVisuals = [];
  let actuallyNewVisuals = [];

  // Identify any cards that will be moving to a character sheet.
  for (let handle in gainedCards) {
    if (lostCards[handle] != null) {  // Card was traded.
      continue;
    }
    let dest = gainedCards[handle];
    let [source, isBack] = findVisual(handle);
    if (source != null) {  // Found an appropriate card in uicardchoice
      leavingVisuals.push([source, dest, source.getBoundingClientRect()]);
      continue;
    }
    // No existing card found - create a new one and animate it.
    // Note that this uses enteringscroll, and does not change the placement of any other visuals.
    if (document.getElementById("eventlog").children.length) {  // Hack to not do this on the first message.
      let holder = createVisual(document.getElementById("enteringscroll"), newVisual(handle, "card"));
      holder.classList.add("rising");
      runningAnim.push(true);
      let moveToSheet = function() {
        doneAnimating(holder);
        setTimeout(function() { translateNodeThenRemove(holder, dest); }, 10);
      };
      holder.ontransitionend = moveToSheet;
      holder.ontransitioncancel = moveToSheet;
      enteringVisuals.push(holder);
    }
  }

  // Re-sort the visuals so that fronts are processed before backs. This is because we want a
  // back to consume a back from oldVisuals, but only after the fronts have had a chance to find
  // existing backs inside of oldVisuals.
  let newFrontVisuals = [];
  let newBackVisuals = [];
  for (let visual of newVisuals) {
    if (["common", "unique", "spells", "skills", "allies"].includes(visual.handle)) {
      newBackVisuals.push(visual);
      continue;
    }
    if (visual.handle.endsWith("Card")) {
      newBackVisuals.push(visual);
      continue;
    }
    newFrontVisuals.push(visual);
  }
  newVisuals = [...newFrontVisuals, ...newBackVisuals];

  // Go through the new visuals and consume any old visuals we can. Find truly new visuals.
  for (let visual of newVisuals) {
    let [existing, isBack] = findVisual(visual.handle, visual.monster);
    if (existing != null) {
      let boundingRect = existing.getBoundingClientRect();
    }
    if (existing != null) {
      movingVisuals.push([existing, visual, isBack, existing.getBoundingClientRect()]);
      continue;
    }
    actuallyNewVisuals.push([findExternal(visual.handle, visual.monster), visual]);
  }

  // Now that any used old visuals have been consumed, find destinations for the remaining old visuals.
  for (let handleOrName in oldVisuals) {
    let visuals = oldVisuals[handleOrName];
    for (let visual of visuals) {
      if (visual.classList.contains("used")) {
        continue;
      }
      let external = null;
      // Some things should not be collapsed back to the monster on the board. Specifically, we
      // never collapse monsterchoices back to the board. We also don't collapse anything back to
      // the board if there are other visuals being shows (e.g. if we just evaded one monster of many).
      if (!visual.getElementsByClassName("monsterchoice").length) {
        let hasMonster = visual.getElementsByClassName("monsterback").length;
        external = findExternal(handleOrName, hasMonster);
        if (visuals.length == 2) {  // Special case where both fightchoices are leaving.
          let allFightChoices = true;
          for (let v of visuals) {
            if (v.getElementsByClassName("fightchoice").length < 1) {
              allFightChoices = false;
              break;
            }
          }
          if (allFightChoices) {
            external = null;
          }
        }
        if (external != null && external.classList.contains("monstercontainer") && newVisuals.length) {
          external = null;
        }
      }
      if (lostCards[handleOrName] != null && gainedCards[handleOrName] == null) {
        external = lostCards[handleOrName].failed ? "shaking" : "leaving";
        lostCards[handleOrName] = null;
      }
      leavingVisuals.push([visual, external, visual.getBoundingClientRect()]);
    }
  }

  // Identify any cards that will be leaving from a character sheet.
  for (let handle in lostCards) {
    if (gainedCards[handle] != null) {  // Card was traded.
      continue;
    }
    if (lostCards[handle] == null) {  // Already animated from card choice.
      continue;
    }
    let holder = createVisual(document.getElementById("enteringscroll"), newVisual(handle, "card"));
    holder.classList.add("noanimate");
    translateNode(holder, lostCards[handle]);
    runningAnim.push(true);
    let lastAnim = function() { doneAnimating(holder); holder.parentNode.removeChild(holder); finishAnim(); };
    let startLeaving = function() {
      doneAnimating(holder);
      setTimeout(function() {
        holder.ontransitionend = lastAnim;
        holder.ontransitioncancel = lastAnim;
        holder.classList.add("leaving");
      }, 10);
    };
    if (lostCards[handle].failed) {
      startLeaving = function() {
        doneAnimating(holder);
        holder.classList.add("shaking");
        setTimeout(lastAnim, 1200);
      };
    }
    holder.ontransitionend = startLeaving;
    holder.ontransitioncancel = startLeaving;
    setTimeout(function() { holder.classList.remove("noanimate"); holder.style.removeProperty("transform"); }, 10);
  }

  if (enteringVisuals.length || movingVisuals.length || leavingVisuals.length || actuallyNewVisuals.length) {
    cardsShown = true;
    document.getElementById("cardchoicescroll").classList.remove("hidden");
    document.getElementById("togglecards").classList.remove("hidden");
  } else {
    document.getElementById("cardchoicescroll").classList.add("hidden");
    document.getElementById("togglecards").classList.add("hidden");
  }
  setCardButtonText();

  // All necessary information has been computed and recorded. Now we can mutate uicardchoice.
  let uiCardChoice = document.getElementById("uicardchoice");

  // Animate the divs that are leaving. Start by attaching them to the body at their current
  // coordinates, then translate and remove them.
  let uiBox = document.getElementById("ui").getBoundingClientRect();
  for (let [visual, dest, rect] of leavingVisuals) {
    let diffX = rect.left - uiBox.left;
    let diffY = rect.top - uiBox.top;
    visual.style.position = "absolute";
    visual.style.left = `${diffX}px`;
    visual.style.top = `${diffY}px`;
    visual.style.zIndex = 19;
    document.getElementById("ui").appendChild(visual);
    while (visual.getElementsByClassName("desc").length) {
      visual.removeChild(visual.getElementsByClassName("desc")[0]);
    }
    runningAnim.push(true);
    if (dest == null) {  // Not going anywhere, but may still be referenced by other animations.
      // TODO: in some situations (i.e. passing a rumor), should this fade out instead?
      setTimeout(function() { visual.parentNode.removeChild(visual); finishAnim(); }, 10);
    } else if (typeof(dest) == "string") {
      if (dest == "shaking") {
        setTimeout(function() { visual.parentNode.removeChild(visual); finishAnim(); }, 1200);
      } else {
        visual.ontransitionend = function() { doneAnimating(visual); visual.parentNode.removeChild(visual); finishAnim(); };
        visual.ontransitioncancel = function() { doneAnimating(visual); visual.parentNode.removeChild(visual); finishAnim(); };
      }
      setTimeout(function() { visual.classList.add(dest); }, 10);
    } else {
      let trueDest = dest.classList.contains("monstercontainer");
      translateNodeThenRemove(visual, dest, null, trueDest);
    }
  }

  // Some moving visuals are moving from a card back to a card front. For those, we replace the
  // entire card because of the ability to reuse a card back for multiple card fronts.
  for (let entry of movingVisuals) {
    let [existing, visual, isBack, rect] = entry;
    if (!isBack) {
      entry.push(null);
      continue;
    }
    entry.push(createVisual(uiCardChoice, visual));
    if (existing.parentNode == uiCardChoice && existing.classList.contains("used")) {
      uiCardChoice.removeChild(existing);
    }
  }

  // Add new visuals. We will animate them after adding anything needed from moving visuals.
  for (let entry of actuallyNewVisuals) {
    let [source, visual] = entry;
    entry.push(createVisual(uiCardChoice, visual));
  }

  // Update any visuals that are moving before animating. This is because the order of the visuals
  // may change, moving other visuals to different locations.
  for (let [existing, visual, isBack, rect, newDiv] of movingVisuals) {
    if (newDiv == null) {
      createVisual(uiCardChoice, visual, existing);
    }
  }

  // All visuals are now in their new location. Animate the transition.
  for (let [existing, visual, isBack, rect, newDiv] of movingVisuals) {
    let div = newDiv ?? existing;
    let wasMoved = translateNodeOrFalse(div, rect);
    if (isBack) {
      if (wasMoved) {
        div.style.transform += " rotateY(-180deg)";
      } else {
        div.style.transform = "rotateY(-180deg)";
      }
    }
    if (wasMoved || isBack) {
      div.classList.add("noanimate");
      runningAnim.push(true);
      div.ontransitionend = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
      div.ontransitioncancel = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
      setTimeout(function() { div.classList.remove("noanimate"); div.style.removeProperty("transform"); }, 10);
    } else {
      setTimeout(function() { visual.callback(div); }, 10);
    }
  }

  // Animate any new visuals, either from a source or from the bottom of the screen.
  for (let [source, visual, div] of actuallyNewVisuals) {
    div.classList.add("noanimate");
    runningAnim.push(true);
    if (source != null) {
      div.ontransitionend = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
      div.ontransitioncancel = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
      translateNode(div, source);
      setTimeout(function() { div.classList.remove("noanimate"); div.style.removeProperty("transform"); }, 10);
      continue;
    }
    if (visual.backName == null) {
      div.classList.add("rising");
      div.ontransitionend = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
      div.ontransitioncancel = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
      setTimeout(function() { div.classList.remove("noanimate"); div.classList.remove("rising"); }, 10);
    } else {
      div.classList.add("entering", "rotated");
      let rotate = function() {
        div.ontransitionend = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
        div.ontransitioncancel = function() { doneAnimating(div); visual.callback(div); finishAnim(); };
        div.classList.remove("rotated");
      };
      div.ontransitionend = rotate;
      div.ontransitioncancel = rotate;
      setTimeout(function() { div.classList.remove("noanimate"); div.classList.remove("entering"); }, 10);
    }
  }

  // Animate anything that is entering, but is not in the cardchoice div.
  for (let visual of enteringVisuals) {
    setTimeout(function() { visual.classList.remove("rising"); }, 10);
  }
}

function findVisual(handle, monster) {
  // Start with exact match.
  for (let handleOrName in oldVisuals) {
    if (handle != handleOrName) {
      continue;
    }
    for (let [idx, value] of oldVisuals[handleOrName].entries()) {
      // Because monsterchoice visuals have a top and bottom, we use findExternal instead of
      // considering them to be moving visuals.
      if (value.getElementsByClassName("monsterchoice").length) {
        continue;
      }
      // Match monster backs with monster backs and monster fronts with monster fronts.
      if ((value.getElementsByClassName("monsterback").length == 0) == (monster == null)) {
        oldVisuals[handleOrName].splice(idx, 1);
        value.classList.remove("used");
        return [value, false];
      }
    }
  }
  let [name, backName] = getNameAndBack(handle);
  // After exact matches are exhausted, try to match to the name corresponding to the handle.
  for (let handleOrName in oldVisuals) {
    if (name != handleOrName) {
      continue;
    }
    for (let [idx, value] of oldVisuals[handleOrName].entries()) {
      if (value.getElementsByClassName("monsterchoice").length) {
        continue;
      }
      // Match monster backs with monster backs and monster fronts with monster fronts.
      if ((value.getElementsByClassName("monsterback").length == 0) == (monster == null)) {
        oldVisuals[handleOrName].splice(idx, 1);
        return [value, false];
      }
    }
  }
  // Lastly, if this is the front of a card, try to match with an existing card back so we can
  // animate turning the card around.
  for (let handleOrName in oldVisuals) {
    if (backName == handleOrName && oldVisuals[handleOrName].length > 0) {
      if (oldVisuals[handleOrName].length > 1) {
        return [oldVisuals[handleOrName].pop(), true];
      }
      // We are allowed to reuse card backs, so don't consume the last one.
      oldVisuals[handleOrName][0].classList.add("used");
      return [oldVisuals[handleOrName][0], true];
    }
  }
  return [null, null];
}

function findExternal(handle, hasMonster) {
  let [name, unused] = getNameAndBack(handle);
  hasMonster = !!hasMonster;
  for (let glob of document.getElementsByClassName("mythoscontainer")) {
    if (glob.name == name) {
      // When the current card shows up for the first time, animate it from the bottom of the
      // screen instead of animating it from the globals sidebar.
      if (glob.id == "currentcard" && glob.name != oldCurrent) {
        continue;
      }
      return glob.getElementsByClassName("mythoscard")[0];
    }
  }
  for (let pos of document.getElementsByClassName("possession")) {
    if (pos.handle == handle) {
      return pos;
    }
  }
  for (let trophy of document.getElementsByClassName("trophy")) {
    if (trophy.handle == handle) {
      return trophy;
    }
  }
  // The monster front/back matches up with the corresponding half of the monsterchoice visual.
  let monsterClass = hasMonster ? "monsterback" : "cnvcontainer";
  for (let div of document.getElementsByClassName("monsterchoice")) {
    if (div.parentNode.handle == handle) {
      for (let inner of div.getElementsByClassName("fightchoice")) {
        if (inner.classList.contains(monsterClass)) {
          return inner;
        }
      }
    }
  }
  // If we don't find any matching visuals (fightchoice or monsterchoice) for this monster, but
  // we do have the back side (instead of the front), animate from the back side (or vice versa).
  for (let div of document.getElementsByClassName("fightchoice")) {
    if (div.parentNode.handle == handle) {
      // Make sure a leaving fight/monster choice doesn't find itself.
      if (!div.classList.contains(monsterClass)) {
        return div;
      }
    }
  }
  for (let monsterIdx in monsters) {
    if (monsters[monsterIdx] != null && monsters[monsterIdx].monsterInfo.handle == handle) {
      return monsters[monsterIdx].getElementsByClassName("monstercontainer")[0];
    }
  }
  for (let gateCont of document.getElementsByClassName("gatecontainer")) {
    if (gateCont.handle == handle) {
      return gateCont;
    }
  }
  // When a character gains a card from a card choice, the card choice only has a name, but the
  // possession will have a handle. In that case, we match to the possession by name.
  // TODO: card choice should use handles instead of names, but that might take some work
  for (let pos of document.getElementsByClassName("possession")) {
    if (pos.handle == name) {
      return pos;
    }
  }
  return null;
}

function updateChoices(choice, current, isMyChoice, chooser, autoChoose) {
  let doneItems = document.getElementById("doneitems");
  let uichoice = document.getElementById("uichoice");
  let uicardchoice = document.getElementById("uicardchoice");
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
  for (let highlight of document.getElementsByClassName("placehighlight")) {
    highlight.classList.remove("shown");
  }
  for (let pos of pDiv.getElementsByClassName("possession")) {
    pos.classList.remove("choosable");
  }
  uichoice.style.display = "none";
  if (doneItems != null) {
    doneItems.style.display = "none";
  }
  if (choice != null && choice.board_monster != null && isMyChoice) {
    monsterBox.classList.add("choosable");
  } else {
    monsterBox.classList.remove("choosable");
  }
  // Clean out any old choices it may have.
  for (let child of uichoice.getElementsByClassName("choice")) {
    child.classList.add("todelete");
  }
  let resultChoice = document.getElementById("resultchoice");
  if (resultChoice != null) {
    resultChoice.classList.add("todelete");
  }
  let spendChoice = document.getElementById("spendchoice");
  if (spendChoice != null) {
    spendChoice.classList.add("todelete");
  }
  if (choice == null || choice.to_spawn != null) {
    document.getElementById("charoverlay").classList.remove("shown");
    while (uichoice.getElementsByClassName("todelete").length) {
      uichoice.removeChild(uichoice.getElementsByClassName("todelete")[0]);
    }
    if (resultChoice != null && resultChoice.classList.contains("todelete")) {
      resultChoice.parentNode.removeChild(resultChoice);
    }
    if (spendChoice != null && spendChoice.classList.contains("todelete")) {
      spendChoice.parentNode.removeChild(spendChoice);
    }
    return;
  }
  // Set display style for uichoice div.
  if (choice.items == null && choice.board_monster == null && isMyChoice) {
    uichoice.style.display = "flex";
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
  if (choice.board_monster != null) {
    document.getElementById("charoverlay").classList.remove("shown");
    while (uichoice.getElementsByClassName("todelete").length) {
      uichoice.removeChild(uichoice.getElementsByClassName("todelete")[0]);
    }
    if (resultChoice != null && resultChoice.classList.contains("todelete")) {
      resultChoice.parentNode.removeChild(resultChoice);
    }
    if (spendChoice != null && spendChoice.classList.contains("todelete")) {
      spendChoice.parentNode.removeChild(spendChoice);
    }
    return;
  }
  let showOverlay = isMyChoice && (choice.items != null || choice.spendable != null);
  document.getElementById("charoverlay").classList.toggle("shown", showOverlay);
  if (choice.cards == null && choice.monster == null && choice.monsters == null) {
    if (choice.visual != null) {
      let rumorDiv = document.getElementById("rumor");
      let desc = (choice.visual == rumorDiv.name) ? rumorDiv.annotation : null;
      let pct = (choice.visual == rumorDiv.name) ? rumorDiv.percent : null;
      newVisuals.push(newVisual(choice.visual, "card", {"descText": desc, "backgroundPct": pct}));
    }
  }
  if (choice.items != null) {
    if (isMyChoice) {
      for (let pos of pDiv.getElementsByClassName("possession")) {
        pos.classList.toggle("choosable", choice.items.includes(pos.handle));
      }
      doneItems.style.display = "inline-block";
    }
    if (choice.monster != null) {
      newVisuals.push(newVisual(choice.monster.handle, "fight", {"monster": choice.monster}));
    }
  } else {  // choice.items == null
    if (choice.places != null) {
      updatePlaceChoices(uichoice, choice.places, choice.annotations, isMyChoice);
      if (choice.monster != null) {
        newVisuals.push(newVisual(choice.monster.handle, "fight", {"monster": choice.monster}));
      }
    } else if (choice.cards != null) {
      addCardChoices(uichoice, uicardchoice, choice.cards, choice.invalid_choices, choice.spent, choice.remaining_spend, choice.remaining_max, choice.annotations, choice.sort_uniq, current, isMyChoice, autoChoose, chooser);
    } else if (choice.monsters != null) {
      addMonsterChoices(uichoice, uicardchoice, choice.monsters, choice.invalid_choices, choice.annotations, current, isMyChoice);
    } else if (choice.monster != null) {
      addFightOrEvadeChoices(uichoice, uicardchoice, choice.monster, choice.choices, choice.invalid_choices, choice.annotations, current, isMyChoice);
    } else {
      if (isMyChoice) {
        addChoices(uichoice, choice.choices, choice.invalid_choices, choice.spent, choice.remaining_spend, choice.remaining_max);
      }
    }
  }
  while (uichoice.getElementsByClassName("todelete").length) {
    uichoice.removeChild(uichoice.getElementsByClassName("todelete")[0]);
  }
  if (resultChoice != null && resultChoice.classList.contains("todelete")) {
    resultChoice.parentNode.removeChild(resultChoice);
  }
  if (spendChoice != null && spendChoice.classList.contains("todelete")) {
    spendChoice.parentNode.removeChild(spendChoice);
  }
}

function updateMonsterChoices(choice, monsterList, isMyChoice, chooser) {
  let uiprompt = document.getElementById("uiprompt");
  let uimonsterchoice = document.getElementById("uimonsterchoice");
  let choicesBox = document.getElementById("monsterchoices");
  for (let monsterCount of document.getElementsByClassName("monstercount")) {
    monsterCount.classList.remove("choosable");
  }
  if (choice == null || choice.to_spawn == null) {
    uimonsterchoice.style.display = "none";
    return;
  }
  let total = 0;
  for (let name of choice.open_gates) {
    let monsterCount = document.getElementById("place" + name).getElementsByClassName("monstercount")[0];
    monsterCount.classList.add("choosable");
    let plus = monsterCount.getElementsByClassName("plus")[0];
    let minus = monsterCount.getElementsByClassName("minus")[0];
    let textBox = monsterCount.getElementsByClassName("monstercounttext")[0];
    let count = choice.pending[name] ?? 0;
    total += count;
    textBox.innerText = count;
    plus.classList.toggle("choosable", isMyChoice && count != choice.max_count);
    minus.classList.toggle("choosable", isMyChoice && count != choice.min_count);
    if (name == choice.location) {
      minus.classList.remove("choosable");
    }
  }
  let text;
  if (isMyChoice) {
    text = "Distribute ";
  } else {
    let chooserName = serverNames[chooser.name] ?? chooser.name;
    text = chooserName + " must distribute ";
  }
  text += (choice.board - total) + " monsters to the board";
  uiprompt.innerText = text;
  uimonsterchoice.style.display = "flex";
  for (let btn of uimonsterchoice.getElementsByTagName("BUTTON")) {
    btn.disabled = !isMyChoice;
  }
}

function addMonsterChoices(uichoice, cardChoice, monsters, invalidChoices, annotations, current, isMyChoice) {
  let otherChoices = [];
  for (let [idx, monster] of monsters.entries()) {
    if (typeof(monster) == "string") {
      otherChoices.push(monster);
      continue;
    }
    let visual = newVisual(monster.handle, "monster");
    visual.choice = isMyChoice ? monster.handle : null;
    visual.monster = monster;
    visual.descText = annotations && annotations[idx];
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      visual.classes.push("unchoosable");
      visual.order = 1;
    } else {
      visual.order = 0;
    }
    newVisuals.push(visual);
  }
  let scrollParent = cardChoice.parentNode;
  if (monsters.length > 4) {
    scrollParent.classList.add("overflowing");
  } else {
    scrollParent.classList.remove("overflowing");
  }
  if (isMyChoice) {
    addChoices(uichoice, otherChoices, [], {}, [], []);
  }
}

function newVisual(handleOrName, type, opts) {
  let [name, backName] = getNameAndBack(handleOrName);
  let result = {
    "handle": handleOrName,
    "name": name,
    "type": type,
    "backName": backName,
    "monster": null,
    "choice": null,
    "defaultSpend": null,
    "doneUse": false,
    "order": null,
    "classes": [],
    "descText": null,
    "backgroundPct": null,
    "callback": function() {},
  };
  if (opts == null) {
    return result;
  }
  return {...result, ...opts};
}

function createVisual(scrollParent, visual, existing) {
  let classNames = {
    "fight": "fightchoice",
    "monster": "monsterchoice",
    "card": "cardchoice",
    "mythos": "bigmythoscard",
  };
  let className = classNames[visual.type];

  let holder, div, cnv, backDiv, backCnv;
  if (existing != null) {
    holder = existing;
    holder.className = "";
    holder.style.removeProperty("order");
    while (holder.getElementsByClassName("visualback").length > 0) {
      holder.removeChild(holder.getElementsByClassName("visualback")[0]);
    }
  } else {
    holder = document.createElement("DIV");
  }
  holder.classList.add("cardholder", ...visual.classes);
  if (existing != null) {
    div = holder.firstChild;
    div.className = "";
    div.onclick = null;
    div.style.removeProperty("cursor");
    delete div.monsterInfo;
    while (div.children.length) {
      div.removeChild(div.firstChild);
    }
  } else {
    div = document.createElement("DIV");
  }
  div.classList.toggle("visualchoice", visual.choice != null || visual.doneUse);
  div.classList.toggle("mustspend", visual.defaultSpend != null);
  div.classList.add(className);
  if (existing == null) {
    holder.appendChild(div);
    scrollParent.appendChild(holder);
  }
  if (className == "monsterchoice") {
    let frontDiv = document.createElement("DIV");
    frontDiv.classList.add("fightchoice", "cnvcontainer");
    let backDiv = document.createElement("DIV");
    backDiv.classList.add("fightchoice", "monsterback");
    backDiv.monsterInfo = visual.monster;
    let frontCnv = document.createElement("CANVAS");
    frontCnv.classList.add("markercnv");  // TODO: use a better class name for this
    frontDiv.appendChild(frontCnv);
    let backCnv = document.createElement("CANVAS");
    backCnv.classList.add("markercnv");  // TODO: use a better class name for this
    backDiv.appendChild(backCnv);
    div.appendChild(frontDiv);
    div.appendChild(backDiv);
    renderAssetToDiv(frontDiv, visual.monster.name);
    renderMonsterBackToDiv(backDiv, visual.monster);
  } else {
    cnv = document.createElement("CANVAS");
    cnv.classList.add("markercnv");  // TODO: use a better class name for this
    div.appendChild(cnv);
    if (visual.monster != null) {
      div.classList.add("monsterback");
      div.monsterInfo = visual.monster;
      renderMonsterBackToDiv(div, visual.monster);
    } else {
      div.classList.add("cnvcontainer");
      renderAssetToDiv(div, visual.name);
    }
  }

  if (visual.backName != null) {
    backDiv = document.createElement("DIV");
    backDiv.classList.add(className, "visualback", "cnvcontainer");
    backCnv = document.createElement("CANVAS");
    backCnv.classList.add("markercnv");
    backDiv.appendChild(backCnv);
    holder.appendChild(backDiv);
    renderAssetToDiv(backDiv, visual.backName);
  }

  let desc = null;
  if (holder.getElementsByClassName("desc").length > 0) {
    desc = holder.getElementsByClassName("desc")[0];
    if (visual.descText == null) {
      holder.removeChild(desc);
    }
  }
  if (visual.descText != null) {
    if (desc == null) {
      desc = document.createElement("DIV");
      desc.classList.add("desc");
      holder.appendChild(desc);
    }
    desc.innerText = formatServerString(visual.descText);
    if (visual.backgroundPct != null) {
      desc.style.backgroundPosition = "left " + visual.backgroundPct + "% top";
    } else {
      desc.style.removeProperty("background-position");
    }
  }

  if (visual.defaultSpend != null) {
    setDefaultSpendCursor(div, visual.defaultSpend);
    div.onclick = function(e) { defaultSpend(visual.defaultSpend, visual.choice); };
  } else if (visual.choice != null) {
    div.onclick = function(e) { clearTimeout(autoClickTimeout); autoClickTimeout = null; makeChoice(visual.choice); };
  } else if (visual.doneUse) {
    div.onclick = doneUse;
  }

  if (visual.order != null) {
    holder.style.order = visual.order;
  }

  holder.handle = visual.handle;
  return holder;
}

function setDefaultSpendCursor(div, defaultSpend) {
  let cursorType = null;
  for (let stat in defaultSpend) {
    if (statNames[stat] != null) {
      cursorType = statNames[stat];
      break;
    }
  }
  if (cursorType != null) {
    div.style.cursor = "url(" + cursorURLs[cursorType] + ") 13 13, grab";
  }
}

function addFightOrEvadeChoices(uichoice, cardChoice, monster, choices, invalidChoices, annotations, current, isMyChoice) {
  for (let [idx, choice] of choices.entries()) {
    let descText = choice;
    if (annotations && annotations[idx] != null) {
      descText += " (" + formatServerString(annotations[idx]) + ")";
    }
    let visual = newVisual(monster.handle, "fight");
    visual.choice = isMyChoice ? choice : null;
    visual.monster = choice == "Fight" ? monster : null;
    visual.descText = descText;
    visual.order = choice == "Fight" ? 1 : 0;
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      visual.classes.push("unchoosable");
    }
    newVisuals.push(visual);
  }
}

function addCardChoices(uichoice, cardChoice, cards, invalidChoices, spent, remainingSpend, remainingMax, annotations, sortUniq, current, isMyChoice, autoChoose, chooser) {
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
  let newMaxSpend = [];
  let autoClick = false;
  if (cards.length == 1 && isMyChoice && autoChoose && assetNames.includes(cards[0])) {
    if (annotations == null || annotations.length == 0) {
      let annotate = "OK";
      if (typeof(autoChoose) == "string") {
        annotate = replacer(autoChoose, autoChoose);
      } else if (!cards[0].startsWith("Mythos")) {
        annotate = replacer(chooser.place ?? "OK", chooser.place ?? "OK");
      }
      annotations = [annotate];
    }
    autoClick = true;
  }
  for (let [idx, card] of cards.entries()) {
    let [assetName, backName] = getNameAndBack(card);
    if (!assetNames.includes(assetName)) {
      if (invalidChoices != null && invalidChoices.includes(idx)) {
        newInvalid.push(notFound.length);
      }
      if (remainingSpend != null && remainingSpend.length > idx) {
        newRemainingSpend.push(remainingSpend[idx]);
      }
      if (remainingMax != null && remainingMax.length > idx) {
        newMaxSpend.push(remainingMax[idx]);
      }
      notFound.push(card);
      continue;
    }
    if (sortUniq && uniqueCards.has(card)) {
      continue;
    }
    uniqueCards.add(card);
    count++;
    let visual = newVisual(card, "card");
    visual.choice = isMyChoice ? card : null;
    visual.backName = backName;
    visual.descText = annotations && annotations[idx];
    if (sortUniq) {
      visual.order = cardToOrder[card];
    } else {
      visual.order = count;
    }
    if (autoClick) {
      visual.classes.push("willchoose");
      visual.callback = function(holder) {
        holder.classList.add("autochoose");
        autoClickTimeout = setTimeout(function() { makeChoice(card); }, 6000);
      }
    }
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      visual.classes.push("unchoosable");
    } else if (remainingMax != null && remainingMax.length > idx && remainingMax[idx]) {
      let rem = remainingMax[idx];
      let spentPct = spentPercent(spent, rem);
      visual.backgroundPct = 100-spentPct;
      if (remainingSpend[idx] && isMyChoice) {
        visual.defaultSpend = rem;
      }
    }
    newVisuals.push(visual);
  }
  let scrollParent = cardChoice.parentNode;
  if (count > 4) {
    scrollParent.classList.add("overflowing");
  } else {
    scrollParent.classList.remove("overflowing");
  }
  if (isMyChoice) {
    addChoices(uichoice, notFound, newInvalid, spent, newRemainingSpend, newMaxSpend);
  }
}

function addChoices(uichoice, choices, invalidChoices, spent, remainingSpend, remainingMax) {
  let nameToDiv = {};
  for (let child of uichoice.getElementsByClassName("choice")) {
    nameToDiv[child.innerText] = child;
  }
  let resultChoice = document.getElementById("resultchoice");
  if (resultChoice != null) {
    nameToDiv[resultChoice.innerText] = resultChoice;
  }
  let spendChoice = document.getElementById("spendchoice");
  if (spendChoice != null) {
    nameToDiv[spendChoice.innerText] = spendChoice;
  }
  let isResultChoice = (choices.length == 2);
  for (let c of choices) {
    if (!["Pass", "Fail", "Spend"].includes(c)) {
      isResultChoice = false;
      break;
    }
  }

  for (let [idx, c] of choices.entries()) {
    choiceText = serverNames[c] ?? c;
    let div = nameToDiv[choiceText];
    if (div == null) {
      div = document.createElement("DIV");
      if (isResultChoice && ["Pass", "Fail"].includes(c)) {
        div.id = "resultchoice";
        document.getElementById("promptline").appendChild(div);
      } else if (isResultChoice && c == "Spend") {
        div.id = "spendchoice";
        document.getElementById("uidice").appendChild(div);
      } else {
        uichoice.appendChild(div);
      }
    }
    div.innerText = choiceText;
    // Start with a clean slate and redo all class list calculations.
    div.className = "";
    div.style.removeProperty("background-position");
    div.style.removeProperty("cursor");
    div.classList.add("choice");
    if (c == "Pass") {
      div.classList.add("success");
    }
    if (c == "Fail") {
      div.classList.add("fail");
    }
    div.onclick = function(e) { makeChoice(c); };
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      div.classList.add("unchoosable");
    } else if (remainingMax != null && remainingMax.length > idx && remainingMax[idx]) {
      let rem = remainingMax[idx];
      let spentPct = spentPercent(spent, rem);
      div.style.backgroundPosition = "left " + (100-spentPct) + "% top";
      if (remainingSpend[idx]) {
        setDefaultSpendCursor(div, rem);
        div.classList.add("mustspend");
        div.onclick = function(e) { defaultSpend(rem, c); };
      } else {
        div.classList.add("choosable");
      }
    } else {
      div.classList.add("choosable");
    }
  }
}

function spentPercent(spent, remaining) {
  if (spent == null) {
    return 0;
  }
  let totalSpent = 0;
  for (let spendType in spent) {
    for (let handle in spent[spendType]) {
      totalSpent += spent[spendType][handle];
    }
  }
  let totalRem = 0;
  let overSpent = 0;
  for (let spendType in remaining) {
    if (remaining[spendType]) {
      totalRem += Math.abs(remaining[spendType]);
    }
    if (remaining[spendType] < 0) {
      overSpent -= remaining[spendType];
    }
  }
  if (overSpent > 0) {
    return 0; // TODO: decide what to do with this later
  }
  let totalSpendable = totalSpent + totalRem;
  if (totalSpendable == 0) {
    return 0;
  }
  return 100 * totalSpent / totalSpendable;
}

function updateUsables(usables, log, spendables, choice, sliders, dice) {
  let doneUsing = document.getElementById("doneusing");
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
  usableList = usableList.concat(spendables || []);
  let anyPosUsable = false;
  let anyTrophyUsable = false;
  for (let pos of posList) {
    let isUsable = usableList.includes(pos.handle);
    pos.classList.toggle("usable", isUsable);
    anyPosUsable = anyPosUsable || isUsable || pos.classList.contains("choosable");
  }
  for (let pos of trophyList) {
    let isUsable = usableList.includes(pos.handle);
    pos.classList.toggle("usable", isUsable);
    anyTrophyUsable = anyTrophyUsable || isUsable;
  }
  pTab.classList.toggle("usable", anyPosUsable);
  tTab.classList.toggle("usable", anyTrophyUsable);
  if (doneUsing != null) {
    doneUsing.style.display = "none";
  }
  if (usables == null && spendables == null) {
    if (choice == null) {
      document.getElementById("charoverlay").classList.remove("shown");
    }
    return;
  }

  let tradeOnly = true;
  for (let val of usableList) {
    if (val != "trade") {
      tradeOnly = false;
      break;
    }
  }
  if (!tradeOnly) {
    document.getElementById("charoverlay").classList.add("shown");
  }
  if (choice == null && sliders == null && (dice == null || !dice.prompt)) {
    if (log != null && log != "") {
      document.getElementById("uiprompt").innerText = formatServerString(log);
    }
    if (doneUsing != null) {
      doneUsing.style.display = "inline-block";
    }
  }
  if (doneUsing != null) {
    doneUsing.innerText = "Done Using";
    if (choice == null && tradeOnly) {
      document.getElementById("uiprompt").innerText = "Trade?";
      doneUsing.innerText = "Done Trading";
    }
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
    setTimeout(function() { div.classList.add("moving"); div.style.removeProperty("transform"); }, 10);
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
    setTimeout(function() { div.classList.add("moving"); div.style.removeProperty("transform"); }, 10);
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

function translateNodeThenRemove(div, dest, callback, trueDest) {
  let lastAnim = function() {
    doneAnimating(div);
    div.parentNode.removeChild(div);
    if (callback != null) {
      callback();
    }
    finishAnim();
  };
  div.ontransitionend = lastAnim;
  div.ontransitioncancel = lastAnim;
  translateNode(div, dest, trueDest);
}

function translateNode(div, dest, trueDest) {
  let oldRect = div.getBoundingClientRect();
  let newRect = dest.getBoundingClientRect();
  let oldTransform = null;
  if (trueDest) {
    if (dest.parentNode.style.transform != null) {
      oldTransform = dest.parentNode.style.transform;
      dest.parentNode.style.transform = "none";
      newRect = dest.getBoundingClientRect();
    }
  }
  let diffX = Math.floor((newRect.left + newRect.right - oldRect.left - oldRect.right) / 2);
  let diffY = Math.floor((newRect.top + newRect.bottom - oldRect.top - oldRect.bottom) / 2);
  let scaleFactor = (newRect.right - newRect.left) / (oldRect.right - oldRect.left);
  div.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px) scale(" + scaleFactor+ ")";
  if (oldTransform != null) {
    dest.parentNode.style.transform = oldTransform;
  }
}

// TODO: deduplicate many translateNode functions
function translateNodeOrFalse(div, newRect) {
  let oldRect = div.getBoundingClientRect();
  let diffX = Math.floor((newRect.left + newRect.right - oldRect.left - oldRect.right) / 2);
  let diffY = Math.floor((newRect.top + newRect.bottom - oldRect.top - oldRect.bottom) / 2);
  let scaleFactor = (newRect.right - newRect.left) / (oldRect.right - oldRect.left);
  if (diffX > 1 || diffX < -1 || scaleFactor > 1.05 || scaleFactor < 0.95) {
    div.style.transform = "translateX(" + diffX + "px) translateY(" + diffY + "px) scale(" + scaleFactor+ ")";
    return true;
  }
  return false;
}

function updatePlaces(places, activity, current) {
  let oldGates = [];
  let gateCount = 0;
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
      let shouldAnimate = document.getElementById("eventlog").children.length && !oldGates.includes(handle);
      updateGate(place, gateDiv, shouldAnimate);
    }
    if (place.sealed != null) {
      updateSeal(place);
    }
    if (place.clues != null) {
      updateClues(place, current);
    }
    if (place.closed != null) {
      updateClosed(place);
    }
    updateActivity(placeName, activity[placeName]);
    gateCount += place.gate == null ? 0 : 1;
  }
  return gateCount;
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
    placeBox.classList.toggle("withmonsters", (placeMonsters && placeMonsters.getElementsByClassName("monster").length >= 1) || place.gate != null);
    placeBox.classList.toggle("withdetails", placeChars && placeChars.children.length > 0);
    placeBox.classList.toggle("withgate", place.gate != null);
    if (placeChars != null) {
      for (let child of placeChars.children) {
        child.classList.remove("lastchild");
      }
      for (let className of ["marker", "closed", "activity", "seal", "clue"]) {
        let children = placeChars.getElementsByClassName(className);
        if (children.length) {
          children[children.length-1].classList.add("lastchild");
          break;
        }
      }
    }
  }
}

function updateClues(place, current) {
  let charsDiv = document.getElementById("place" + place.name + "chars");
  let numClues = charsDiv.getElementsByClassName("clue").length;
  for (let i = 0; i < numClues - place.clues; i++) {
    let dest = gainedClues.length > 0 ? gainedClues.pop() : null;
    let clueDiv = charsDiv.getElementsByClassName("clue")[0];
    if (dest != null) {
      runningAnim.push(true);
      moveAndTranslateNode(clueDiv, dest, "abs");
      clueDiv.ontransitionend = function() { clueDiv.parentNode.removeChild(clueDiv); finishAnim(); };
      clueDiv.ontransitioncancel = function() { clueDiv.parentNode.removeChild(clueDiv); finishAnim(); };
      setTimeout(function() { clueDiv.classList.add("moving"); clueDiv.style.removeProperty("transform"); }, 10);
    } else {
      charsDiv.removeChild(clueDiv);
    }
  }
  let shouldAnimate = current != null && current.startsWith("Mythos");
  let enterDiv = document.getElementById("enteringscroll");
  let addedClues = [];
  for (let i = 0; i < place.clues - numClues; i++) {
    let clueDiv = document.createElement("DIV");
    clueDiv.classList.add("clue");
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("cluecontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnvContainer.appendChild(cnv);
    clueDiv.appendChild(cnvContainer);
    if (shouldAnimate) {
      clueDiv.classList.add("entering");
      enterDiv.appendChild(clueDiv);
      addedClues.push(clueDiv);
    } else {
      charsDiv.appendChild(clueDiv);
    }
    renderAssetToDiv(cnvContainer, "Clue");
  }
  for (let i = addedClues.length-1; i >=0; i--) {
    let c = addedClues[i];
    runningAnim.push(true);  // One animation per clue.
    let lastAnim = function() {
      doneAnimating(c);
      finishAnim();
    };
    let moveToBoard = function() {
      doneAnimating(c);
      let sibling = c.nextSibling;
      moveAndTranslateNode(c, charsDiv, "moving");
      c.ontransitionend = lastAnim;
      c.ontransitioncancel = lastAnim;
      setTimeout(function() { c.classList.add("moving"); c.style.removeProperty("transform"); }, 10);
      // In order for this animation to work, you must keep the number of clues in this div
      // constant so that future clues you animate don't shift when this clue is removed.
      let dummyClue = document.createElement("DIV");
      dummyClue.classList.add("clue", "dummy");
      enterDiv.insertBefore(dummyClue, sibling);
    };
    setTimeout(function() {
      c.ontransitionend = moveToBoard;
      c.ontransitioncancel = moveToBoard;
      c.classList.add("moving");
      c.classList.remove("entering");
    }, 10);
  }
}

function animateClues(current) {
  if (current == null || !current.startsWith("Mythos")) {
    return;
  }
  let enterDiv = document.getElementById("enteringscroll");
  while (gainedClues.length > 0) {
    runningAnim.push(true);  // One animation per clue.
    let dest = gainedClues.pop();
    let clueDiv = document.createElement("DIV");
    clueDiv.classList.add("clue");
    let cnvContainer = document.createElement("DIV");
    cnvContainer.classList.add("cluecontainer", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("cluecnv");
    cnvContainer.appendChild(cnv);
    clueDiv.appendChild(cnvContainer);
    clueDiv.classList.add("entering");
    enterDiv.appendChild(clueDiv);
    renderAssetToDiv(cnvContainer, "Clue");
    let lastAnim = function() {
      doneAnimating(clueDiv);
      clueDiv.parentNode.removeChild(clueDiv);
      finishAnim();
    };
    let moveToSheet = function() {
      doneAnimating(clueDiv);
      let sibling = clueDiv.nextSibling;
      moveAndTranslateNode(clueDiv, dest, "moving");
      clueDiv.ontransitionend = lastAnim;
      clueDiv.ontransitioncancel = lastAnim;
      setTimeout(function() { clueDiv.classList.add("abs", "moving"); clueDiv.style.removeProperty("transform"); }, 10);
      // In order for this animation to work, you must keep the number of clues in this div
      // constant so that future clues you animate don't shift when this clue is removed.
      let dummyClue = document.createElement("DIV");
      dummyClue.classList.add("clue", "dummy");
      enterDiv.insertBefore(dummyClue, sibling);
    };
    setTimeout(function() {
      clueDiv.ontransitionend = moveToSheet;
      clueDiv.ontransitioncancel = moveToSheet;
      clueDiv.classList.add("moving");
      clueDiv.classList.remove("entering");
    }, 10);
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
  let moveFromBoard = [];
  if (place.gate) {
    let gateName = place.gate.name;
    gateDiv.classList.add("placegatepresent");
    gateCont.handle = place.gate.handle;
    if (shouldAnimate) {
      // TODO: figure out back name automatically?
      let visual = newVisual(place.gate.handle, "fight", {"backName": "Gate Back"});
      let holder = createVisual(document.getElementById("enteringscroll"), visual);
      holder.classList.add("entering");
      runningAnim.push(true);
      let callback = function() { renderAssetToDiv(gateCont, gateName); };
      let moveToBoard = function() {
        doneAnimating(holder);
        setTimeout(function() { translateNodeThenRemove(holder, gateCont, callback); }, 10);
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
    // Don't animate if the gate in card choice is going to be animated.
    for (let src of document.getElementsByClassName("cardholder")) {
      if (src.handle == gateCont.handle) {
        clearAssetFromDiv(gateCont);
        gateDiv.classList.remove("placegatepresent");
        gateCont.handle = null;
        return;
      }
    }
    if (dest != null) {
      runningAnim.push(true);
      let lastAnim = function() {
        doneAnimating(gateCont);
        gateCont.style.removeProperty("transform");
        clearAssetFromDiv(gateCont);
        gateDiv.classList.remove("placegatepresent");
        finishAnim();
      };
      gateCont.ontransitionend = lastAnim;
      gateCont.ontransitioncancel = lastAnim;
      translateNode(gateCont, dest);
    } else if (gateCont.handle != null) {
      let holder = createVisual(document.getElementById("enteringscroll"), newVisual(gateCont.handle, "fight"));
      runningAnim.push(true);
      let lastAnim = function() {
        doneAnimating(holder);
        holder.parentNode.removeChild(holder);
        finishAnim();
      };
      let startLeaving = function() {
        doneAnimating(holder);
        setTimeout(function() {
          holder.ontransitionend = lastAnim;
          holder.ontransitioncancel = lastAnim;
          holder.classList.add("leaving");
        }, 10);
      };
      holder.ontransitionend = startLeaving;
      holder.ontransitioncancel = startLeaving;
      holder.classList.add("noanimate");
      translateNode(holder, gateCont);

      setTimeout(function() {
        clearAssetFromDiv(gateCont);
        gateDiv.classList.remove("placegatepresent");
        holder.classList.remove("noanimate");
        holder.style.removeProperty("transform");
      }, 10);

    }
    gateCont.handle = null;
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
  for (let highlight of document.getElementsByClassName("placehighlight")) {
    highlight.classList.remove("shown");
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
    // Mild hack: don't highlight locations for movement choice.
    if (!place.innerText.startsWith("Move ") && (places.length < 15)) {
      document.getElementById("place" + placeName + "highlight").classList.add("shown");
    }
  }
  if (isMyChoice && notFound.length) {
    addChoices(uichoice, notFound, [], {}, [], []);
  }
}

function updateBottomText(gameStage, turnPhase, characters, turnIdx, playerIdx, host) {
  let uiprompt = document.getElementById("uiprompt");
  let btn = document.getElementById("start");
  uiprompt.innerText = "";
  btn.style.display = "none";
  if (gameStage == "setup") {
    if (host) {
      btn.style.display = "flex";
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
    if (rumorDiv.name != null) {  // Animate the rumor leaving.
      lostCards[rumorDiv.name] = rumorDiv;
      rumorDiv.failed = (rumorDiv.percent == 0);
    } else {
      rumorDiv.failed = null;
    }
    clearAssetFromDiv(rumorCnt);
    rumorDiv.classList.add("missing");
    rumorDiv.name = null;
    rumorDiv.annotation = null;
    rumorDiv.percent = null;
  } else {
    let oldPercent = rumorDiv.percent;
    rumorDiv.classList.remove("missing");
    rumorDiv.name = rumor.name;
    rumorDiv.annotation = "Rumor: " + rumor.progress + "/" + rumor.max_progress;
    rumorDiv.percent = 100 - (100 * rumor.progress / rumor.max_progress);
    rumorDiv.failed = null;
    if (rumorDiv.percent != oldPercent) {
      if (document.getElementById("eventlog").children.length) {  // Hack to not do this on the first message.
        newVisuals.push(newVisual(rumorDiv.name, "card", {"descText": rumorDiv.annotation, "backgroundPct": rumorDiv.percent}));
        runningAnim.push(true);  // let the user see the progress change
        setTimeout(finishAnim, (oldVisuals[rumorDiv.name] != null) ? 1200 : 2100);
      }
    }
    renderAssetToDiv(rumorCnt, rumorDiv.name);
  }
  let toRemove = {};
  for (let node of document.getElementById("globals").getElementsByClassName("mythoscontainer")) {
    if (node.id == "environment" || node.id == "rumor" || node.id == "currentcard") {
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

function updateBottomCards(bottom) {
  if (bottom == null) {
    return;
  }
  let scrounge = null;
  for (let pos of document.getElementsByClassName("possession")) {
    if (pos.handle == "Scrounge") {
      scrounge = pos;
      break;
    }
  }
  if (scrounge == null) {
    return;
  }
  scrounge.onmouseenter = function(e) {
    bringTop(e);
    let enteringScroll = document.getElementById("enteringscroll");
    for (let card of ["common", "unique", "spells"]) {
      if (bottom[card] == null) {
        continue;
      }
      let visual = newVisual(bottom[card], "card", {"classes": ["bottomcard"]});
      let holder = createVisual(enteringScroll, visual);
    }
  };
  scrounge.onmouseleave = function(e) {
    returnBottom(e);
    let enteringScroll = document.getElementById("enteringscroll");
    while (enteringScroll.getElementsByClassName("bottomcard").length) {
      enteringScroll.removeChild(enteringScroll.getElementsByClassName("bottomcard")[0]);
    }
  };
}

function updateCurrentCard(current, visual, monster, choice) {
  let currDiv = document.getElementById("currentcard");
  let currCnt = currDiv.firstChild;
  if (current == null) {
    // TODO: because rendering happens in a promise, clearing the asset from the div can
    // actually happen before the promise is fulfilled. ugh.
    clearAssetFromDiv(currCnt);
    currDiv.classList.add("missing");
    currDiv.name = null;
    currDiv.annotation = null;
  } else {
    currDiv.classList.remove("missing");
    currDiv.name = current;
    currDiv.annotation = current.startsWith("Mythos") ? "Mythos" : "Encounter";
    renderAssetToDiv(currCnt, current);
  }
  // If we're not showing anything, prioritize showing the monster the player is fighting.
  if (newVisuals.length == 0 && monster != null) {
    newVisuals.push(newVisual(monster.handle, "fight", {"monster": monster}));
  }
  // If we're still not showing anything, show the current card (unless we need to see the board for our choice).
  // TODO: how do we make this work for things like gaining money?
  let bareChoice = choice != null && choice.to_spawn == null && choice.board_monster == null && choice.places == null;
  if (newVisuals.length == 0 && current != null && bareChoice) {
    newVisuals.push(newVisual(current, "card"));
  }
  if (visual != null) {
    let visualCard = newVisual(visual, "card");
    let doneUsing = document.getElementById("doneusing");
    if (choice == null && doneUsing.style.display != "none" && doneUsing.innerText == "Done Using") {
      // For cases where the visual is shown because a player may need to decide to use something,
      // clicking the visual should be the equivalent of clicking "done using".
      visualCard.doneUse = true;
    }
    newVisuals.push(visualCard);
    // This is the case when we show the mythos card for the second time. Give the players some
    // time to read it. TODO: other times we draw cards.
    if (visual == oldCurrent) {
      runningAnim.push(true);
      setTimeout(finishAnim, 6000);
    }
  }
}

function toggleGlobals(e, frontCard) {
  let globalBox = document.getElementById("globals");
  let globalScroll = document.getElementById("globalscroll");
  let globalCards = document.getElementById("globalcards");
  let toAnimate = [];
  if (globalBox.classList.contains("zoomed")) {
    for (let holder of globalCards.getElementsByClassName("cardholder")) {
      let found = false;
      for (let cont of document.getElementById("globals").getElementsByClassName("mythoscontainer")) {
        if (holder.handle == cont.name) {
          // Use the mythoscard container, as the mythoscontainer can be compressed/stretched.
          toAnimate.push([cont.getElementsByClassName("mythoscard")[0], holder]);
          found = true;
          break;
        }
      }
      if (!found) {
        toAnimate.push([null, holder]);
      }
    }
    // Animate
    for (let [dest, source] of toAnimate) {
      if (dest == null) {
        setTimeout(function() { source.parentNode.removeChild(source); }, 1);
        continue;
      }
      setTimeout(function() { translateNode(source, dest); }, 1);
    }
    globalBox.classList.remove("zoomed");
    setTimeout(function() { globalScroll.style.display = "none"; }, 820);
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
    let visual = newVisual(cont.name, "mythos", {"descText": cont.annotation, "backgroundPct": cont.percent});
    if (frontCard != null && cont.name != frontCard) {
      visual.classes.push("unchoosable");
    }
    let holder = createVisual(globalCards, visual);
    if (frontCard != null && cont.name == frontCard) {
      toDisplay = holder;
    }
    toAnimate.push([cont.getElementsByClassName("mythoscard")[0], holder]);
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

  // Animate
  for (let [source, dest] of toAnimate) {
    dest.classList.add("noanimate");
    translateNode(dest, source);
    setTimeout(function() { dest.classList.remove("noanimate"); dest.style.removeProperty("transform"); }, 1);
  }
}

function toggleAncient(e) {
  let bigAncient = document.getElementById("ancientdetails");
  let ancientOne = document.getElementById("ancientone");
  if (ancientOne.classList.contains("zoomed")) {
    ancientOne.classList.remove("zoomed");
    bigAncient.style.display = "none";
  } else {
    ancientOne.classList.add("zoomed");
    bigAncient.style.display = "flex";
    renderAssetToDiv(document.getElementById("bigancient"), chosenAncient);
  }
}

function updateDice(dice, playerIdx, monsterList) {
  let uidice = document.getElementById("uidice");
  if (dice == null) {
    uidice.style.display = "none";
    return;
  }
  // Unconditionally show the spend bar when rolling dice to avoid the dice moving around.
  let spendDiv = document.getElementById("uispend");
  spendDiv.classList.add("spendable");

  if (dice.name != null && dice.name != chosenAncient) {  // Show the monster/card that is causing this dice roll.
    let found = false;
    if (dice.check_type != "evade") {
      // If the dice refers to a monster, find the monster by handle. Exception: if it's an evade check, we
      // want to show the front of the monster instead of the back of the monster.
      for (let m of monsterList) {
        if (m.handle == dice.name) {
          newVisuals.push(newVisual(m.handle, "fight", {"monster": m}));
          found = true;
          break;
        }
      }
    }
    if (!found) {
      let rumorDiv = document.getElementById("rumor");
      let desc = (dice.name == rumorDiv.name) ? rumorDiv.annotation : null;
      let pct = (dice.name == rumorDiv.name) ? rumorDiv.percent : null;
      newVisuals.push(newVisual(dice.name, "card", {"descText": desc, "backgroundPct": pct}));
    }
  }
  if (dice.prompt) {
    document.getElementById("uiprompt").innerText = formatServerString(dice.prompt);
  }

  let roll = dice.roll || [];
  let diceDiv = document.getElementById("dice");
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
  diceDiv.classList.toggle("rollable", dice.roller == playerIdx && remaining);
  if (dice.check_type == null) {
    runningAnim.push(true);  // let the user see the dice for a moment
    setTimeout(finishAnim, 1500);
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

function updateOptions(options) {
  let expansionList = ["hilltown", "clifftown", "seaside", "pharaoh", "king", "goat", "lurker"];
  for (let expansion of expansionList) {
    let expCheck = document.getElementById("expansion"+expansion);
    let tableRow = expCheck.parentNode.parentNode;
    let count = -1;
    for (let checkBox of tableRow.getElementsByTagName("INPUT")) {
      checkBox.checked = false;
      count++;
    }
    for (let option of options[expansion]) {
      let checkBox = document.getElementById(expansion + option);
      checkBox.checked = true;
    }
    expCheck.indeterminate = (options[expansion].length != 0 && options[expansion].length != count);
    expCheck.checked = (options[expansion].length == count);
  }
}

function updateAncientOne(gameStage, ancientOne, terror, gateCount, gateLimit, numCharacters) {
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
  let ancientOneDiv = document.getElementById("ancientone");
  let doomTrack = document.getElementById("doomtrack");
  let gateTrack = document.getElementById("gatetrack");
  doomTrack.innerText = "Doom " + ancientOne.doom + "/" + doom.maxValue;
  doomTrack.style.backgroundPosition = "left " + 100*(1-ancientOne.doom/doom.maxValue) + "% top";
  gateTrack.innerText = "Gates " + gateCount + "/" + gateLimit;
  gateTrack.style.backgroundPosition = "left " + 100*(1-gateCount/gateLimit) + "% top";
  // TODO: too many monsters
  if (gameStage == "slumber") {
    ancientOneDiv.onclick = toggleAncient;
    ancientOneDiv.classList.remove("setup");
  } else {
    ancientOneDiv.onclick = null;
    ancientOneDiv.classList.add("setup");
  }
  if (["awakened", "defeat", "victory"].includes(gameStage)) {
    document.getElementById("ancientdetails").style.display = "flex";
    renderAssetToDiv(document.getElementById("bigancient"), chosenAncient);
    if (ancientOne.health != null) {
      doomTrack.innerText = "Doom " + ancientOne.health + "/" + numCharacters*doom.maxValue;
      let ratio = Math.min(ancientOne.health / (numCharacters*doom.maxValue), 1);
      doomTrack.style.backgroundPosition = "left " + 100*(1-ratio) + "% top";
    }
    gateTrack.style.display = "none";
    if (gameStage != "victory") {
      document.getElementById("uicont").style.display = "none";
    }
    if (gameStage == "victory" && oldStage == null) {
      document.getElementById("ancientdetails").classList.add("fade");
      ancientOneDiv.classList.add("fade");
    }
  }
}

function updateCharacterSelect(gameStage, characters, playerIdx) {
  let selectors = document.getElementById("selectors");
  if (playerIdx != null && !characters[playerIdx].gone) {
    selectors.style.display = "none";
    return;
  }
  if (!["slumber", "setup"].includes(gameStage)) {
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
    sheet = createCharacterSheet(null, character, charChoiceDiv, false);
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

function updateCharacterSheets(characters, pendingCharacters, playerIdx, firstPlayer, choice, sliders) {
  gainedClues = [];  // Reset this before updating all characters.
  gainedCards = {};  // Also reset this.
  lostCards = {};
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
  spendDiv.classList.toggle("spendable", spendable != null);

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
      updateSliders(sheet, allCharacters[charName], false, null);
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
    updateCharacterSheet(sheet, character, order, playerIdx == idx, choice, spent, (playerIdx == idx) ? sliders : null);
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
  if (isPlayer) {
    let sliderButtons = document.createElement("DIV");
    sliderButtons.id = "sliderbuttons";
    let doneBtn = document.createElement("BUTTON");
    doneBtn.innerText = "Set Sliders";
    doneBtn.onclick = doneSliders;
    let resetBtn = document.createElement("BUTTON");
    resetBtn.innerText = "Reset";
    resetBtn.onclick = resetSliders;
    sliderButtons.appendChild(doneBtn);
    sliderButtons.appendChild(resetBtn);
    sliderCont.appendChild(sliderButtons);
  }
  div.appendChild(sliderCont);
  let slidersCnv = document.createElement("CANVAS");
  slidersCnv.classList.add("worldcnv");  // TODO
  sliders.appendChild(slidersCnv);

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
  if (isPlayer) {
    let useButtons = document.createElement("DIV");
    useButtons.id = "usebuttons";
    let doneItems = document.createElement("BUTTON");
    doneItems.id = "doneitems";
    doneItems.onclick = chooseItems;
    doneItems.innerText = "Done Choosing";
    let doneUsing = document.createElement("BUTTON");
    doneUsing.id = "doneusing";
    doneUsing.onclick = doneUse;
    doneUsing.innerText = "Done Using";
    useButtons.appendChild(doneItems);
    useButtons.appendChild(doneUsing);
    bag.appendChild(useButtons);
  }
  div.appendChild(bag);

  rightUI.appendChild(div);
  renderAssetToDiv(charPic, character.name + " picture");
  renderAssetToDiv(charName, character.name + " title");
  renderAssetToDiv(statsBg, "statsbg");
  renderAssetToDiv(sliders, character.name + " sliders");

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
      if (!setDivXYPercent(sliderDiv, slidersCnv, "Nun sliders", "Slider " + i + " " + j, true)) {
        let xoff = (i % 2 == 0) ? 1 : 2;
        let xpct = (2 * (j+1) + xoff) * 9.09 + "%";
        sliderDiv.style.left = xpct;
        sliderDiv.style.bottom = (3 + 5 * (2-i)) * 100 / 16 + "%";
      }
    }
  }

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

function updateCharacterSheet(sheet, character, order, isPlayer, choice, spent, sliders) {
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
  updateSliders(sheet, character, isPlayer, sliders);
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
        movingStat.ontransitionend = function() { movingStat.classList.remove("moving"); doneAnimating(movingStat); };
        movingStat.ontransitioncancel = function() { movingStat.classList.remove("moving"); doneAnimating(movingStat); };
        setTimeout(function() { movingStat.classList.add("moving"); movingStat.style.removeProperty("transform"); }, 10);
        setTimeout(finishAnim, 300);  // We are okay starting on the next update before this is done animating.
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
        toRemove.ontransitionend = function() { toRemove.parentNode.removeChild(toRemove); };
        toRemove.ontransitioncancel = function() { toRemove.parentNode.removeChild(toRemove); };
        setTimeout(function() { toRemove.classList.add("moving"); toRemove.style.removeProperty("transform"); }, 10);
        setTimeout(finishAnim, 300);
      }
    } else {
      for (let i = 0; i < newValue - oldValue; i++) {
        gainedClues.push(statDiv);
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

function updateSliders(sheet, character, isPlayer, pendingSliders) {
  let sliders = sheet.getElementsByClassName("sliders")[0];
  renderAssetToDiv(sliders, character.name + " sliders");
  for (let slider of sliders.getElementsByClassName("slider")) {
    slider.classList.remove("chosen", "orig", "pending");
  }
  if (pendingSliders == null) {
    sliders.classList.remove("usable");
    for (let [idx, [sliderName, sliderInfo]] of Object.entries(character.sliders).entries()) {
      let chosen = sheet.getElementsByClassName("slider" + idx + "" + sliderInfo.selection)[0];
      chosen.classList.add("chosen");
    }
  } else {
    sliders.classList.add("usable");
    for (let [idx, [sliderName, sliderInfo]] of Object.entries(character.sliders).entries()) {
      let pendingValue = pendingSliders[sliderName].selection;
      let oldValue = sliderInfo.selection;
      if (pendingValue == oldValue) {
        let chosen = sheet.getElementsByClassName("slider" + idx + "" + oldValue)[0];
        chosen.classList.add("chosen");
      } else {
        let pending = sheet.getElementsByClassName("slider" + idx + "" + pendingValue)[0];
        pending.classList.add("pending");
        let orig = sheet.getElementsByClassName("slider" + idx + "" + oldValue)[0];
        orig.classList.add("orig");
      }
    }
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
      if (sheet.getElementsByClassName("playertop")[0].idx != null && !div.classList.contains("big")) {
        lostCards[div.handle] = div;
      }
      toRemove.push(div);
      continue;
    }
    updatePossession(div, handleToInfo[div.handle], spent, chosen, selectType);
    delete handleToInfo[div.handle];
  }
  for (let div of toRemove) {
    // Keep for a little bit so that we can animate them.
    setTimeout(function() { pDiv.removeChild(div); }, 10);
  }
  for (let handle in handleToInfo) {
    if (handle.startsWith("Bad Credit") || handle.startsWith("Voice Bonus") || handle.startsWith("Stamina Decrease") || handle.startsWith("Sanity Decrease") || ["Streetwise", "Blessed is the Child"].includes(handle)) {
      continue;
    }
    let div = createPossession(handleToInfo[handle], isPlayer, pDiv);
    updatePossession(div, handleToInfo[div.handle], spent, chosen, selectType);
    if (sheet.getElementsByClassName("playertop")[0].idx != null) {
      if (!div.classList.contains("big")) {
        gainedCards[handle] = div;
      }
    }
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
  let tokensDiv = document.createElement("DIV");
  tokensDiv.classList.add("tokens");
  div.appendChild(tokensDiv);
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
  if (info.hands) {
    handsText = "✋".repeat(info.hands);
  } else if (info.hands != null) {
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
  div.classList.toggle("check", showText == "✔️");
  if (selectType == "hands" || selectType == null) {
    div.classList.toggle("active", Boolean(info.active));
  } else {
    div.classList.remove("active");
  }
  div.classList.toggle("spent", spent[info.handle] != null);
  div.classList.toggle("exhausted", Boolean(info.exhausted));

  // Update tokens.
  let tokensDiv = div.getElementsByClassName("tokens")[0];
  let tokenInfo = info.tokens || {};
  for (let tokenType in statNames) {
    let numTokens = tokensDiv.getElementsByClassName(tokenType).length;
    let expectedNum = tokenInfo[tokenType] || 0;
    while (numTokens > expectedNum) {
      tokensDiv.removeChild(tokensDiv.getElementsByClassName(tokenType)[0]);
      numTokens--;
    }
    while (numTokens < expectedNum) {
      let tokenDiv = document.createElement("DIV");
      tokenDiv.classList.add("token", "cnvcontainer", tokenType);
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("markercnv");
      tokenDiv.appendChild(cnv);
      tokensDiv.appendChild(tokenDiv);
      renderAssetToDiv(tokenDiv, statNames[tokenType]);
      numTokens++;
    }
  }
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
    if (div.monsterInfo != null) {
      div.monsterInfo = handleToInfo[div.handle];
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
