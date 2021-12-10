isDragging = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;
scale = 1;
function wheelie(event) {
  event.preventDefault();
  if (event.deltaY < 0) {
    scale -= 0.05;
  } else if (event.deltaY > 0) {
    scale += 0.05;
  }
  scale = Math.min(Math.max(0.05, scale), 20);
  document.getElementById("scale").value = scale;
  draw(null);
}
function onmove(event) {
  if (isDragging) {
    let newX = event.clientX;
    let newY = event.clientY;
    dX = newX - startX;
    dY = newY - startY;
    document.getElementById("xoff").value = dX + offsetX;
    document.getElementById("yoff").value = dY + offsetY;
    draw(null);
  }
}
function ondown(event) {
  if (event.button != 0) {
    return;
  }
  startX = event.clientX;
  startY = event.clientY;
  isDragging = true;
}
function onup(event) {
  if (event.button != 0) {
    return;
  }
  isDragging = false;
  offsetX += dX;
  offsetY += dY;
  dX = 0;
  dY = 0;
  document.getElementById("xoff").value = dX + offsetX;
  document.getElementById("yoff").value = dY + offsetY;
  draw(null);
}
function loadimg() {
  let sourceImg = document.getElementById("sourceimg");
  sourceImg.src = document.getElementById("imgSrc").value;
  sourceImg.onload = draw;
}
function loadfilter() {
  if (document.getElementById("filterSrc").value) {
    let filterImg = document.getElementById("filter");
    filterImg.src = document.getElementById("filterSrc").value;
    filterImg.onload = draw;
  }
}
function update(e) {
  offsetX = parseFloat(document.getElementById("xoff").value);
  offsetY = parseFloat(document.getElementById("yoff").value);
  scale = parseFloat(document.getElementById("scale").value);
  draw(e);
}
function changeFilter(e) {
  let filterType = document.getElementById("filterType").value;
  document.getElementById("filterSrc").disabled = true;
  document.getElementById("filterWidth").disabled = true;
  document.getElementById("filterHeight").disabled = true;
  document.getElementById("filterRadius").disabled = true;
  if (filterType == "image") {
    document.getElementById("filterSrc").disabled = false;
  } else if (filterType == "rectangle") {
    document.getElementById("filterWidth").disabled = false;
    document.getElementById("filterHeight").disabled = false;
  } else if (filterType == "circle") {
    document.getElementById("filterRadius").disabled = false;
  }
  update(e);
}
function draw(e) {
  let filter = document.getElementById("filter");
  let newImg = document.getElementById("sourceimg");
  let imgWidth = document.getElementById('sourceimg').width;
  let imgHeight = document.getElementById('sourceimg').height;
  let filterType = document.getElementById("filterType").value;
  let myCanvas = document.getElementById("myCanvas");
  if (filterType == "image" && document.getElementById("filterSrc").value) {
    myCanvas.width = filter.width;
    myCanvas.height = filter.height;
  } else if (filterType == "rectangle") {
    myCanvas.width = document.getElementById("filterWidth").value;
    myCanvas.height = document.getElementById("filterHeight").value;
  } else if (filterType == "circle") {
    let rad = parseFloat(document.getElementById("filterRadius").value);
    myCanvas.width = 2 * rad;
    myCanvas.height = 2 * rad;
  } else {
    myCanvas.width = imgWidth;
    myCanvas.height = imgHeight;
  }
  let orig = document.getElementById('orig');
  orig.width = imgWidth;
  orig.height = imgHeight;
  let xoff = document.getElementById("xoff").value;
  let yoff = document.getElementById("yoff").value;
  let scale = document.getElementById("scale").value;
  let rotation = document.getElementById("rotation").value;

  var context = orig.getContext('2d');
  context.save();
  context.drawImage(newImg, 0, 0);
  if (filterType != "none") {
    context.translate(xoff, yoff);
    context.rotate(-Math.PI * rotation / 180);
    context.scale(1/scale, 1/scale);
    context.globalAlpha = 0.3;
    if (filterType == "image" && document.getElementById("filterSrc").value) {
      context.drawImage(filter, -filter.width/2, -filter.height/2);
    } else if (filterType == "rectangle") {
      context.fillRect(-myCanvas.width/2, -myCanvas.height/2, myCanvas.width, myCanvas.height);
    } else if (filterType == "circle") {
      context.arc(0, 0, myCanvas.width/2, 0, 2 * Math.PI);
      context.fill();
    }
  }
  context.restore();

  var canvas = document.getElementById('myCanvas');

  var context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  if (filterType != "none") {
    context.save();
    context.translate(canvas.width/2, canvas.height/2);
    if (filterType == "image" && document.getElementById("filterSrc").value) {
      context.drawImage(filter, -filter.width/2, -filter.height/2);
    } else if (filterType == "rectangle") {
      context.fillRect(-canvas.width/2, -canvas.height/2, canvas.width, canvas.height);
    } else if (filterType == "circle") {
      context.arc(0, 0, canvas.width/2, 0, 2 * Math.PI);
      context.fill();
    }
    context.rotate(Math.PI * rotation / 180);
    context.scale(scale, scale);
    context.globalCompositeOperation = "source-in";
    context.drawImage(newImg, -xoff, -yoff);
    context.restore();
  } else {
    context.save();
    context.drawImage(newImg, -xoff, -yoff);
    context.restore();
  }
}
function changebg(e) {
  document.getElementsByTagName("BODY")[0].style.background = document.getElementById("bgcolor").value;
}
function choosenew(e) {
  let chosen = document.getElementById("imgname").value;
  let variants = JSON.parse(localStorage.getItem(assetPrefix + "customvariants") || "{}")[chosen];
  updatevariants(variants);
  let imageData = JSON.parse(localStorage.getItem(assetPrefix + "customimageinfo") || "{}")[chosen];
  let sources = JSON.parse(localStorage.getItem(assetPrefix + "customsources") || "[]");
  if (!imageData) {
    imageData = {};
    document.getElementById("imgSrc").value = "";
    loadimg();
    loadfilter();
    update(null);
    return;
  }
  let src = sources[imageData.srcnum];
  let filterType = "none";
  let filterSrc = null;
  let filterWidth = null;
  let filterHeight = null;
  let filterRadius = null;
  if (imageData.filternum != null) {
    let filter = sources[imageData.filternum];
    if (typeof(filter) == "object") {
      if (filter.shape == "rect") {
        filterType = "rectangle";
        filterWidth = filter.width;
        filterHeight = filter.height;
      } else if (filter.shape == "circle") {
        filterType = "circle";
        filterRadius = filter.radius;
      }
    } else {
      filterType = "image";
      filterSrc = filter;
    }
  }
  let xoff = imageData.xoff || 0;
  let yoff = imageData.yoff || 0;
  let rotation = imageData.rotation || 0;
  let scale = imageData.scale || 1;
  document.getElementById("imgSrc").value = src;
  loadimg();
  document.getElementById("filterType").value = filterType;
  document.getElementById("filterSrc").value = filterSrc;
  document.getElementById("filterWidth").value = filterWidth;
  document.getElementById("filterHeight").value = filterHeight;
  document.getElementById("filterRadius").value = filterRadius;
  loadfilter();
  document.getElementById("xoff").value = xoff;
  document.getElementById("yoff").value = yoff;
  document.getElementById("rotation").value = rotation;
  document.getElementById("scale").value = scale;
  changeFilter(null);
}
function updatevariants(variants) {
  let dlist = document.getElementById("variantchoice");
  while (dlist.firstChild) {
    dlist.removeChild(dlist.firstChild);
  }
  if (!variants) {
    variants = {"variants": [""]};
  }
  for (variant of variants["variants"]) {
    let opt = document.createElement("OPTION");
    opt.value = variant;
    if (variant == "") {
      opt.text = "(default)";
    } else {
      opt.text = variant;
    }
    dlist.appendChild(opt);
  }
}
function saveimg() {
  let imgName = document.getElementById("imgname").value;
  let imgVariant = document.getElementById("imgvariant").value;
  let imgSrc = document.getElementById("imgSrc").value;
  let filterType = document.getElementById("filterType").value;
  let filterSrc = null;
  if (filterType != "none") {
    if (filterType == "image" && document.getElementById("filterSrc").value) {
      filterSrc = document.getElementById("filterSrc").value;
    } else if (filterType == "rectangle") {
      filterSrc = {
        "shape": "rect",
        "width": parseFloat(document.getElementById("filterWidth").value),
        "height": parseFloat(document.getElementById("filterHeight").value),
      };
    } else if (filterType == "circle") {
      filterSrc = {
        "shape": "circle",
        "radius": parseFloat(document.getElementById("filterRadius").value),
      };
    }
  }
  let currentSources = JSON.parse(localStorage.getItem(assetPrefix + "customsources") || "[]");
  let imgSrcEquality = function(elem) {
    if (elem == imgSrc) {
      return true;
    }
    if (typeof(elem) != "object" || typeof(imgSrc) != "object") {
      return false;
    }
    return elem.shape == imgSrc.shape && elem.width == imgSrc.width && elem.height == imgSrc.height && elem.radius == imgSrc.radius;
  };
  let imgIdx = currentSources.findIndex(imgSrcEquality);
  if (imgIdx < 0) {
    imgIdx = currentSources.length;
    currentSources.push(imgSrc);
  }
  let filterIdx = null;
  if (filterSrc != null) {
    let filterSrcEquality = function(elem) {
      if (elem == filterSrc) {
        return true;
      }
      if (typeof(elem) != "object" || typeof(filterSrc) != "object") {
        return false;
      }
      return elem.shape == filterSrc.shape && elem.width == filterSrc.width && elem.height == filterSrc.height && elem.radius == filterSrc.radius;
    };
    filterIdx = currentSources.findIndex(filterSrcEquality);
    if (filterIdx < 0) {
      filterIdx = currentSources.length;
      currentSources.push(filterSrc);
    }
  }
  let variantInfo = JSON.parse(localStorage.getItem(assetPrefix + "customvariants") || "{}");
  if (imgVariant != "") {
    // TODO: cleanup unused image variants. And allow images without a default variant.
    if (!variantInfo[imgName]) {
      variantInfo[imgName] = {"variants": [""]};
    }
    if (!variantInfo[imgName]["variants"].includes(imgVariant)) {
      variantInfo[imgName]["variants"].push(imgVariant);
    }
  }
  let imageInfo = JSON.parse(localStorage.getItem(assetPrefix + "customimageinfo") || "{}");
  let data = {
    xoff: parseFloat(document.getElementById("xoff").value),
    yoff: parseFloat(document.getElementById("yoff").value),
    rotation: parseFloat(document.getElementById("rotation").value),
    scale: parseFloat(document.getElementById("scale").value),
    srcnum: imgIdx,
  }
  if (filterIdx != null) {
    data.filternum = filterIdx;
  }
  imageInfo[imgName + imgVariant] = data;
  compactSources(currentSources, imageInfo);
  localStorage.setItem(assetPrefix + "customsources", JSON.stringify(currentSources));
  localStorage.setItem(assetPrefix + "customvariants", JSON.stringify(variantInfo));
  localStorage.setItem(assetPrefix + "customimageinfo", JSON.stringify(imageInfo));
  localStorage.setItem(assetPrefix + "sources", JSON.stringify(currentSources));
  localStorage.setItem(assetPrefix + "variants", JSON.stringify(variantInfo));
  localStorage.setItem(assetPrefix + "imageinfo", JSON.stringify(imageInfo));
  document.getElementById("sources").value = localStorage.getItem(assetPrefix + "sources");
  document.getElementById("variants").value = localStorage.getItem(assetPrefix + "variants");
  document.getElementById("imageinfo").value = localStorage.getItem(assetPrefix + "imageinfo");
}
function compactSources(sources, imageInfo) {
  let usedIdxs = {};
  for (let [key, info] of Object.entries(imageInfo)) {
    if (!usedIdxs[info.srcnum]) {
      usedIdxs[info.srcnum] = [];
    }
    usedIdxs[info.srcnum].push(key);
    if (info.filternum != null) {
      if (!usedIdxs[info.filternum]) {
        usedIdxs[info.filternum] = [];
      }
      usedIdxs[info.filternum].push(key);
    }
  }
  let unusedIdxs = [];
  for (let i = 0; i < sources.length; i++) {
    if (!usedIdxs[i]) {
      unusedIdxs.push(i);
    }
  }
  let swaps = {};
  let count = 0;
  let i = sources.length;
  while (count < unusedIdxs.length && i > 0) {
    i--;
    if (unusedIdxs.includes(i)) {
      continue;
    }
    swaps[i] = unusedIdxs[count];
    count++;
  }
  for (let [from, to] of Object.entries(swaps)) {
    sources[to] = sources[from];
    sources[from] = null;
    for (let key of usedIdxs[from]) {
      if (imageInfo[key].srcnum == from) {
        imageInfo[key].srcnum = to;
      }
      if (imageInfo[key].filternum == from) {
        imageInfo[key].filternum = to;
      }
    }
  }
  while (sources.length > 0 && sources[sources.length - 1] == null) {
    sources.pop();
  }
}
function initializeAssetNames() {
  while (document.getElementById("imgname").children.length) {
    document.getElementById("imgname").removeChild(document.getElementById("imgname").firstChild);
  }
  for (imgName of assetNames) {
    let opt = document.createElement("OPTION");
    opt.value = imgName;
    opt.text = imgName;
    document.getElementById("imgname").appendChild(opt);
  }
  choosenew();
}
function initializeNameStrings() {
  let nameDiv = document.getElementById("names");
  while (nameDiv.children.length) {
    nameDiv.removeChild(nameDiv.firstChild);
  }
  let names = JSON.parse(localStorage.getItem(assetPrefix + "customnames") || "{}");
  for (let name in serverNames) {
    let newDiv = document.createElement("DIV");
    let namespan = document.createElement("SPAN");
    namespan.innerText = name;
    let input = document.createElement("INPUT");
    input.type = "text";
    input.id = name;
    input.value = names[name] || serverNames[name];
    newDiv.appendChild(namespan);
    newDiv.appendChild(input);
    nameDiv.appendChild(newDiv);
  }
}
function changesource(e) {
  initializeNameStrings();
  initializeAssetNames();
}
function changegroup(e) {
  let old = document.getElementById("assetsource");
  if (old != null) {
    old.parentNode.removeChild(old);
  }
  let chosen = document.getElementById("assetgroup").value;
  newScript = document.createElement("SCRIPT");
  newScript.onload = changesource;
  newScript.src = chosen;
  newScript.id = "assetsource";
  document.getElementsByTagName("HEAD")[0].appendChild(newScript);
}
function savenames(e) {
  let currentNames = JSON.parse(localStorage.getItem(assetPrefix + "customnames") || "{}");
  for (let name in serverNames) {
    currentNames[name] = document.getElementById(name).value;
  }
  localStorage.setItem(assetPrefix + "customnames", JSON.stringify(currentNames));
  localStorage.setItem(assetPrefix + "names", JSON.stringify(currentNames));
  document.getElementById("shownames").value = localStorage.getItem(assetPrefix + "names");
}
