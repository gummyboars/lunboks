// Expected format of localStorage to use this file:
// variants: a mapping from asset name to an object with the variants, cycle, and default props.
//   variants = {rsrc1tile: {variants: [0, 1, "other"], cycle: false, default: 0}}
// imageinfo: a mapping from (assetName + variant) to
//   imageinfo = {rsrc2tile: {src: "/local/img.png", filter: "http://remote.com/img.png", xoff, yoff, scale, rotation, lazy},
//                rsrc1tile0: {srcnum: "relative.png", xoff, yoff, scale, rotation, lazy}, ...}
// This file also expects global variable assetNames to be set to a list of asset names.

renderLoops = {};
sources = [];
variants = {};
imageInfo = {};
totalImages = 0;
eagerImages = 0;
loadedImages = 0;
errorImages = 0;
imagePromises = [];
resizeTimeout = null;

function equalityFunc(imgSrc) {
  return function(elem) {
    if (elem == imgSrc) {
      return true;
    }
    if (typeof(elem) != "object" || typeof(imgSrc) != "object") {
      return false;
    }
    return elem.shape == imgSrc.shape && elem.width == imgSrc.width && elem.height == imgSrc.height && elem.radius == imgSrc.radius;
  };
}

function setSources() {
  sources = [];
  for (let imgName in imageInfo) {
    let info = imageInfo[imgName];
    if (info.src == null) {
      if (info.src !== undefined) {
        info.srcnum = null;
      }
    } else {
      info.srcnum = sources.findIndex(equalityFunc(info.src));
      if (info.srcnum < 0) {
        info.srcnum = sources.length;
        sources.push(info.src);
      }
    }
    if (info.filter == null) {
      if (info.filter !== undefined) {
        info.filternum = null;
      }
    } else {
      info.filternum = sources.findIndex(equalityFunc(info.filter));
      if (info.filternum < 0) {
        info.filternum = sources.length;
        sources.push(info.filter);
      }
    }
  }
}

function getAsset(assetName, variant) {
  let img = document.getElementById("canvas" + assetName + variant);
  if (img == null) {
    img = document.getElementById("canvas" + assetName);
  }
  if (img == null) {
    img = document.getElementById("default" + assetName + variant);
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

function renderAssetToDiv(div, assetName, variant) {
  variant = variant || "";
  // These will be used to re-render the div when it is resized.
  div.assetName = assetName;
  div.variant = variant;
  // Resize the canvas to match the size of its container.
  let cnv = div.getElementsByTagName("CANVAS")[0];
  let cnvScale = div.cnvScale || 1;
  cnv.width = div.offsetWidth * cnvScale;
  cnv.height = div.offsetHeight * cnvScale;

  // Clear the canvas.
  let ctx = cnv.getContext("2d");
  ctx.clearRect(0, 0, cnv.width, cnv.height);

  // If there is nothing specified for this asset, render the default asset.
  let imgData = imageInfo[assetName + variant] || imageInfo[assetName];
  if (imgData == null) {
    renderDefaultToCanvas(cnv, cnv.width, cnv.height, assetName, variant);
    return new Promise((resolve, reject) => {resolve(true);});
  }
  // If this asset is specified but the source is not, this skin does not want to render this asset.
  if (imgData.srcnum == null) {
    return new Promise((resolve, reject) => {resolve(true);});
  }

  let prom = createImage(imgData.srcnum);
  let handleDefault = function() { renderDefaultToCanvas(cnv, cnv.width, cnv.height, assetName, variant); };
  if (imgData.filternum == null) {
    return prom.then(function() { renderImage(cnv, imgData.srcnum); }, handleDefault);
  }
  return prom.then(function() { renderMaskedImage(cnv, imgData); }, handleDefault);
}

function clearAssetFromDiv(div) {
  div.assetName = null;
  div.variant = null;
  let cnv = div.getElementsByTagName("CANVAS")[0];
  cnv.width = div.offsetWidth;
  cnv.height = div.offsetHeight;
  let ctx = cnv.getContext("2d");
  ctx.clearRect(0, 0, cnv.width, cnv.height);
}

function preloadAsset(assetName, variant) {
  let imgData = imageInfo[assetName + variant] || imageInfo[assetName];
  if (imgData == null || imgData.srcnum == null) {
    return;
  }
  createImage(imgData.srcnum);
}

function renderRatio(orig, destCnv) {
  let imageRatio = (orig.naturalWidth || orig.width) / (orig.naturalHeight || orig.height);
  let cnvRatio = destCnv.width / destCnv.height;
  let renderWidth, renderHeight, scaleMultiplier;
  if (imageRatio > cnvRatio) {
    renderWidth = destCnv.width;
    renderHeight = destCnv.width / imageRatio;
    scaleMultiplier = (orig.naturalWidth || orig.width) / destCnv.width;
  } else {
    renderHeight = destCnv.height;
    renderWidth = destCnv.height * imageRatio;
    scaleMultiplier = (orig.naturalHeight || orig.height) / destCnv.height;
  }
  return [renderWidth, renderHeight, scaleMultiplier];
}

function renderImage(cnv, idx) {
  let img = document.getElementById("img" + idx);
  if (img == null) {
    throw "renderImage: img was null " + idx;
  }
  let renderWidth, renderHeight, unused;
  [renderWidth, renderHeight, unused] = renderRatio(img, cnv);
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.translate(cnv.width/2, cnv.height/2);
  ctx.drawImage(img, -renderWidth/2, -renderHeight/2, renderWidth, renderHeight);
  ctx.restore();
}

function renderMaskedImage(cnv, imgData) {
  let img = document.getElementById("img" + imgData.srcnum);
  let mask = document.getElementById("img" + imgData.filternum);
  if (img == null || mask == null) {
    throw "renderMaskedImage: img or mask was null " + imgData.srcnum + " " + imgData.filternum;
  }

  let xoff = imgData.xoff || 0;
  let yoff = imgData.yoff || 0;
  let rotation = imgData.rotation || 0;
  let scale = imgData.scale || 1;
  let colorDiff = imgData.difference;

  // Calculate rendering size.
  let renderWidth, renderHeight, scaleMultiplier;
  [renderWidth, renderHeight, scaleMultiplier] = renderRatio(mask, cnv);

  // Clear the canvas.
  let ctx = cnv.getContext("2d");
  ctx.clearRect(0, 0, cnv.width, cnv.height);

  ctx.save();
  ctx.translate(cnv.width/2, cnv.height/2);
  // Draw a color correction rectangle if necessary.
  if (colorDiff != null) {
    ctx.fillStyle = colorDiff;
    ctx.fillRect(-cnv.width/2, -cnv.height/2, cnv.width, cnv.height);
    ctx.globalCompositeOperation = "difference";
  }
  // Rotate, scale, draw the base image.
  ctx.rotate(Math.PI * rotation / 180);
  ctx.scale(scale / scaleMultiplier, scale / scaleMultiplier);
  let cssFilter = "";
  for (let filterName of ["contrast", "saturate", "brightness"]) {
    if (imgData[filterName] != null) {
      cssFilter += " " + filterName + "(" + imgData[filterName] + "%)";
    }
  }
  if (cssFilter != "") {
    ctx.filter = cssFilter;
  }
  ctx.drawImage(img, -xoff, -yoff);
  ctx.restore();

  // Now, mask the image using the mask. TODO: rename filter to mask.
  ctx.save();
  ctx.translate(cnv.width/2, cnv.height/2);
  ctx.globalCompositeOperation = "destination-in";
  ctx.drawImage(mask, -renderWidth/2, -renderHeight/2, renderWidth, renderHeight);
  ctx.restore();
}

function setDivXYPercent(div, parentCnv, baseAsset, relativeAsset, fromBottom) {
  if (imageInfo[baseAsset] == null || imageInfo[relativeAsset] == null) {
    return false;
  }
  let xoff = imageInfo[relativeAsset].xoff - imageInfo[baseAsset].xoff;
  let yoff = imageInfo[relativeAsset].yoff - imageInfo[baseAsset].yoff;
  let angle = Math.PI * imageInfo[baseAsset].rotation / 180;
  let xdiff = Math.cos(angle) * xoff - Math.sin(angle) * yoff;
  let ydiff = Math.sin(angle) * xoff + Math.cos(angle) * yoff;
  // TODO: scale
  let baseImg;
  if (imageInfo[baseAsset].filternum != null) {
    baseImg = document.getElementById("img" + imageInfo[baseAsset].filternum);
  } else {
    baseImg = document.getElementById("img" + imageInfo[baseAsset].srcnum);
  }
  let [renderWidth, renderHeight, scaleMultiplier] = renderRatio(baseImg, parentCnv);
  let width = baseImg.naturalWidth || baseImg.width;
  let height = baseImg.naturalHeight || baseImg.height;
  let xpct = (width / 2 + xdiff) / width;
  let ypct = (height / 2 + ydiff) / height;
  xpct = 0.5 - (0.5 - xpct) * renderWidth/parentCnv.width;
  ypct = 0.5 - (0.5 - ypct) * renderHeight/parentCnv.height;
  if (fromBottom) {
    div.style.bottom = 100 * (1-ypct) + "%";
  } else {
    div.style.top = 100 * ypct + "%";
  }
  div.style.left = 100 * xpct + "%";
  div.xpct = xpct;
  div.ypct = ypct;
  return true;
}

function loadImages() {
  let prefix = assetPrefix || "";
  // Parse data and set globals.
  variants = JSON.parse(localStorage.getItem(prefix + "variants") || "{}");
  imageInfo = JSON.parse(localStorage.getItem(prefix + "imageinfo") || "{}");
  setSources();

  imagePromises = [];
  totalImages = sources.length;
  loadedImages = 0;
  errorImages = 0;

  // Just computes which image sources should be eagerly rendered (and how many there are).
  let eagerLoaded = [];
  eagerImages = 0;
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
        continue;
      }
      if (!imgData.lazy) {
        if (imgData.srcnum != null && !eagerLoaded[imgData.srcnum]) {
          eagerImages++;
          eagerLoaded[imgData.srcnum] = true;
        }
      }
      // Filters are always eagerly loaded.
      if (imgData.filternum != null && !eagerLoaded[imgData.filternum]) {
        eagerImages++;
        eagerLoaded[imgData.filternum] = true;
      }
    }
  }

  // Reset assets and loading bar.
  let assets = document.getElementById("assets");
  while (assets.firstChild) {
    assets.removeChild(assets.firstChild);
  }
  if (document.getElementById("uiload") != null) {
    document.getElementById("uiload").style.display = "block";
  }
  updateLoad();

  // Create an element for every image, and return a promise that resolves when all are loaded.
  let promises = [];
  for (let [idx, source] of sources.entries()) {
    if (!eagerLoaded[idx]) {
      continue;
    }
    let promise = createImage(idx);
    promise.then(incrementLoad, incrementError);
    promises.push(promise);
  }
  return Promise.allSettled(promises);
}

function createImage(idx) {
  if (imagePromises[idx] != null) {
    return imagePromises[idx];
  }
  imagePromises[idx] = new Promise((resolve, reject) => {
    let assets = document.getElementById("assets");
    let source = sources[idx];
    let img;
    if (typeof(source) == "object") {
      try {
        img = createShape(source);
        img.id = "img" + idx;
        assets.appendChild(img);
        resolve(idx);
      } catch(err) {
        reject(idx);
      }
    } else {
      img = document.createElement("IMG");
      img.id = "img" + idx;
      img.src = source;
      img.addEventListener("load", function () { resolve(idx); });
      img.addEventListener("error", function () { reject(idx); });
      img.addEventListener("abort", function () { reject(idx); });
      assets.appendChild(img);
    }
  });
  return imagePromises[idx];
}

function rerenderAll() {
  let toRerender = document.getElementsByClassName("cnvcontainer");
  for (let div of toRerender) {
    if (div.assetName == null) {
      continue;
    }
    renderAssetToDiv(div, div.assetName, div.variant);
  }
}

function incrementLoad() {
  loadedImages++;
  updateLoad();
}

function incrementError() {
  errorImages++;
  updateLoad();
}

function updateLoad() {
  let loadbar = document.getElementById("loadingbar");
  if (loadbar != null) {
    loadbar.style.width = (100 * loadedImages / eagerImages) + "%";
  }
  let errorbar = document.getElementById("errorbar");
  if (errorbar != null) {
    errorbar.style.width = (100 * errorImages / eagerImages) + "%";
  }
  let loadspan = document.getElementById("loadcount");
  if (loadspan != null) {
    let loadCount = String(loadedImages) + " / " + String(eagerImages);
    if (errorImages > 0) {
      loadCount += " (" + String(errorImages) + " errors)";
    }
    loadspan.innerText = loadCount;
  }
  let uiload = document.getElementById("uiload");
  if (uiload != null && (loadedImages + errorImages) == eagerImages) {
    document.getElementById("uiload").style.display = "none";
  }
}

function failRender(assetName, cnv) {
  console.warn("Could not render asset " + assetName);
  // TODO: this can still be a problem if you are switching to a skin whose sources 404.
  if (cnv != null) {  // Can sometimes fail before we even create the canvas.
    cnv.parentNode.removeChild(cnv);
  }
}

function createShape(specs) {
  let cnv = document.createElement("CANVAS");
  if (specs.shape == "rect") {
    cnv.width = specs.width;
    cnv.height = specs.height;
  } else if (specs.shape == "circle") {
    cnv.width = specs.radius * 2;
    cnv.height = specs.radius * 2;
  }
  let ctx = cnv.getContext("2d");
  if (specs.style) {
    ctx.fillStyle = specs.style;
  }
  if (specs.shape == "rect") {
    ctx.fillRect(0, 0, specs.width, specs.height);
  } else if (specs.shape == "circle") {
    ctx.arc(specs.radius, specs.radius, specs.radius, 0, 2 * Math.PI);
    ctx.fill();
  }
  return cnv;
}

function renderImages() {
  loadImages();
  let renderPromises = [];
  for (let assetName of assetNames) {
    let variantConfig = variants[assetName];
    let assetVariants = [""];
    if (variantConfig) {
      assetVariants = variantConfig.variants;
    }
    for (let variant of assetVariants) {
      let imgData = imageInfo[assetName + variant];
      if (imgData == null || imgData.srcnum == null) {
        continue;
      }
      let cnv = document.createElement("CANVAS");
      cnv.id = "canvas" + assetName + variant;
      assets.appendChild(cnv);
      let imgPromise = createImage(imgData.srcnum);
      if (imgData.filternum != null) {
        let finishRender = function() {
          let img = document.getElementById("img" + imgData.filternum);
          cnv.width = img.naturalWidth || img.width;
          cnv.height = img.naturalHeight || img.height;
          renderMaskedImage(cnv, imgData);
        };
        imgPromise = Promise.all([createImage(imgData.srcnum), createImage(imgData.filternum)]);
        renderPromises.push(imgPromise.then(finishRender, () => failRender(assetName + variant, cnv)));
      } else {
        let finishRender = function() {
          let img = document.getElementById("img" + imgData.srcnum);
          cnv.width = img.naturalWidth || img.width;
          cnv.height = img.naturalHeight || img.height;
          renderImage(cnv, imgData.srcnum);
        }
        renderPromises.push(imgPromise.then(finishRender, () => failRender(assetName + variant, cnv)));
      }
    }
  }
  return Promise.allSettled(renderPromises);
}

window.addEventListener("resize", function() {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(rerenderAll, 250);
});
