// Expected format of localStorage to use this file:
// sources: a list of image sources as strings. example:
//   sources = ["a.png", "b.png", "c.png"]
// variants: a mapping from asset name to an object with the variants, cycle, and default props.
//   variants = {rsrc1tile: {variants: [0, 1, "other"], cycle: false, default: 0}}
// imageinfo: a mapping from (assetName + variant) to
//   imageinfo = {rsrc2tile: {srcnum: 0, filternum: 1, xoff, yoff, scale, rotation},
//                rsrc1tile0: {srcnum: 2, xoff, yoff, scale, rotation}, ...}
// This file also expects global variable assetNames to be set to a list of asset names.

renderLoops = {};
variants = {};
imageInfo = {};
totalImages = 0;
loadedImages = 0;

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

// TODO: allow variant to be null/undefined
function renderAssetToCanvas(canvas, assetName, variant) {
  let asset = getAsset(assetName, variant);
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

function renderImages() {
  // Reset to make sure we wait for all assets to load again.
  renderLoops = {};
  let assets = document.getElementById("assets");
  while (assets.firstChild) {
    assets.removeChild(assets.firstChild);
  }
  try {
    let sources = JSON.parse(localStorage.getItem("sources") || "[]");
    totalImages = sources.length;
    loadedImages = 0;
    for (let [idx, source] of sources.entries()) {
      let img = document.createElement("IMG");
      img.src = source;
      img.id = "img" + idx;
      img.addEventListener("load", function(e) { loadedImages++; });
      assets.appendChild(img);
    }
    variants = JSON.parse(localStorage.getItem("variants") || "{}");
    imageInfo = JSON.parse(localStorage.getItem("imageinfo") || "{}");
    for (let assetName of assetNames) {
      let variantConfig = variants[assetName];
      let assetVariants;
      if (!variantConfig) {
        assetVariants = [""];
      } else {
        assetVariants = variantConfig.variants;
      }
      for (let variant of assetVariants) {
        let imgData = imageInfo[assetName + variant];
        if (imgData == null) {
          console.log("Missing data for asset " + assetName + variant);
          continue;
        }
        // Not every skin will define every asset.
        if (imgData.srcnum == null) {
          continue;
        }
        let source = document.getElementById("img" + imgData.srcnum);
        if (imgData.filternum == null) {
          renderLoops[assetName + variant] = 1;
          let img = document.createElement("IMG");
          img.src = source.src;
          img.id = "canvas" + assetName + variant;
          assets.appendChild(img);
          img.addEventListener("load", function(e) { finishImgLoad(assetName + variant) });
          // TODO: add listeners for error/abort.
        } else {
          let cnv = document.createElement("CANVAS");
          cnv.id = "canvas" + assetName + variant;
          assets.appendChild(cnv);
          let filter = document.getElementById("img" + imgData.filternum);
          source.addEventListener("load", function(e) {
            renderSource(assetName + variant, cnv, source, filter);
          });
          filter.addEventListener("load", function(e) {
            renderSource(assetName + variant, cnv, source, filter);
          });
        }
      }
    }
  } catch(err) {
    somePromise = new Promise((resolve, reject) => {
      console.log(err);
      failInit(resolve, reject, err.message);
    });
    return somePromise;
  }
  // There's probably a better way to do this (create many promises and resolve them from inside
  // renderSource? How do we get the resolve function in renderSource? Anyway, I'm not going to
  // try to figure it out right now.
  somePromise = new Promise((resolve, reject) => {
    setTimeout(function() { checkInitDone(resolve, reject, 300) }, 100);
  });
  return somePromise;
}

function failInit(resolver, rejecter, errText) {
  rejecter(errText);
}

function checkInitDone(resolver, rejecter, maxTries) {
  if (!maxTries) {
    rejecter("deadline exceeded");
    return;
  }
  let allDone = true;
  for (let iname in renderLoops) {
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
