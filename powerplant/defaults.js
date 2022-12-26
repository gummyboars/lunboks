cityGermanyDefaults = {
  "FLENSBURG": {"x": 0.4033333333333333, "y": 0.026344086021505377},
  "KIEL": {"x": 0.4553333333333333, "y": 0.09301075268817205},
  "HAMBURG": {"x": 0.4513333333333333, "y": 0.1956989247311828},
  "HANNOVER": {"x": 0.452, "y": 0.3586021505376344},
  "BREMEN": {"x": 0.352, "y": 0.2591397849462366},
  "CUXHAVEN": {"x": 0.3333333333333333, "y": 0.15376344086021507},
  "WILHELMSHAVEN": {"x": 0.2653333333333333, "y": 0.19516129032258064},
  "OSNABRUCK": {"x": 0.2733333333333333, "y": 0.34408602150537637},
  "MUNSTER": {"x": 0.216, "y": 0.40698924731182795},
  "ESSEN": {"x": 0.14333333333333334, "y": 0.45376344086021503},
  "DUISBURG": {"x": 0.08133333333333333, "y": 0.4360215053763441},
  "DUSSELDORF": {"x": 0.09733333333333333, "y": 0.5134408602150538},
  "DORTMUND": {"x": 0.23133333333333334, "y": 0.4838709677419355},
  "KASSEL": {"x": 0.4013333333333333, "y": 0.5005376344086021},
  "AACHEN": {"x": 0.066, "y": 0.589247311827957},
  "KOLN": {"x": 0.164, "y": 0.5655913978494623},
  "TRIER": {"x": 0.10866666666666666, "y": 0.7112903225806452},
  "WIESBADEN": {"x": 0.2753333333333333, "y": 0.6688172043010753},
  "SAARBRUCKEN": {"x": 0.196, "y": 0.7881720430107527},
  "MANNHEIM": {"x": 0.328, "y": 0.7672043010752688},
  "FRANKFURT-M": {"x": 0.338, "y": 0.646236559139785},
  "STUTTGART": {"x": 0.36, "y": 0.8510752688172043},
  "FREIBURG": {"x": 0.24133333333333334, "y": 0.9333333333333333},
  "KONSTANZ": {"x": 0.358, "y": 0.9724193548387097},
  "AUGSBURG": {"x": 0.526, "y": 0.8795698924731182},
  "MUNCHEN": {"x": 0.6246666666666667, "y": 0.9344086021505377},
  "REGENSBURG": {"x": 0.6573333333333333, "y": 0.8150537634408602},
  "PASSAU": {"x": 0.81, "y": 0.8720430107526882},
  "NURNBERG": {"x": 0.5786666666666667, "y": 0.7516129032258064},
  "WURZBURG": {"x": 0.4646666666666667, "y": 0.7075268817204301},
  "FULDA": {"x": 0.448, "y": 0.6021505376344086},
  "ERFURT": {"x": 0.5793333333333334, "y": 0.5419354838709678},
  "HALLE": {"x": 0.6533333333333333, "y": 0.4720430107526882},
  "LEIPZIG": {"x": 0.708, "y": 0.5021505376344086},
  "DRESDEN": {"x": 0.852, "y": 0.5473118279569893},
  "MAGDEBURG": {"x": 0.6353333333333333, "y": 0.36774193548387096},
  "BERLIN": {"x": 0.7853333333333333, "y": 0.33602150537634407},
  "FRANKFURT-D": {"x": 0.8906666666666667, "y": 0.3596774193548387},
  "SCHWERIN": {"x": 0.5973333333333334, "y": 0.2010752688172043},
  "TORGELOW": {"x": 0.8493333333333334, "y": 0.1935483870967742},
  "ROSTOCK": {"x": 0.6586666666666666, "y": 0.11290322580645161},
  "LUBECK": {"x": 0.5306666666666666, "y": 0.1381720430107527},
};

cityGermanyConnections = [
  ["FLENSBURG", "KIEL", 4],
  ["HAMBURG", "KIEL", 8],
  ["LUBECK", "KIEL", 4],
  ["HAMBURG", "LUBECK", 6],
  ["HAMBURG", "SCHWERIN", 8],
  ["HAMBURG", "HANNOVER", 17],
  ["HAMBURG", "BREMEN", 11],
  ["HAMBURG", "CUXHAVEN", 11],
  ["BREMEN", "CUXHAVEN", 8],
  ["BREMEN", "WILHELMSHAVEN", 11],
  ["BREMEN", "OSNABRUCK", 11],
  ["BREMEN", "HANNOVER", 10],
  ["HANNOVER", "SCHWERIN", 19],
  ["HANNOVER", "MAGDEBURG", 15],
  ["HANNOVER", "ERFURT", 19],
  ["HANNOVER", "KASSEL", 15],
  ["HANNOVER", "OSNABRUCK", 16],
  ["OSNABRUCK", "WILHELMSHAVEN", 14],
  ["OSNABRUCK", "MUNSTER", 7],
  ["OSNABRUCK", "KASSEL", 20],
  ["ESSEN", "MUNSTER", 6],
  ["ESSEN", "DUISBURG", 0],
  ["ESSEN", "DUSSELDORF", 2],
  ["ESSEN", "DORTMUND", 4],
  ["MUNSTER", "DORTMUND", 2],
  ["DUSSELDORF", "KOLN", 4],
  ["DUSSELDORF", "AACHEN", 9],
  ["KASSEL", "DORTMUND", 18],
  ["KASSEL", "FRANKFURT-M", 13],
  ["KASSEL", "FULDA", 8],
  ["KASSEL", "ERFURT", 15],
  ["KOLN", "DUSSELDORF", 4],
  ["KOLN", "DORTMUND", 10],
  ["KOLN", "AACHEN", 7],
  ["KOLN", "TRIER", 20],
  ["KOLN", "WIESBADEN", 21],
  ["FRANKFURT-M", "DORTMUND", 20],
  ["FRANKFURT-M", "WIESBADEN", 0],
  ["FRANKFURT-M", "FULDA", 8],
  ["FRANKFURT-M", "WURZBURG", 13],
  ["TRIER", "AACHEN", 19],
  ["TRIER", "WIESBADEN", 18],
  ["TRIER", "SAARBRUCKEN", 11],
  ["WIESBADEN", "SAARBRUCKEN", 10],
  ["WIESBADEN", "MANNHEIM", 11],
  ["MANNHEIM", "SAARBRUCKEN", 11],
  ["MANNHEIM", "WURZBURG", 10],
  ["MANNHEIM", "STUTTGART", 6],
  ["STUTTGART", "SAARBRUCKEN", 17],
  ["STUTTGART", "FREIBURG", 16],
  ["STUTTGART", "KONSTANZ", 16],
  ["FREIBURG", "KONSTANZ", 14],
  ["STUTTGART", "AUGSBURG", 15],
  ["STUTTGART", "WURZBURG", 12],
  ["AUGSBURG", "KONSTANZ", 17],
  ["AUGSBURG", "MUNCHEN", 6],
  ["AUGSBURG", "REGENSBURG", 13],
  ["AUGSBURG", "NURNBERG", 18],
  ["AUGSBURG", "WURZBURG", 19],
  ["MUNCHEN", "PASSAU", 14],
  ["REGENSBURG", "PASSAU", 12],
  ["REGENSBURG", "MUNCHEN", 10],
  ["REGENSBURG", "AUGSBURG", 13],
  ["REGENSBURG", "NURNBERG", 12],
  ["NURNBERG", "WURZBURG", 8],
  ["NURNBERG", "ERFURT", 21],
  ["WURZBURG", "FULDA", 11],
  ["ERFURT", "FULDA", 13],
  ["ERFURT", "HALLE", 6],
  ["ERFURT", "DRESDEN", 19],
  ["HALLE", "LEIPZIG", 0],
  ["HALLE", "BERLIN", 17],
  ["HALLE", "MAGDEBURG", 11],
  ["LEIPZIG", "DRESDEN", 13],
  ["FRANKFURT-D", "LEIPZIG", 21],
  ["FRANKFURT-D", "DRESDEN", 16],
  ["FRANKFURT-D", "BERLIN", 6],
  ["BERLIN", "MAGDEBURG", 10],
  ["BERLIN", "SCHWERIN", 18],
  ["BERLIN", "TORGELOW", 15],
  ["TORGELOW", "ROSTOCK", 19],
  ["SCHWERIN", "MAGDEBURG", 16],
  ["SCHWERIN", "TORGELOW", 19],
  ["SCHWERIN", "ROSTOCK", 6],
  ["SCHWERIN", "LUBECK", 6],
];

function setDefaultXYPercent(div, boardCnv, board, city) {
  let bheight;
  let bwidth;
  let renderWidth;
  let renderHeight;
  switch (board) {
    case "Germany":
      bheight = 1860;
      bwidth = 1500;
      break;
    default:
      throw new Error("unknown board " + board);
  }
  if (boardCnv.height / boardCnv.width > bheight / bwidth) {
    renderWidth = boardCnv.width;
    renderHeight = bheight * boardCnv.width / bwidth;
  } else {
    renderHeight = boardCnv.height;
    renderWidth = bwidth * boardCnv.height / bheight;
  }
  let loc = cityGermanyDefaults[city];
  let xloc = (boardCnv.width / 2 - renderWidth / 2) + renderWidth * loc.x;
  let yloc = (boardCnv.height / 2 - renderHeight / 2) + renderHeight * loc.y;
  div.xpct = xloc / boardCnv.width;
  div.ypct = yloc / boardCnv.height;
  div.style.left = 100 * div.xpct + "%";
  div.style.top = 100 * div.ypct + "%";
}

function renderDefaultToCanvas(cnv, width, height, assetName, variant) {
  if (assetName == "Germany") {
    return renderGermany(cnv, width, height);
  }
  if (assetName == "supply") {
    return renderSupply(cnv, width, height);
  }
  if (assetName == "coal") {
    return renderCoal(cnv, width, height, width/2, height/2);
  }
  if (assetName == "oil") {
    return renderOil(cnv, width, height, width/2, height/2);
  }
  if (assetName == "gas") {
    return renderGas(cnv, width, height, width/2, height/2);
  }
  if (assetName == "uranium") {
    return renderUranium(cnv, width, height, width/2, height/2);
  }
  if (assetName == "stage3") {
    return renderStage3(cnv, width, height);
  }
  if (assetName.startsWith("plant")) {
    let num = assetName.substring(5, assetName.length);
    return renderPlant(cnv, width, height, num, plantInfo[num]);
  }
}

function renderGermany(cnv, width, height) {
  let bheight = 1860;
  let bwidth = 1500;
  let renderWidth;
  let renderHeight;
  if (height / width > bheight / bwidth) {
    renderWidth = width;
    renderHeight = bheight * width / bwidth;
  } else {
    renderHeight = height;
    renderWidth = bwidth * height / bheight;
  }
  ctx = cnv.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate((width - renderWidth)/2, (height - renderHeight)/2);
  ctx.fillStyle = "darkgreen";
  ctx.fillRect(0, 0, renderWidth, renderHeight);
  let radius = renderWidth * 19 / 600;

  ctx.save();
  ctx.fillStyle = "saddlebrown";
  ctx.fillRect(0, 0, renderWidth, 0.407*renderHeight);
  ctx.beginPath();
  ctx.fillStyle = "red";
  ctx.fillRect(0, 0, 0.493*renderWidth, renderHeight);
  ctx.fillStyle = "cyan";
  ctx.beginPath();
  ctx.moveTo(0.493*renderWidth, 0.472*renderHeight);
  ctx.lineTo(0, 0);
  ctx.lineTo(0.493*renderWidth, 0);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "blue";
  ctx.fillRect(0, 0.54*renderHeight, renderWidth, renderHeight);
  ctx.fillStyle = "yellow";
  ctx.beginPath();
  ctx.moveTo(0.401*renderWidth, 0.572*renderHeight);
  ctx.lineTo(0.493*renderWidth, 0.407*renderHeight);
  ctx.lineTo(renderWidth, 0.407*renderHeight);
  ctx.lineTo(renderWidth, renderHeight);
  ctx.lineTo(0.401*renderWidth, renderHeight);
  ctx.fill();
  ctx.fillStyle = "purple";
  ctx.beginPath();
  ctx.moveTo(0, renderHeight);
  ctx.lineTo(0, 0.851*renderHeight);
  ctx.lineTo(renderWidth, 0.752*renderHeight);
  ctx.lineTo(renderWidth, renderHeight);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  for (let [city1, city2, cost] of cityGermanyConnections) {
    let loc1 = cityGermanyDefaults[city1];
    let loc2 = cityGermanyDefaults[city2];
    ctx.save();
    ctx.lineWidth = radius / 2;
    ctx.strokeStyle = "darkgray";
    ctx.beginPath();
    ctx.moveTo(loc1.x * renderWidth, loc1.y * renderHeight);
    ctx.lineTo(loc2.x * renderWidth, loc2.y * renderHeight);
    ctx.closePath();
    ctx.stroke();

    if (cost != 0) {
      let smallRadius = cost <= 8 ? (radius/2) : (2 * radius / 3);
      ctx.beginPath();
      ctx.arc((loc1.x + loc2.x) * renderWidth / 2, (loc1.y + loc2.y) * renderHeight / 2, smallRadius, 0, 2 * Math.PI, true);
      ctx.closePath();
      ctx.fillStyle = "darkgray";
      ctx.fill();
    }
    ctx.restore();
  }

  for (let city in cityGermanyDefaults) {
    ctx.save();
    ctx.translate(cityGermanyDefaults[city].x * renderWidth, cityGermanyDefaults[city].y * renderHeight);
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, 2 * Math.PI, true);
    ctx.closePath();
    ctx.fillStyle = "gray";
    ctx.fill();

    ctx.fillStyle = "white";
    ctx.fillRect(-5 * radius / 4, 3 * radius / 5, 5 * radius / 2, 2 * radius / 5);
    let newFontSize = getTextSize(ctx, city, 5*radius/2, 2 * radius / 5);
    ctx.font = newFontSize + "px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "black";
    ctx.fillText(city, 0, 4 * radius / 5);
    ctx.restore();
  }

  for (let [city1, city2, cost] of cityGermanyConnections) {
    if (cost == 0) {
      continue;
    }
    let loc1 = cityGermanyDefaults[city1];
    let loc2 = cityGermanyDefaults[city2];
    ctx.save();
    let newFontSize = getTextSize(ctx, cost, 2 * radius / 3, 2 * radius / 3);
    ctx.font = newFontSize + "px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "black";
    ctx.fillText(cost, (loc1.x + loc2.x) * renderWidth / 2, (loc1.y + loc2.y) * renderHeight / 2);
    ctx.restore();
  }

  ctx.restore();
}

function renderSupply(cnv, width, height) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#D2A253";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "black";
  let boxPct = 9.6;
  let uPct = 100/13;
  let spacerPct = (98 - (8*boxPct) - uPct) / 10;
  let boxWidth = width * boxPct / 100;
  let boxHeight = height * 8.75 / 10;
  let vPadding = height - boxHeight;
  for (let i = 0; i < 8; i++) {
    let offset = width * (spacerPct * (i+1) + boxPct * i + 1) / 100;
    renderResourceBox(ctx, offset, vPadding, boxWidth, boxHeight, i+1);
  }
  let subuPct = (uPct - spacerPct) / 2;
  let uboxSize = width * subuPct / 100;
  vPadding = height - 2*uboxSize - width*spacerPct/100;
  for (let i = 0; i < 2; i++) {
    for (let j = 0; j < 2; j++) {
      let offset = width * (100 - spacerPct * (i+1) - subuPct * (i+1) - 1) / 100;
      let yoff = width * (spacerPct * j + subuPct * j) / 100;
      renderUraniumBox(ctx, offset, yoff, vPadding, uboxSize, uboxSize, 10+j*4+(1-i)*2);
    }
  }
  ctx.restore();
}

function renderResourceBox(ctx, offset, vPadding, boxWidth, boxHeight, num) {
  ctx.strokeRect(offset, vPadding/2, boxWidth, boxHeight);
  ctx.beginPath();
  ctx.arc(offset+boxWidth, vPadding, vPadding, 0, 2 * Math.PI, true);
  ctx.closePath();
  ctx.fillStyle = "yellow";
  ctx.fill();
  let newFontSize = getTextSize(ctx, num, 4 * vPadding / 3, 4 * vPadding / 3);
  ctx.font = newFontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "black";
  ctx.fillText(num, offset+boxWidth, vPadding);
}

function renderUraniumBox(ctx, offset, yoff, vPadding, boxWidth, boxHeight, cost) {
  ctx.strokeRect(offset, vPadding/2 + yoff, boxWidth, boxHeight);
  ctx.beginPath();
  ctx.arc(offset+boxWidth, vPadding/2 + yoff, vPadding/2, 0, 2 * Math.PI, true);
  ctx.closePath();
  ctx.fillStyle = "yellow";
  ctx.fill();
  let newFontSize = getTextSize(ctx, cost, 2 * vPadding / 3, 2 * vPadding / 3);
  ctx.font = newFontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "black";
  ctx.fillText(cost, offset+boxWidth, vPadding/2 + yoff);
}

function renderPlant(cnv, width, height, num, info) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "silver";
  ctx.fillRect(0, 0, width, height);
  let colors = {"coal": "saddlebrown", "oil": "black", "green": "green", "uranium": "red", "gas": "gold"};
  ctx.fillStyle = colors[info.resource];
  if (info.resource == "hybrid") {
    ctx.fillStyle = "saddlebrown";
  }
  ctx.fillRect(0, 0, width, height / 4);
  if (info.resource == "hybrid") {
    ctx.fillStyle = "black";
    ctx.fillRect(width/2, 0, width, height / 4);
  }
  // Minimum of intake is 1 to make sure make sure the arrow is centered.
  let numThings = Math.max(info.intake, 1) + 2;
  for (let i = 0; i < info.intake; i++) {
    let numOffset = (numThings-1)/2 - i;
    let centerX = width / 2 - (numOffset * width / 5);
    switch (info.resource) {
      case "coal":
        renderCoal(cnv, width/6, height/6, centerX, 9*height/10);
        break;
      case "oil":
        renderOil(cnv, width/6, height/6, centerX, 9*height/10);
        break;
      case "gas":
        renderGas(cnv, width/6, height/6, centerX, 9*height/10);
        break;
      case "uranium":
        renderUranium(cnv, width/6, height/6, centerX, 9*height/10);
        break;
      case "hybrid":
        renderHybrid(cnv, width/6, height/6, centerX, 9*height/10);
        break;
    }
  }
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  let fontSize = getTextSize(ctx, "⇨", width / 6, height / 6);
  ctx.font = fontSize + "px sans-serif";
  let numOffset = (numThings-1)/2 - (numThings-2);
  let centerX = width / 2 - (numOffset * width / 5);
  ctx.fillText("⇨", centerX, 9*height/10);

  fontSize = getTextSize(ctx, info.output + "", width / 6, height / 6);
  ctx.font = fontSize + "px sans-serif";
  numOffset = (numThings-1)/2 - (numThings-1);
  centerX = width / 2 - (numOffset * width / 5);
  ctx.fillText(info.output + "", centerX, 9*height/10);

  ctx.fillStyle = "white";
  fontSize = getTextSize(ctx, num, width / 4, width / 4);
  ctx.font = fontSize + "px sans-serif";
  ctx.fillText(num, width / 8, height / 8);

  ctx.strokeStyle = "black";
  ctx.strokeRect(0, 0, width, height);
  ctx.strokeRect(0, 4 * height/5, width, height);
  ctx.restore();
}

function renderStage3(cnv, width, height) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "silver";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  let fontSize = getTextSize(ctx, "STAGE 3", 5 * width / 6, height);
  ctx.font = fontSize + "px sans-serif";
  ctx.fillText("STAGE 3", width / 2, height / 2);
  ctx.restore();
}

function renderCoal(cnv, width, height, x, y) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "saddlebrown";
  ctx.fillRect(x - width/2, y - width/2, width, height);
  ctx.restore();
}
function renderOil(cnv, width, height, x, y) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "black";
  ctx.beginPath();
  ctx.arc(x, y, width/2, 0, 2 * Math.PI, true);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
function renderHybrid(cnv, width, height, x, y) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "saddlebrown";
  ctx.fillRect(x - width/2, y - width/2, width/2, height);
  ctx.fillStyle = "black";
  ctx.beginPath();
  ctx.arc(x, y, width/2, -Math.PI/2, Math.PI/2, false);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
function renderGas(cnv, width, height, x, y) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "gold";
  ctx.beginPath();
  ctx.moveTo(x - width/2, y);
  ctx.lineTo(x - width/4, y - 1.732 * height/4);
  ctx.lineTo(x + width/4, y - 1.732 * height/4);
  ctx.lineTo(x + width/2, y);
  ctx.lineTo(x + width/4, y + 1.732 * height/4);
  ctx.lineTo(x - width/4, y + 1.732 * height/4);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
function renderUranium(cnv, width, height, x, y) {
  let length = Math.min(width, height);
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "red";
  ctx.beginPath();
  ctx.moveTo(x - length/2, y - 0.707*length/4);
  ctx.lineTo(x - 0.707*length/4, y - length/2);
  ctx.lineTo(x + 0.707*length/4, y - length/2);
  ctx.lineTo(x + length/2, y - 0.707*length/4);
  ctx.lineTo(x + length/2, y + 0.707*length/4);
  ctx.lineTo(x + 0.707*length/4, y + length/2);
  ctx.lineTo(x - 0.707*length/4, y + length/2);
  ctx.lineTo(x - length/2, y + 0.707*length/4);
  ctx.closePath();
  ctx.fill();
}

function getTextSize(ctx, text, maxWidth, maxHeight) {
  ctx.font = "72px sans-serif";
  let alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
  let widthMeasure = ctx.measureText(text);
  let heightMeasure = ctx.measureText(alphabet);
  let textHeight;
  if (heightMeasure.emHeightAscent) {
    textHeight = heightMeasure.emHeightAscent + heightMeasure.emHeightDescent;
  } else if (heightMeasure.fontBoundingBoxAscent) {
    textHeight = heightMeasure.fontBoundingBoxAscent + heightMeasure.fontBoundingBoxDescent;
  } else {
    textHeight = heightMeasure.actualBoundingBoxAscent + heightMeasure.actualBoundingBoxDescent;
  }
  let shrinkRatio = Math.min(maxWidth / widthMeasure.width, maxHeight / textHeight);
  return Math.floor(72 * shrinkRatio);
}
