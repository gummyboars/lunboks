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
    document.getElementById("myCanvas").width = filterImg.width;
    document.getElementById("myCanvas").height = filterImg.height;
  }
}
function update(e) {
  offsetX = parseFloat(document.getElementById("xoff").value);
  offsetY = parseFloat(document.getElementById("yoff").value);
  scale = parseFloat(document.getElementById("scale").value);
  draw(e);
}
function draw(e) {
  let filter = document.getElementById("filter");
  let newImg = document.getElementById("sourceimg");
  let imgWidth = document.getElementById('sourceimg').width;
  let imgHeight = document.getElementById('sourceimg').height;
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
  if (document.getElementById("filterSrc").value) {
    context.translate(xoff, yoff);
    context.rotate(-Math.PI * rotation / 180);
    context.scale(1/scale, 1/scale);
    context.globalAlpha = 0.3;
    context.drawImage(filter, -filter.width/2, -filter.height/2);
  }
  context.restore();

  var canvas = document.getElementById('myCanvas');

  var context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  if (document.getElementById("filterSrc").value) {
    context.save();
    context.translate(filter.width/2, filter.height/2);
    context.drawImage(filter, -filter.width/2, -filter.height/2);
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
  let imageData = imageInfo[chosen];
  let src = imageData.src;
  let filter = imageData.filter || null;
  let xoff = imageData.xoff || 0;
  let yoff = imageData.yoff || 0;
  let rotation = imageData.rotation || 0;
  let scale = imageData.scale || 1;
  document.getElementById("imgSrc").value = src;
  loadimg();
  document.getElementById("filterSrc").value = filter;
  loadfilter();
  document.getElementById("xoff").value = xoff;
  document.getElementById("yoff").value = yoff;
  document.getElementById("rotation").value = rotation;
  document.getElementById("scale").value = scale;
  update(null);
}
function saveimg() {
  let filterSrc = null;
  if (document.getElementById("filterSrc").value) {
    filterSrc = document.getElementById("filterSrc").value;
  }
  let data = {
    src: document.getElementById("imgSrc").value,
    filter: filterSrc,
    xoff: parseFloat(document.getElementById("xoff").value),
    yoff: parseFloat(document.getElementById("yoff").value),
    rotation: parseFloat(document.getElementById("rotation").value),
    scale: parseFloat(document.getElementById("scale").value),
  }
  localStorage.setItem(document.getElementById("imgname").value, JSON.stringify(data));
}
function initializeNameOptions() {
  for (imgName in imageInfo) {
    let opt = document.createElement("OPTION");
    opt.value = imgName;
    opt.text = imgName;
    document.getElementById("imgname").appendChild(opt);
  }
}
