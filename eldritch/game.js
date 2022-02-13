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
scale = 1;
monsterChoice = {};
charChoice = null;
ancientChoice = null;
runningAnim = [];
messageQueue = [];
statTimeout = null;
cardsStyle = "flex";
statNames = {"stamina": "Stamina", "sanity": "Sanity", "clues": "Clue", "dollars": "Dollar"};

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
  allAncients = data.all_ancients;
  pendingName = data.pending_name;
  chosenAncient = (data.ancient_one == null) ? null : data.ancient_one.name;
  updateAvailableCharacters(data.characters, data.pending_chars);
  updateCharacterSelect(data.characters, data.player_idx);
  updateAncientSelect(data.game_stage, data.host);
  updateAncientOne(data.ancient_one, data.terror);
  updateCharacterSheets(data.characters, data.pending_chars, data.player_idx, data.first_player, data.choice);
  updateBottomText(data.game_stage, data.turn_phase, data.characters, data.turn_idx, data.player_idx, data.host);
  updateGlobals(data.environment, data.rumor);
  updatePlaces(data.places);
  updateCharacters(data.characters);
  updateSliderButton(data.sliders);
  updateChoices(data.choice);
  updateMonsters(data.monsters);
  updateMonsterChoices(data.choice, data.monsters);
  updateUsables(data.usables, data.choice);
  updateSpending(data.choice);
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
  for (let monsterDiv of document.getElementsByClassName("monster")) {
    if (monsterDiv.monsterIdx != null && monsterDiv.draggable) {
      document.getElementById("monsterchoices").appendChild(monsterDiv);
    }
  }
  monsterChoice = {};
}

function defaultSpend(spendDict) {
  for (let spendType of ["sanity", "stamina", "clues", "dollars"]) {
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
    let handle = monsterDiv.monsterName + monsterDiv.monsterIdx;
    container.onclick = function(e) { makeChoice(handle) };
    let frontDiv = createMonsterDiv(monsterDiv.monsterName, "big");
    container.appendChild(frontDiv);
    let backDiv = createMonsterDiv(monsterDiv.monsterName, "big");
    container.appendChild(backDiv);
    box.appendChild(container);
    renderAssetToDiv(frontDiv.getElementsByClassName("cnvcontainer")[0], monsterDiv.monsterName);
    renderAssetToDiv(backDiv.getElementsByClassName("cnvcontainer")[0], monsterDiv.monsterName + " back");
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
  document.getElementById("cardchoicescroll").style.display = cardsStyle;
  setCardButtonText();
}

function setCardButtonText() {
  if (cardsStyle == "flex") {
    document.getElementById("togglecards").innerText = "Hide Cards";
  } else {
    document.getElementById("togglecards").innerText = "Show Cards";
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

function updateChoices(choice) {
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
  for (let place of document.getElementsByClassName("placeselect")) {
    place.classList.remove("selectable");
    place.classList.remove("unselectable");
    place.innerText = "";
  }
  uichoice.style.display = "none";
  document.getElementById("cardchoicescroll").style.display = "none";
  btn.style.display = "none";
  cardtoggle.style.display = "none";
  if (choice != null && choice.board_monster != null) {
    monsterBox.classList.add("choosable");
  } else {
    monsterBox.classList.remove("choosable");
  }
  if (choice == null || choice.monsters != null || choice.board_monster != null) {
    pDiv.classList.remove("choose");
    return;
  }
  // Set display style for uichoice div.
  if (!choice.items) {
    uichoice.style.display = "flex";
  }
  if (choice.cards != null) {
    document.getElementById("cardchoicescroll").style.display = cardsStyle;
    cardtoggle.style.display = "inline-block";
    setCardButtonText();
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
    pDiv.classList.add("choose");
    btn.style.display = "inline-block";
  } else {
    pDiv.classList.remove("choose");
    if (choice.places != null) {
      updatePlaceChoices(uichoice, choice.places, choice.annotations);
    } else if (choice.cards != null) {
      addCardChoices(uichoice, uicardchoice, choice.cards, choice.invalid_choices, choice.remaining_spend, choice.annotations, choice.sort_uniq);
    } else {
      addChoices(uichoice, choice.choices, choice.invalid_choices, choice.remaining_spend);
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

function addCardChoices(uichoice, cardChoice, cards, invalidChoices, remainingSpend, annotations, sortUniq) {
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
    let holder = document.createElement("DIV");
    holder.classList.add("cardholder");
    if (sortUniq) {
      holder.style.order = cardToOrder[card];
    }
    let div = document.createElement("DIV");
    div.classList.add("cardchoice", "cnvcontainer");
    div.onclick = function(e) { makeChoice(card); };
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      holder.classList.add("unchoosable");
    } else if (remainingSpend != null && remainingSpend.length > idx && remainingSpend[idx]) {
      let rem = remainingSpend[idx];
      holder.classList.add("mustspend");
      div.onclick = function(e) { defaultSpend(rem); };
    }
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
  let scrollParent = cardChoice.parentNode;
  if (count > 4) {
    scrollParent.classList.add("overflowing");
  } else {
    scrollParent.classList.remove("overflowing");
  }
  addChoices(uichoice, notFound, newInvalid, newRemainingSpend);
}

function addChoices(uichoice, choices, invalidChoices, remainingSpend) {
  for (let [idx, c] of choices.entries()) {
    let div = document.createElement("DIV");
    div.classList.add("choice");
    div.innerText = c;
    div.onclick = function(e) { makeChoice(c); };
    if (invalidChoices != null && invalidChoices.includes(idx)) {
      div.classList.add("unchoosable");
    } else if (remainingSpend != null && remainingSpend.length > idx && remainingSpend[idx]) {
      let rem = remainingSpend[idx];
      div.classList.add("mustspend");
      div.onclick = function(e) { defaultSpend(rem); };
    } else {
      div.classList.add("choosable");
    }
    uichoice.appendChild(div);
  }
}

function updateUsables(usables, choice) {
  let uiuse = document.getElementById("uiuse");
  let pDiv, tDiv;
  if (!document.getElementsByClassName("you").length) {
    pDiv = document.createElement("DIV");  // Dummy div.
    tDiv = pDiv;
  } else {
    [pDiv, tDiv] = document.getElementsByClassName("you")[0].getElementsByClassName("possessions");
  }
  uiuse.style.display = "none";
  if (usables == null) {
    pDiv.classList.remove("use");
    tDiv.classList.remove("use");
    return;
  }
  if (choice == null) {
    uiuse.style.display = "flex";
  }
  pDiv.classList.add("use");
  tDiv.classList.add("use");
  let posList = pDiv.getElementsByClassName("possession");
  let trophyList = tDiv.getElementsByClassName("trophy");
  let allList = Array.from(posList).concat(Array.from(trophyList));
  for (let pos of allList) {
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
  let tradeOnly = true;
  for (let val of usables) {
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

function updateSpending(choice) {
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
  updateSpendList(spendable, spent);
  updateStatSpending(spendable);
}

function updateSpendList(spendable, spent) {
  let spendDiv = document.getElementById("uispend");
  if (spendable == null) {
    spendDiv.style.display = "none";
    return;
  }
  spendDiv.style.display = "flex";
  for (let stat in statNames) {
    let count = spent[stat] || 0;
    while (spendDiv.getElementsByClassName(stat).length > count) {
      spendDiv.removeChild(spendDiv.getElementsByClassName(stat)[0]);
    }
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
    renderAssetToDiv(gateCont, place.gate.name);
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
    uiprompt.innerText = characters[turnIdx].name + "'s " + turnPhase + " phase";
  }
}

function updateGlobals(env, rumor) {
  let envDiv = document.getElementById("environment");
  let envCnt = envDiv.getElementsByClassName("mythoscard")[0];
  let rumorDiv = document.getElementById("rumor");
  let rumorCnt = rumorDiv.getElementsByClassName("mythoscard")[0];
  if (env == null) {
    clearAssetFromDiv(envCnt);
    envDiv.classList.add("missing");
    envDiv.name = null;
  } else {
    envDiv.classList.remove("missing");
    envDiv.name = typeof(env) == "string" ? env : env.name;
    renderAssetToDiv(envCnt, envDiv.name);
  }
  if (rumor == null) {
    clearAssetFromDiv(rumorCnt);
    rumorDiv.classList.add("missing");
    rumorDiv.name = null;
  } else {
    rumorDiv.classList.remove("missing");
    rumorDiv.name = typeof(rumor) == "string" ? rumor : rumor.name;
    renderAssetToDiv(rumorCnt, rumorDiv.name);
  }
}

function toggleGlobals(e) {
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
  while (globalCards.getElementsByClassName("bigmythoscard").length) {
    globalCards.removeChild(globalCards.getElementsByClassName("bigmythoscard")[0]);
  }
  let count = 0;
  for (let cont of document.getElementById("globals").getElementsByClassName("mythoscontainer")) {
    if (!cont.name) {
      continue;
    }
    count++;
    let holder = document.createElement("DIV");
    holder.classList.add("bigmythoscard", "cnvcontainer");
    let cnv = document.createElement("CANVAS");
    cnv.classList.add("markercnv");  // TODO: use a better class name for this
    holder.appendChild(cnv);
    globalCards.appendChild(holder);
    renderAssetToDiv(holder, cont.name);
  }
  if (count > 4) {
    globalScroll.classList.add("overflowing");
  } else {
    globalScroll.classList.remove("overflowing");
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
  let rightUI = document.getElementById("uiright");
  let toKeep = Object.keys(pendingCharacters);
  // If no characters have been chosen yet, draw the characters players have selected.
  if (!characters.length) {
    for (let charName in pendingCharacters) {
      let sheet = characterSheets[charName];
      if (sheet == null) {
        sheet = createCharacterSheet(null, allCharacters[charName], rightUI, false);
        characterSheets[charName] = sheet;
      }
      updateInitialStats(sheet, allCharacters[charName]);
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
    updateCharacterSheet(sheet, character, order, playerIdx == idx, choice);
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
  for (let sheet of document.getElementById("uiright").getElementsByClassName("player")) {
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

function updateCharacterSheet(sheet, character, order, isPlayer, choice) {
  sheet.style.order = order;
  let spent = {};
  let chosen = [];
  if (choice != null) {
    for (let key in choice.spent) {
      for (let handle in choice.spent[key]) {
        spent[handle] = (spent[handle] || 0) + choice.spent[key][handle];
      }
    }
    chosen = choice.chosen || [];
  }
  updateCharacterStats(sheet, character, isPlayer, spent);
  updateSliders(sheet, character, isPlayer);
  updatePossessions(sheet, character.possessions, isPlayer, spent, chosen);
  updateTrophies(sheet, character, isPlayer, spent);
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

function updateCharacterStats(sheet, character, isPlayer, spent) {
  let stats = sheet.getElementsByClassName("playerstats")[0];
  let cfgs = [
    ["Stamina", "stamina", "white", "max_stamina"], ["Sanity", "sanity", "white", "max_sanity"],
    ["Clue", "clues", "white"], ["Dollar", "dollars", "black"],
  ];
  for (let cfg of cfgs) {
    let statDiv = sheet.getElementsByClassName(cfg[1])[0];
    renderAssetToDiv(statDiv, cfg[0]);
    let statSpent = isPlayer ? (spent[cfg[1]] || 0) : 0;
    statDiv.statValue = character[cfg[1]] - statSpent;
    statDiv.textColor = cfg[2];
    if (cfg.length > 3) {
      statDiv.maxValue = character[cfg[3]];
    } else {
      statDiv.maxValue = null;
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
  let possessions = [];
  for (let pos of character.fixed) {
    possessions.push({name: pos, active: false, handle: null, bonuses: {}});
  }
  for (let deck in character.random) {
    for (let i = 0; i < character.random[deck]; i++) {
      possessions.push({name: deck, active: false, handle: null, bonuses: {}});
    }
  }
  updatePossessions(sheet, possessions, false, {}, []);
}

function updatePossessions(sheet, possessions, isPlayer, spent, chosen) {
  // TODO: figure out which possessions to add/remove based on handle
  let pDiv = sheet.getElementsByClassName("possessions")[0];
  while (pDiv.firstChild) {
    pDiv.removeChild(pDiv.firstChild);
  }
  for (let pos of possessions) {
    createPossession(pos, isPlayer, pDiv, spent, chosen);
  }
}

function createPossession(info, isPlayer, sheet, spent, chosen) {
  let div = document.createElement("DIV");
  div.classList.add("possession", "cnvcontainer");
  div.cnvScale = 2.5;
  if (info.active) {
    div.classList.add("active");
  }
  if (spent[info.handle] != null) {
    div.classList.add("spent");
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
    if (chosen.includes(handle)) {
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

function updateTrophies(sheet, character, isPlayer, spent) {
  let tDiv = sheet.getElementsByClassName("possessions")[1];
  while (tDiv.firstChild) {
    tDiv.removeChild(tDiv.firstChild);
  }
  for (let trophy of character.trophies) {
    createTrophy(trophy, isPlayer, tDiv, spent);
  }
}

function createTrophy(info, isPlayer, tDiv, spent) {
  let handle = info.handle;
  let div = document.createElement("DIV");
  div.classList.add("trophy", "cnvcontainer");
  div.cnvScale = 2.5;
  if (spent[handle] != null) {
    div.classList.add("spent");
  }
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
  let assetName = info.name;
  if (monsterNames.includes(assetName)) {
    assetName += " back";
  }
  renderAssetToDiv(div, assetName);
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
