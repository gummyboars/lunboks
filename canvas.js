// For manipulating the canvas.
isDragging = false;
ignoreNextClick = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;
scale = 1;
eventX = null;
eventY = null;

hoverTile = null;
hoverCorner = null;
hoverEdge = null;

renderLoops = {};

function locationsEqual(locA, locB) {
  if (locA == null && locB == null) {
    return true;
  }
  if (locA == null || locB == null) {
    return false;
  }
  if (locA.length != locB.length) {
    return false;
  }
  for (let i = 0; i < locA.length; i++) {
    if (locA[i] != locB[i]) {
      return false;
    }
  }
  return true;
}

function draw() {
  var canvas = document.getElementById('myCanvas');
  var context = canvas.getContext('2d');

  if (tiles.length < 1) {
    window.requestAnimationFrame(draw);
    return;
  }

  context.save();
  context.clearRect(0, 0, canWidth, canHeight);
  context.translate(offsetX + dX, offsetY + dY);
  context.scale(scale, scale);
  context.textAlign = 'center';
  let portMap = {};
  for (let i = 0; i < ports.length; i++) {
    let loc = ports[i].location.toString();
    portMap[loc] = ports[i];
  }
  context.save();
  for (let i = 0; i < tiles.length; i++) {
    drawTile(tiles[i], context);
    drawNumber(tiles[i], context);
  }
  context.restore();
  context.save();
  for (let i = 0; i < ports.length; i++) {
    drawPort(ports[i], context);
  }
  context.restore();
  context.save();
  for (let i = 0; i < tiles.length; i++) {
    if (!tiles[i].is_land) {
      drawCoast(tiles[i], portMap, context);
    }
  }
  context.restore();
  context.save();
  for (let i = 0; i < roads.length; i++) {
    drawRoad(roads[i].location, playerData[roads[i].player].color, context);
  }
  context.restore();
  context.save();
  // Draw pieces over roads.
  for (let i = 0; i < pieces.length; i++) {
    drawPiece(pieces[i].location, playerData[pieces[i].player].color, pieces[i].piece_type, context);
  }
  context.restore();
  context.save();
  drawHover(context);
  context.restore();
  context.save();
  let robberOpacity = 1;
  if (robberLoc != null && locationsEqual(robberLoc, hoverTile)) {
    robberOpacity = 0.5;
  }
  drawRobber(context, robberLoc, robberOpacity);
  context.restore();
  drawDebug(context);
  context.restore();
  window.requestAnimationFrame(draw);
}

function coordsToEdgeCenter(loc) {
  let leftCorn = coordToCornerCenter([loc[0], loc[1]]);
  let rightCorn = coordToCornerCenter([loc[2], loc[3]]);
  return {
    x: (leftCorn.x + rightCorn.x) / 2,
    y: (leftCorn.y + rightCorn.y) / 2,
  };
}
function coordToCornerCenter(loc) {
  let x = (2 * Math.floor(loc[0]/2)) * tileWidth * 3 / 8;
  let y = loc[1] * tileHeight / 2;
  if (Math.abs(loc[0]) % 2 == 1) {
    x += tileWidth / 2;
  }
  return {x: x, y: y};
}
function coordToTileUpperLeft(loc) {
  let x = loc[0] * tileWidth * 3 / 8 - tileWidth / 4;
  let y = loc[1] * tileHeight / 2;
  return {x: x, y: y};
}
function coordToTileCenter(loc) {
  let ul = coordToTileUpperLeft(loc);
  return {x: ul.x + tileWidth/2, y: ul.y + tileHeight/2};
}
function drawRoad(roadLoc, style, ctx) {
  let leftCorner = coordToCornerCenter([roadLoc[0], roadLoc[1]]);
  let rightCorner = coordToCornerCenter([roadLoc[2], roadLoc[3]]);
  ctx.strokeStyle = style;
  ctx.lineWidth = pieceRadius;
  ctx.lineCap = 'butt';
  ctx.beginPath();
  let leftX = 0.15 * rightCorner.x + 0.85 * leftCorner.x;
  let rightX = 0.15 * leftCorner.x + 0.85 * rightCorner.x;
  let leftY = 0.15 * rightCorner.y + 0.85 * leftCorner.y;
  let rightY = 0.15 * leftCorner.y + 0.85 * rightCorner.y;
  ctx.moveTo(leftX, leftY);
  ctx.lineTo(rightX, rightY);
  ctx.stroke();
}
function drawDebug(ctx) {
  if (debug) {
    ctx.strokeStyle = "black";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(-10000, 0);
    ctx.lineTo(10000, 0);
    ctx.stroke();
    ctx.moveTo(0, -10000);
    ctx.lineTo(0, 10000);
    ctx.stroke();
    ctx.fillStyle = "black";
    ctx.fillText("" + eventX + ", " + eventY, 0, 0);
  }
}
function drawPiece(pieceLoc, style, pieceType, ctx) {
  let canvasLoc = coordToCornerCenter(pieceLoc);
  ctx.fillStyle = style;
  if (pieceType == "settlement") {
    ctx.beginPath();
    ctx.moveTo(canvasLoc.x - pieceRadius, canvasLoc.y + pieceRadius * 3/2);
    ctx.lineTo(canvasLoc.x + pieceRadius, canvasLoc.y + pieceRadius * 3/2);
    ctx.lineTo(canvasLoc.x + pieceRadius, canvasLoc.y - pieceRadius * 1/2);
    ctx.lineTo(canvasLoc.x, canvasLoc.y - pieceRadius * 3/2);
    ctx.lineTo(canvasLoc.x - pieceRadius, canvasLoc.y - pieceRadius * 1/2);
    ctx.closePath();
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "black";
    ctx.stroke();
  }
  if (pieceType == "city") {
    let radius = pieceRadius * 1.5;
    ctx.beginPath();
    ctx.moveTo(canvasLoc.x - radius, canvasLoc.y + radius);
    ctx.lineTo(canvasLoc.x + radius, canvasLoc.y + radius);
    ctx.lineTo(canvasLoc.x + radius, canvasLoc.y - radius/2);
    ctx.lineTo(canvasLoc.x + radius/2, canvasLoc.y - radius);
    ctx.lineTo(canvasLoc.x, canvasLoc.y - radius/2);
    ctx.lineTo(canvasLoc.x, canvasLoc.y);
    ctx.lineTo(canvasLoc.x - radius, canvasLoc.y);
    ctx.closePath();
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "black";
    ctx.stroke();
  }
}
function drawTile(tileData, ctx) {
  let img = document.getElementById("canvas" + tileData.tile_type + tileData.variant);
  if (img == null) {
    img = document.getElementById("canvas" + tileData.tile_type);
  }
  let canvasLoc = coordToTileCenter(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  if (tileData.rotation) {
    ctx.rotate(Math.PI * tileData.rotation / 3);
  }
  if (img != null) {
    ctx.drawImage(img, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  ctx.restore();
}
function drawPort(portData, ctx) {
  let portImg = document.getElementById("canvasport" + portData.variant);
  if (portImg == null) {
    portImg = document.getElementById("canvasport");
  }
  let img = document.getElementById("canvas" + portData.port_type + "port" + portData.variant);
  if (img == null) {
    img = document.getElementById("canvas" + portData.port_type + "port");
  }
  let canvasLoc = coordToTileCenter(portData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  if (portData.rotation) {
    ctx.rotate(Math.PI * portData.rotation / 3);
  }
  if (portImg != null) {
    ctx.drawImage(portImg, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  if (img != null) {
    ctx.drawImage(img, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  ctx.restore();
}
function drawCoast(tileData, portMap, ctx) {
  coastImg = document.getElementById("canvascoast" + tileData.variant);
  if (coastImg == null) {
    coastImg = document.getElementById("canvascoast");
  }
  if (coastImg == null || !Array.isArray(tileData.land_rotations)) {
    return;
  }
  let portData = portMap[tileData.location.toString()];
  let portRotation = null;
  if (portData != null) {
    portRotation = (portData.rotation + 6) % 6;
  }
  let canvasLoc = coordToTileCenter(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  for (let rotation of tileData.land_rotations) {
    if ((rotation+6)%6 == portRotation) {
      continue;
    }
    ctx.save();
    ctx.rotate(Math.PI * rotation / 3);
    ctx.drawImage(coastImg, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
    ctx.restore();
  }
  ctx.restore();
}
function drawNumber(tileData, ctx) {
  let textHeightOffset = 12; // Adjust as necessary.
  let canvasLoc = coordToTileCenter(tileData.location);
  if (tileData.number) {
    // Draw the white circle.
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.beginPath();
    ctx.arc(canvasLoc.x, canvasLoc.y, 28, 0, Math.PI * 2, true);
    ctx.fill();
    // Draw the number.
    if (tileData.number == '6' || tileData.number == '8') {
      ctx.fillStyle = 'red';
      ctx.font = 'bold 36px sans-serif';
    } else {
      ctx.fillStyle = 'black';
      ctx.font = 'bold 32px sans-serif';
    }
    ctx.fillText(tileData.number + "", canvasLoc.x, canvasLoc.y + textHeightOffset);
  }
}
function drawHover(ctx) {
  if (turn != myIdx) {
    return;
  }
  let canvas = document.getElementById("myCanvas");
  if (hoverTile != null) {
    if (!locationsEqual(robberLoc, hoverTile)) {
      drawRobber(ctx, hoverTile, 0.5);
      canvas.style.cursor = "pointer";
    }
    return;
  }
  if (hoverCorner != null) {
    let drawType = "settlement";
    for (let i = 0; i < pieces.length; i++) {
      if (locationsEqual(pieces[i].location, hoverCorner)) {
        if (pieces[i].player == myIdx) {
          drawType = "city";
        }
        break;
      }
    }
    drawPiece(hoverCorner, 'rgba(127, 127, 127, 0.5)', drawType, ctx);
    canvas.style.cursor = "pointer";
    return;
  }
  if (hoverEdge != null) {
    drawRoad(hoverEdge, 'rgba(127, 127, 127, 0.5)', ctx);
    canvas.style.cursor = "pointer";
    return;
  }
  canvas.style.cursor = "auto";
}
function drawRobber(ctx, loc, alpha) {
  if (loc == null) {
    return;
  }
  let isLand = true;
  for (let tile of tiles) {
    if (locationsEqual(tile.location, loc)) {
      isLand = tile.is_land;
      break;
    }
  }
  let canvasLoc = coordToTileCenter(loc);
  let robimg, robWidth, robHeight;
  if (isLand) {
    robimg = document.getElementById("robber");
    robwidth = 26;
    robheight = 60;
  } else {
    robimg = document.getElementById("pirate");
    robwidth = 45;
    robheight = 40;
  }
  ctx.globalAlpha = alpha;
  ctx.drawImage(robimg, canvasLoc.x - robwidth/2, canvasLoc.y - robheight/2, robwidth, robheight);
}
function getEdge(eventX, eventY) {
  for (let i = 0; i < edges.length; i++) {
    let edgeCenter = coordsToEdgeCenter(edges[i].location);
    let centerX = edgeCenter.x * scale + offsetX + dX;
    let centerY = edgeCenter.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = pieceRadius * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
}
function getCorner(eventX, eventY, cList) {
  for (let i = 0; i < cList.length; i++) {
    let canvasLoc = coordToCornerCenter(cList[i].location);
    let centerX = canvasLoc.x * scale + offsetX + dX;
    let centerY = canvasLoc.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = pieceRadius * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
}
function getTile(eventX, eventY) {
  for (let i = 0; i < tiles.length; i++) {
    let canvasLoc = coordToTileCenter(tiles[i].location);
    let centerX = canvasLoc.x * scale + offsetX + dX;
    let centerY = canvasLoc.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = 50 * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
  return null;
}
function onclick(event) {
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  let clickTile = getTile(event.clientX, event.clientY);
  if (clickTile != null) {
    let msg = {
      type: "robber",
      location: tiles[clickTile].location,
    };
    ws.send(JSON.stringify(msg));
  }
  let clickPiece = getCorner(event.clientX, event.clientY, pieces);
  if (clickPiece != null && pieces[clickPiece].player == myIdx) {
    let msg = {
      type: "city",
      location: pieces[clickPiece].location,
    };
    ws.send(JSON.stringify(msg));
  } else {
    let clickCorner = getCorner(event.clientX, event.clientY, corners);
    if (clickCorner != null) {
      let msg = {
        type: "settle",
        location: corners[clickCorner].location,
      };
      ws.send(JSON.stringify(msg));
    }
  }
  let clickEdge = getEdge(event.clientX, event.clientY);
  if (clickEdge != null) {
    let msg = {
      type: "road",
      location: edges[clickEdge].location,
    };
    ws.send(JSON.stringify(msg));
  }
}
function onmove(event) {
  eventX = event.clientX;
  eventY = event.clientY;
  let hoverLoc = getTile(event.clientX, event.clientY);
  if (hoverLoc != null) {
    hoverTile = tiles[hoverLoc].location;
  } else {
    hoverTile = null;
  }
  hoverLoc = getCorner(event.clientX, event.clientY, corners);
  if (hoverLoc != null) {
    hoverCorner = corners[hoverLoc].location;
  } else {
    hoverCorner = null;
  }
  hoverLoc = getEdge(event.clientX, event.clientY);
  if (hoverLoc != null) {
    hoverEdge = edges[hoverLoc].location;
  } else {
    hoverEdge = null;
  }
  if (isDragging) {
    newX = event.clientX;
    newY = event.clientY;
    
    dX = newX - startX;
    dY = newY - startY;
  }
}
function onwheel(event) {
  event.preventDefault();
  let oldScale = scale;
  if (event.deltaY < 0) {
    scale += 0.05;
  } else if (event.deltaY > 0) {
    scale -= 0.05;
  }
  scale = Math.min(Math.max(0.125, scale), 4);
  offsetX = event.clientX - ((event.clientX - offsetX) * scale / oldScale);
  offsetY = event.clientY - ((event.clientY - offsetY) * scale / oldScale);
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
  if (isDragging && (dX != 0 || dY != 0)) {
    ignoreNextClick = true;
  }
  isDragging = false;
  offsetX += dX;
  offsetY += dY;
  dX = 0;
  dY = 0;
}
function centerCanvas() {
  if (tiles.length < 1) {
    return;
  }
  let tileLoc = coordToTileCenter(tiles[0].location);
  let minX = tileLoc.x;
  let minY = tileLoc.y;
  let maxX = tileLoc.x;
  let maxY = tileLoc.y;
  for (let i = 0; i < tiles.length; i++) {
    tileLoc = coordToTileCenter(tiles[i].location);
    minX = Math.min(tileLoc.x, minX);
    minY = Math.min(tileLoc.y, minY);
    maxX = Math.max(tileLoc.x, maxX);
    maxY = Math.max(tileLoc.y, maxY);
  }
  offsetX = canWidth / 2 - (minX + maxX) / 2;
  offsetY = canHeight / 2 - (minY + maxY) / 2;
}
function finishImgLoad(assetName) {
  renderLoops[assetName] = 2;
}
function renderSource(assetName, cnv, img, filter) {
  if (!renderLoops[assetName]) {
    renderLoops[assetName] = 1;
    return;
  }
  cnv.width = filter.naturalWidth;
  cnv.height = filter.naturalHeight;
  let context = cnv.getContext('2d');
  let xoff = imageInfo[assetName].xoff || 0;
  let yoff = imageInfo[assetName].yoff || 0;
  let rotation = imageInfo[assetName].rotation || 0;
  let scale = imageInfo[assetName].scale || 1;
  context.clearRect(0, 0, filter.width, filter.height);
  context.save();
  context.translate(filter.width/2, filter.height/2);
  context.drawImage(filter, -filter.width/2, -filter.height/2);
  context.rotate(Math.PI * rotation / 180);
  context.scale(scale, scale);
  context.globalCompositeOperation = "source-in";
  context.drawImage(img, -xoff, -yoff);
  context.restore();
  renderLoops[assetName] = 2;
}
function initializeImages() {
  // Reset to make sure we wait for all assets to load again.
  renderLoops = {};
  let assets = document.getElementById("assets");
  for (let iname in imageInfo) {
    let assetName = iname;
    let oldImg = document.getElementById("img" + assetName);
    if (oldImg != null) {
      assets.removeChild(oldImg);
    }
    let oldCnv = document.getElementById("canvas" + assetName);
    if (oldCnv != null) {
      assets.removeChild(oldCnv);
    }
    // Some variants (such as a corner tile for space) don't exist, so skip them.
    if (imageInfo[assetName].src == null) {
      renderLoops[assetName] = 2;
      continue
    }
    let img = document.createElement("IMG");
    img.src = imageInfo[assetName].src;
    img.id = "img" + assetName;
    assets.appendChild(img);
    if (imageInfo[assetName].filter == null) {
      renderLoops[assetName] = 1;
      img.id = "canvas" + assetName;
      img.onload = function(e) {
        finishImgLoad(assetName);
      };
      continue;
    }
    let filter = document.createElement("IMG");
    filter.src = imageInfo[assetName].filter;
    filter.id = "filter" + assetName;
    assets.appendChild(filter);
    let cnv = document.createElement("CANVAS");
    cnv.id = "canvas" + assetName;
    assets.appendChild(cnv);
    img.onload = function(e) {
      renderSource(assetName, cnv, img, filter);
    };
    filter.onload = function(e) {
      renderSource(assetName, cnv, img, filter);
    };
  }
  // There's probably a better way to do this (create many promises and resolve them from inside
  // renderSource? How do we get the resolve function in renderSource? Anyway, I'm not going to
  // try to figure it out right now.
  somePromise = new Promise((resolve, reject) => {
    setTimeout(function() { checkInitDone(resolve, reject, 300) }, 100);
  });
  return somePromise;
}
function checkInitDone(resolver, rejecter, maxTries) {
  if (!maxTries) {
    rejecter("deadline exceeded");
    return;
  }
  let allDone = true;
  for (let iname in imageInfo) {
    if (renderLoops[iname] != 2) {
      allDone = false;
      break;
    }
  }
  if (!allDone) {
    setTimeout(function() { checkInitDone(resolver, rejecter, maxTries - 1) }, 100);
    return;
  }
  resolver("loaded");
}
