renderLoops = {};

function getAsset(assetName, variant) {
  let img = document.getElementById("canvas" + assetName + variant);
  if (img == null) {
    img = document.getElementById("canvas" + assetName);
  }
  if (img == null) {
    img = document.getElementById("default" + assetName);
  }
  return img;
}

function renderAssetToCanvas(assetName, variant, canvas) {
  let asset = getAsset(assetName, canvas);
  if (asset == null) {
    return;
  }
  let ctx = canvas.getContext("2d");
  ctx.save();
  ctx.scale(canvas.width / asset.width, canvas.height / asset.height);
  ctx.clearRect(0, 0, asset.width, asset.height);
  ctx.drawImage(asset, 0, 0);
  ctx.restore();
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
