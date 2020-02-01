// Constants.
// Haha, canvas height/width is no longer constant. Set on page load.
// TODO: update on resize.
// Constants for drawing on the canvas.
canWidth = 1011;
canHeight = 876;
tileWidth = 337 / 2;
tileHeight = 292 / 2;
pieceRadius = 10;
// Constants for sizing items on the page.
cardWidth = 145;
cardHeight = 210;
summaryCardWidth = 29;
summaryCardHeight = 41;
selectCardWidth = summaryCardWidth * 3;
selectCardHeight = summaryCardHeight * 3;
// Other constants.
cardResources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4", "rsrc5"];
globalNames = {
  rsrc1: "sulfur",
  rsrc2: "olivine",
  rsrc3: "water",
  rsrc4: "clay",
  rsrc5: "metal",
  norsrc: "desert",
  space: "space",
};
imageNames = {
  rsrc1: "/sulfur.png",
  rsrc2: "/olivine.png",
  rsrc3: "/permafrost.png",
  rsrc4: "/clay.png",
  rsrc5: "/metal.png",
  rsrc1card: "/sulfurcard.png",
  rsrc2card: "/olivinecard.png",
  rsrc3card: "/watercard.png",
  rsrc4card: "/claycard.png",
  rsrc5card: "/metalcard.png",
  norsrc: "/desert.png",
  space: "/space.png",
  rsrc1port: "/sulfurport.png",
  rsrc2port: "/olivineport.png",
  rsrc3port: "/waterport.png",
  rsrc4port: "/clayport.png",
  rsrc5port: "/metalport.png",
  "3port": "/3port.png",
  knight: "/knight.png",
  roadbuilding: "/roadbuilding.png",
  yearofplenty: "/yearofplenty.png",
  monopoly: "/monopoly.png",
  palace: "/palace.png",
  chapel: "/chapel.png",
  university: "/university.png",
  library: "/library.png",
  market: "/market.png",
  cardback: "/cardback.png",
  devcard: "/devcard.png",
};
devCards = ["knight", "roadbuilding", "yearofplenty", "monopoly", "palace", "chapel", "university", "library", "market"];
resourceSelectionUI = {
  tradeOffer: {
    topPanelText: "You Want",
    bottomPanelText: "You Give",
    okText: "Offer",
    cancelText: "Cancel",
    resetText: "Reset",
  },
  tradeBank: {
    topPanelText: "You Want",
    bottomPanelText: "You Give",
    okText: "Trade",
    cancelText: "Cancel",
    resetText: "Reset",
  },
  tradeCounterOffer: {
    topPanelText: "You Want",
    bottomPanelText: "You Give",
    okText: "Accept",
    resetText: "Reset",
    cancelText: "Reject",
  },
  monopoly: {
    bottomPanelText: "Choose a resource to monopolize.",
    okText: "Monopoly!",
    cancelText: "Cancel",
  },
  yearofplenty: {
    bottomPanelText: "Choose two resources to receive from the bank.",
    okText: "OK",
    cancelText: "Cancel",
  },
  discard: {
    bottomPanelText: "Choose cards to discard.",
    okText: "Discard",
  },
};

// Game state.
myColor = null;
playerColors = null;
turnOrder = [];
tiles = [];
corners = [];
pieces = [];
edges = [];
roads = [];
cards = {};
cardCounts = {};
points = {};
armies = {};
longestRoads = {};
turn = null;
diceRoll = null;
robberLoc = null;
tradeOffer = null;
gamePhase = null;
turnPhase = null;
discardPlayers = {};

// Local state.
debug = false;
resourceSelectorActive = false;
resourceSelectorType = null;  // values are tradeOffer, tradeBank, tradeCounterOffer, dev, and discard
resourceSelection = {"top": {}, "bottom": {}};
tradeActiveOffer = {"want": {}, "give": {}};  // null until someone makes an offer.
counterOffers = {};
devCardType = null;  // knight, yearofplenty, roadbuilding, monopoly


function formatServerString(serverString) {
  var str = serverString;
  for (rsrc in globalNames) {
    str = str.replace(new RegExp("\\{" + rsrc + "\\}", "gi"), globalNames[rsrc]);
  }
  return str;
}

function toggleDebug() {
  debug = !debug;
}
function acceptCounter(event, player, offer) {
  let msg = {
    type: "accept_counter",
    counter_player: player,
    counter_offer: offer,
  };
  ws.send(JSON.stringify(msg));
}
function confirmSelection(event) {
  if (resourceSelectorType == "tradeBank") {
    let msg = {
      type: "trade_bank",
      offer: {"want": resourceSelection["top"], "give": resourceSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    return;
  } else if (resourceSelectorType == "tradeOffer") {
    let msg = {
      type: "trade_offer",
      offer: {"want": resourceSelection["top"], "give": resourceSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    return;
  } else if (resourceSelectorType == "tradeCounterOffer") {
    let msg = {
      type: "counter_offer",
      offer: {"want": resourceSelection["top"], "give": resourceSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    return;
  } else if (resourceSelectorType == "dev") {
    let msg = {
      type: "play_dev",
      card_type: devCardType,
      selection: resourceSelection["bottom"],
    };
    ws.send(JSON.stringify(msg));
    return;
  } else if (resourceSelectorType == "discard") {
    let msg = {
      type: "discard",
      selection: resourceSelection["bottom"],
    };
    ws.send(JSON.stringify(msg));
    return;
  } else {
    // TODO: fill this in.
  }
}
function clearResourceSelection(side) {
  resourceSelection[side] = {};
}
function resetSelection(event) {
  if (resourceSelectorType == "tradeCounterOffer") {
    copyActiveOffer();
    updateSelectCounts();
  } else {
    // TODO: Are there any scenarios where we wouldn't want to reset this?
    resourceSelection = {"top": {}, "bottom": {}};
    updateSelectCounts();
  }
}
function cancelSelection(event) {
  if (resourceSelectorType == "tradeCounterOffer") {
    let msg = {
      type: "counter_offer",
      offer: null,
    };
    ws.send(JSON.stringify(msg));
    hideSelectorWindow();
    return;
  } else if (resourceSelectorType == "discard") {
    // You can't cancel discarding.
    return;
  } else if (resourceSelectorType == "tradeOffer") {
    clearResourceSelection("top");
    clearResourceSelection("bottom");
    let msg = {
      type: "trade_offer",
      offer: {"want": resourceSelection["top"], "give": resourceSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    hideSelectorWindow();
  } else {
    hideSelectorWindow();
  }
}
function selectResource(event, windowName, rsrc) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  let num = 1;
  if (event.shiftKey) {
    num = -1;
  }
  selectResourceHelper(windowName, rsrc, num);
}
function deselectResource(event, windowName, rsrc) {
  // Only called for right-click - prevents context menu from appearing.
  event.preventDefault();
  selectResourceHelper(windowName, rsrc, -1);
}
function selectResourceHelper(windowName, rsrc, num) {
  let current = resourceSelection[windowName][rsrc] || 0;
  resourceSelection[windowName][rsrc] = current + num;
  if (resourceSelection[windowName][rsrc] < 0) {
    resourceSelection[windowName][rsrc] = 0;
  }
  updateSelectCounts();
}
function updateSelectCounts() {
  for (let key in resourceSelection) {
    let container = document.getElementById(key + "selectbox");
    for (let i = 0; i < cardResources.length; i++) {
      let subcontainer = container.getElementsByClassName(cardResources[i])[0];
      let counter = subcontainer.getElementsByClassName("selectcount")[0];
      counter.innerText = "x" + (resourceSelection[key][cardResources[i]] || 0);
    }
  }
  updateSelectSummary();
  if (resourceSelectorType == "tradeCounterOffer") {
    let myOffer = {"want": resourceSelection["top"], "give": resourceSelection["bottom"]};
    if (areOffersEqual(myOffer, tradeActiveOffer, true)) {
      document.getElementById("selectconfirm").innerText = "Accept";
    } else {
      document.getElementById("selectconfirm").innerText = "Counter";
    }
  }
}
function comparePlayers(nameA, nameB) {
  return turnOrder.indexOf(playerColors[nameA]) - turnOrder.indexOf(playerColors[nameB]);
}
function updateSelectSummary() {
  // TODO: fix the width of these summary windows and don't let them make the whole
  // resource popup wider when the user selects a ridiculous number of resources.
  let summary = document.getElementById("tradesummary");
  if (resourceSelectorType != "tradeOffer" && resourceSelectorType != "tradeCounterOffer") {
    summary.style.display = "none";
    return;
  } else {
    summary.style.display = "flex";
  }
  let leftText = document.getElementById("selfsummary").getElementsByClassName("summaryfixed")[0];
  let rightText = document.getElementById("selfsummary").getElementsByClassName("summaryfixed")[2];
  leftText.firstChild.innerText = document.getElementById("bottomselecttitle").innerText;
  rightText.firstChild.innerText = document.getElementById("topselecttitle").innerText;
  let mySelection;
  if (turn == myColor) {
    mySelection = tradeActiveOffer;
  } else {
    mySelection = {"want": resourceSelection["top"], "give": resourceSelection["bottom"]};
  }
  for (let key in mySelection) {
    let side;
    if (key == "want") {
      side = "right";
    } else {
      side = "left";
    }
    let selectPanel = document.getElementById("selfsummary").getElementsByClassName("summary" + side)[0];
    while (selectPanel.getElementsByClassName("summarycard").length) {
      selectPanel.removeChild(selectPanel.getElementsByClassName("summarycard")[0]);
    }
    addSelectionToPanel(mySelection[key], selectPanel);
  }
  updateCounterOfferSummary();
}
function addSelectionToPanel(selection, panel) {
  // TODO: how does this happen?
  if (!selection) {
    return;
  }
  for (let rsrc of cardResources) {
    let count = selection[rsrc] || 0;
    for (let i = 0; i < count; i++) {
      let div = document.createElement("DIV");
      div.classList.add("summarycard");
      let img = document.createElement("IMG");
      img.src = imageNames[rsrc + "card"];
      img.classList.add("noclick");
      img.width = summaryCardWidth;
      img.height = summaryCardHeight;
      img.style.display = "block";
      div.appendChild(img);
      panel.appendChild(div);
    }
  }
}
function updateCounterOfferSummary() {
  let container = document.getElementById("tradesummary");
  while (container.getElementsByClassName("countersummary").length) {
    container.removeChild(container.getElementsByClassName("countersummary")[0]);
  }
  let playerNames = Object.keys(playerColors);
  playerNames.sort(comparePlayers);
  for (let p of playerNames) {
    let pColor = playerColors[p];
    if (pColor == myColor) {
      continue;
    }
    let leftSide = "want";
    let rightSide = "give";
    let newsummary = document.createElement("DIV");
    newsummary.classList.add("selectsummary");
    newsummary.classList.add("countersummary");
    let leftText = document.createElement("DIV");
    leftText.classList.add("summaryfixed");
    let newp = document.createElement("P");
    let namespan = document.createElement("SPAN");
    namespan.innerText = p;
    namespan.style.color = pColor;
    namespan.style.fontWeight = "bold";
    let textspan = document.createElement("SPAN");
    textspan.innerText = leftSide == "want" ? " wants" : " offers";
    textspan.style.color = "black";
    newp.appendChild(namespan);
    newp.appendChild(textspan);
    leftText.appendChild(newp);
    let showMore = true;
    let canAccept = (myColor == turn);
    if (pColor != turn) {
      var counterOffer = counterOffers[pColor];
      if (counterOffer === undefined) {
        textspan.innerText = " is considering...";
        canAccept = false;
        showMore = false;
      } else if (!counterOffer) {
        textspan.innerText = " rejects the offer.";
        newsummary.classList.add("rejected");
        canAccept = false;
        showMore = false;
      } else if (areOffersEqual(tradeActiveOffer, counterOffer, true)) {
        // The user may change their selection without updating their offer,
        // so we make sure that the selection and the offer match the counter offer.
        let currentOffer = {want: resourceSelection["top"], give: resourceSelection["bottom"]};
        if (areOffersEqual(currentOffer, counterOffer, true)) {
          textspan.innerText = " accepts.";
          showMore = false;
        }
      }
    }
    newsummary.appendChild(leftText);
    if (showMore) {
      let rightText = document.createElement("DIV");
      rightText.classList.add("summaryfixed");
      newp = document.createElement("P");
      namespan = document.createElement("SPAN");
      namespan.innerText = p;
      namespan.style.color = pColor;
      namespan.style.fontWeight = "bold";
      textspan = document.createElement("SPAN");
      textspan.innerText = rightSide == "want" ? " wants" : " offers";
      textspan.style.color = "black";
      newp.appendChild(namespan);
      newp.appendChild(textspan);
      rightText.appendChild(newp);
      let centerText = document.createElement("DIV");
      centerText.classList.add("summaryfixed");
      newp = document.createElement("P");
      newp.innerText = "🔄";
      let summaryLeft = document.createElement("DIV");
      summaryLeft.classList.add("summaryleft");
      summaryLeft.classList.add("summarypanel");
      let summaryRight = document.createElement("DIV");
      summaryRight.classList.add("summaryright");
      summaryRight.classList.add("summarypanel");
      if (pColor == turn) {
        addSelectionToPanel(tradeActiveOffer[leftSide], summaryLeft);
        addSelectionToPanel(tradeActiveOffer[rightSide], summaryRight);
        newsummary.style.order = "-1";
      } else if (counterOffers[pColor]) {
        addSelectionToPanel(counterOffers[pColor][leftSide], summaryLeft);
        addSelectionToPanel(counterOffers[pColor][rightSide], summaryRight);
      }
      centerText.appendChild(newp);
      newsummary.appendChild(summaryLeft);
      newsummary.appendChild(centerText);
      newsummary.appendChild(summaryRight);
      newsummary.appendChild(rightText);
    }
    if (canAccept) {
      newsummary.classList.add("clickable");
      newsummary.classList.add("selectable");
      newsummary.classList.add("acceptable");
      newsummary.onclick = function(event) {
        acceptCounter(event, pColor, counterOffers[pColor]);
      }
    }
    container.appendChild(newsummary);
  }
}
function toggleTradeWindow(partner) {
  let selectorType;
  if (turn != myColor && partner == "player") {
    selectorType = "tradeCounterOffer";
  } else if (turn == myColor && partner == "player") {
    selectorType = "tradeOffer";
  } else if (turn == myColor && partner == "bank") {
    selectorType = "tradeBank";
  } else {
    return;
  }
  if (resourceSelectorActive && resourceSelectorType == selectorType) {
    resourceSelectorActive = false;
  } else {
    resourceSelectorActive = true;
    resourceSelectorType = selectorType;
  }
  if (resourceSelectorActive) {
    showResourceUI(resourceSelectorType);
  } else {
    hideSelectorWindow();
  }
}
function hideSelectorWindow() {
  resourceSelectorActive = false;
  document.getElementById("resourcepopup").style.display = 'none';
  updateTradeButtons();
}
function rememberActiveOffer() {
  // When the current player opens the trading UI after closing it (maybe they
  // wanted to look behind it?), we restore the trade offer that they have made.
  if (tradeActiveOffer && (tradeActiveOffer["want"] || tradeActiveOffer["give"])) {
    resourceSelection["top"] = Object.assign({}, tradeActiveOffer["want"]);
    resourceSelection["bottom"] = Object.assign({}, tradeActiveOffer["give"]);
  } else {
    clearResourceSelection("top");
    clearResourceSelection("bottom");
  }
}
function copyActiveOffer() {
  // This function puts the active offer into the resource selector for all players
  // except the player that is making the offer.
  // Note that we switch these around to make it more intuitive for the player
  // receiving the trade offer - the stuff they will give will still be on bottom.
  resourceSelection["top"] = Object.assign({}, tradeActiveOffer["give"]);
  resourceSelection["bottom"] = Object.assign({}, tradeActiveOffer["want"]);
}
function copyPreviousCounterOffer(offer) {
  // This function is only called the first time the user connects, and is used
  // to restore any counter-offer they had previously made.
  resourceSelection["top"] = Object.assign({}, offer["want"]);
  resourceSelection["bottom"] = Object.assign({}, offer["give"]);
}
function areOffersEqual(offerA, offerB, swapSides) {
  if (offerA == null && offerB == null) {
    return true;
  }
  if (offerA == null || offerB == null) {
    return false;
  }
  for (let aside of ["want", "give"]) {
    let bside = aside;
    if (swapSides) {
      bside = (aside == "want") ? "give" : "want";
    }
    if (offerA[aside] == null && offerB[bside] != null) {
      return false;
    }
    if (offerB[bside] == null && offerA[aside] != null) {
      return false;
    }
    if (offerB[bside] == null && offerA[aside] == null) {
      continue;
    }
    for (let key in offerA[aside]) {
      // dict[resource] == 0 and a dict without the resource should be equivalent.
      if (offerA[aside][key] == 0 && !offerB[bside][key]) {
        continue;
      }
      if (offerA[aside][key] != offerB[bside][key]) {
        return false;
      }
    }
    for (let key in offerB[bside]) {
      // dict[resource] == 0 and a dict without the resource should be equivalent.
      if (offerB[bside][key] == 0 && !offerA[aside][key]) {
        continue;
      }
      if (offerB[bside][key] != offerA[aside][key]) {
        return false;
      }
    }
  }
  return true;
}
function maybeShowActiveTradeOffer(oldActiveOffer) {
  // Update any counter-offers.
  updateSelectCounts();
  // Do not change the trade window for the player offering the trade.
  if (turn == myColor) {
    return;
  }
  // Do nothing when the trade hasn't actually changed.
  let equalOffers = areOffersEqual(tradeActiveOffer, oldActiveOffer, false);
  if (equalOffers) {
    return;
  }
  let shouldCopy = false;
  // If they're not actively looking at the trade window, update the selection.
  if (!resourceSelectorActive) {
    shouldCopy = true;
  }
  // If they haven't touched the trade offer and haven't made a counter offer, update it.
  if (!counterOffers[myColor] && areOffersEqual(oldActiveOffer, {want: resourceSelection["top"], give: resourceSelection["bottom"]}, true)) {
    shouldCopy = true;
  }
  // If they have no selection (e.g. if the window was already open when the offer was made),
  // then we should show them the new offer.
  if (!Object.keys(resourceSelection["top"]) && !Object.keys(resourceSelection["bottom"])) {
    shouldCopy = true;
  }
  if (shouldCopy) {
    if (counterOffers[myColor]) {
      copyPreviousCounterOffer(counterOffers[myColor]);
    } else {
      copyActiveOffer();
    }
  }
  updateSelectCounts();
  if (tradeActiveOffer && ((tradeActiveOffer.want && Object.keys(tradeActiveOffer.want).length) || (tradeActiveOffer.give && Object.keys(tradeActiveOffer.give).length))) {
    if (counterOffers[myColor] !== null) {
      resourceSelectorType = "tradeCounterOffer";
      showResourceUI(resourceSelectorType);
    }
  } else {
    hideSelectorWindow();
  }
}
function updateTradeButtons() {
  let playerButton = document.getElementById("tradeplayer");
  let bankButton = document.getElementById("tradebank");
  if (resourceSelectorActive && resourceSelectorType.startsWith("trade")) {
    let activeButton = null;
    let inactiveButton = null;
    if (resourceSelectorType == "tradeBank") {
      activeButton = bankButton;
      inactiveButton = playerButton;
    } else {
      activeButton = playerButton;
      inactiveButton = bankButton;
    }
    activeButton.classList.add("active");
    inactiveButton.classList.remove("active");
  } else {
    for (let button of [playerButton, bankButton]) {
      button.classList.remove("active");
      enableButton(button);
    }
  }
  // Disable buttons if it's not the player's turn.
  if (turn != myColor) {
    disableButton(bankButton);
    // Disable unless there is an active trade offer.
    if (!tradeActiveOffer || !(tradeActiveOffer["want"] || tradeActiveOffer["give"])) {
      disableButton(playerButton);
    }
  }
  if (gamePhase != "main" || turnPhase != "main") {
    disableButton(playerButton);
    disableButton(bankButton);
  }
}
function disableButton(elem) {
  elem.classList.add("disabled");
  elem.disabled = true;
}
function enableButton(elem) {
  elem.classList.remove("disabled");
  elem.disabled = false;
}
function maybeShowDiscardWindow() {
  if (turnPhase == "discard" && discardPlayers[myColor]) {
    if (resourceSelectorType != "discard") {
      // Clear selection counts only if we just popped the window up.
      clearResourceSelection("bottom");
      updateSelectCounts();
    }
    resourceSelectorType = "discard";
    showResourceUI(resourceSelectorType);
  } else if (turnPhase == "discard" || turnPhase == "robber") {
    hideSelectorWindow();
  }
}
function rollDice() {
  if (turn != myColor) {
    return;
  }
  let msg = {
    type: "roll_dice",
  };
  ws.send(JSON.stringify(msg));
}
function endTurn() {
  let msg = {
    type: "end_turn",
  };
  ws.send(JSON.stringify(msg));
}
function populateCards() {
  let newContainer = document.createElement("DIV");
  newContainer.classList.add("uicards");
  newContainer.classList.add("noclick");
  let oldContainer = document.getElementById("uibottom").firstChild;
  if (cards) {
    for (let i = 0; i < cardResources.length; i++) {
      for (let j = 0; j < cards[cardResources[i]]; j++) {
        addCard(newContainer, cardResources[i] + "card", false);
      }
    }
    for (let i = 0; i < devCards.length; i++) {
      for (let j = 0; j < cards[devCards[i]]; j++) {
        addCard(newContainer, devCards[i], true);
      }
    }
  }
  if (newContainer.childElementCount > 0) {
    newContainer.lastChild.classList.add("shown");
  }
  // TODO: how do we avoid the problem of having flicker?
  document.getElementById("uibottom").replaceChild(newContainer, oldContainer);
}
function addCard(cardContainer, elemId, usable) {
  let img = document.createElement("IMG");
  img.src = imageNames[elemId];
  img.classList.add("clickable");
  img.width = cardWidth;
  img.height = cardHeight;
  img.style.display = "block";
  let div = document.createElement("DIV");
  div.classList.add("clickable");
  div.classList.add("uicard");
  div.appendChild(img);
  div.onmouseenter = bringforward;
  div.onmouseleave = pushbackward;
  if (usable) {
    div.onclick = function(e) {
      playDevCard(elemId);
    }
    div.classList.add("resourceselector");
  }
  cardContainer.appendChild(div);
}
function bringforward(e) {
  e.currentTarget.classList.add("selected");
  e.currentTarget.style.overflowX = "visible";
}
function pushbackward(e) {
  e.currentTarget.classList.remove("selected");
  e.currentTarget.style.overflowX = "hidden";
}
function buyDevCard() {
  ws.send(JSON.stringify({type: "buy_dev"}));
}
function playDevCard(cardType) {
  devCardType = cardType;
  let selectInfo = resourceSelectionUI[cardType];
  if (selectInfo) {
    clearResourceSelection("bottom");
    resourceSelectorType = "dev";
    updateSelectCounts();
    showResourceUI(cardType);
  } else {
    ws.send(JSON.stringify({type: "play_dev", card_type: cardType}));
  }
}
function showResourceUI(uiType) {
  let selectInfo = resourceSelectionUI[uiType];
  if (!selectInfo) {
    console.log("unknown selector " + uiType);
    return;
  }
  if (selectInfo.topPanelText) {
    document.getElementById("topselect").style.display = 'flex';
    document.getElementById("topselecttitle").innerText = selectInfo.topPanelText;
  } else {
    document.getElementById("topselect").style.display = 'none';
  }
  document.getElementById("bottomselecttitle").innerText = selectInfo.bottomPanelText;
  let buttons = {"okText": "selectconfirm", "resetText": "selectreset", "cancelText": "selectcancel"};
  for (let button in buttons) {
    if (selectInfo[button]) {
      document.getElementById(buttons[button]).innerText = selectInfo[button];
      document.getElementById(buttons[button]).style.display = 'inline-block';
    } else {
      document.getElementById(buttons[button]).style.display = 'none';
    }
  }
  resourceSelectorActive = true;
  if (resourceSelectorType == "tradeOffer" && turn == myColor) {
    rememberActiveOffer();
  }
  updateSelectCounts();
  document.getElementById("resourcepopup").style.display = 'flex';
  updateTradeButtons();
}
function onkey(event) {
  let thing = event.which || event.keyCode; // Cross-browser compatibility.
  console.log("keypress " + thing);
  if (thing == 32 && turnPhase == "dice") {
    rollDice();
    return;
  }
  if (thing == 13 && turnPhase == "main") {
    endTurn();
    return;
  }
}
function clearerror() {
  etxt = document.getElementById("errorText")
  if (etxt.holdSeconds > 0) {
    etxt.holdSeconds -= 0.1;
    setTimeout(clearerror, 100);
  } else {
    newOpac = etxt.style.opacity - 0.02;
    etxt.style.opacity = newOpac;
    if (newOpac <= 0.1) {
      etxt.innerText = null;
    } else {
      setTimeout(clearerror, 50);
    }
  }
}
function onmsg(event) {
  var data = JSON.parse(event.data);
  if (data.type == "error") {
    document.getElementById("errorText").holdSeconds = 3;
    document.getElementById("errorText").style.opacity = 1.0;
    document.getElementById("errorText").innerText = formatServerString(data.message);
    setTimeout(clearerror, 100);
    return;
  }
  let firstMsg = false;
  if (tiles.length < 1) {
    firstMsg = true;
  }
  // data.type should be game_state now - maybe handle more later
  playerColors = data.player_colors;
  gamePhase = data.game_phase;
  turnPhase = data.turn_phase;
  tiles = data.tiles;
  corners = data.corners;
  edges = data.edges;
  robberLoc = data.robber;
  cards = data.cards;
  cardCounts = data.card_counts;
  points = data.points;
  armies = data.armies;
  longestRoads = data.longest_roads;
  diceRoll = data.dice_roll;
  pieces = data.pieces;
  roads = data.roads;
  let oldTurn = turn;
  turn = data.turn;
  turnOrder = data.turn_order;
  discardPlayers = data.discard_players;
  let oldActiveOffer = tradeActiveOffer;
  tradeActiveOffer = data.trade_offer;
  counterOffers = data.counter_offers;
  if (data.you) {
    myColor = data.you.color;
  }
  if (firstMsg) {
    centerCanvas();
    initPlayerData();
    initializePlayerName();
  }
  if (data.you) {
    if (document.getElementById('nameInput').value == data.you.name) {
      if (getCookie("playername") != data.you.name) {
        document.cookie = "playername=" + data.you.name;
      }
    }
    if (!document.getElementById('nameInput').value) {
      document.getElementById('nameInput').value = data.you.name;
    }
    fixNameSize(null);
  }
  populateCards();
  updateDice();
  updateUI("buydev");
  updateUI("endturn");
  updateTradeButtons();
  updatePlayerData();
  if (firstMsg && counterOffers[myColor]) {
    copyPreviousCounterOffer(counterOffers[myColor]);
  }
  maybeShowActiveTradeOffer(oldActiveOffer);
  if (oldTurn != null && oldTurn != turn) {
    hideSelectorWindow();
  }
  maybeShowDiscardWindow();
}
function updateUI(elemName) {
  if (gamePhase != "main" || turn != myColor || turnPhase != "main") {
    document.getElementById(elemName).classList.remove("selectable");
    document.getElementById(elemName).classList.add("disabled");
    document.getElementById(elemName).disabled = true;
  } else {
    document.getElementById(elemName).classList.add("selectable");
    document.getElementById(elemName).classList.remove("disabled");
    document.getElementById(elemName).disabled = false;
  }
}
function updateDice() {
  diceEl = document.getElementById("uidice");
  if (diceRoll == null && turnPhase != "dice") {
    diceEl.style.display = "none";
  } else {
    diceEl.style.display = "block";
  }
  if (diceRoll == null) {
    document.getElementById("reddie").firstChild.firstChild.innerText = "?";
    document.getElementById("whitedie").firstChild.firstChild.innerText = "?";
  } else {
    document.getElementById("reddie").firstChild.firstChild.innerText = diceRoll[0];
    document.getElementById("whitedie").firstChild.firstChild.innerText = diceRoll[1];
  }
  if (turn != myColor) {
    diceEl.classList.remove("selectable");
    diceEl.classList.add("unallowed");
  } else {
    diceEl.classList.remove("unallowed");
    diceEl.classList.add("selectable");
  }
}
function login(e) {
  let msg = {
    type: "player",
    player: {
      name: document.getElementById('nameInput').value,
    },
  };
  ws.send(JSON.stringify(msg));
}
function fixNameSize(e) {
  let nameInput = document.getElementById("nameInput");
  let sizeCalculator = document.getElementById("sizeCalculator");
  sizeCalculator.textContent = nameInput.value;
  nameInput.style.width = sizeCalculator.offsetWidth + "px";
}
function initPlayerData() {
  let rightUI = document.getElementById("uiright");
  while (rightUI.firstChild) {
    rightUI.removeChild(rightUI.firstChild);
  }
  let playerNames = Object.keys(playerColors);
  playerNames.sort(comparePlayers);
  for (let p of playerNames) {
    createPlayerData(p);
  }
  fixNameSize(null);
}
function createPlayerData(p) {
  let rightUI = document.getElementById("uiright");
  let pColor = playerColors[p];
  let newdiv = document.createElement("DIV");
  newdiv.style.background = pColor;
  newdiv.classList.add(pColor + "player");
  newdiv.classList.add("playerinfo");

  let username = p;
  let topText = document.createElement("DIV");
  topText.classList.add("playername");
  if (pColor == myColor) {
    let sizeCalculator = document.createElement("SPAN");
    sizeCalculator.id = "sizeCalculator";
    sizeCalculator.classList.add("hide");
    let nameInput = document.createElement("INPUT");
    nameInput.id = "nameInput";
    nameInput.type = "text";
    // nameInput.contentEditable = true;
    nameInput.classList.add("nameinput");
    nameInput.classList.add("clickable");
    nameInput.style.background = pColor;
    nameInput.innerText = username;
    nameInput.maxlength = 16;
    nameInput.oninput = fixNameSize;
    // Setting nameInput.onfocusout does not work in webkit browsers.
    nameInput.addEventListener("focusout", login);
    topText.appendChild(sizeCalculator);
    topText.appendChild(nameInput);
  } else {
    let nameDiv = document.createElement("DIV");
    nameDiv.innerText = username;
    nameDiv.classList.add("nametext");
    topText.appendChild(nameDiv);
  }
  let turnMarker = document.createElement("DIV");
  turnMarker.innerText = "👉";  // ▶️ looks bad.
  turnMarker.classList.add("turnmarker");
  topText.appendChild(turnMarker);
  let phaseMarker = document.createElement("DIV");
  phaseMarker.innerText = "";
  phaseMarker.classList.add("phasemarker");
  topText.appendChild(phaseMarker);
  newdiv.appendChild(topText);
  let cardDiv = document.createElement("DIV");
  let rightWidth = document.getElementById("uiright").offsetWidth;
  cardDiv.style.width = 0.8 * rightWidth + "px";
  cardDiv.classList.add("cardinfo");
  newdiv.appendChild(cardDiv);
  /*
   * TODO: add data about # of cities, army size, longest road, victory points
  let dataDiv = document.createElement("DIV");
  newdiv.appendChild(dataDiv);
  */
  rightUI.appendChild(newdiv);
  return newdiv;
}
function updatePlayerData() {
  let rightUI = document.getElementById("uiright");
  let playerNames = Object.keys(playerColors);
  playerNames.sort(comparePlayers);
  for (let p of playerNames) {
    let pColor = playerColors[p];
    let thediv = null;
    for (let somediv of rightUI.getElementsByClassName("playerinfo")) {
      if (somediv.classList.contains(pColor + "player")) {
        thediv = somediv;
        break;
      }
    }
    if (!thediv) {
      thediv = createPlayerData(p);
    }
    if (pColor != myColor) {
      let namediv = thediv.getElementsByClassName("nametext")[0];
      namediv.innerText = p;
    }

    let turnMarker = thediv.getElementsByClassName("turnmarker")[0];
    let phaseMarker = thediv.getElementsByClassName("phasemarker")[0];
    if (!turnMarker || !phaseMarker) {  // TODO: better error checking.
      continue;
    }
    if (turnPhase == "discard") {
      if (discardPlayers[pColor]) {
        phaseMarker.style.display = "block";
        phaseMarker.innerText = "🖐️";
      } else {
        phaseMarker.innerText = "";
      }
      continue;
    }
    if (turn == pColor) {
      turnMarker.style.display = "block";
      phaseMarker.style.display = "block";
      if (turnPhase == "robber") {
        phaseMarker.innerText = "💂";
      } else if (turnPhase == "dice") {
        phaseMarker.innerText = "🎲";
      } else if (turnPhase == "main") {
        phaseMarker.innerText = "";
      } else if (turnPhase == "settle") {
        phaseMarker.innerText = "🏠";
      } else if (turnPhase == "road" || turnPhase == "dev_road") {
        phaseMarker.innerText = "🛣️";
      } else {
        // ?
        phaseMarker.innerText = "";
      }
      // TODO: use 🛡️
    } else {
      turnMarker.style.display = "none";
      phaseMarker.style.display = "none";
    }
    let cardDiv = thediv.getElementsByClassName("cardinfo")[0];
    updatePlayerCardInfo(pColor, cardDiv);
  }
  fixNameSize(null);
}
function updatePlayerCardInfo(pColor, cardDiv) {
  while (cardDiv.firstChild) {
    cardDiv.removeChild(cardDiv.firstChild);
  }
  if (!cardCounts[pColor]) {
    return;
  }
  if (cardCounts[pColor]["resource"] && cardCounts[pColor]["dev"]) {
    let sepDiv = document.createElement("DIV");
    sepDiv.classList.add("cardseparator");
    sepDiv.style.width = summaryCardWidth / 2 + "px";
    sepDiv.style.height = summaryCardHeight + "px";
    sepDiv.style.order = 1;
    cardDiv.appendChild(sepDiv);
  }
  let orders = {resource: 0, dev: 2};
  let imgs = {resource: imageNames.cardback, dev: imageNames.devcard};
  for (let cardType of ["resource", "dev"]) {
    for (let i = 0; i < cardCounts[pColor][cardType]; i++) {
      let contDiv = document.createElement("DIV");
      contDiv.classList.add("cardback");
      contDiv.style.order = orders[cardType];
      let backImg = document.createElement("IMG");
      backImg.src = imgs[cardType];
      backImg.width = summaryCardWidth;
      backImg.height = summaryCardHeight;
      contDiv.appendChild(backImg);
      if (i == cardCounts[pColor][cardType]-1) {
        contDiv.style.flex = "0 0 auto";
      }
      cardDiv.appendChild(contDiv);
    }
  }
}
function createSelectors() {
  for (selectBox of ["top", "bottom"]) {
    let box = document.getElementById(selectBox + "selectbox");
    for (cardRsrc of cardResources) {
      let boxCopy = selectBox;
      let rsrcCopy = cardRsrc;
      let img = document.createElement("IMG");
      img.classList.add("selector");
      img.classList.add("clickable");
      img.width = selectCardWidth;
      img.height = selectCardHeight;
      img.src = imageNames[cardRsrc + "card"];
      img.onclick = function(e) { selectResource(e, boxCopy, rsrcCopy); };
      img.oncontextmenu = function(e) { deselectResource(e, boxCopy, rsrcCopy); };
      let counter = document.createElement("DIV");
      counter.innerText = "x0";
      counter.classList.add("selectcount");
      counter.classList.add("noclick");
      let container = document.createElement("DIV");
      container.classList.add("selectcontainer");
      container.classList.add(cardRsrc);
      container.appendChild(img);
      container.appendChild(counter);
      box.appendChild(container);
    }
  }
}
function sizeThings() {
  let totalWidth = document.documentElement.clientWidth;
  let totalHeight = document.documentElement.clientHeight;
  document.getElementById('ui').style.width = totalWidth + "px";
  document.getElementById('ui').style.height = totalHeight + "px";
  rightWidth = document.getElementById('uiright').offsetWidth;
  canWidth = totalWidth - rightWidth;
  canHeight = totalHeight;
  document.getElementById('uibottom').style.width = canWidth + "px";
  document.getElementById('myCanvas').width = canWidth;
  document.getElementById('myCanvas').height = canHeight;
  document.getElementById('buydev').width = cardWidth;
  document.getElementById('buydev').height = cardHeight;
  for (let pdiv of document.getElementsByClassName("cardinfo")) {
    pdiv.style.width = 0.8 * rightWidth + "px";
  }
}
function init() {
  sizeThings();
  createSelectors();
  window.requestAnimationFrame(draw);
  let l = window.location;
  ws = new WebSocket("ws://" + l.hostname + ":8081/");
  ws.onmessage = onmsg;
  document.getElementById('myCanvas').onmousemove = onmove;
  document.getElementById('myCanvas').onclick = onclick;
  document.getElementById('myCanvas').onmousedown = ondown;
  document.getElementById('myCanvas').onmouseup = onup;
  document.getElementById('myCanvas').onmouseout = onout;
  document.getElementById('myCanvas').onkeydown = onkey;
  // TODO: zoom in/out should come later.
  // document.getElementById('myCanvas').onwheel = onwheel;
  document.body.onclick = onBodyClick;
  window.onresize = sizeThings;
}
function onBodyClick(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  let hideSelector = true;
  if (resourceSelectorType == "discard") {
    return;
  }
  if (resourceSelectorActive) {
    let target = event.target;
    while (target != null) {
      if (target.id == "resourcepopup") {
        hideSelector = false;
        break;
      }
      if (target.classList && target.classList.contains("resourceselector")) {
        hideSelector = false;
        break;
      }
      target = target.parentNode;
    }
    if (hideSelector) {
      resourceSelectorActive = false;
      hideSelectorWindow();
    }
  }
}
function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for(var i = 0; i <ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return null;
}
function initializeImageLocations() {
  // TODO: is there a way people can use their local directories?
  let prefixDir = getCookie("image_prefix");
  let newImages = {};
  for (imgName in imageNames) {
    let imgPath = getCookie(imgName);
    if (imgPath && prefixDir) {
      // TODO: be smart about joining i.e. look for URI prefixes.
      newImages[imgName] = prefixDir + "/" + imgPath;
    } else if (imgPath) {
      newImages[imgName] = imgPath;
    }
  }
  for (imgName in newImages) {
    imageNames[imgName] = newImages[imgName];
  }
}
function initializeNames() {
  let overrides = JSON.parse(getCookie("names") || "");
  if (!overrides) {
    return;
  }
  let newNames = {};
  for (let name in globalNames) {
    if (overrides[name]) {
      newNames[name] = overrides[name];
    }
  }
  for (let name in newNames) {
    globalNames[name] = newNames[name];
  }
}
function initializePlayerName() {
  let pName = getCookie("playername");
  if (pName) {
    document.getElementById("nameInput").value = pName;
    fixNameSize(null);
    login(null);
  }
}
initializeImageLocations();
initializeNames();
