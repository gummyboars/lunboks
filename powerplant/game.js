ws = null;
runningAnim = [];
messageQueue = [];
// Keep track of resources.
resourceCounts = {"coal": 0, "oil": 0, "gas": 0, "uranium": 0};
totalCounts = {"coal": 24, "oil": 24, "gas": 24, "uranium": 12};
// Keep track of player city counts.
playerCityCounts = [];
// Supply rate constant
supplyRates = [
  null,
  null,
  {"coal": [3, 4, 3], "oil": [2, 2, 4], "gas": [1, 2, 3], "uranium": [1, 1, 1]},
  {"coal": [4, 5, 3], "oil": [2, 3, 4], "gas": [1, 2, 3], "uranium": [1, 1, 1]},
  {"coal": [5, 6, 4], "oil": [3, 4, 5], "gas": [2, 3, 4], "uranium": [1, 2, 2]},
  {"coal": [5, 7, 5], "oil": [4, 5, 6], "gas": [3, 3, 5], "uranium": [2, 3, 2]},
  {"coal": [7, 9, 6], "oil": [5, 6, 7], "gas": [3, 5, 6], "uranium": [2, 3, 3]},
];
// Keep track of phase transitions.
oldPhase = null;
oldDiscard = null;
hasBurned = false;
canBurn = false;
regionsDone = false;
// Keep track of the auction.
bidPlant = null;
pendingPlant = null;
plantDivs = [];
// For updating cities in-place.
cityDivs = {};
connDivs = {};
// For figuring out which connections to highlight.
chosenColors = [];
// For swapping resources between plants.
dragged = null;
draggedFrom = null;
// Setting a small delay on expanded windows disappearing when the mouse leaves.
expandId = null;

isDragging = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;
boardScale = 1;

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
  moveBoard();
  renderAssetToDiv(document.getElementById("payments"), "payments");
  renderAssetToDiv(document.getElementById("board"), "Germany");
  renderAssetToDiv(document.getElementById("supply"), "supply");
  let supp = document.getElementById("supplycnt");
  let spacer = document.createElement("DIV");
  spacer.classList.add("spacer");
  supp.appendChild(spacer);
  for (let i = 0; i < 8; i++) {
    createResourceBox(supp, i);
  }
  let ucnt = document.createElement("DIV");
  ucnt.classList.add("ucnt");
  supp.appendChild(ucnt);
  for (let i = 0; i < 2; i++) {
    let urow = document.createElement("DIV");
    urow.classList.add("urow");
    ucnt.appendChild(urow);
    for (let j = 0; j < 2; j++) {
      let ubox = document.createElement("DIV");
      ubox.classList.add("usmallbox", "box");
      urow.appendChild(ubox);
      createResourceDiv("uranium", (9 + 2*i + j), ubox);
      ubox.onclick = function (e) { buyResource("uranium", 9+2*i+j); };
    }
  }
  spacer = document.createElement("DIV");
  spacer.classList.add("spacer");
  supp.appendChild(spacer);

  document.getElementById("boardcnt").onmousemove = onmove;
  document.getElementById("boardcnt").onmousedown = ondown;
  document.getElementById("boardcnt").onmouseup = onup;
  document.getElementById("boardcnt").onmouseout = onout;
  document.getElementById("boardcnt").onwheel = onwheel;
}

function onmove(event) {
  if (isDragging) {
    let changeX = event.clientX - startX;
    let changeY = event.clientY - startY;
    dX = changeX;
    dY = changeY;
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
  offsetX -= (mouseXScaled - mouseX);
  offsetY -= (mouseYScaled - mouseY);
  moveBoard();
}
function moveBoard() {
  document.getElementById("board").style.transform = "translate(" + (offsetX+dX) + "px, " + (offsetY+dY) + "px) scale(" + boardScale + ")";
}

function createResourceBox(supply, num) {
  let rsrcBox = document.createElement("DIV");
  rsrcBox.classList.add("rsrcbox");
  supply.appendChild(rsrcBox);
  for (let rsrc of ["coal", "oil", "gas"]) {
    let row = document.createElement("DIV");
    row.classList.add("row", rsrc + "row");
    rsrcBox.appendChild(row);
    for (let i = 1; i <= 3; i++) {
      let box = document.createElement("DIV");
      box.classList.add("box", rsrc + "box");
      row.appendChild(box);
      createResourceDiv(rsrc, 3*num+i, box);
      box.onclick = function (e) { buyResource(rsrc, 3*num + i); };
    }
    if (rsrc == "oil") {
      let box = document.createElement("DIV");
      box.classList.add("box", "utailbox");
      row.appendChild(box);
      createResourceDiv("uranium", num+1, box);
      box.onclick = function (e) { buyResource("uranium", num+1); };
    }
  }
}

function createResourceDiv(rsrc, num, box) {
  let rsrcDiv = document.createElement("DIV");
  rsrcDiv.classList.add("resource", "cnvcontainer");
  rsrcDiv.id = rsrc + num;
  let rsrcCnv = document.createElement("CANVAS");
  rsrcCnv.classList.add("cnv");
  rsrcDiv.appendChild(rsrcCnv);
  box.appendChild(rsrcDiv);
  renderAssetToDiv(rsrcDiv, rsrc);
}

function toggleMarket() {
  let marketDiv = document.getElementById("market");
  if (marketDiv.ontransitionend != null) {
    return;
  }
  let btn = document.getElementById("markettoggle");
  let btnRect = btn.getBoundingClientRect();
  let divRect = marketDiv.getBoundingClientRect();
  let scaleX = 100 * btnRect.width / divRect.width;
  let scaleY = 100 * btnRect.height / divRect.height;
  let scale = Math.min(scaleX, scaleY);
  let diffX = btnRect.left - divRect.left;
  let diffY = btnRect.top - divRect.top;
  if (btn.classList.contains("shown")) {
    btn.classList.remove("shown");
    marketDiv.ontransitionend = function(e) { doneAnimating(marketDiv); marketDiv.classList.remove("animating", "shown"); marketDiv.style.transform = "none"; finishAnim(); };
    marketDiv.ontransitioncancel = function(e) { doneAnimating(marketDiv); marketDiv.classList.remove("animating", "shown"); marketDiv.style.transform = "none"; finishAnim(); };
    marketDiv.classList.add("animating");
    marketDiv.style.transform = `translate(${diffX}px, ${diffY}px) scale(${scale}%)`;
  } else {
    btn.classList.add("shown");
    marketDiv.style.transform = `translate(${diffX}px, ${diffY}px) scale(${scale}%)`;
    marketDiv.classList.add("shown");
    runningAnim.push(true);
    marketDiv.ontransitionend = function(e) { doneAnimating(marketDiv); marketDiv.classList.remove("animating"); finishAnim(); };
    marketDiv.ontransitioncancel = function(e) { doneAnimating(marketDiv); marketDiv.classList.remove("animating"); finishAnim(); };
    setTimeout(function() { marketDiv.classList.add("animating"); marketDiv.style.transform = "none"; }, 5);
  }
}

function togglePaySupply() {
  let paySupply = document.getElementById("paysupply");
  if (paySupply.ontransitionend != null) {
    return;
  }
  let btn = document.getElementById("paysupplytoggle");
  let btnRect = btn.getBoundingClientRect();
  let divRect = paySupply.getBoundingClientRect();
  let scaleX = 100 * btnRect.width / divRect.width;
  let scaleY = 100 * btnRect.height / divRect.height;
  let scale = Math.min(scaleX, scaleY);
  let diffX = btnRect.left - divRect.left;
  let diffY = btnRect.top - divRect.top;
  if (btn.classList.contains("shown")) {
    btn.classList.remove("shown");
    paySupply.ontransitionend = function(e) { doneAnimating(paySupply); paySupply.classList.remove("animating", "shown"); paySupply.style.transform = "none"; };
    paySupply.ontransitioncancel = function(e) { doneAnimating(paySupply); paySupply.classList.remove("animating", "shown"); paySupply.style.transform = "none"; };
    paySupply.classList.add("animating");
    paySupply.style.transform = `translate(${diffX}px, ${diffY}px) scale(${scale}%)`;
  } else {
    btn.classList.add("shown");
    paySupply.style.transform = `translate(${diffX}px, ${diffY}px) scale(${scale}%)`;
    paySupply.classList.add("shown");
    paySupply.ontransitionend = function(e) { doneAnimating(paySupply); paySupply.classList.remove("animating"); };
    paySupply.ontransitioncancel = function(e) { doneAnimating(paySupply); paySupply.classList.remove("animating"); };
    setTimeout(function() { paySupply.classList.add("animating"); paySupply.style.transform = "none"; }, 5);
   }
}

function joinGame() {
  ws.send(JSON.stringify({
    "type": "join",
    "name": document.getElementById("joinnameinput").value,
    "color": document.getElementById("joincolor").color,
  }));
  localStorage.setItem("playername", document.getElementById("joinnameinput").value);
}

function selectOptions() {
  ws.send(JSON.stringify({
    "type": "options",
    "options": {
      "region": document.getElementById("region").value,
      "plantlist": document.getElementById("plantlist").value,
    },
  }));
}

function startGame() {
  ws.send(JSON.stringify({"type": "start"}));
}

function prepareBid(idx) {
  pendingPlant = idx;
  document.getElementById("bid").value = plantDivs[idx].cost;
  updateAuctionPlants(true);
}

function makeBid() {
  let bid = parseInt(document.getElementById("bid").value);
  ws.send(JSON.stringify({
    "type": "bid",
    "bid": bid,
    "plant": bidPlant ?? pendingPlant,
  }));
}

function passBid() {
  ws.send(JSON.stringify({
    "type": "bid",
    "bid": null,
    "plant": null,
  }));
}

function buyResource(rsrc, numFromLeft) {
  let desiredRemaining = totalCounts[rsrc] - numFromLeft;
  let toBuy = resourceCounts[rsrc] - desiredRemaining;
  ws.send(JSON.stringify({
    "type": "buy",
    "resource": rsrc,
    "count": toBuy,
  }));
}

function doConfirm() {
  ws.send(JSON.stringify({
    "type": "confirm",
  }));
}

function doReset() {
  ws.send(JSON.stringify({
    "type": "reset",
  }));
}

function clickCity(city, color) {
  if (regionsDone) {
    ws.send(JSON.stringify({
      "type": "build",
      "city": city,
    }));
    return;
  }
  ws.send(JSON.stringify({
    "type": "region",
    "region": color,
  }));
}

function hoverRegion(color) {
  if (regionsDone) {
    color = null;
  }
  for (let cityDiv of document.getElementsByClassName("city")) {
    cityDiv.classList.toggle("hovered", cityDiv.classList.contains("region"+color));
  }
  if (regionsDone) {
    return;
  }
  let colorList = [];
  for (let c of chosenColors) {
    colorList.push(c+color);
    colorList.push(color+c);
  }
  colorList.push(color+color);
  for (let connDiv of document.getElementsByClassName("conn")) {
    let hover = false;
    for (let c of colorList) {
      if (connDiv.classList.contains(c)) {
        hover = true;
        break;
      }
    }
    connDiv.classList.toggle("hovered", hover);
  }
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
    document.getElementById("colortext").innerText = "?";
    if (document.getElementById("join").disabled) {
      joinGame();
    }
    return;
  }
  document.getElementById("colortext").innerText = "";
  let inner = document.createElement("DIV");
  inner.classList.add("innercolor");
  inner.style.backgroundColor = color;
  document.getElementById("joincolor").appendChild(inner);
  if (document.getElementById("join").disabled) {
    joinGame();
  }
}

function toggleBurn(e) {
  if (oldPhase != "bureaucracy" || hasBurned) {
    return;
  }
  if (waitBurn()) {
    dontWait();
  }
  let rsrcDiv = e.currentTarget;
  if (rsrcDiv.assetName == null) {
    return;
  }
  rsrcDiv.classList.toggle("toburn");
  let plantCnt = rsrcDiv.parentNode;
  while (plantCnt != null && !plantCnt.classList.contains("plantcnt")) {
    plantCnt = plantCnt.parentNode;
  }
  if (plantCnt == null) {
    return;
  }
  updateBurnCounts(plantCnt);
}

function changeBurn(plantCnt, phase) {
  if (waitBurn()) {
    dontWait();
  }
  if (oldPhase == "bureaucracy" || phase == "bureaucracy") {
    updatePendingPower();
  }
  let check = plantCnt.getElementsByTagName("INPUT")[0];
  if (check.checked) {
    // Auto-burn
    let plantDiv = plantCnt.getElementsByClassName("marketplant")[0];
    if (plantDiv.intake == null) {
      check.checked = false;
      return;
    }
    let stores = plantDiv.getElementsByClassName("stored");
    // Figure out how many are selected right now.
    let selectCount = 0;
    for (let store of stores) {
      if (store.classList.contains("toburn")) {
        selectCount++;
      }
    }
    // Select more until we have enough.
    for (let i = selectCount; i < plantDiv.intake; i++) {
      for (let store of stores) {
        if (store.assetName != null && !store.classList.contains("toburn")) {
          store.classList.add("toburn");
          break;
        }
      }
    }
    // Deselect until we are no longer over.
    for (let i = plantDiv.intake; i < selectCount; i++) {
      for (let store of stores) {
        if (store.classList.contains("toburn")) {
          store.classList.remove("toburn");
          break;
        }
      }
    }
    return;
  }
  // Do not burn - deselect all.
  for (let rsrcDiv of plantCnt.getElementsByClassName("stored")) {
    rsrcDiv.classList.remove("toburn");
  }
}

function updatePendingPower() {
  let output = 0;
  for (let plantDiv of document.getElementsByClassName("owned")) {
    let chk = plantDiv.parentNode.getElementsByTagName("INPUT")[0];
    if (chk.checked) {
      output += plantDiv.output;
    }
  }
  document.getElementById("pending").innerText = `POWER: ${output}`;
  document.getElementById("pending").classList.remove("empty");
}

function discardPlant(plantCnt, really) {
  let plantDiv = plantCnt.getElementsByClassName("marketplant")[0];
  let stored = plantDiv.getElementsByClassName("exists").length;
  let btn = plantCnt.getElementsByClassName("plantdiscard")[0];
  if (!really) {
    if (btn.classList.contains("pressed")) {
      document.getElementById("confirmdiscard").classList.remove("shown");
      btn.classList.remove("pressed");
      return;
    }
    if (stored > 0) {
      btn.classList.add("pressed");
      document.getElementById("discardbtn").onclick = function(e) { discardPlant(plantCnt, true) };
      plantCnt.appendChild(document.getElementById("confirmdiscard"));
      document.getElementById("confirmdiscard").classList.add("shown");
      return;
    }
  }
  let idx = plantDiv.idx;
  ws.send(JSON.stringify({
    "type": "discard",
    "plant": parseInt(idx),
  }));
}

function burn() {
  if (!canBurn) {
    document.getElementById("confirmbtn").classList.add("pressed");
    return;
  }
  let burnCounts = [];
  for (let plantDiv of document.getElementsByClassName("owned")) {
    let plantCnt = plantDiv.parentNode;
    let checkBox = plantCnt.getElementsByTagName("INPUT")[0];
    let toBurn = getBurnCount(plantDiv);
    if (Object.keys(toBurn).length && !checkBox.checked) {
      showError("You have selected resources on an unused plant");
      setTimeout(clearError, 100);
      return;
    }
    if (!checkBox.checked) {
      burnCounts.push(null);
    } else {
      burnCounts.push(toBurn);
    }
  }
  ws.send(JSON.stringify({
    "type": "burn",
    "counts": burnCounts,
  }));
}

function getBurnCount(plantDiv) {
  let toBurn = {};
  for (let stored of plantDiv.getElementsByClassName("stored")) {
    if (stored.assetName == null || !stored.classList.contains("toburn")) {
      continue;
    }
    if (!toBurn[stored.assetName]) {
      toBurn[stored.assetName] = 1;
    } else {
      toBurn[stored.assetName] += 1;
    }
  }
  return toBurn;
}

function updateBurnCounts(plantCnt) {
  let checkbox = plantCnt.getElementsByTagName("INPUT")[0];
  let toBurn = getBurnCount(plantCnt.getElementsByClassName("marketplant")[0]);
  if (Object.keys(toBurn).length) {
    checkbox.checked = true;
    updatePendingPower();
  } else {
    checkbox.checked = false;
    updatePendingPower();
  }
}

function dragStart(e) {
  let plantDiv = e.target;
  while (plantDiv != null && !plantDiv.classList.contains("marketplant")) {
    plantDiv = plantDiv.parentNode;
  }
  if (plantDiv == null) {
    return;
  }
  if (plantDiv.idx == null) {
    return;
  }
  dragged = e.target;
  draggedFrom = plantDiv.idx;
}

function dragEnd(e) {
  dragged = null;
  draggedFrom = null;
}

function dragEnter(e) {
  e.preventDefault();
}

function dragOver(e) {
  e.preventDefault();
}

function drop(e) {
  if (dragged == null || draggedFrom == null) {
    return;
  }
  let resource = dragged.assetName;
  if (resource == null) {
    return;
  }
  let plantDiv = e.currentTarget;
  if (plantDiv.idx == null) {
    return;
  }
  e.preventDefault();
  ws.send(JSON.stringify({
    "type": "shuffle",
    "resource": resource,
    "source": draggedFrom,
    "dest": plantDiv.idx,
  }));
}

function showPlants(plantExpand) {
  plantExpand.classList.add("shown");
  plantExpand.classList.remove("temphide");
  for (let pe of document.getElementsByClassName("plantexpand")) {
    if (pe == plantExpand) {
      continue;
    }
    pe.classList.remove("shown");
  }
  if (expandId != null) {
    clearTimeout(expandId);
  }
}

function hidePlants(plantExpand) {
  if (expandId != null) {
    clearTimeout(expandId);
  }
  expandId = setTimeout(hideAllPlants, 100);
}

function hideAllPlants() {
  for (let pe of document.getElementsByClassName("plantexpand")) {
    if (pe.classList.contains("defaultshow") && !pe.classList.contains("temphide")) {
      pe.classList.add("shown");
    } else {
      pe.classList.remove("shown");
    }
  }
  if (expandId != null) {
    clearTimeout(expandId);
  }
}

function hideDefaultPlant(plantExpand) {
  plantExpand.classList.remove("shown");
  plantExpand.classList.add("temphide");
}

function placeCities(cities, colors) {
  if (cities == null) {
    return;
  }
  chosenColors = colors;
  let boardCnv = document.getElementById("boardcnv");
  for (let city in cities) {
    if (cityDivs[city] != null) {
      continue;
    }
    let color = cities[city].color;
    let div = document.createElement("DIV");
    div.classList.add("city", "region"+color);
    addHouseDiv(div, "first");
    addHouseDiv(div, "second");
    addHouseDiv(div, "third");
    if (!setDivXYPercent(div, boardCnv, "Germany", city)) {
      setDefaultXYPercent(div, boardCnv, "Germany", city);
    }
    div.onclick = function(e) { clickCity(city, color); };
    document.getElementById("board").appendChild(div);
    cityDivs[city] = div;
  }
  for (let city in cityDivs) {
    let chosen = false;
    for (let color of colors) {
      if (cityDivs[city].classList.contains("region"+color)) {
        chosen = true;
        break;
      }
    }
    cityDivs[city].classList.toggle("chosen", chosen);
    if (!regionsDone && !chosen) {
      cityDivs[city].onmouseenter = function(e) { hoverRegion(cities[city].color); };
      cityDivs[city].onmouseleave = function(e) { hoverRegion(null); };
    }
  }
  for (let city in cities) {
    for (let connCity in cities[city].connections) {
      if (connDivs[city+","+connCity] != null || connDivs[connCity+","+city] != null) {
        continue;
      }
      let div = document.createElement("DIV");
      div.classList.add("conn");
      div.classList.add(cities[city].color+cities[connCity].color, cities[connCity].color+cities[city].color);
      let pcta, pctb;
      pcta = cityDivs[city].style.top;
      pctb = cityDivs[connCity].style.top;
      pcta = Number(pcta.substring(0, pcta.length-1));
      pctb = Number(pctb.substring(0, pctb.length-1));
      div.style.top = ((pcta + pctb)/2) + "%";
      pcta = cityDivs[city].style.left;
      pctb = cityDivs[connCity].style.left;
      pcta = Number(pcta.substring(0, pcta.length-1));
      pctb = Number(pctb.substring(0, pctb.length-1));
      div.style.left = ((pcta + pctb)/2) + "%";
      document.getElementById("board").appendChild(div);
      connDivs[city+","+connCity] = div;
    }
  }
  let colorList = [];
  for (let color of chosenColors) {
    for (let c of chosenColors) {
      colorList.push(color+c);
      colorList.push(c+color);
    }
  }
  for (let conn in connDivs) {
    let chosen = false;
    for (let c of colorList) {
      if (connDivs[conn].classList.contains(c)) {
        chosen = true;
        break;
      }
    }
    connDivs[conn].classList.toggle("chosen", chosen);
  }
}

function addHouseDiv(cityDiv, order) {
  let house = document.createElement("DIV");
  house.classList.add("house", order);
  let houseCnt = document.createElement("DIV");
  houseCnt.classList.add("housecnt");
  house.appendChild(houseCnt);
  cityDiv.appendChild(house);
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
    let msg = messageQueue.shift();
    handleData(msg);
  }
}

function handleData(data) {
  placeCities(data.all_cities, data.colors);
  if (data.to_choose != null && data.colors != null && data.to_choose == data.colors.length) {
    regionsDone = true;
  }
  updateJoinWindow(data.started, data.host, data.player_idx, data.players, data.options, data.colors);
  updateSupplyRates(data.players, data.turn_order != null);
  updateCities(data.cities, data.pending_build, data.players, data.turn_idx);
  updateResources(data.resources, data.pending_buy);
  updatePending(data.pending_spend, data.phase);
  updatePlayers(data.players, data.turn_order, data.player_idx, data.pending_spend, data.pending_buy, data.turn_idx, data.phase, data.winner);
  updateMarket(data.market, data.phase);
  updateAuction(data.auction_bid, data.auction_plant_idx, data.turn_order, data.players, data.auction_idx, data.auction_passed, data.auction_bought, data.phase, data.player_idx)
  maybeShowExpandedPlants(data.phase, data.player_idx, data.auction_discard_idx);
  updateBurn(data.phase, data.player_idx, data.turn_order, data.turn_idx);
  updatePhase(data.phase);
  updateButtons(data.phase, data.player_idx == data.turn_idx);
  oldDiscard = data.auction_discard_idx;
  oldPhase = regionsDone ? data.phase : null;
  if (canBurn && waitBurn()) {
    burn();
    dontWait();
  }
  if (messageQueue.length && !runningAnim.length) {
    let msg = messageQueue.shift();
    handleData(msg);
  }
}

function updateJoinWindow(started, host, playerIdx, players, options, colors) {
  let uiJoin = document.getElementById("uijoin");
  if (!uiJoin.classList.contains("shown") && !started) {
    document.getElementById("joinnameinput").value = localStorage.getItem("playername") || "";
  }
  uiJoin.classList.toggle("shown", !started);
  if (players.length > 1 && playerIdx != null && host) {
    document.getElementById("start").classList.remove("disabled");
    document.getElementById("start").disabled = false;
  } else {
    document.getElementById("start").classList.add("disabled");
    document.getElementById("start").disabled = true;
  }
  if (!started) {
    document.getElementById("join").disabled = (playerIdx != null);
    document.getElementById("join").classList.toggle("disabled", playerIdx != null);
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
    for (let name in options) {
      document.getElementById(name).value = options[name];
      document.getElementById(name).disabled = !host;
    }
  }
}

function updateSupplyRates(players, hasStarted) {
  if (!hasStarted) {
    return;
  }
  let numPlayers = players.length;
  let rates = supplyRates[numPlayers];
  for (let rsrc in rates) {
    for (let [idx, rate] of rates[rsrc].entries()) {
      let supplyDiv = document.getElementById("resupply" + (idx +1) + rsrc);
      supplyDiv.innerText = rate;
    }
    let rsrcDiv = document.getElementById("resupply" + rsrc);
    renderAssetToDiv(rsrcDiv, rsrc);
  }
}

function updateCities(cities, pendingBuild, players, turnIdx) {
  if (players == null || players.length == 0) {  // game hasn't started
    return;
  }
  playerCityCounts = [];
  let ordering = ["first", "second", "third"];
  for (let city in cities) {
    let div = cityDivs[city];
    let i;
    for (let [i, order] of ordering.entries()) {
      let color = null;
      let owningPlayer = null;
      if (i < cities[city].occupants.length) {
        color = players[cities[city].occupants[i]].color;
        owningPlayer = cities[city].occupants[i];
      } else if (pendingBuild.includes(city) && i == cities[city].occupants.length) {
        color = players[turnIdx].color;
        owningPlayer = turnIdx;
      }
      div.getElementsByClassName(ordering[i])[0].children[0].style.background = color;
      if (owningPlayer != null) {
        playerCityCounts[owningPlayer] = (playerCityCounts[owningPlayer] ?? 0) + 1;
      }
    }
  }
}

function updateResources(resources, pendingBuy) {
  if (resources == null) {
    return;
  }
  resourceCounts = resources;
  if (pendingBuy != null) {
    for (let rsrc in pendingBuy) {
      resourceCounts[rsrc] -= pendingBuy[rsrc];
    }
  }
  for (let rsrc in resourceCounts) {
    let pendingMissing = totalCounts[rsrc] - resourceCounts[rsrc];
    let missing = pendingMissing - (pendingBuy[rsrc] ?? 0);
    for (let i = 1; i <= totalCounts[rsrc]; i++) {
      let rsrcDiv = document.getElementById(rsrc + i);
      rsrcDiv.classList.toggle("hidden", i <= missing);
      rsrcDiv.classList.toggle("pending", i > missing && i <= pendingMissing);
    }
  }
}

function updatePending(pendingSpend, phase) {
  if (phase == "bureaucracy") {
    updatePendingPower();
  } else if (pendingSpend != null && ["materials", "building"].includes(phase)) {
    document.getElementById("pending").innerText = `COST: ${pendingSpend}`;
    document.getElementById("pending").classList.remove("empty");
  } else {
    document.getElementById("pending").innerText = "COST";
    document.getElementById("pending").classList.add("empty");
  }
}

function updatePlayers(players, turnOrder, playerIdx, pendingSpend, pendingBuy, turnIdx, phase, winner) {
  if (players == null) {
    return;
  }
  for (let [idx, player] of players.entries()) {
    let pdiv = document.getElementById("player" + idx);
    if (pdiv == null) {
      pdiv = createPlayer(idx, player);
    }
    let order = idx;
    if (turnOrder != null) {
      order = turnOrder.indexOf(idx);
    }
    let isTurn = (turnIdx == idx);
    if (phase == "auction" && regionsDone) {
      isTurn = false;
    }
    updatePlayer(pdiv, player, order, idx, pendingSpend, pendingBuy, playerIdx == idx, isTurn, winner);
  }
  while (document.getElementsByClassName("player").length > players.length) {
    let allPlayerDivs = document.getElementsByClassName("player");
    let lastPlayer = allPlayerDivs[allPlayerDivs.length-1];
    lastPlayer.parentNode.removeChild(lastPlayer);
  }
  // Only after updating everythig should we adjust the upper/lower classes of plantexpand.
  for (let [idx, player] of players.entries()) {
    let pdiv = document.getElementById("player" + idx);
    if (pdiv == null) {
      continue;
    }
    let totalHeight = pdiv.offsetParent.offsetHeight;
    let offsetCenter = pdiv.offsetTop + (pdiv.offsetHeight / 2);
    let plantExpand = pdiv.getElementsByClassName("plantexpand")[0];
    if (offsetCenter / totalHeight < 0.2) {
      plantExpand.classList.remove("lower");
      plantExpand.classList.add("upper");
    } else if (offsetCenter / totalHeight > 0.7) {
      plantExpand.classList.add("lower");
      plantExpand.classList.remove("upper");
    } else {
      plantExpand.classList.remove("lower");
      plantExpand.classList.remove("upper");
    }
  }
}

function createPlayer(idx, player) {
  let div = document.createElement("DIV");
  div.id = "player" + idx;
  div.classList.add("player");
  let nameBg = document.createElement("DIV");
  nameBg.classList.add("namebg");
  let nameCont = document.createElement("DIV");
  nameCont.classList.add("namecont");
  let name = document.createElement("DIV");
  name.classList.add("playername");
  nameCont.appendChild(name);
  nameBg.appendChild(nameCont);
  div.appendChild(nameBg);
  let arrowLeft = document.createElement("DIV");
  arrowLeft.classList.add("arrow", "arrowleft", "hidden");
  let leftText = document.createElement("DIV");
  leftText.classList.add("arrowtext");
  leftText.innerText = "🔺";
  arrowLeft.appendChild(leftText);
  let arrowRight = document.createElement("DIV");
  arrowRight.classList.add("arrow", "arrowright", "hidden");
  let rightText = document.createElement("DIV");
  rightText.classList.add("arrowtext");
  rightText.innerText = "🔺";
  arrowRight.appendChild(rightText);
  nameCont.appendChild(arrowLeft);
  nameCont.appendChild(arrowRight);
  let info = document.createElement("DIV");
  info.classList.add("playerinfo");
  div.appendChild(info);
  let infoTypes = {"cities": "🏠", "power": "⚡", "money": "💵"};
  for (let infoType in infoTypes) {
    let infoDiv = document.createElement("DIV");
    infoDiv.classList.add("info", "info" + infoType);
    info.appendChild(infoDiv);
    let desc = document.createElement("SPAN");
    desc.classList.add("infodesc");
    desc.innerText = infoTypes[infoType];
    infoDiv.appendChild(desc);
    let val = document.createElement("SPAN");
    val.classList.add("infoval");
    infoDiv.appendChild(val);
  }
  let plantExpand = document.createElement("DIV");
  plantExpand.classList.add("plantexpand");
  plantExpand.onmouseenter = function(e) { showPlants(plantExpand); };
  plantExpand.onmouseleave = function(e) { hidePlants(plantExpand); };
  div.appendChild(plantExpand);
  let forceHide = document.createElement("DIV");
  forceHide.classList.add("forcehide");
  plantExpand.appendChild(forceHide);
  let hideText = document.createElement("DIV");
  hideText.innerText = "▶️";
  forceHide.appendChild(hideText);
  forceHide.onclick = function(e) { hideDefaultPlant(plantExpand); };
  document.getElementById("players").appendChild(div);
  return div;
}

function updatePlayer(div, player, ordering, idx, pendingSpend, pendingBuy, owned, isTurn, winner) {
  div.style.order = ordering;
  div.getElementsByClassName("playerinfo")[0].style.background = player.color;
  div.getElementsByClassName("namebg")[0].style.background = player.color;
  let name = player.name;
  for (let arrow of div.getElementsByClassName("arrow")) {
    arrow.classList.toggle("hidden", !isTurn || winner != null);
    arrow.classList.toggle("winner", winner != null && winner.includes(idx));
    arrow.firstChild.innerText = (winner != null && winner.includes(idx)) ? "🏆" : "🔺";
  }
  div.getElementsByClassName("playername")[0].innerText = name;
  div.getElementsByClassName("infocities")[0].getElementsByTagName("SPAN")[1].innerText = (playerCityCounts[idx] ?? 0);
  let powerCount = 0;
  for (let plant of player.plants ?? []) {
    powerCount += plant.output;
  }
  div.getElementsByClassName("infopower")[0].getElementsByTagName("SPAN")[1].innerText = powerCount;
  let money = player.money ?? "??";
  if (player.money != null && isTurn && pendingSpend > 0) {
    money = player.money - pendingSpend;
  }
  div.getElementsByClassName("infomoney")[0].getElementsByTagName("SPAN")[1].innerText = money;
  updatePlants(div, player.plants ?? [], isTurn ? pendingBuy : null, owned);
}

function updatePlants(playerDiv, plants, pendingBuy, owned) {
  let plantExpand = playerDiv.getElementsByClassName("plantexpand")[0];
  let playerPlants = playerDiv.getElementsByClassName("playerplant");
  while (playerDiv.getElementsByClassName("playerplant").length > plants.length) {
    playerDiv.removeChild(playerDiv.getElementsByClassName("playerplant")[0]);
  }
  while (playerDiv.getElementsByClassName("playerplant").length < plants.length) {
    createPlant(playerDiv, plantExpand);
  }
  let allocations = getPendingAllocations(plants, pendingBuy);
  for (let [idx, plant] of plants.entries()) {
    updatePlant(playerPlants[idx], plant, allocations[idx]);
  }

  while (plantExpand.getElementsByClassName("plantcnt").length > plants.length) {
    plantExpand.removeChild(plantExpand.getElementsByClassName("plantcnt")[0]);
  }
  while (plantExpand.getElementsByClassName("plantcnt").length < plants.length) {
    createPlayerMarketPlant(plantExpand, owned);
  }
  let playerMarketPlants = playerDiv.getElementsByClassName("marketplant");
  for (let [idx, plant] of plants.entries()) {
    updateMarketPlant(playerMarketPlants[idx], plant, allocations[idx], idx);
  }
}

function createPlant(playerDiv, plantExpand) {
  let div = document.createElement("DIV");
  div.classList.add("playerplant");
  let num = document.createElement("DIV");
  num.classList.add("plantnum");
  let output = document.createElement("DIV");
  output.classList.add("plantoutput");
  let storage = document.createElement("DIV");
  storage.classList.add("plantstorage");
  div.appendChild(num);
  div.appendChild(output);
  div.appendChild(storage);
  playerDiv.appendChild(div);
  div.onmouseenter = function(e) { showPlants(plantExpand); };
  div.onmouseleave = function(e) { hidePlants(plantExpand); };
}

function updatePlant(plantDiv, plant, allocations) {
  let colors = {"coal": "saddlebrown", "oil": "black", "green": "green", "uranium": "red", "gas": "goldenrod"};
  if (colors[plant.resource] != null) {
    plantDiv.style.background = colors[plant.resource];
  } else if (plant.resource == "hybrid") {
    plantDiv.style.background = "repeating-linear-gradient(-45deg, black, saddlebrown 10px)";
  }
  plantDiv.getElementsByClassName("plantnum")[0].innerText = plant.cost + (plant.plus ? "+" : "");
  plantDiv.getElementsByClassName("plantoutput")[0].innerText = plant.output;
  let stored = 0;
  for (let rsrc in plant.storage) {
    stored += plant.storage[rsrc];
  }
  for (let rsrc in allocations) {
    stored += allocations[rsrc];
  }
  plantDiv.getElementsByClassName("plantstorage")[0].innerText = stored + "/" + (2 * plant.intake);
}

function getPendingAllocations(plants, pendingBuy) {
  // Exact copy of logic in finish_buy
  let allocations = [];
  for (let _ of plants) {
    allocations.push({"coal": 0, "oil": 0, "gas": 0, "uranium": 0});
  }
  if (pendingBuy == null) {
    return allocations;
  }
  let remaining = Object.assign({}, pendingBuy);
  for (let [idx, plant] of plants.entries()) {
    if (!remaining[plant.resource]) {
      continue;
    }
    let remainingCapacity = 2 * plant.intake;
    for (let rsrc in plant.storage) {
      remainingCapacity -= plant.storage[rsrc];
    }
    let allocated = Math.min(remainingCapacity, remaining[plant.resource]);
    allocations[idx][plant.resource] += allocated;
    remaining[plant.resource] -= allocated;
  }
  for (let [idx, plant] of plants.entries()) {
    if (plant.resource != "hybrid") {
      continue;
    }
    let remainingCapacity = 2 * plant.intake;
    for (let rsrc in plant.storage) {
      remainingCapacity -= plant.storage[rsrc];
    }
    let allocated;
    for (let rsrc of ["coal", "oil"]) {
      if (remaining[rsrc]) {
        allocated = Math.min(remainingCapacity, remaining[rsrc]);
        allocations[idx][rsrc] += allocated;
        remaining[rsrc] -= allocated;
        remainingCapacity -= allocated;
      }
    }
  }
  return allocations;
}

function plantName(plant) {
  if (plant.cost >= stage3Cost) {
    return "stage3";
  }
  let name = "plant" + plant.cost;
  if (plant.plus) {
    name += "plus";
  }
  return name;
}

function createPlayerMarketPlant(parentDiv, owned) {
  let cnt = document.createElement("DIV");
  cnt.classList.add("plantcnt");
  parentDiv.appendChild(cnt);
  createMarketPlant(cnt, owned);
  if (owned) {
    let burn = document.createElement("LABEL");
    burn.classList.add("plantburn");
    cnt.appendChild(burn);
    let burnCheck = document.createElement("INPUT");
    burnCheck.classList.add("burncheck");
    burnCheck.type = "checkbox";
    burnCheck.onchange = function(e) { changeBurn(cnt); };
    burn.appendChild(burnCheck);
    let burnSlider = document.createElement("DIV");
    burnSlider.classList.add("burnslider");
    burn.appendChild(burnSlider);
    let burnKnob = document.createElement("DIV");
    burnKnob.classList.add("burnknob");
    burnSlider.appendChild(burnKnob);
    let discard = document.createElement("BUTTON");
    discard.classList.add("plantdiscard", "joinbutton");
    discard.innerText = "DISCARD";
    cnt.appendChild(discard);
    discard.onclick = function(e) { discardPlant(cnt) };
  }
}

function createMarketPlant(parentDiv, owned) {
  // TODO: dedup
  let plantDiv = document.createElement("DIV");
  plantDiv.classList.add("marketplant", "cnvcontainer");
  plantDiv.classList.toggle("owned", !!owned);
  let plantCnv = document.createElement("CANVAS");
  plantCnv.classList.add("cnv");
  plantDiv.appendChild(plantCnv);
  plantDiv.ondrop = drop;
  plantDiv.ondragenter = dragEnter;
  plantDiv.ondragover = dragOver;
  parentDiv.appendChild(plantDiv);
  for (let part of ["top", "bottom"]) {
    let storage = document.createElement("DIV");
    storage.classList.add("storage" + part, "storage");
    plantDiv.appendChild(storage);
    for (let i = 0; i < 3; i++) {
      let stored = document.createElement("DIV");
      stored.classList.add("stored", "cnvcontainer");
      let cnv = document.createElement("CANVAS");
      cnv.classList.add("cnv");
      let storedCheck = document.createElement("DIV");
      storedCheck.classList.add("storedcheck");
      storedCheck.innerText = "✔️";
      stored.appendChild(storedCheck);
      stored.appendChild(cnv);
      storage.appendChild(stored);
      clearAssetFromDiv(stored);
      if (owned) {
        stored.onclick = toggleBurn;
        stored.draggable = true;
        stored.ondragstart = dragStart;
        stored.ondragend = dragEnd;
      }
    }
  }
}

function updateMarketPlant(plantDiv, plant, allocations, idx) {
  plantDiv.intake = plant.intake;
  plantDiv.output = plant.output;
  plantDiv.idx = idx;
  renderAssetToDiv(plantDiv, plantName(plant));
  let storeCounts = {};
  for (let store of plantDiv.getElementsByClassName("stored")) {
    if (store.assetName == null) {
      continue;
    }
    if (!storeCounts[store.assetName]) {
      storeCounts[store.assetName] = 1;
    } else {
      storeCounts[store.assetName] += 1;
    }
  }
  let storage = Object.assign({}, plant.storage);
  for (let rsrc in allocations) {
    storage[rsrc] = (storage[rsrc] ?? 0) + allocations[rsrc];
  }
  let toRemove = [];
  let toAdd = [];
  for (let rsrc in storeCounts) {
    let desired = storage[rsrc] ?? 0;
    for (let i = desired; i < storeCounts[rsrc]; i++) {
      toRemove.push(rsrc);
    }
  }
  for (let rsrc in storage) {
    let current = storeCounts[rsrc] ?? 0;
    for (let i = current; i < storage[rsrc]; i++) {
      toAdd.push(rsrc);
    }
  }
  let changed = (toRemove.length || toAdd.length);
  let storeDivs = plantDiv.getElementsByClassName("stored");
  for (let rsrc of toRemove) {
    for (let i = storeDivs.length-1; i >=0; i--) {
      if (storeDivs[i].assetName == rsrc) {
        clearAssetFromDiv(storeDivs[i]);
        storeDivs[i].classList.remove("toburn");
        storeDivs[i].classList.remove("exists");
        break;
      }
    }
  }
  for (let rsrc of toAdd) {
    for (let i = 0; i < storeDivs.length; i++) {
      if (storeDivs[i].assetName == null) {
        renderAssetToDiv(storeDivs[i], rsrc);
        storeDivs[i].classList.add("exists");
        break;
      }
    }
  }
  let pendingCounts = Object.assign({}, allocations);
  for (let i = storeDivs.length-1; i >= 0; i--) {
    if (storeDivs[i].assetName == null) {
      continue;
    }
    if (pendingCounts[storeDivs[i].assetName]) {
      storeDivs[i].classList.add("pending");
      pendingCounts[storeDivs[i].assetName]--;
    } else {
      storeDivs[i].classList.remove("pending");
    }
  }
  if (plantDiv.classList.contains("owned") && changed) {
    if (waitBurn()) {
      dontWait();
    }
    document.getElementById("confirmdiscard").classList.remove("shown");
    for (let btn of plantDiv.parentNode.getElementsByClassName("plantdiscard")) {
      btn.classList.remove("pressed");
    }
    if (oldPhase == "bureaucracy") {
      let count = plantDiv.getElementsByClassName("exists").length;
      let plantCnt = plantDiv.parentNode;
      let checkBox = plantCnt.getElementsByTagName("INPUT")[0];
      if (count >= plant.intake) {
        checkBox.checked = true;
        changeBurn(plantCnt);
      } else if (count == 0) {
        checkBox.checked = false;
        changeBurn(plantCnt);
      }
    }
  }
}

function updateMarket(market, phase) {
  if (market == null) {
    return;
  }
  // Don't show the market until players have selected regions.
  if (!regionsDone) {
    return;
  }
  let marketDiv = document.getElementById("market");
  if (oldPhase != phase) {
    // Player can adjust this on their own; only update on phase change.
    let shouldShow = phase == "auction";
    let showBtn = document.getElementById("markettoggle");
    if (showBtn.classList.contains("shown") != shouldShow) {
      toggleMarket();
    }
  }
  while (marketDiv.getElementsByClassName("marketplant").length) {
    let plantDiv = marketDiv.getElementsByClassName("marketplant")[0];
    plantDiv.parentNode.removeChild(plantDiv);
  }
  plantDivs = [];  // global
  for (let [idx, plant] of market.entries()) {
    let plantDiv = document.createElement("DIV");
    plantDiv.classList.add("marketplant", "cnvcontainer");
    let plantCnv = document.createElement("CANVAS");
    plantCnv.classList.add("cnv");
    plantDiv.appendChild(plantCnv);
    if (idx < market.length / 2) {
      document.getElementById("markettop").appendChild(plantDiv);
    } else {
      document.getElementById("marketbottom").appendChild(plantDiv);
    }
    renderAssetToDiv(plantDiv, plantName(plant));
    plantDivs.push(plantDiv);
    plantDiv.cost = plant.cost;
    plantDiv.onclick = function(e) { prepareBid(idx); };
  }
}

function updateAuction(currentBid, bidPlantIdx, turnOrder, players, auctionIdx, passed, bought, phase, playerIdx) {
  let yourBidTurn = (phase == "auction" && auctionIdx == playerIdx);
  document.getElementById("auction").classList.toggle("hidden", phase != "auction");
  bidPlant = bidPlantIdx;
  let bidInput = document.getElementById("bid");
  if (!yourBidTurn) {
    pendingPlant = null;
    bidInput.value = currentBid;
  } else {
    let myBid = parseInt(bidInput.value);
    if (currentBid != null) {
      if (myBid != myBid || myBid <= currentBid) {
        bidInput.value = currentBid+1;
      }
    }
  }
  document.getElementById("bid").disabled = !yourBidTurn;
  updateAuctionPlants(yourBidTurn);
  if (phase == "auction") {
    updateBidders(currentBid, turnOrder, players, auctionIdx, passed, bought);
  }
}

function updateBidders(currentBid, turnOrder, players, auctionIdx, passed, bought) {
  let bidders = document.getElementById("bidders");
  let eligible = Array(...turnOrder);
  let alreadyBought = [];
  for (let idx of eligible) {
    if (bought[idx] !== undefined) {
      alreadyBought.push(idx);
    }
  }
  for (let idx of alreadyBought) {
    eligible.splice(eligible.indexOf(idx), 1);
  }
  while (6 > bidders.children.length) {
    let d = document.createElement("DIV");
    d.classList.add("bidder");
    let pname = document.createElement("DIV");
    pname.classList.add("biddername");
    let pbid = document.createElement("DIV");
    pbid.classList.add("bidderbid");
    d.appendChild(pname);
    d.appendChild(pbid);
    d.style.color = "white";
    bidders.appendChild(d);
  }
  for (let i = eligible.length; i < bidders.children.length; i++) {
    bidders.children[i].firstChild.innerText = "";
    bidders.children[i].lastChild.innerText = "";
    bidders.children[i].style.backgroundColor = "transparent";
  }
  let lastBidIdx = null;
  let prevBidIdx = null;
  for (let [idx, pidx] of eligible.entries()) {
    bidders.children[idx].style.backgroundColor = players[pidx].color;
    let pname = bidders.children[idx].firstChild;
    let pbid = bidders.children[idx].lastChild;
    pname.innerText = players[pidx].name;
    if (currentBid == null) {
      pbid.innerText = "";
    }
    if (passed.includes(pidx)) {
      pname.style.textDecoration = "line-through white";
      pbid.innerText = "";
    } else {
      pname.style.textDecoration = "none";
      if (pidx == auctionIdx) {
        prevBidIdx = lastBidIdx;
        pbid.innerText = "?";
      }
      lastBidIdx = pidx;
    }
  }
  if (currentBid != null && prevBidIdx == null) {
    prevBidIdx = lastBidIdx;
  }
  if (currentBid != null && prevBidIdx != null) {
    let idx = eligible.indexOf(prevBidIdx);
    bidders.children[idx].lastChild.innerText = currentBid;
  }
}

function updateAuctionPlants(yourBidTurn) {
  for (let [idx, plantDiv] of plantDivs.entries()) {
    if (bidPlant == null && pendingPlant == null) {
      plantDiv.classList.toggle("disabled", (plantDivs.length > 6 && idx >= 4));
    } else {
      plantDiv.classList.toggle("disabled", idx != bidPlant && idx != pendingPlant);
    }
    if (plantDivs.length <= 6 || idx < 4) {
      plantDiv.classList.toggle("auction", yourBidTurn && bidPlant == null);
    }
  }
}

function maybeShowExpandedPlants(phase, playerIdx, discardIdx) {
  let playerDiv = document.getElementById("player" + playerIdx);
  if (playerDiv == null) {
    return;
  }
  let plantExpand = playerDiv.getElementsByClassName("plantexpand")[0];
  let shouldShow = ["bureaucracy", "materials"].includes(phase);
  shouldShow = shouldShow || discardIdx == playerIdx;
  if (phase != oldPhase || oldDiscard != discardIdx) {
    plantExpand.classList.toggle("shown", shouldShow);
  }
  plantExpand.classList.toggle("defaultshow", shouldShow);
  plantExpand.classList.toggle("discard", discardIdx == playerIdx);
  if (discardIdx != playerIdx) {
    document.getElementById("confirmdiscard").classList.remove("shown");
    for (let btn of plantExpand.getElementsByClassName("plantdiscard")) {
      btn.classList.remove("pressed");
    }
  }
}

function updateBurn(phase, playerIdx, turnOrder, turnIdx) {
  let playerDiv = document.getElementById("player" + playerIdx);
  if (playerDiv == null) {
    return;
  }
  let plantExpand = playerDiv.getElementsByClassName("plantexpand")[0];
  if (phase == "bureaucracy" && phase != oldPhase) {
    hasBurned = false;
    // If we have just entered the bureaucracy phase, auto-fire the player's plants.
    for (let plantDiv of document.getElementsByClassName("owned")) {
      let plantCnt = plantDiv.parentNode;
      let checkBox = plantCnt.getElementsByTagName("INPUT")[0];
      let storeTotal = 0;
      for (let stored of plantDiv.getElementsByClassName("stored")) {
        if (stored.assetName != null) {
          storeTotal++;
        }
      }
      if (storeTotal >= plantDiv.intake) {
        checkBox.checked = true;
        changeBurn(plantCnt, phase);
      } else if (storeTotal == 0) {
        checkBox.checked = false;
        changeBurn(plantCnt, phase);
      }
    }
  }
  if (phase == "bureaucracy" && turnOrder.indexOf(turnIdx) > turnOrder.indexOf(playerIdx)) {
    hasBurned = true;
  }
  canBurn = (phase == "bureaucracy" && turnIdx == playerIdx);
  if ((phase == "bureaucracy" && hasBurned) || phase != "bureaucracy") {
    for (let plantDiv of document.getElementsByClassName("owned")) {
      for (let stored of plantDiv.getElementsByClassName("stored")) {
        stored.classList.remove("toburn");
      }
    }
  }
  for (let checkbox of document.getElementsByClassName("burncheck")) {
    checkbox.disabled = (phase != "bureaucracy" || hasBurned);
  }
}

function updatePhase(phase) {
  if (!regionsDone) {
    return;
  }
  for (let p of document.getElementsByClassName("orderitem")) {
    p.classList.toggle("current", p.id == "order" + phase);
  }
}

function updateButtons(phase, myTurn) {
  if (!regionsDone) {
    return;
  }
  if (phase == "bureaucracy") {
    document.getElementById("confirmbtn").innerText = "Burn";
    document.getElementById("confirmbtn").classList.add("burn");
    document.getElementById("confirmbtn").onclick = burn;
  } else {
    document.getElementById("confirmbtn").innerText = "Done";
    document.getElementById("confirmbtn").classList.remove("burn");
    document.getElementById("confirmbtn").onclick = doConfirm;
  }
  document.getElementById("confirmbtn").disabled = true;
  document.getElementById("resetbtn").disabled = true;
  if (phase == "bureaucracy") {
    document.getElementById("confirmbtn").disabled = hasBurned;
  }
  if (myTurn && ["materials", "building"].includes(phase)) {
    document.getElementById("confirmbtn").disabled = false;
    document.getElementById("resetbtn").disabled = false;
  }
}

function waitBurn() {
  return document.getElementById("confirmbtn").classList.contains("pressed");
}

function dontWait() {
  document.getElementById("confirmbtn").classList.remove("pressed");
}
