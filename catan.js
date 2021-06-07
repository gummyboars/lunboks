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
devCards = ["knight", "roadbuilding", "yearofplenty", "monopoly", "palace", "chapel", "university", "library", "market"];
resourceSelectionUI = {
  tradeOffer: {
    topPanelText: "You Want",
    bottomPanelText: "You Give",
    okText: "Offer",
    cancelText: "Close",
    resetText: "Reset",
  },
  tradeBank: {
    topPanelText: "You Want",
    bottomPanelText: "You Give",
    okText: "Trade",
    cancelText: "Close",
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
    bottomPanelText: "Choose {} cards to discard.",
    okText: "Discard",
  },
  collect: {
    bottomPanelText: "Choose {} resources to collect.",
    okText: "OK",
  },
};
var snd1 = new Audio("beep.mp3");

// The websocket
ws = null;

// Game state.
gameStarted = false;
gameOptions = [];
myIdx = null;
amHost = false;
playerData = [];
tiles = [];
ports = [];
corners = [];
pieces = [];
landings = [];
edges = [];
roads = [];
cards = {};
devCardCount = 0;
turn = null;
collectTurn = null;
collectCounts = [];
extraBuildTurn = null;
diceRoll = null;
robberLoc = null;
pirateLoc = null;
tradeOffer = null;
gamePhase = null;
turnPhase = null;
discardPlayers = {};
robPlayers = [];
longestRoutePlayer = null;
largestArmyPlayer = null;

// Local state.
debug = false;
resourceSelectorActive = false;
resourceSelectorType = null;  // values are tradeOffer, tradeBank, tradeCounterOffer, dev, and discard
resourceSelection = {"top": {}, "bottom": {}};
tradeActiveOffer = {"want": {}, "give": {}};  // null until someone makes an offer.
counterOffers = [];
devCardType = null;  // knight, yearofplenty, roadbuilding, monopoly


function formatServerString(serverString) {
  var str = serverString;
  for (let rsrc in serverNames) {
    str = str.replace(new RegExp("\\{" + rsrc + "\\}", "gi"), serverNames[rsrc]);
  }
  return str;
}

function formatStringWithParam(fmtString, param) {
  return fmtString.replace(new RegExp("\\{\\}", "gi"), "" + param);
}

function substitutePlayerName(serverString) {
  let div = document.createElement("DIV");
  div.classList.add("logevent");
  let newstr = formatServerString(serverString);
  let substrRegex = /(\{player\d+\})/;
  let splits = newstr.split(substrRegex);
  for (let piece of splits) {
    if (!piece.length) {
      continue;
    }
    let match = piece.match(/\{player(\d+)\}/);
    if (!match) {
      let normal = document.createElement("SPAN");
      normal.innerText = piece;
      div.appendChild(normal);
      continue;
    }
    let playerIdx = parseInt(match[1]);
    let span = document.createElement("SPAN");
    span.innerText = playerData[playerIdx].name;
    span.style.color = playerData[playerIdx].color;
    span.style.fontWeight = "bold";
    div.appendChild(span);
  }
  return div;
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
  } else if (resourceSelectorType == "collect") {
    let msg = {
      type: "collect",
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
      offer: 0,
    };
    ws.send(JSON.stringify(msg));
    hideSelectorWindow();
    return;
  } else if (resourceSelectorType == "discard" || resourceSelectorType == "collect") {
    // You can't cancel discarding or collecting resources.
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
  if (turn == myIdx) {
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
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("noclick");
      cnv.width = summaryCardWidth;
      cnv.height = summaryCardHeight;
      cnv.style.display = "block";
      div.appendChild(cnv);
      panel.appendChild(div);
      renderAssetToCanvas(cnv, rsrc + "card", "");
    }
  }
}
function updateCounterOfferSummary() {
  let container = document.getElementById("tradesummary");
  while (container.getElementsByClassName("countersummary").length) {
    container.removeChild(container.getElementsByClassName("countersummary")[0]);
  }
  for (let i = 0; i < playerData.length; i++) {
    if (i == myIdx) {
      continue;
    }
    let playerIdx = i;  // Capture for onclick function.
    let leftSide = "want";
    let rightSide = "give";
    let newsummary = document.createElement("DIV");
    newsummary.classList.add("selectsummary");
    newsummary.classList.add("countersummary");
    let leftText = document.createElement("DIV");
    leftText.classList.add("summaryfixed");
    let newp = document.createElement("P");
    let namespan = document.createElement("SPAN");
    namespan.innerText = playerData[i].name;
    namespan.style.color = playerData[i].color;
    namespan.style.fontWeight = "bold";
    let textspan = document.createElement("SPAN");
    textspan.innerText = leftSide == "want" ? " wants" : " offers";
    textspan.style.color = "black";
    newp.appendChild(namespan);
    newp.appendChild(textspan);
    leftText.appendChild(newp);
    let showMore = true;
    let canAccept = (myIdx == turn);
    if (i != turn) {
      var counterOffer = counterOffers[i];
      if (counterOffer === null) {
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
      namespan.innerText = playerData[i].name;
      namespan.style.color = playerData[i].color;
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
      if (i == turn) {
        addSelectionToPanel(tradeActiveOffer[leftSide], summaryLeft);
        addSelectionToPanel(tradeActiveOffer[rightSide], summaryRight);
        newsummary.style.order = "-1";
      } else if (counterOffers[i]) {
        addSelectionToPanel(counterOffers[i][leftSide], summaryLeft);
        addSelectionToPanel(counterOffers[i][rightSide], summaryRight);
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
        acceptCounter(event, playerIdx, counterOffers[i]);
      }
    }
    container.appendChild(newsummary);
  }
}
function toggleTradeWindow(partner) {
  let selectorType;
  if (turn != myIdx && partner == "player") {
    selectorType = "tradeCounterOffer";
  } else if (turn == myIdx && partner == "player") {
    selectorType = "tradeOffer";
  } else if (turn == myIdx && partner == "bank") {
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
    showResourceUI(resourceSelectorType, null);
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
  if (tradeActiveOffer == null) {
    return;
  }
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
  if (turn == myIdx) {
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
  if (!counterOffers[myIdx] && areOffersEqual(oldActiveOffer, {want: resourceSelection["top"], give: resourceSelection["bottom"]}, true)) {
    shouldCopy = true;
  }
  // If they have no selection (e.g. if the window was already open when the offer was made),
  // then we should show them the new offer.
  if (!Object.keys(resourceSelection["top"]) && !Object.keys(resourceSelection["bottom"])) {
    shouldCopy = true;
  }
  if (shouldCopy) {
    if (counterOffers[myIdx]) {
      copyPreviousCounterOffer(counterOffers[myIdx]);
    } else {
      copyActiveOffer();
    }
  }
  updateSelectCounts();
  if (tradeActiveOffer && ((tradeActiveOffer.want && Object.keys(tradeActiveOffer.want).length) || (tradeActiveOffer.give && Object.keys(tradeActiveOffer.give).length))) {
    if (counterOffers[myIdx] != 0) {
      resourceSelectorType = "tradeCounterOffer";
      showResourceUI(resourceSelectorType, null);
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
  if (turn != myIdx) {
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
function maybeShowCollectWindow(oldPhase) {
  if (turnPhase == "collect" && (collectTurn == myIdx || (collectTurn == null && collectCounts[myIdx]))) {
    if (resourceSelectorType != "collect") {
      // Clear selection counts only if we just popped the window up.
      clearResourceSelection("bottom");
      updateSelectCounts();
    }
    resourceSelectorType = "collect";
    showResourceUI(resourceSelectorType, collectCounts[myIdx]);
  } else if (oldPhase == "collect") {
    hideSelectorWindow();
  }
}
function maybeShowDiscardWindow() {
  if (turnPhase == "discard" && discardPlayers[myIdx]) {
    if (resourceSelectorType != "discard") {
      // Clear selection counts only if we just popped the window up.
      clearResourceSelection("bottom");
      updateSelectCounts();
    }
    resourceSelectorType = "discard";
    showResourceUI(resourceSelectorType, discardPlayers[myIdx]);
  } else if (turnPhase == "discard" || turnPhase == "robber") {
    hideSelectorWindow();
  }
}
function maybeShowRobWindow() {
  let playerpopup = document.getElementById("playerpopup");
  if (turnPhase == "rob" && turn == myIdx) {
    while (playerpopup.firstChild) {
      playerpopup.removeChild(playerpopup.firstChild);
    }
    let titleDiv = document.createElement("DIV");
    titleDiv.innerText = "Select a player to steal from";
    titleDiv.style.padding = "5px";
    playerpopup.appendChild(titleDiv);
    for (let i = 0; i < playerData.length; i++) {
      let playerIdx = i;  // capture for onclick function.
      if (!robPlayers.includes(i)) {
        continue;
      }
      let selectDiv = document.createElement("DIV");
      selectDiv.classList.add("selectsummary");
      selectDiv.classList.add("selectable");
      selectDiv.classList.add("acceptable");
      selectDiv.style.position = "relative";
      selectDiv.style.padding = "5px 0px 5px 0px";
      let nameOuter = document.createElement("DIV");
      nameOuter.style.flexGrow = "0";
      nameOuter.style.flexShrink = "0";
      nameOuter.style.flexBasis = "auto";
      nameOuter.style.margin = "0px 5px 0px 5px";
      let nameDiv = document.createElement("DIV");
      nameDiv.style.display = "flex";
      nameDiv.style.flexDirection = "row";
      nameDiv.style.justifyContent = "flex-start";
      nameDiv.style.color = playerData[i].color;
      nameDiv.style.fontWeight = "bold";
      nameDiv.innerText = playerData[i].name;
      nameOuter.appendChild(nameDiv);
      let cardsOuter = document.createElement("DIV");
      cardsOuter.classList.add("summarypanel");
      cardsOuter.style.width = "100%";
      cardsOuter.style.flexBasis = "100%";
      cardsOuter.style.margin = "0px 5px 0px 5px";
      let cardsDiv = document.createElement("DIV");
      cardsDiv.style.display = "flex";
      cardsDiv.style.flexDirection = "row";
      cardsDiv.style.justifyContent = "flex-end";
      cardsDiv.style.width = "100%";
      updatePlayerCardInfo(i, cardsDiv, true);
      cardsOuter.appendChild(cardsDiv);
      selectDiv.appendChild(nameOuter);
      selectDiv.appendChild(cardsOuter);
      selectDiv.onclick = function(e) {
        let msg = {
          type: "rob",
          player: playerIdx,
        };
        ws.send(JSON.stringify(msg));
      }
      playerpopup.appendChild(selectDiv);
    }
    popupMaxWidth = selectCardWidth * 5 + 100;
    playerpopup.style.display = 'flex';
    if (playerpopup.offsetWidth > popupMaxWidth) {
      playerpopup.style.width = popupMaxWidth + "px";
    }
  } else {
    playerpopup.style.display = 'none';
  }
}
function showCoastPopup() {
  document.getElementById("coastpopup").style.display = "block";
}
function cancelCoast() {
  document.getElementById("coastpopup").style.display = "none";
  clickEdgeLocation = null;
}
function coastSelect(edgeType) {
  if (clickEdgeLocation != null) {
    ws.send(JSON.stringify({type: edgeType, location: clickEdgeLocation}));
  }
  cancelCoast();
}
function rollDice() {
  if (turn != myIdx) {
    return;
  }
  let msg = {
    type: "roll_dice",
  };
  ws.send(JSON.stringify(msg));
}
function endTurn() {
  let msg = {
    type: (turnPhase == "extra_build") ? "end_extra_build" : "end_turn",
  };
  ws.send(JSON.stringify(msg));
}
function updateCostCard() {
  let container = document.getElementById("uicost");
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }
  // TODO: cleaner way of getting the height/width of the cost card.
  let prerendered = getAsset("costcard", "");
  if (prerendered == null) {
    return;
  }
  let cnv = document.createElement("CANVAS");
  cnv.height = cardHeight;
  cnv.width = cardHeight / prerendered.height * prerendered.width;
  cnv.style.display = "block";
  renderAssetToCanvas(cnv, "costcard", "");
  let div = document.createElement("DIV");
  div.style.maxWidth = cnv.width + "px";
  div.style.width = cnv.width + "px";
  div.style.height = cnv.height + "px";
  div.appendChild(cnv);
  container.appendChild(div);
}
function updateCards() {
  if (cards == null) {
    return;
  }
  let container = document.getElementById("uibottom").firstChild;
  cfgs = [
    {
      clist: cardResources,
      clickable: false,
      suffix: "card",
    },
    {
      clist: devCards,
      clickable: true,
      suffix: "",
    }
  ];
  for (child of container.children) {
    child.classList.remove("shown");
  }
  let oldCards = {};
  let ordering = 0;
  for (cfg of cfgs) {
    for (let cardType of cfg.clist) {
      if (!cards[cardType]) {
        cards[cardType] = 0;
      }
      oldCards[cardType] = countOldCards(container, cardType + cfg.suffix);
      for (i = 0; i < cards[cardType] - oldCards[cardType]; i++) {
        addCard(container, cardType + cfg.suffix, ordering, cfg.clickable);
      }
      removeCards(container, oldCards[cardType] - cards[cardType], cardType + cfg.suffix);
      ordering++;
    }
  }
  for (child of container.children) {
    updateCard(child);
  }
  let maxOrder = 0;
  let maxChild = null;
  for (child of container.children) {
    if (parseInt(child.style.order) >= maxOrder && !child.classList.contains("leave")) {
      maxOrder = parseInt(child.style.order);
      maxChild = child;
    }
  }
  if (maxChild != null) {
    maxChild.classList.add("shown");
  }
}
function countOldCards(container, elemID) {
  let count = 0;
  for (child of container.children) {
    if (child.cardType == elemID && !child.classList.contains("leave")) {
      count++;
    }
  }
  return count;
}
function addCard(cardContainer, elemId, ordering, usable) {
  let cnv = document.createElement("CANVAS");
  cnv.width = cardWidth;
  cnv.height = cardHeight;
  cnv.style.display = "block";
  cnv.classList.add("clickable");
  cnv.classList.add("innercard");
  let div = document.createElement("DIV");
  div.classList.add("clickable");
  div.classList.add("uicard");
  div.classList.add("enter");
  div.classList.add("changed");
  div.style.maxWidth = cardWidth + "px";
  div.style.width = "0px";
  div.style.height = cardHeight + "px";
  div.style.order = ordering;
  div.style.zIndex = ordering;
  div.appendChild(cnv);
  div.onmouseenter = bringforward;
  div.onmouseleave = pushbackward;
  div.cardType = elemId;
  if (usable) {
    div.onclick = function(e) {
      playDevCard(elemId);
    }
    div.classList.add("resourceselector");
  }
  cardContainer.appendChild(div);
  setTimeout(function() { div.classList.remove("enter"); div.style.width = cardWidth + "px"; }, 5);
  div.addEventListener('transitionend', function() { div.classList.remove("changed"); });
  return div;
}
function updateCard(div) {
  let elemId = div.cardType;
  let cnv = div.firstChild;
  renderAssetToCanvas(cnv, elemId, "");
}
function removeCards(cardContainer, count, cardType) {
  let removed = 0;
  for (let child of cardContainer.children) {
    if (removed >= count) {
      break;
    }
    if (child.cardType == cardType && !child.classList.contains("leave")) {
      removeCard(cardContainer, child);
      removed++;
    }
  }
}
function removeCard(cardContainer, div) {
  div.classList.add("leave");
  div.classList.add("changed");
  div.style.width = "0px";
  div.addEventListener('transitionend', function() { cardContainer.removeChild(div) }, {once: true});
}
function bringforward(e) {
  e.currentTarget.classList.add("selected");
  e.currentTarget.oldZ = e.currentTarget.style.zIndex;
  e.currentTarget.style.zIndex = 15;
}
function pushbackward(e) {
  e.currentTarget.classList.remove("selected");
  e.currentTarget.style.zIndex = e.currentTarget.oldZ;
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
    showResourceUI(cardType, null);
  } else {
    ws.send(JSON.stringify({type: "play_dev", card_type: cardType}));
  }
}
function showResourceUI(uiType, param) {
  let selectInfo = resourceSelectionUI[uiType];
  if (!selectInfo) {
    console.log("unknown selector " + uiType);
    return;
  }
  if (selectInfo.topPanelText) {
    let topText = formatStringWithParam(selectInfo.topPanelText, param);
    document.getElementById("topselect").style.display = 'flex';
    document.getElementById("topselecttitle").innerText = topText;
  } else {
    document.getElementById("topselect").style.display = 'none';
  }
  let bottomText = formatStringWithParam(selectInfo.bottomPanelText, param);
  document.getElementById("bottomselecttitle").innerText = bottomText;
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
  if (resourceSelectorType == "tradeOffer" && turn == myIdx) {
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
    firstMsg = true; // TODO: update this.
  }
  // data.type should be game_state now - maybe handle more later
  gameStarted = data.started;
  gameOptions = data.options;
  amHost = data.host;
  playerData = data.player_data;
  gamePhase = data.game_phase;
  let oldPhase = turnPhase;
  turnPhase = data.turn_phase;
  tiles = data.tiles;
  ports = data.ports;
  corners = data.corners;
  edges = data.edges;
  robberLoc = data.robber;
  pirateLoc = data.pirate;
  cards = data.cards;
  devCardCount = data.dev_cards;
  diceRoll = data.dice_roll;
  pieces = data.pieces;
  landings = data.landings;
  roads = data.roads;
  let oldTurn = turn;
  turn = data.turn;
  collectTurn = data.collect_idx;
  collectCounts = data.collect_counts;
  extraBuildTurn = data.extra_build_idx;
  discardPlayers = data.discard_players;
  let oldActiveOffer = tradeActiveOffer;
  tradeActiveOffer = data.trade_offer;
  counterOffers = data.counter_offers;
  robPlayers = data.rob_players;
  longestRoutePlayer = data.longest_route_player;
  largestArmyPlayer = data.largest_army_player;
  eventLog = data.event_log;
  // TODO: this is just messy. Clean up initPlayerData.
  let myOld = myIdx;
  if ("you" in data) {
    myIdx = data.you;
  } else {
    myIdx = null;
  }
  if (firstMsg) {
    centerCanvas();
    initPlayerData();
  } else if (myOld != myIdx) {
    initPlayerData();
  }
  if (myIdx != null) {
    if (document.getElementById('nameInput') != document.activeElement) {
      document.getElementById('nameInput').value = playerData[myIdx].name;
    }
    fixNameSize(null);
  }
  updateJoinWindow();
  updateCards();
  updateBuyDev();
  updateDice();
  updateEndTurn();
  updateTradeButtons();
  updatePlayerData();
  updateEventLog();
  if (firstMsg && counterOffers[myIdx]) {
    copyPreviousCounterOffer(counterOffers[myIdx]);
  }
  maybeShowActiveTradeOffer(oldActiveOffer);
  if (data.turn == myIdx && oldTurn != myIdx) {
    snd1.play();
  }
  if (oldTurn != null && oldTurn != turn) {
    hideSelectorWindow();
  }
  maybeShowCollectWindow(oldPhase);
  maybeShowDiscardWindow();
  maybeShowRobWindow();
}
function updateEndTurn() {
  let canUseButton = false;
  let button = document.getElementById("endturn");
  if (turnPhase == "extra_build" && turn != myIdx) {
    button.innerText = "End Build";
    canUseButton = (extraBuildTurn == myIdx);
  } else {
    button.innerText = "End Turn";
    canUseButton = (turn == myIdx && turnPhase == "main");
  }
  if (!canUseButton) {
    button.classList.remove("selectable");
    button.classList.add("disabled");
    button.disabled = true;
  } else {
    button.classList.add("selectable");
    button.classList.remove("disabled");
    button.disabled = false;
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
  if (turn != myIdx) {
    diceEl.classList.remove("selectable");
    diceEl.classList.add("unallowed");
  } else {
    diceEl.classList.remove("unallowed");
    diceEl.classList.add("selectable");
  }
}
function updateJoinWindow() {
  let uiJoin = document.getElementById("uijoin");
  if (gameStarted) {
    uiJoin.style.display = "none";
    return;
  }
  if (uiJoin.style.display != "flex" && document.getElementById("joinnameinput").value == "") {
    document.getElementById("joinnameinput").value = localStorage.getItem("playername") || "";
  }
  uiJoin.style.display = "flex";
  let flagOptionDiv = document.getElementById("flagoptions");
  let choiceOptionDiv = document.getElementById("choiceoptions");
  let allOptions = [];
  for (let option of gameOptions) {
    allOptions.push(option.name);
    // TODO: yes, this is hacky.
    let found = false;
    for (let elem of document.getElementsByClassName("gameoption")) {
      if (elem.optionName == option.name) {
        found = updateOptionValue(option, elem);
        break;
      }
    }
    if (found) {
      continue;
    }
    let optDiv = createOption(option);
    if (option.choices != null) {
      choiceOptionDiv.appendChild(optDiv);
    } else {
      flagOptionDiv.appendChild(optDiv);
    }
  }
  // Remove options that no longer exist.
  for (let oDiv of document.getElementsByClassName("gameoption")) {
    if (!allOptions.includes(oDiv.optionName)) {
      oDiv.parentNode.parentNode.removeChild(oDiv.parentNode);
    }
  }
  if (myIdx != null) {
    disableButton(document.getElementById("join"));
    disableButton(document.getElementById("observe"));
  }
  if (amHost) {
    enableButton(document.getElementById("start"));
  }
}
function updateOptionValue(option, elem) {
  elem.disabled = !amHost || option.forced;
  if (option.choices != null) {
    if (option.choices.includes(elem.value)) {
      if (option.value != null) {
        elem.value = option.value;
      }
      return true;
    } else {
      // Recreate any selections where the current selection is invalid.
      // TODO: need to be able to handle the option choices changing.
      elem.parentNode.parentNode.removeChild(elem.parentNode);
      return false;
    }
  }
  if (option.value != null) {
    elem.checked = option.value;
  }
  return true;
}
function createOption(option) {
  let optDiv = document.createElement("DIV");
  let elem;
  if (option.choices != null) {
    let desc = document.createElement("SPAN");
    desc.innerText = option.name + "  ";
    elem = document.createElement("SELECT");
    for (let optValue of option.choices) {
      let opt = document.createElement("OPTION");
      opt.value = optValue;
      opt.text = optValue;
      elem.appendChild(opt);
    }
    if (option.value != null) {
      elem.value = option.value;
    } else if (option.default != null) {
      elem.value = option.default;
    }
    optDiv.appendChild(desc);
    optDiv.appendChild(elem);
  } else {
    elem = document.createElement("INPUT");
    elem.type = "checkbox";
    if (option.value != null) {
      elem.checked = option.value;
    } else {
      elem.checked = option.default;
    }
    let desc = document.createElement("SPAN");
    desc.innerText = option.name;
    optDiv.appendChild(elem);
    optDiv.appendChild(desc);
  }
  elem.optionName = option.name;
  elem.disabled = !amHost || option.forced;
  elem.onchange = sendOptions;
  elem.classList.add("gameoption");
  return optDiv;
}
function observe(e) {
  document.getElementById("uijoin").style.display = "none";
}
function collectOptions() {
  let options = {};
  for (let elem of document.getElementsByClassName("gameoption")) {
    if (elem.tagName == "SELECT") {
      options[elem.optionName] = elem.value;
    } else {
      options[elem.optionName] = !!(elem.checked);
    }
  }
  return options;
}
function sendOptions(e) {
  let msg = {
    type: "options",
    options: collectOptions(),
  };
  ws.send(JSON.stringify(msg));
}
function startGame(e) {
  let msg = {
    type: "start",
    options: collectOptions(),
  };
  ws.send(JSON.stringify(msg));
}
function joinGame(e) {
  let msg = {
    type: "join",
    name: document.getElementById("joinnameinput").value,
  };
  ws.send(JSON.stringify(msg));
  localStorage.setItem("playername", document.getElementById("joinnameinput").value);
}
function rename(e) {
  let msg = {
    type: "rename",
    name: document.getElementById('nameInput').value,
  };
  ws.send(JSON.stringify(msg));
  localStorage.setItem("playername", document.getElementById("nameInput").value);
}
function takeover(e, idx) {
  let msg = {
    type: "takeover",
    player: idx,
  };
  ws.send(JSON.stringify(msg));
}
function fixNameSize(e) {
  let nameInput = document.getElementById("nameInput");
  let sizeCalculator = document.getElementById("sizeCalculator");
  if (nameInput == null || sizeCalculator == null) {
    return;
  }
  sizeCalculator.textContent = nameInput.value;
  nameInput.style.width = sizeCalculator.offsetWidth + "px";
}
function initPlayerData() {
  let rightUI = document.getElementById("uiplayer");
  while (rightUI.firstChild) {
    rightUI.removeChild(rightUI.firstChild);
  }
  for (let i = 0; i < playerData.length; i++) {
    createPlayerData(i);
  }
  fixNameSize(null);
}
function createPlayerData(i) {
  let rightUI = document.getElementById("uiplayer");
  let playerDiv = document.createElement("DIV");
  playerDiv.style.background = playerData[i].color;
  playerDiv.classList.add("playerinfo");
  for (let i of [0, 2, 4, 6]) {
    let spacer = document.createElement("DIV");
    spacer.classList.add("playerpadding");
    spacer.style.order = i;
    playerDiv.appendChild(spacer);
  }

  let username = playerData[i].name;
  let topText = document.createElement("DIV");
  topText.classList.add("playername");
  topText.style.order = 1;
  if (i == myIdx) {
    let sizeCalculator = document.createElement("SPAN");
    sizeCalculator.id = "sizeCalculator";
    sizeCalculator.classList.add("hide");
    let nameInput = document.createElement("INPUT");
    nameInput.id = "nameInput";
    nameInput.type = "text";
    // nameInput.contentEditable = true;
    nameInput.classList.add("nameinput");
    nameInput.classList.add("clickable");
    nameInput.style.background = playerData[i].color;
    nameInput.innerText = username;
    nameInput.maxlength = 16;
    nameInput.oninput = fixNameSize;
    // Setting nameInput.onfocusout does not work in webkit browsers.
    nameInput.addEventListener("focusout", rename);
    topText.appendChild(sizeCalculator);
    topText.appendChild(nameInput);
  } else {
    let nameDiv = document.createElement("DIV");
    nameDiv.innerText = username;
    nameDiv.classList.add("nametext");
    topText.appendChild(nameDiv);
    let joinButton = document.createElement("BUTTON");
    joinButton.classList.add("takeoverbutton", "button", "clickable");
    joinButton.innerText = "Take Over";
    joinButton.style.display = "none";
    joinButton.onclick = function(e) { takeover(e, i) };
    topText.appendChild(joinButton);
    if (playerData[i].disconnected) {
      nameDiv.classList.add("disconnectedplayer");
      if (myIdx == null) {
        joinButton.style.display = "inline-block";
      }
      if (!gameStarted) {
        nameDiv.innerText = "<empty slot>";
      }
    }
  }
  let turnMarker = document.createElement("DIV");
  turnMarker.innerText = "👉";  // ▶️ looks bad.
  turnMarker.classList.add("turnmarker");
  topText.appendChild(turnMarker);
  let phaseMarker = document.createElement("DIV");
  phaseMarker.innerText = "";
  phaseMarker.classList.add("phasemarker");
  topText.appendChild(phaseMarker);
  playerDiv.appendChild(topText);
  let cardDiv = document.createElement("DIV");
  cardDiv.classList.add("cardinfo");
  cardDiv.style.order = 3;
  playerDiv.appendChild(cardDiv);
  let dataDiv = document.createElement("DIV");
  dataDiv.classList.add("otherinfo");
  dataDiv.style.order = 5;
  playerDiv.appendChild(dataDiv);
  rightUI.appendChild(playerDiv);
  return playerDiv;
}
function updatePlayerData() {
  let rightUI = document.getElementById("uiplayer");
  for (let i = 0; i < playerData.length; i++) {
    let playerDiv = rightUI.children.item(i);
    if (playerDiv == null) {
      playerDiv = createPlayerData(i);
    }
    if (i != myIdx) {
      let nameDiv = playerDiv.getElementsByClassName("nametext")[0];
      let joinButton = playerDiv.getElementsByClassName("button")[0];
      nameDiv.innerText = playerData[i].name;
      if (playerData[i].disconnected) {
        nameDiv.classList.add("disconnectedplayer");
        if (!gameStarted) {
          nameDiv.innerText = "<empty slot>";
        }
      } else {
        nameDiv.classList.remove("disconnectedplayer");
      }
      if (playerData[i].disconnected && gameStarted && myIdx == null) {
        joinButton.style.display = "inline-block";
      } else {
        joinButton.style.display = "none";
      }
    }

    let turnMarker = playerDiv.getElementsByClassName("turnmarker")[0];
    let phaseMarker = playerDiv.getElementsByClassName("phasemarker")[0];
    if (!turnMarker || !phaseMarker) {  // TODO: better error checking.
      continue;
    }
    if (turn == i) {
      turnMarker.style.display = "block";
      phaseMarker.style.display = "block";
      if (gamePhase == "victory") {
        turnMarker.innerText = "🏆";
        phaseMarker.innerText = "🏆";
      } else if (turnPhase == "robber") {
        phaseMarker.innerText = "💂";
      } else if (turnPhase == "dice") {
        phaseMarker.innerText = "🎲";
      } else if (turnPhase == "main") {
        phaseMarker.innerText = "";
      } else if (turnPhase == "settle") {
        phaseMarker.innerText = "🏠";
      } else if (turnPhase == "road" || turnPhase == "dev_road") {
        phaseMarker.innerText = "🛤️";  // I didn't like 🛣️
      } else {
        // ?
        phaseMarker.innerText = "";
      }
    } else {
      turnMarker.style.display = "none";
      phaseMarker.style.display = "none";
    }
    if (turnPhase == "discard" && discardPlayers[i]) {
      phaseMarker.style.display = "block";
      phaseMarker.innerText = "🖐️";
    }
    if (turnPhase == "collect" && (collectTurn == i || (collectTurn == null && collectCounts[i]))) {
      phaseMarker.style.display = "block";
      phaseMarker.innerText = "💰";
    }
    if (turnPhase == "extra_build" && extraBuildTurn == i) {
      phaseMarker.style.display = "block";
      phaseMarker.innerText = "⚒️ ";
    }
    let cardDiv = playerDiv.getElementsByClassName("cardinfo")[0];
    updatePlayerCardInfo(i, cardDiv, false);
    let dataDiv = playerDiv.getElementsByClassName("otherinfo")[0];
    updatePlayerInfo(i, dataDiv);
  }
  fixNameSize(null);
}
function updatePlayerInfo(idx, dataDiv) {
  while (dataDiv.firstChild) {
    dataDiv.removeChild(dataDiv.firstChild);
  }
  let cardCount = document.createElement("DIV");
  cardCount.innerText = playerData[idx].resource_cards + " 🎴";
  cardCount.classList.add("otheritem");
  let points = document.createElement("DIV");
  points.innerText = playerData[idx].points + " ⭐";
  points.classList.add("otheritem");
  let armySize = document.createElement("DIV");
  let armyText = document.createElement("SPAN");
  armyText.innerText = playerData[idx].armies;
  if (idx === largestArmyPlayer) {
    armyText.style.padding = "2px";
    armyText.style.border = "2px white solid";
    armyText.style.borderRadius = "50%";
  }
  let shieldText = document.createElement("SPAN");
  shieldText.innerText = " 🛡️";
  armySize.appendChild(armyText);
  armySize.appendChild(shieldText);
  armySize.classList.add("otheritem");
  let longRoute = document.createElement("DIV");
  let routeText = document.createElement("SPAN");
  routeText.innerText = playerData[idx].longest_route;
  if (idx === longestRoutePlayer) {
    routeText.style.padding = "2px";
    routeText.style.border = "2px white solid";
    routeText.style.borderRadius = "50%";
  }
  let linkText = document.createElement("SPAN");
  linkText.innerText = " 🔗";
  longRoute.appendChild(routeText);
  longRoute.appendChild(linkText);
  longRoute.classList.add("otheritem");
  // TODO: use 👑 or 🏆?
  dataDiv.appendChild(points);
  dataDiv.appendChild(cardCount);
  dataDiv.appendChild(armySize);
  dataDiv.appendChild(longRoute);
}
function updatePlayerCardInfo(idx, cardDiv, onlyResources) {
  while (cardDiv.firstChild) {
    cardDiv.removeChild(cardDiv.firstChild);
  }
  if (!onlyResources && playerData[idx].resource_cards && playerData[idx].dev_cards) {
    let sepDiv = document.createElement("DIV");
    sepDiv.classList.add("cardseparator");
    sepDiv.style.width = summaryCardWidth / 2 + "px";
    sepDiv.style.height = summaryCardHeight + "px";
    sepDiv.style.order = 1;
    cardDiv.appendChild(sepDiv);
  }
  let orders = {resource_cards: 0, dev_cards: 2};
  let imgs = {resource_cards: "cardback", dev_cards: "devcard"};
  let typeList = ["resource_cards", "dev_cards"];
  if (onlyResources) {
    typeList = ["resource_cards"];
  }
  for (let cardType of typeList) {
    if (Number.isInteger(playerData[idx][cardType])) {
      let count = playerData[idx][cardType];
      for (let i = 0; i < count; i++) {
        addSummaryCard(cardDiv, orders[cardType], imgs[cardType], (i == count-1));
      }
    } else {
      for (cardName in playerData[idx][cardType]) {
        let count = playerData[idx][cardType][cardName]; 
        let assetName = cardName;
        if (cardType == "resource_cards") {
          assetName += "card";
        }
        for (let i = 0; i < count; i++) {
          addSummaryCard(cardDiv, orders[cardType], assetName, (i == count-1));
        }
      }
    }
  }
  if (onlyResources) {
    return;
  }
  if (longestRoutePlayer === idx) {
    addBonusCard(cardDiv, 3, "longestroute");
  }
  if (largestArmyPlayer === idx) {
    addBonusCard(cardDiv, 5, "largestarmy");
  }
}
function addSummaryCard(cardContainer, order, cardName, isLast) {
  let contDiv = document.createElement("DIV");
  contDiv.classList.add("cardback");
  contDiv.style.order = order;
  let backImg = document.createElement("CANVAS");
  backImg.width = summaryCardWidth;
  backImg.height = summaryCardHeight;
  contDiv.appendChild(backImg);
  if (isLast) {
    contDiv.style.flex = "0 0 auto";
  }
  cardContainer.appendChild(contDiv);
  renderAssetToCanvas(backImg, cardName, "");
}
function addBonusCard(cardContainer, order, cardName) {
  let sepDiv = document.createElement("DIV");
  sepDiv.classList.add("cardseparator");
  sepDiv.style.width = summaryCardWidth / 2 + "px";
  sepDiv.style.height = summaryCardHeight + "px";
  sepDiv.style.order = order;
  cardContainer.appendChild(sepDiv);
  let itemDiv = document.createElement("DIV");
  itemDiv.classList.add("cardseparator");
  itemDiv.style.order = order+1;
  cardContainer.appendChild(itemDiv);
  // TODO: cleaner way of getting the height/width of the bonus card.
  let prerendered = getAsset(cardName, "");
  if (prerendered == null) {
    return;
  }
  let cnv = document.createElement("CANVAS");
  cnv.height = summaryCardHeight;
  cnv.width = summaryCardHeight / prerendered.height * prerendered.width;
  itemDiv.appendChild(cnv);
  renderAssetToCanvas(cnv, cardName, "");
}
function createSelectors() {
  for (selectBox of ["top", "bottom"]) {
    let box = document.getElementById(selectBox + "selectbox");
    while (box.firstChild) {
      box.removeChild(box.firstChild);
    }
    for (cardRsrc of cardResources) {
      let boxCopy = selectBox;
      let rsrcCopy = cardRsrc;
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("selector");
      cnv.classList.add("clickable");
      cnv.width = selectCardWidth;
      cnv.height = selectCardHeight;
      cnv.onclick = function(e) { selectResource(e, boxCopy, rsrcCopy); };
      cnv.oncontextmenu = function(e) { deselectResource(e, boxCopy, rsrcCopy); };
      let counter = document.createElement("DIV");
      counter.innerText = "x0";
      counter.classList.add("selectcount");
      counter.classList.add("noclick");
      let container = document.createElement("DIV");
      container.classList.add("selectcontainer");
      container.classList.add(cardRsrc);
      container.appendChild(cnv);
      container.appendChild(counter);
      box.appendChild(container);
      renderAssetToCanvas(cnv, cardRsrc + "card", "");
    }
  }
}
function updateEventLog() {
  let logDiv = document.getElementById("eventlog");
  while (logDiv.firstChild) {
    logDiv.removeChild(logDiv.firstChild);
  }
  for (let e of eventLog) {
    let text = substitutePlayerName(e.text);
    logDiv.appendChild(text);
  }
  let uidiv = document.getElementById("uilog");
  uidiv.scrollTop = uidiv.scrollHeight;
}
function sizeThings() {
  let totalWidth = document.documentElement.clientWidth;
  let totalHeight = document.documentElement.clientHeight;
  document.getElementById('ui').style.width = totalWidth + "px";
  document.getElementById('ui').style.height = totalHeight + "px";
  rightWidth = document.getElementById('uiplayer').offsetWidth;
  canWidth = totalWidth - rightWidth;
  canHeight = totalHeight;
  document.getElementById('uibottom').style.width = canWidth + "px";
  document.getElementById('myCanvas').width = canWidth;
  document.getElementById('myCanvas').height = canHeight;
}
function updateBuyDev() {
  let block = document.getElementById('buydev');
  while (block.firstChild) {
      block.removeChild(block.firstChild);
  }
  block.style.width = (cardWidth + devCardCount) + "px";
  block.style.height = (cardHeight + devCardCount) + "px";
  for (let i = 0; i < devCardCount; i++) {
    let buydev = document.createElement("CANVAS");
    buydev.width = cardWidth;
    buydev.height = cardHeight;
    renderAssetToCanvas(buydev, "devcard", "");
    let offset = devCardCount - i - 1;
    buydev.style.position = "absolute";
    if (i == devCardCount-1) {
      buydev.classList.add("buyactive");
    } else {
      buydev.style.transform = "translate(" + offset + "px," + offset + "px)";
    }
    block.appendChild(buydev);
  }
  let canUse = (gamePhase == "main" && turnPhase == "main" && turn == myIdx);
  canUse = canUse || (turnPhase == "extra_build" && extraBuildTurn == myIdx);
  if (!canUse) {
    block.classList.remove("selectable");
    block.classList.add("disabled");
    block.disabled = true;
  } else {
    block.classList.add("selectable");
    block.classList.remove("disabled");
    block.disabled = false;
  }
}
function flip() {
  turned = !turned;
  if (turned) {
    document.getElementById("flipinner").classList.remove("flipnormal");
    document.getElementById("flipinner").classList.add("flipreverse");
  } else {
    document.getElementById("flipinner").classList.remove("flipreverse");
    document.getElementById("flipinner").classList.add("flipnormal");
  }
  localStorage.setItem("flipped", JSON.stringify(turned));
  centerCanvas();
}
function chooseSkin(e) {
  let chosen = document.getElementById("skinchoice").value;
  if (chosen == "null") {
    return;
  }
  if (chosen == "custom" && !localStorage.getItem("customsources") && !localStorage.getItem("customnames")) {
    window.open("/customization.html", "_blank");
    return;
  }
  localStorage.removeItem("names");
  if (chosen == "none") {
    initializeNone();
  }
  if (chosen == "space") {
    initializeSpace();
  }
  if (chosen == "custom") {
    initializeCustom();
  }
  initializeNames();
  let promise = renderImages();
  promise.then(refreshUI, showError);
}
function refreshUI() {
  createSelectors();
  updateCards();
  updateCostCard();
  updatePlayerData();
  updateBuyDev();
}
function initDefaultSkin() {
  let sources = localStorage.getItem("sources");
  if (sources == null) {
    initializeSpace();
  }
}
function init() {
  let params = new URLSearchParams(window.location.search);
  if (!params.has("game_id")) {
    showError("No game id specified.");
    return;
  }
  let gameId = params.get("game_id");
  initializeDefaults();
  initDefaultSkin();
  initializeNames();
  sizeThings();
  if (localStorage.getItem("flipped") === "true") {
    flip();
  }
  let promise = renderImages();
  promise.then(function() { continueInit(gameId); }, showError);
}
function continueInit(gameId) {
  refreshUI();
  window.requestAnimationFrame(draw);
  document.getElementById('myCanvas').onmousemove = onmove;
  document.getElementById('myCanvas').onclick = onclick;
  document.getElementById('myCanvas').onmousedown = ondown;
  document.getElementById('myCanvas').onmouseup = onup;
  document.getElementById('myCanvas').onkeydown = onkey;
  document.getElementById('myCanvas').onwheel = onwheel;
  document.body.onclick = onBodyClick;
  window.onresize = sizeThings;
  ws = new WebSocket("ws://" + window.location.hostname + ":8081/" + gameId);
  ws.onmessage = onmsg;
}
function onBodyClick(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  let hideSelector = true;
  if (resourceSelectorType == "discard" || resourceSelectorType == "collect") {
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
  let hideCoast = true;
  if (clickEdgeLocation != null) {
    let target = event.target;
    while (target != null) {
      if (target.id == "coastpopup") {
        hideCoast = false;
        break;
      }
      target = target.parentNode;
    }
    if (hideCoast) {
      cancelCoast();
    }
  }
}
function showError(errText) {
  document.getElementById("errorText").holdSeconds = 0;
  document.getElementById("errorText").style.opacity = 1.0;
  document.getElementById("errorText").innerText = errText;
}
