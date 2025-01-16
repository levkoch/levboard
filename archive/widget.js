/**
 * Widget code for a Scriptable widget. Works on iOS, iPadOS, and MacOS Sonoma.
 * Requires Scriptable: https://apps.apple.com/app/id1405459188
 * Copy & Paste into your files, and change the API keys in the function below to 
 * point to your spreadsheet and utilize your Google Service Account.
 */

async function loadData(segment) {
  // CHANGE THESE !!
  var spreadsheet_id = "1_SPREADSHEET";
  var api_key = "API_KEY";
  // CHANGE THESE !!
  const url =
    "https://sheets.googleapis.com/v4/spreadsheets/" +
    spreadsheet_id +
    "/values/" +
    segment +
    "?alt=json&key=" +
    api_key;
  console.log(url);
  var r = new Request(url);
  var data = await r.loadJSON();
  console.log(data);
  return data.values;
}

let widget = await createWidget();
if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  widget.presentMedium();
}
Script.complete();

async function createWidget(api) {
  let appIcon = await loadAppIcon();
  let widget = new ListWidget();
  let gradient = new LinearGradient();
  gradient.locations = [0, 1];
  gradient.colors = [new Color("FFFFFF"), new Color("F1F1F1")];
  widget.backgroundGradient = gradient;

  let titleStack = widget.addStack();
  titleStack.layoutHorizontally();
  titleStack.centerAlignContent();

  let appIconElement = titleStack.addImage(appIcon);
  appIconElement.imageSize = new Size(24, 24);
  appIconElement.cornerRadius = 6;
  titleStack.addSpacer(8);
  title = titleStack.addText("LEVBOARD ALBUMS");
  title.font = Font.mediumRoundedSystemFont(24);
  title.textColor = new Color("3D3D3D");

  widget.addSpacer(8);
  let mainStack = widget.addStack();
  mainStack.layoutVertically();

  const albums_n_changes = await loadData("Recent!A28:B32");
  const albums = [];
  const changes = [];
  for (var i = 0; i < albums_n_changes.length; i += 1) {
    albums.push(albums_n_changes[i][1]);
    changes.push(albums_n_changes[i][0]);
  }
  const allImages = await loadImageMapping();

  let albumStack = widget.addStack();
  albumStack.layoutHorizontally();
  albumStack.spacing = 8;

  for (var i = 0; i < albums.length; i += 1) {
    let image = await loadImage(getAlbumLink(albums[i], allImages));
    let canvas = new DrawContext();
    canvas.respectScreenScale = true;
    canvas.size = new Size(50, 50);
    canvas.setFillColor(new Color("F1F1F1"));
    canvas.drawImageInRect(image, new Rect(0, 0, 50, 50));
    var position = new Rect(30, 30, 16, 16);
    canvas.fillEllipse(position);

    let change = changes[i];
    var symbol;

    if (change.startsWith("▲")) {
      symbol = SFSymbol.named("arrow.up");
    } else if (change.startsWith("▼")) {
      symbol = SFSymbol.named("arrow.down");
    } else if (change.startsWith("=")) {
      symbol = SFSymbol.named("arrow.right");
    } else {
      symbol = SFSymbol.named("star");
    }
    symbol.applyMediumWeight();
    position = new Rect(32, 32, 12, 12);
    canvas.drawImageInRect(symbol.image, position);
    let element = albumStack.addImage(canvas.getImage());
    element.cornerRadius = 10;
  }
  return widget;
}

async function loadSongs(segment) {
  var data = await loadData(segment);
  var songs = [];

  for (var i = 0; i < data.length; i += 1) {
    var place = data[i];
    songs.push(place[0]);
  }
  return songs;
}

function getSongLink(name, all) {
  if (name + " (Single)" in all) {
    return all[name + " (Single)"];
  } else {
    return getAlbumLink(name, all);
  }
}

function getAlbumLink(name, all) {
  if (name in all) {
    return all[name];
  } else {
    // defaults to levboard logo
    return "https://i.imgur.com/fnTODuo.png";
  }
}

async function loadImageMapping() {
  var data = await loadData("Images!A2:E");
  var info = {};
  for (var i = 0; i < data.length; i += 1) {
    if (data[i][1] == "Album") {
      info[data[i][0]] = data[i][4];
    }
  }
  return info;
}

async function loadImage(url) {
  return new Request(url).loadImage();
}

async function loadAppIcon() {
  // the url of the lime levboard logo
  return loadImage("http://i.imgur.com/fnTODuo.png");
}
