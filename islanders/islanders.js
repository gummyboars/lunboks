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
tradables = [...cardResources, "gold"];
devCards = ["knight", "roadbuilding", "yearofplenty", "monopoly", "palace", "chapel", "university", "library", "market"];
tradeSelectionUI = {
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
};
resourceSelectionUI = {
  monopoly: {
    topText: "Choose a resource to monopolize.",
    okText: "Monopoly!",
    cancelText: "Cancel",
  },
  yearofplenty: {
    topText: "Choose two resources to receive from the bank.",
    okText: "OK",
    cancelText: "Cancel",
  },
  collect: {
    topText: "Choose {} to collect.",
    okText: "OK",
  },
};
var snd1 = new Audio("/beep.mp3");

// The websocket
ws = null;

// Game state.
gameStarted = false;
gameOptions = {};
gameScenarios = {};
myIdx = null;
amHost = false;
colors = [];
playerData = [];
tiles = [];
tileMatrix = [];
ports = [];
corners = [];
cornerMatrix = [];
pieces = [];
pieceMatrix = [];
landings = [];
treasures = [];
edges = [];
edgeMatrix = [];
roads = [];
roadMatrix = [];
knights = [];
knightMatrix = [];
cards = {};
devCardCount = 0;
turn = null;
collectTurn = null;
collectCounts = [];
extraBuildTurn = null;
diceRoll = null;
robberLoc = null;
pirateLoc = null;
targetTile = null;
placementPort = null;
tradeOffer = null;
gamePhase = null;
turnPhase = null;
discardPlayers = {};
robPlayers = [];
treasure = null;
longestRoutePlayer = null;
largestArmyPlayer = null;

// Local state.
debug = false;
resourceSelection = {};
tradeSelectorType = null;  // values are tradeOffer, tradeBank, tradeCounterOffer
tradeSelection = {"top": {}, "bottom": {}};
tradeActiveOffer = {"want": {}, "give": {}};  // null until someone makes an offer.
counterOffers = [];
handSelection = {};
devCardType = null;  // knight, yearofplenty, roadbuilding, monopoly
draggedWin = null;
sizeTimeout = null;


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
function confirmTrade(event) {
  if (tradeSelectorType == "tradeBank") {
    let msg = {
      type: "trade_bank",
      offer: {"want": tradeSelection["top"], "give": tradeSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    return;
  } else if (tradeSelectorType == "tradeOffer") {
    let msg = {
      type: "trade_offer",
      offer: {"want": tradeSelection["top"], "give": tradeSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    return;
  } else if (tradeSelectorType == "tradeCounterOffer") {
    let msg = {
      type: "counter_offer",
      offer: {"want": tradeSelection["top"], "give": tradeSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    return;
  }
}
function clearTradeSelection(side) {
  tradeSelection[side] = {};
}
function resetTrade(event) {
  if (tradeSelectorType == "tradeCounterOffer") {
    copyActiveOffer();
    updateSelectCounts();
  } else {
    // TODO: Are there any scenarios where we wouldn't want to reset this?
    tradeSelection = {"top": {}, "bottom": {}};
    updateSelectCounts();
  }
}
function cancelTrade(event) {
  if (tradeSelectorType == "tradeCounterOffer") {
    let msg = {
      type: "counter_offer",
      offer: 0,
    };
    ws.send(JSON.stringify(msg));
    hideTradeWindow();
    return;
  } else if (tradeSelectorType == "tradeOffer") {
    clearTradeSelection("top");
    clearTradeSelection("bottom");
    let msg = {
      type: "trade_offer",
      offer: {"want": tradeSelection["top"], "give": tradeSelection["bottom"]},
    };
    ws.send(JSON.stringify(msg));
    hideTradeWindow();
  } else {
    hideTradeWindow();
  }
}
function confirmSelection(event) {
  if (turnPhase != null && turnPhase.startsWith("collect")) {
    let msg = {
      type: "collect",
      selection: resourceSelection,
    };
    ws.send(JSON.stringify(msg));
    return;
  }
  let msg = {
    type: "play_dev",
    card_type: devCardType,
    selection: resourceSelection,
  };
  ws.send(JSON.stringify(msg));
  hideSelectorWindow();
}
function clearResourceSelection() {
  resourceSelection = {};
}
function resetSelection(event) {
  resourceSelection = {};
  updateSelectCounts();
}
function cancelSelection(event) {
  if (document.getElementById("selectcancel").style.display == "none") {
    // You can't cancel collecting resources.
    return;
  } else {
    hideSelectorWindow();
  }
}
function toggleSelect(e, elemName) {
  if (discardPlayers[myIdx] == null) {
    return;
  }
  let cardType = elemName.substring(0, elemName.length - 4);
  let cardTarget = e.currentTarget;
  let count = 1;
  if (cardTarget.classList.contains("chosen")) {
    count = -1;
    cardTarget.classList.remove("chosen");
    cardTarget.classList.add("unchosen");
  } else {
    cardTarget.classList.add("chosen");
  }
  handResourceHelper(cardType, count);
}
function handResourceHelper(cardType, count) {
  let current = handSelection[cardType] || 0;
  handSelection[cardType] = current + count;
  if (handSelection[cardType] < 0) {
    handSelection[cardType] = 0;
  }
  updateHandSelection();
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
  let selections = windowName == "resource" ? resourceSelection : tradeSelection[windowName];
  let current = selections[rsrc] || 0;
  selections[rsrc] = current + num;
  if (selections[rsrc] < 0) {
    selections[rsrc] = 0;
  }
  updateSelectCounts();
}
function updateSelectCounts() {
  for (let key of ["top", "bottom", "resource"]) {
    let container = document.getElementById(key + "selectbox");
    let rsrcs = key == "resource" ? cardResources : tradables;
    for (let i = 0; i < rsrcs.length; i++) {
      let subcontainer = container.getElementsByClassName(rsrcs[i])[0];
      let counter = subcontainer.getElementsByClassName("selectcount")[0];
      let counts = key == "resource" ? resourceSelection : tradeSelection[key];
      counter.innerText = "x" + (counts[rsrcs[i]] || 0);
    }
  }
  updateSelectSummary();
  if (tradeSelectorType == "tradeCounterOffer") {
    let myOffer = {"want": tradeSelection["top"], "give": tradeSelection["bottom"]};
    if (areOffersEqual(myOffer, tradeActiveOffer, true)) {
      document.getElementById("tradeconfirm").innerText = "Accept";
    } else {
      document.getElementById("tradeconfirm").innerText = "Counter";
    }
  }
}
function updateSelectSummary() {
  // TODO: fix the width of these summary windows and don't let them make the whole
  // resource popup wider when the user selects a ridiculous number of resources.
  let summary = document.getElementById("tradesummary");
  if (tradeSelectorType != "tradeOffer" && tradeSelectorType != "tradeCounterOffer") {
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
    mySelection = {"want": tradeSelection["top"], "give": tradeSelection["bottom"]};
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
  for (let rsrc of tradables) {
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
  let counters = [];
  for (let [idx, p] of playerData.entries()) {
    counters.push({name: p.name, color: p.color, offer: counterOffers[idx]});
  }
  if (myIdx == turn) {
    let bankOffers = computeBankOffers();
    for (let off of bankOffers) {
      counters.push({name: "Bank", color: "black", offer: off});
    }
  }
  for (let [i, counterData] of counters.entries()) {
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
    namespan.innerText = counterData.name;
    namespan.style.color = counterData.color;
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
      var counterOffer = counterData.offer;
      if (counterOffer === null) {
        textspan.innerText = " is considering...";
        canAccept = false;
        showMore = false;
      } else if (!counterOffer) {
        textspan.innerText = " rejects the offer.";
        newsummary.classList.add("rejected");
        canAccept = false;
        showMore = false;
      } else if (i < playerData.length && areOffersEqual(tradeActiveOffer, counterOffer, true)) {
        // The user may change their selection without updating their offer,
        // so we make sure that the selection and the offer match the counter offer.
        let currentOffer = {want: tradeSelection["top"], give: tradeSelection["bottom"]};
        if (areOffersEqual(currentOffer, counterOffer, true)) {
          textspan.innerText = " accepts ✔️.";
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
      namespan.innerText = counterData.name;
      namespan.style.color = counterData.color;
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
      } else if (counterData.offer) {
        addSelectionToPanel(counterData.offer[leftSide], summaryLeft);
        addSelectionToPanel(counterData.offer[rightSide], summaryRight);
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
        if (i < playerData.length) {
          acceptCounter(event, playerIdx, counterData.offer);
        } else {
          let msg = {
            type: "trade_bank",
            offer: {"want": counterData.offer["give"], "give": counterData.offer["want"]},
          };
          ws.send(JSON.stringify(msg));
        }
      }
    }
    container.appendChild(newsummary);
  }
}
function computeBankOffers() {
  if (myIdx != turn) {
    return [];
  }
  let want = tradeSelection["top"];
  let give = tradeSelection["bottom"];
  let count = 0;
  for (let rsrc of cardResources) {
    count += want[rsrc] || 0;
  }
  let goldCount = want["gold"] || 0;
  if (!count && !goldCount) {
    return [];
  }
  let trades = [];
  if (!want["gold"]) {
    trades.push({rsrc: "gold", selected: (give["gold"] || 0) > 0, ratio: 2});
  }
  for (let rsrc of cardResources) {
    if ((want[rsrc] || 0) > 0) {
      continue;
    }
    trades.push({rsrc: rsrc, selected: (give[rsrc] || 0) > 0, ratio: playerData[myIdx].trade_ratios[rsrc]});
  }
  trades.sort(function(a, b) {
    if (a.selected && !b.selected) {
      return -1;
    }
    if (!a.selected && b.selected) {
      return 1;
    }
    return a.ratio - b.ratio;
  });
  let used = {};
  let available = {};
  for (let rsrc of tradables) {
    available[rsrc] = cards[rsrc] || 0;
  }
  for (let i = 0; i < count + goldCount; i++) {
    let found = false;
    for (let trade of trades) {
      let ratio = trade.ratio;
      if (i < goldCount && ratio <= 2) {  // cannot trade 2 resources for 1 gold
        ratio = playerData[myIdx].trade_ratios["default"];
      }
      if (available[trade.rsrc] >= ratio) {
        available[trade.rsrc] -= ratio;
        used[trade.rsrc] = (used[trade.rsrc] || 0) + ratio;
        found = true;
        break;
      }
    }
    if (!found) {
      return [];
    }
  }
  return [{want: used, give: Object.assign({}, want)}];
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
  if (tradeSelectorActive() && tradeSelectorType == selectorType) {
    hideTradeWindow();
  } else {
    tradeSelectorType = selectorType;
    showTradeUI();
  }
}
function hideSelectorWindow() {
  document.getElementById("resourcepopup").style.display = "none";
}
function hideTradeWindow() {
  document.getElementById("tradepopup").style.display = "none";
  updateTradeButtons();
}
function rememberActiveOffer() {
  // When the current player opens the trading UI after closing it (maybe they
  // wanted to look behind it?), we restore the trade offer that they have made.
  if (tradeActiveOffer && (tradeActiveOffer["want"] || tradeActiveOffer["give"])) {
    tradeSelection["top"] = Object.assign({}, tradeActiveOffer["want"]);
    tradeSelection["bottom"] = Object.assign({}, tradeActiveOffer["give"]);
  } else {
    clearTradeSelection("top");
    clearTradeSelection("bottom");
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
  tradeSelection["top"] = Object.assign({}, tradeActiveOffer["give"]);
  tradeSelection["bottom"] = Object.assign({}, tradeActiveOffer["want"]);
}
function copyPreviousCounterOffer(offer) {
  // This function is only called the first time the user connects, and is used
  // to restore any counter-offer they had previously made.
  tradeSelection["top"] = Object.assign({}, offer["want"]);
  tradeSelection["bottom"] = Object.assign({}, offer["give"]);
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
  if (!tradeSelectorActive()) {
    shouldCopy = true;
  }
  // If they haven't touched the trade offer and haven't made a counter offer, update it.
  if (!counterOffers[myIdx] && areOffersEqual(oldActiveOffer, {want: tradeSelection["top"], give: tradeSelection["bottom"]}, true)) {
    shouldCopy = true;
  }
  // If they have no selection (e.g. if the window was already open when the offer was made),
  // then we should show them the new offer.
  if (!Object.keys(tradeSelection["top"]) && !Object.keys(tradeSelection["bottom"])) {
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
      tradeSelectorType = "tradeCounterOffer";
      showTradeUI();
    }
  } else {
    hideTradeWindow();
  }
}
function updateTradeButtons() {
  let playerButton = document.getElementById("tradeplayer");
  let bankButton = document.getElementById("tradebank");
  if (tradeSelectorActive()) {
    let activeButton = null;
    let inactiveButton = null;
    if (tradeSelectorType == "tradeBank") {
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
  let collectText = null;
  if (turnPhase == "collect" && (collectTurn == myIdx || (collectTurn == null && collectCounts[myIdx]))) {
    collectText = collectCounts[myIdx] + " resources";
  }
  if (turn == myIdx) {
    if (turnPhase == "collect1") {
      collectText = "1 resource";
    } else if (turnPhase == "collect2") {
      collectText = "2 resources";
    } else if (turnPhase == "collectpi") {
      collectText = "1 " + serverNames["rsrc1"] + ", " + serverNames["rsrc3"] + ", or " + serverNames["rsrc4"];
    }
  }
  if (collectText != null) {
    if (oldPhase != turnPhase) {
      // Clear selection counts only if we just popped the window up.
      clearResourceSelection();
      updateSelectCounts();
    }
    showResourceUI("collect", collectText);
  } else if (["collect1", "collect2", "collectpi", "collect"].includes(oldPhase)) {
    hideSelectorWindow();
  }
}
function maybeShowDiscardWindow() {
  if (turnPhase == "discard" && discardPlayers[myIdx]) {
    showHandSelect(discardPlayers[myIdx]);
  } else {
    handSelection = {};
    hideHandSelect();
  }
}
function showHandSelect(count) {
  let topText = formatStringWithParam("Choose {} cards to discard.", count);
  document.getElementById("handselecttitle").innerText = topText;
  document.getElementById("handpopup").style.display = "flex";
  updateHandSelection();
}
function hideHandSelect() {
  document.getElementById("handpopup").style.display = "none";
  let toDeselect = [];
  for (let elem of document.getElementsByClassName("chosen")) {
    toDeselect.push(elem);
  }
  for (let elem of toDeselect) {
    elem.classList.remove("chosen");
  }
}
function updateHandSelection() {
  let container = document.getElementById("handselectcards");
  while (container.children.length) {
    container.removeChild(container.firstChild);
  }
  let total = 0;
  for (let [ordering, rsrc] of cardResources.entries()) {
    for (let i = 0; i < handSelection[rsrc] || 0; i++) {
      addHandCard(container, rsrc, ordering);
      total++;
    }
  }
  if (total == discardPlayers[myIdx]) {
    enableButton(document.getElementById("handok"));
  } else {
    disableButton(document.getElementById("handok"));
  }
}
function addHandCard(parentNode, rsrc, ordering) {
  let cnv = document.createElement("CANVAS");
  cnv.width = selectCardWidth;
  cnv.height = selectCardHeight;
  cnv.style.display = "block";
  cnv.classList.add("selector");
  let div = document.createElement("DIV");
  div.style.width = cnv.width + "px";
  div.style.height = cnv.height + "px";
  div.style.order = ordering;
  div.appendChild(cnv);
  parentNode.appendChild(div);
  renderAssetToCanvas(cnv, rsrc + "card", "");
}
function okHandSelection(e) {
  let msg = {
    type: "discard",
    selection: handSelection,
  };
  ws.send(JSON.stringify(msg));
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
function maybeShowBuryWindow() {
  if (turn != myIdx || turnPhase != "bury") {
    document.getElementById("burypopup").style.display = "none";
    return;
  }
  document.getElementById("burypopup").style.display = "flex";
  let div = document.getElementById("treasure");
  while (div.children.length) {
    div.removeChild(div.firstChild);
  }
  let cnv = document.createElement("CANVAS");
  cnv.width = cardWidth;
  cnv.height = cardHeight;
  cnv.style.display = "block";
  div.appendChild(cnv);
  if (treasure == "collect1") {
    renderAssetToCanvas(cnv, "cardback", "");
  }
  if (treasure == "collect2") {
    renderAssetToCanvas(cnv, "cardback", "");
    let cnv2 = document.createElement("CANVAS");
    cnv2.width = cardWidth;
    cnv2.height = cardHeight;
    cnv2.style.display = "block";
    div.appendChild(cnv2);
    renderAssetToCanvas(cnv2, "cardback", "");
  }
  if (treasure == "collectpi") {
    let cnt = document.createElement("DIV");
    cnt.style.width = 1.5*cardWidth + "px";
    cnt.style.maxWidth = 1.5*cardWidth + "px";
    cnt.style.height = 1.5*cardHeight + "px";
    cnt.style.position = "relative";
    cnt.style.display = "block";
    div.appendChild(cnt);
    cnt.appendChild(cnv);
    renderAssetToCanvas(cnv, "rsrc1card", "");
    cnv.style.position = "absolute";
    cnv.style.top = "0";
    cnv.style.left = "0";
    let cnv2 = document.createElement("CANVAS");
    cnv2.width = cardWidth;
    cnv2.height = cardHeight;
    cnv2.style.display = "block";
    cnt.appendChild(cnv2);
    renderAssetToCanvas(cnv2, "rsrc3card", "");
    cnv2.style.position = "absolute";
    cnv2.style.top = "0";
    cnv2.style.right = "0";
    let cnv3 = document.createElement("CANVAS");
    cnv3.width = cardWidth;
    cnv3.height = cardHeight;
    cnv3.style.display = "block";
    cnt.appendChild(cnv3);
    renderAssetToCanvas(cnv3, "rsrc4card", "");
    cnv3.style.position = "absolute";
    cnv3.style.bottom = "0";
    cnv3.style.left = "16.66%";
  }
  if (treasure == "dev_road") {
    renderAssetToCanvas(cnv, "roadbuilding", "");
  }
  if (treasure == "takedev") {
    renderAssetToCanvas(cnv, "devcard", "");
  }
}
function buryTreasure(e) {
  let msg = {
    type: "bury",
  };
  ws.send(JSON.stringify(msg));
}
function useTreasure(e) {
  let msg = {
    type: "treasure",
  };
  ws.send(JSON.stringify(msg));
}
function maybeShowPortWindow() {
  if (turn != myIdx || turnPhase != "placeport") {
    document.getElementById("portpopup").style.display = "none";
    return;
  }
  document.getElementById("portpopup").style.display = "flex";
  if (placementPort != null) {
    document.getElementById("portselect").style.display = "none";
    document.getElementById("portselecttitle").innerText = "Place the " + serverNames[placementPort] + " port";
  } else {
    document.getElementById("portselect").style.display = "flex";
    document.getElementById("portselecttitle").innerText = "Choose a port to place";
  }
  let div = document.getElementById("portselect");
  while (div.children.length) {
    div.removeChild(div.firstChild);
  }
  let portList = [];
  for (let port of ports) {
    portList.push(port.port_type);
  }
  for (let rsrc of cardResources) {
    if (portList.includes(rsrc)) {
      continue;
    }
    let cnv = document.createElement("CANVAS");
    cnv.width = tileWidth;
    cnv.height = tileHeight;
    cnv.style.display = "block";
    cnv.classList.add("selectable");
    cnv.onclick = function(e) { placementPort = rsrc; maybeShowPortWindow(); };
    div.appendChild(cnv);
    let loc = [2, 1];
    let rot = 0;
    if (turned) {
      loc = [-2 * tileHeight / tileWidth, tileWidth / tileHeight];
      rot = 1.5;
    }
    let tmpPort = {port_type: rsrc, location: loc, rotation: rot};
    let tmpTile = {tile_type: "space", location: loc, rotation: rot};
    let ctx = cnv.getContext("2d");
    drawTile(tmpTile, ctx);
    drawPort(tmpPort, ctx);
  }
}
function maybeShowStatusPopup() {
  let statusPopup = document.getElementById("statuspopup");
  if (turn != myIdx || !["knight", "fastknight", "treason", "intrigue", "move_knights", "discard"].includes(turnPhase)) {
    statusPopup.style.display = "none";
    return;
  }
  if (turnPhase == "discard") {
    if (!discardPlayers[myIdx]) {
      statusPopup.style.display = "flex";
      statusPopup.innerText = "Waiting for players to discard";
      return;
    }
    statusPopup.style.display = "none";
    return;
  }
  statusPopup.style.display = "flex";
  if (turnPhase == "knight") {
    statusPopup.innerText = "Place a knight next to the castle";
  } else if (turnPhase == "fastknight") {
    statusPopup.innerText = "Place a knight on the board";
  } else if (turnPhase == "intrigue") {
    statusPopup.innerText = "Choose a barbarian to capture";
  } else if (turnPhase == "move_knights") {
    statusPopup.innerText = "Move your knights";
  } else if (turnPhase == "treason") {
    if (moveBarbarianTiles.length == 0) {
      if (barbarianFromCount == 2) {
        statusPopup.innerText = "Choose two barbarians to move";
      } else if (barbarianFromCount == 1) {
        statusPopup.innerText = "Choose one barbarian to move";
      }
    } else if (moveBarbarianTiles.length == 1) {
      if (barbarianFromCount == 2) {
        statusPopup.innerText = "Choose one more barbarian to move";
      } else if (barbarianFromCount == 1) {
        statusPopup.innerText = "Choose one barbarian to move";
      }
    } else if (moveBarbarianTiles.length == 2) {
      if (barbarianToCount == 2) {
        statusPopup.innerText = "Choose two tiles to move barbarians to";
      } else if (barbarianToCount == 1) {
        statusPopup.innerText = "Choose where to move the barbarian to";
      }
    } else if (moveBarbarianTiles.length == 3) {
      if (barbarianToCount == 2) {
        statusPopup.innerText = "Choose one more tile to move barbarians to";
      } else if (barbarianToCount == 1) {
        statusPopup.style.display = "none";
      }
    }
  }
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
  let end = "end_turn";
  if (turnPhase == "move_knights") {
    end = "end_move_knights";
  }
  if (turnPhase == "extra_build") {
    end = "end_extra_build";
  }
  let msg = {type: end};
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
  let container = document.getElementById("uicards");
  cfgs = [
    {
      clist: cardResources,
      clickAction: toggleSelect,
      suffix: "card",
    },
    {
      clist: ["gold"],
      clickAction: null,
      suffix: "card",
    },
    {
      clist: devCards,
      clickAction: playDevCard,
      suffix: "",
    }
  ];
  for (let child of container.children) {
    child.classList.remove("shown");
  }
  let oldCards = {};
  let ordering = 0;
  for (cfg of cfgs) {
    for (let cardType of cfg.clist) {
      let cardCount = cards[cardType] || 0;
      oldCards[cardType] = countOldCards(container, cardType + cfg.suffix);
      for (i = 0; i < cardCount - oldCards[cardType]; i++) {
        addCard(container, cardType + cfg.suffix, ordering, cfg.clickAction);
      }
      removeCards(container, oldCards[cardType] - cardCount, cardType + cfg.suffix);
      ordering++;
    }
  }
  for (let child of container.children) {
    updateCard(child);
  }
  let maxOrder = {"card": 0, "token": 0, "dev": 0};
  let maxChild = {"card": null, "token": null, "dev": null};
  for (let child of container.children) {
    let cardType = "card";
    if (parseInt(child.style.order) >= cardResources.length + 1) {
      cardType = "dev";
    } else if (parseInt(child.style.order) >= cardResources.length) {
      cardType = "token";
    }
    if (parseInt(child.style.order) >= maxOrder[cardType] && !child.classList.contains("leave")) {
      maxOrder[cardType] = parseInt(child.style.order);
      maxChild[cardType] = child;
    }
  }
  for (let cardType in maxChild) {
    if (maxChild[cardType] != null) {
      maxChild[cardType].classList.add("shown");
    }
  }

  let spendCount = 0;
  for (let knight of knights) {
    if (knight.player == myIdx && knight.movement < 0) {
      spendCount++;
    }
  }
  for (let child of container.children) {
    if (spendCount > 0 && child.cardType == "rsrc3card" && !child.classList.contains("leave")) {
      child.classList.add("spend");
      spendCount--;
    } else {
      child.classList.remove("spend");
    }
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
function addCard(cardContainer, elemId, ordering, clickAction) {
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
  if (clickAction) {
    div.onclick = function(e) {
      clickAction(e, elemId);
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
  // Prioritize removing the chosen cards over random cards. This happens for trades, playing
  // dev cards, and discarding cards.
  for (let child of cardContainer.children) {
    if (removed >= count) {
      break;
    }
    if (child.cardType == cardType && child.classList.contains("chosen")) {
      removeCard(cardContainer, child);
      removed++;
    }
  }
  // Remove the first card(s) of the given type. Happens when the player is robbed, or loses
  // cards to a monopoly, or buys something.
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
  if (e.currentTarget.classList.contains("unchosen")) {
    e.currentTarget.classList.remove("unchosen");
  }
  // TODO: change z-index only when player is not selecting cards.
  e.currentTarget.classList.add("hovered");
  e.currentTarget.oldZ = e.currentTarget.style.zIndex;
  e.currentTarget.style.zIndex = 15;
}
function pushbackward(e) {
  e.currentTarget.classList.remove("hovered");
  e.currentTarget.style.zIndex = e.currentTarget.oldZ;
}
function buyDevCard() {
  ws.send(JSON.stringify({type: "buy_dev"}));
}
function playDevCard(e, cardType) {
  devCardType = cardType;
  let selectInfo = resourceSelectionUI[cardType];
  if (selectInfo) {
    clearResourceSelection();
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
  document.getElementById("resourceselecttitle").innerText = formatStringWithParam(selectInfo.topText, param);
  let buttons = {"okText": "selectconfirm", "resetText": "selectreset", "cancelText": "selectcancel"};
  for (let button in buttons) {
    if (selectInfo[button]) {
      document.getElementById(buttons[button]).innerText = selectInfo[button];
      document.getElementById(buttons[button]).style.display = "inline-block";
    } else {
      document.getElementById(buttons[button]).style.display = "none";
    }
  }
  updateSelectCounts();
  document.getElementById("resourcepopup").style.display = "flex";
}
function showTradeUI() {
  let selectInfo = tradeSelectionUI[tradeSelectorType];
  document.getElementById("topselecttitle").innerText = selectInfo.topPanelText;
  document.getElementById("bottomselecttitle").innerText = selectInfo.bottomPanelText;
  let buttons = {"okText": "tradeconfirm", "resetText": "tradereset", "cancelText": "tradecancel"};
  for (let button in buttons) {
    document.getElementById(buttons[button]).innerText = selectInfo[button];
  }
  if (tradeSelectorType == "tradeOffer" && turn == myIdx) {
    rememberActiveOffer();
  }
  updateSelectCounts();
  document.getElementById("tradepopup").style.display = 'flex';
  updateTradeButtons();
}
function tradeSelectorActive() {
  return document.getElementById("tradepopup").style.display == "flex";
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
  gameScenarios = data.scenario;
  colors = data.colors ?? [];
  amHost = data.host;
  playerData = data.player_data;
  gamePhase = data.game_phase;
  let oldPhase = turnPhase;
  turnPhase = data.turn_phase;
  updateElems(tiles, tileMatrix, data.tiles);
  ports = data.ports;
  updateElems(corners, cornerMatrix, data.corners);
  updateElems(edges, edgeMatrix, data.edges);
  robberLoc = data.robber;
  pirateLoc = data.pirate;
  targetTile = data.target_tile;
  cards = data.cards;
  devCardCount = data.dev_cards;
  diceRoll = data.dice_roll;
  updateElems(pieces, pieceMatrix, data.pieces);
  landings = data.landings;
  treasures = data.treasures;
  updateElems(roads, roadMatrix, data.roads);
  updateElems(knights, knightMatrix, data.knights);
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
  treasure = data.treasure;
  barbarianFromCount = data.from_count ?? 0;
  barbarianToCount = data.to_count ?? 0;
  longestRoutePlayer = data.longest_route_player;
  largestArmyPlayer = data.largest_army_player;
  eventLog = data.event_log;
  let [oldMin, oldMax] = [minCoord, maxCoord];
  [minCoord, maxCoord] = getTileMinMax(true);
  if (oldMin.x != minCoord.x || oldMin.y != minCoord.y || oldMax.x != maxCoord.x || oldMax.y != maxCoord.y) {
    remakeGrid();
    centerCanvas();
  }
  // TODO: this is just messy. Clean up initPlayerData.
  let myOld = myIdx;
  if ("you" in data) {
    myIdx = data.you;
  } else {
    myIdx = null;
  }
  if (firstMsg) {
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
  updateSelectors();
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
    hideTradeWindow();
  }
  maybeShowCollectWindow(oldPhase);
  maybeShowDiscardWindow();
  maybeShowRobWindow();
  maybeShowBuryWindow();
  maybeShowPortWindow();
  maybeShowStatusPopup();
  document.getElementById("grid").classList.toggle("myturn", data.turn == myIdx);
  document.getElementById("grid").classList.toggle("tileselect", ["robber", "expel", "deplete"].includes(turnPhase));
  draw();
}
function updateElems(origElems, elemMatrix, newElems) {
  let compareLocations = function(elemA, elemB) {
    if (elemA.location.length != elemB.location.length) {
      return elemA.location.length - elemB.location.length;  // Should never happen
    }
    for (let i = 0; i < elemA.location.length; i++) {
      if (elemA.location[i] != elemB.location[i]) {
        return elemA.location[i] - elemB.location[i];
      }
    }
    return 0;
  };
  newElems.sort(compareLocations);
  let i = 0;
  let j = 0;
  while (i < origElems.length || j < newElems.length) {
    let comp;
    if (i >= origElems.length) {
      comp = 1;
    } else if (j >= newElems.length) {
      comp = -1;
    } else {
      comp = compareLocations(origElems[i], newElems[j])
    }
    if (comp == 0) {  // In place update
      let [x, y] = coordsFromElem(newElems[j]);
      elemMatrix[x][y] = newElems[j];
      i++;
      j++;
      continue;
    }
    if (comp < 0) {  // Exists in old but not in new
      let [x, y] = coordsFromElem(origElems[i]);
      elemMatrix[x][y] = undefined;
      i++;
      continue;
    }
    if (comp > 0) {  // Exists in new but not in old
      let [x, y] = coordsFromElem(newElems[j]);
      if (elemMatrix[x] == null) {
        elemMatrix[x] = [];
      }
      elemMatrix[x][y] = newElems[j];
      j++;
      continue;
    }
  }
  origElems.splice(0, origElems.length, ...newElems)
}
function updateEndTurn() {
  let canUseButton = false;
  let button = document.getElementById("endturn");
  if (turnPhase == "extra_build" && turn != myIdx) {
    button.innerText = "End Build";
    canUseButton = (extraBuildTurn == myIdx);
  } else if (turnPhase == "move_knights" && turn == myIdx) {
    button.innerText = "Done";
    canUseButton = true;
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
  updateJoinColors();
  let scenarioSelect = document.getElementById("scenario");
  if (!scenarioSelect.children.length) {
    for (let scenarioName of gameScenarios.choices) {
      let opt = document.createElement("OPTION");
      opt.value = scenarioName;
      opt.text = scenarioName;
      scenarioSelect.appendChild(opt);
    }
  }
  document.getElementById("randomslider").optionName = "randomness";
  scenarioSelect.value = gameScenarios.value;
  scenarioSelect.disabled = !amHost;
  let flagOptionDiv = document.getElementById("flagoptions");
  let choiceOptionDiv = document.getElementById("choiceoptions");
  for (let optionName in gameOptions) {
    let option = gameOptions[optionName];
    if (option.hidden) {
      continue;
    }
    if (optionName == "randomness") {
      document.getElementById("randomslider").disabled = !amHost || option.forced;
      document.getElementById("randomslider").value = option.value;
      setRandomness(option.value);
      continue;
    }
    // TODO: yes, this is hacky.
    let found = false;
    for (let elem of document.getElementsByClassName("gameoption")) {
      if (elem.optionName == optionName) {
        found = updateOptionValue(option, elem);
        break;
      }
    }
    if (found) {
      continue;
    }
    let optDiv = createOption(optionName, option);
    if (option.choices != null) {
      choiceOptionDiv.appendChild(optDiv);
    } else {
      flagOptionDiv.appendChild(optDiv);
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
function updateJoinColors() {
  let joinColor = document.getElementById("joincolor");
  let ul = document.getElementById("colorlist");
  let toDelete = [];
  let found = [];
  for (let opt of ul.children) {
    if (opt.color == null) {  // random
      opt.style.order = colors.length;
      opt.onclick = function(e) { chooseColor(null); };
      continue;
    }
    let idx = colors.indexOf(opt.color);
    if (idx < 0) {
      toDelete.push(opt);
    } else {
      opt.style.order = idx;
      found.push(opt.color);
    }
  }
  for (let c of colors) {
    if (!found.includes(c)) {
      let opt = document.createElement("LI");
      opt.classList.add("coloritem");
      opt.color = c;
      let inner = document.createElement("DIV");
      inner.classList.add("innercolor");
      inner.style.backgroundColor = c;
      opt.appendChild(inner);
      ul.appendChild(opt);
      opt.onclick = function(e) { chooseColor(c); };
    }
  }
  for (let d of toDelete) {
    ul.removeChild(d);
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
function createOption(optionName, option) {
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
  elem.optionName = optionName;
  elem.disabled = !amHost || option.forced;
  elem.onchange = sendOptions;
  elem.classList.add("gameoption");
  return optDiv;
}
function setRandomness(value) {
  if (value == 36) {
    document.getElementById("randomvalue").value = "∞";
  } else {
    document.getElementById("randomvalue").value = value;
  }
}
function observe(e) {
  document.getElementById("uijoin").style.display = "none";
}
function collectOptions() {
  let options = {};
  for (let elem of document.getElementsByClassName("gameoption")) {
    if (elem.tagName == "SELECT" || elem.optionName == "randomness") {
      let numericVal = parseInt(elem.value);
      if (Number.isNaN(numericVal)) {
        options[elem.optionName] = elem.value;
      } else {
        options[elem.optionName] = numericVal;
      }
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
function changeScenario(e) {
  let msg = {
    type: "scenario",
    scenario: document.getElementById("scenario").value,
  };
  ws.send(JSON.stringify(msg));
}
function toggleColor(e) {
  document.getElementById("joincolor").classList.toggle("selected");
}
function chooseColor(color) {
  let joinDiv = document.getElementById("joincolor");
  joinDiv.color = color;
  for (child of joinDiv.children) {
    if (child.classList.contains("innercolor")) {
      joinDiv.removeChild(child);
    }
  }
  if (color == null) {
    document.getElementById("colortext").style.display = "flex";
    if (myIdx != null) {
      joinGame(null);
    }
    return;
  }
  document.getElementById("colortext").style.display = "none";
  let inner = document.createElement("DIV");
  inner.classList.add("innercolor");
  inner.style.backgroundColor = color;
  document.getElementById("joincolor").appendChild(inner);
  if (myIdx != null) {
    joinGame(null);
  }
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
    color: document.getElementById("joincolor").color,
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
    playerDiv.style.background = playerData[i].color;
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
    } else {
      document.getElementById("nameInput").style.background = playerData[i].color;
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
      } else if (["robber", "rob", "expel", "knight", "fastknight"].includes(turnPhase)) {
        phaseMarker.innerText = "💂";
      } else if (turnPhase == "deplete") {
        phaseMarker.innerText = "🔃";
      } else if (turnPhase == "move_knights") {
        phaseMarker.innerText = "👣";
      } else if (turnPhase == "intrigue") {
        phaseMarker.innerText = "🎭";
      } else if (turnPhase == "treason") {
        phaseMarker.innerText = "🗡️";
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
  armyText.innerText = playerData[idx].armies || playerData[idx].captured_barbarians || 0;
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
  let numSeparators = 0;
  if (!onlyResources) {
    numSeparators += playerData[idx].resource_cards ? 1 : 0;
    numSeparators += playerData[idx].gold ? 1 : 0;
    numSeparators += playerData[idx].dev_cards ? 1 : 0;
    numSeparators -= 1;
  }
  for (let i = 0; i < numSeparators; i++) {
    let sepDiv = document.createElement("DIV");
    sepDiv.classList.add("cardseparator");
    sepDiv.style.width = summaryCardWidth / 2 + "px";
    sepDiv.style.height = summaryCardHeight + "px";
    sepDiv.style.order = 2*i + 1;
    cardDiv.appendChild(sepDiv);
  }
  let orders = {resource_cards: 0, gold: 2, dev_cards: 4};
  let imgs = {resource_cards: "cardback", gold: "goldcard", dev_cards: "devcard"};
  let typeList = ["resource_cards", "gold", "dev_cards"];
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
    addBonusCard(cardDiv, 5, "longestroute");
  }
  if (largestArmyPlayer === idx) {
    addBonusCard(cardDiv, 7, "largestarmy");
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
function windown(e) {
  if (e.button != 0) {
    return;
  }
  if (["SELECT", "OPTION", "INPUT", "BUTTON", "CANVAS"].includes(e.target.tagName)) {
    return;
  }
  let current = e.target;
  while (current != null) {
    if (!current.classList) {
      break;
    }
    if (current.classList.contains("selectsummary")) {
      return;
    }
    current = current.parentNode;
  }
  draggedWin = e.currentTarget;
  if (e.currentTarget.dX == null) {
    e.currentTarget.dX = 0;
    e.currentTarget.dY = 0;
  }
  e.currentTarget.startX = e.clientX - e.currentTarget.dX;
  e.currentTarget.startY = e.clientY - e.currentTarget.dY;
}
function bodyup(e) {
  canvasup(e);
  if (e.button != 0) {
    return;
  }
  if (draggedWin == null) {
    return;
  }
  let offsetX = e.clientX - draggedWin.startX;
  let offsetY = e.clientY - draggedWin.startY;
  draggedWin.dX = offsetX;
  draggedWin.dY = offsetY;
  draggedWin.style.transform = "translate(" + offsetX + "px, " + offsetY + "px)"
  draggedWin = null;
}
function winmove(e) {
  if (draggedWin == null) {
    return;
  }
  let offsetX = e.clientX - draggedWin.startX;
  let offsetY = e.clientY - draggedWin.startY;
  draggedWin.style.transform = "translate(" + offsetX + "px, " + offsetY + "px)"
}
function createSelectors() {
  for (let selectBox of ["top", "bottom", "resource"]) {
    let box = document.getElementById(selectBox + "selectbox");
    while (box.firstChild) {
      box.removeChild(box.firstChild);
    }
    let rsrcs = selectBox == "resource" ? cardResources : tradables;
    for (let cardRsrc of rsrcs) {
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("selector");
      cnv.classList.add("clickable");
      cnv.width = selectCardWidth;
      cnv.height = selectCardHeight;
      cnv.onclick = function(e) { selectResource(e, selectBox, cardRsrc); };
      cnv.oncontextmenu = function(e) { deselectResource(e, selectBox, cardRsrc); };
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
function updateSelectors() {
  for (let selectBox of ["top", "bottom"]) {
    let box = document.getElementById(selectBox + "selectbox");
    let goldDiv = box.getElementsByClassName("gold")[0];
    if (gameOptions["gold"] != null && gameOptions["gold"].value) {
      goldDiv.style.display = "flex";
    } else {
      goldDiv.style.display = "none";
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
function resizeThings() {
  clearTimeout(sizeTimeout);
  sizeTimeout = setTimeout(sizeThings, 255);
}
function sizeThings() {
  canWidth = document.getElementById("uioverlay").offsetWidth;
  canHeight = document.getElementById("uioverlay").offsetHeight;
  document.getElementById("myCanvas").width = canWidth;
  document.getElementById("myCanvas").height = canHeight;
  if (myIdx != null) {
    fixNameSize(null);
  }
  moveGrid();
  draw();
}
function updateBuyDev() {
  let block = document.getElementById('buydev');
  while (block.firstChild) {
      block.removeChild(block.firstChild);
  }
  block.style.width = (cardWidth + devCardCount) + "px";
  block.style.height = (cardHeight + devCardCount) + "px";
  let totalCount = devCardCount;
  let topDev = null;
  if (["knight", "fastknight", "treason", "intrigue"].includes(turnPhase)) {
    totalCount += 1;
    topDev = turnPhase;
    if (turnPhase == "treason" && turn == myIdx) {
      if (barbarianFromCount <= 1) {
        moveBarbarianTiles[0] = null;
        if (barbarianFromCount <= 0) {
          moveBarbarianTiles[1] = null;
        }
      }
    }
  }
  for (let i = 0; i < totalCount; i++) {
    let buydev = document.createElement("CANVAS");
    buydev.width = cardWidth;
    buydev.height = cardHeight;
    let asset = "devcard";
    if (i == totalCount-1 && topDev != null) {
      asset = topDev;
    }
    renderAssetToCanvas(buydev, asset, "");
    let offset = totalCount - i - 1;
    buydev.style.position = "absolute";
    if (i == totalCount-1 && topDev == null) {
      buydev.classList.add("buyactive");
    } else if (i != totalCount-1) {
      buydev.style.transform = "translate(" + offset + "px," + offset + "px)";
    }
    block.appendChild(buydev);
  }
  let canUse = (gamePhase == "main" && turnPhase == "main" && turn == myIdx);
  canUse = canUse || (turnPhase == "extra_build" && extraBuildTurn == myIdx);
  if (canUse || topDev != null) {
    block.classList.add("selectable");
    block.classList.remove("disabled");
    block.disabled = false;
  } else {
    block.classList.remove("selectable");
    block.classList.add("disabled");
    block.disabled = true;
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
  draw();
}
function chooseSkin(e) {
  let chosen = document.getElementById("skinchoice").value;
  if (chosen == "null") {
    return;
  }
  if (chosen == "custom" && !localStorage.getItem("islanderscustomimageinfo") && !localStorage.getItem("islanderscustomnames")) {
    window.open("/customization.html", "_blank");
    return;
  }
  if (!skinInitializers[chosen]) {
    console.log("Unknown skin " + chosen);
    return;
  }
  localStorage.removeItem("islandersnames");
  skinInitializers[chosen]();
  initializeNames();
  let promise = renderImages();
  promise.then(refreshUI, showError);
}
function refreshUI() {
  createSelectors();
  updateCards();
  updateHandSelection();
  updateCostCard();
  updatePlayerData();
  updateBuyDev();
}
function createSkinOptions() {
  let select = document.getElementById("skinchoice");
  let customOption = null;
  for (let skin in skinInitializers) {
    let option = document.createElement("OPTION");
    option.value = skin;
    option.text = skinNames[skin] ?? skin;
    select.appendChild(option);
    if (skin == "custom") {
      customOption = option;
    }
  }
  // hack: re-append the custom option to put it at the bottom
  if (customOption) {
    select.appendChild(customOption);
  }
}
function initDefaultSkin() {
  let imgInfo = localStorage.getItem("islandersimageinfo");
  if (imgInfo == null) {
    initializeNone();
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
  createSkinOptions();
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
  draw();
  document.getElementById('myCanvas').onmousemove = onmove;
  document.getElementById('myCanvas').onclick = onclick;
  document.getElementById('myCanvas').onmousedown = ondown;
  document.getElementById('myCanvas').onkeydown = onkey;
  document.getElementById('myCanvas').onwheel = onwheel;
  document.body.onclick = onBodyClick;
  window.onresize = resizeThings;
  ws = new WebSocket("ws://" + window.location.hostname + ":8081/" + gameId);
  ws.onmessage = onmsg;
}
function onBodyClick(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  let hideSelector = true;
  let hideTrade = true;
  if (document.getElementById("selectcancel").style.display == "none") {
    hideSelector = false;
  }
  let target = event.target;
  while (target != null) {
    if (target.id == "resourcepopup") {
      hideSelector = false;
    }
    if (target.id == "tradepopup") {
      hideTrade = false;
    }
    if (target.classList && target.classList.contains("resourceselector")) {
      hideSelector = false;
      hideTrade = false;
      break;
    }
    target = target.parentNode;
  }
  if (hideSelector) {
    hideSelectorWindow();
  }
  if (hideTrade) {
    hideTradeWindow();
  }
}
function showError(errText) {
  document.getElementById("errorText").holdSeconds = 0;
  document.getElementById("errorText").style.opacity = 1.0;
  document.getElementById("errorText").innerText = errText;
}
skinInitializers = {
  "none": initializeNone,
  "space": initializeSpace,
  "custom": initializeCustom,
};
skinNames = {
  "none": "None",
  "space": "Space Explorer",
  "custom": "Custom",
};
