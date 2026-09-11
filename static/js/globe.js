/**
 * CesiumJS 3D Globe visualization for airport locations.
 * Token-free OpenStreetMap imagery configuration with interactive 3D markers.
 */

let viewer = null;
const airportEntities = new Map();
let selectedAirport = null;

/* Kiosk Mode state */
let kioskActive = false;
let kioskAirportList = [];
let kioskIndex = 0;
let kioskDwellTimer = null;
let kioskDwellSeconds = 60;

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await initCesiumGlobe();
    setupGlobeControls();
    initPolling(onGlobeDataReceived);
  } catch (error) {
    document.getElementById("globeError").hidden = false;
    document.getElementById("updatedText").textContent = "Globe unavailable";
    console.error("Unable to initialize globe:", error);
  }
});

/**
 * Initialize CesiumJS Viewer with token-free OpenStreetMap imagery.
 */
async function initCesiumGlobe() {
  // Fetch optional client config
  try {
    const cfgRes = await fetch("/api/config", { signal: AbortSignal.timeout(10000) });
    if (cfgRes.ok) {
      const cfg = await cfgRes.json();
      if (Number.isFinite(cfg.kiosk_dwell_seconds) && cfg.kiosk_dwell_seconds > 0) {
        kioskDwellSeconds = cfg.kiosk_dwell_seconds;
      }
    }
  } catch (err) {
    console.warn("Could not fetch client config:", err);
  }

  // Fetch Cesium Ion token separately from config
  let ionToken = "";
  try {
    const tokenRes = await fetch("/api/cesium-token", { signal: AbortSignal.timeout(10000) });
    if (tokenRes.ok) {
      const tokenData = await tokenRes.json();
      ionToken = tokenData.token || "";
    }
  } catch (err) {
    console.warn("Could not fetch Cesium token:", err);
  }
  Cesium.Ion.defaultAccessToken = ionToken;

  // OpenStreetMap tile provider
  const osmProvider = new Cesium.UrlTemplateImageryProvider({
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    maximumLevel: 19,
    credit: "© OpenStreetMap contributors",
  });

  viewer = new Cesium.Viewer("cesiumContainer", {
    baseLayer: new Cesium.ImageryLayer(osmProvider),
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
  });

  // Enable subtle lighting and atmosphere
  viewer.scene.globe.enableLighting = false; // keep all airports clearly visible day and night
  // Enable depth testing so objects behind the globe are occluded
  viewer.scene.globe.depthTestAgainstTerrain = true;

  // Initial global view centering on Atlantic/Americas/Europe
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(-30.0, 15.0, 24000000),
  });

  // Dynamically update point & label visibility based on camera horizon occlusion
  viewer.scene.preRender.addEventListener(updateEntityVisibility);

  // Mouse interaction handler for clicking airport entities
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

  handler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position);
    if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.airportData) {
      stopKiosk();
      showAirportDrawer(pickedObject.id.airportData);
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  // Change cursor to pointer on hover
  handler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.endPosition);
    if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.airportData) {
      viewer.scene.canvas.style.cursor = "pointer";
    } else {
      viewer.scene.canvas.style.cursor = "default";
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
}

/**
 * Test and toggle entity visibility so points and labels on the far side of the Earth
 * (not currently in view) are hidden.
 */
function updateEntityVisibility() {
  if (!viewer || !viewer.scene || !viewer.scene.camera) return;

  const cameraPos = viewer.scene.camera.positionWC;
  const occluder = new Cesium.EllipsoidalOccluder(Cesium.Ellipsoid.WGS84, cameraPos);

  airportEntities.forEach((entity) => {
    const airport = entity.airportData;
    if (!airport) return;

    // Position at altitude corresponding to the marker
    const pos = Cesium.Cartesian3.fromDegrees(airport.longitude, airport.latitude, 20000);
    const isVisible = occluder.isPointVisible(pos);

    if (entity.show !== isVisible) {
      entity.show = isVisible;
    }
  });
}

/**
 * Handle data update from 60s polling cycle.
 */
function onGlobeDataReceived(data) {
  if (!viewer || !data || !data.results) return;

  data.results.forEach((airport) => {
    updateOrCreateAirportEntity(airport);
  });

  // Update visibility immediately after adding or updating entities
  updateEntityVisibility();

  // If an airport was previously selected, refresh its drawer content
  if (selectedAirport) {
    const updated = data.results.find((d) => d.code === selectedAirport.code);
    if (updated) {
      showAirportDrawer(updated);
    }
  }
}

/**
 * Render or update 3D point and label on the globe.
 */
function updateOrCreateAirportEntity(airport) {
  const color = Cesium.Color.fromCssColorString("#38bdf8");
  const position = Cesium.Cartesian3.fromDegrees(airport.longitude, airport.latitude, 20000);

  if (airportEntities.has(airport.code)) {
    const entity = airportEntities.get(airport.code);
    entity.airportData = airport;
    if (entity.point) {
      entity.point.color = color;
    }
  } else {
    const entity = viewer.entities.add({
      id: `airport-${airport.code}`,
      name: `${airport.code} - ${airport.city}`,
      position: position,
      point: {
        pixelSize: 14,
        color: color,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.NONE,
      },
      label: {
        text: airport.code,
        font: 'bold 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        pixelOffset: new Cesium.Cartesian2(0, -16),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      },
    });

    entity.airportData = airport;
    airportEntities.set(airport.code, entity);
  }
}

/**
 * Populate and display floating airport details drawer.
 */
function showAirportDrawer(airport) {
  selectedAirport = airport;
  const drawer = document.getElementById("airportDrawer");
  if (!drawer) return;

  document.getElementById("drawerCode").textContent = airport.code;
  document.getElementById("drawerCity").textContent = `${airport.city}, ${airport.country}`;
  document.getElementById("drawerAirport").textContent = airport.name;
  document.getElementById("drawerLocalTime").textContent = formatLocalTime(airport);
  document.getElementById("drawerTimezone").textContent = formatTimeZone(airport);
  document.getElementById("drawerWeekend").textContent = formatWeekend(airport);
  drawer.hidden = false;
}

function startKiosk() {
  if (airportEntities.size === 0) return;

  kioskActive = true;
  document.getElementById("btnKioskMode").setAttribute("aria-pressed", "true");
  kioskAirportList = Array.from(airportEntities.keys()).sort();
  kioskIndex = 0;

  const btn = document.getElementById("btnKioskMode");
  if (btn) {
    btn.textContent = "■ Stop Kiosk";
    btn.classList.add("active", "kiosk-active");
  }

  kioskFlyToNext();
}

function stopKiosk() {
  if (!kioskActive) return;
  kioskActive = false;
  if (viewer) viewer.camera.cancelFlight();
  document.getElementById("btnKioskMode").setAttribute("aria-pressed", "false");

  if (kioskDwellTimer) {
    clearTimeout(kioskDwellTimer);
    kioskDwellTimer = null;
  }

  const btn = document.getElementById("btnKioskMode");
  if (btn) {
    btn.textContent = "▶ Kiosk Mode";
    btn.classList.remove("active", "kiosk-active");
  }
}

function kioskFlyToNext() {
  if (!kioskActive || !viewer) return;

  if (kioskIndex >= kioskAirportList.length) {
    kioskIndex = 0;
  }

  const airportCode = kioskAirportList[kioskIndex];
  const entity = airportEntities.get(airportCode);

  if (!entity || !entity.airportData) {
    kioskIndex++;
    setTimeout(() => kioskFlyToNext(), 0);
    return;
  }

  const airport = entity.airportData;
  showAirportDrawer(airport);

  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      airport.longitude,
      airport.latitude - 1.5,
      2500000
    ),
    duration: 1.5,
    complete: function () {
      if (!kioskActive) return;
      kioskDwellTimer = setTimeout(() => {
        if (!kioskActive) return;
        kioskIndex++;
        kioskFlyToNext();
      }, kioskDwellSeconds * 1000);
    },
    cancel: function () { stopKiosk(); },
  });
}

/**
 * Setup camera preset controls and drawer interaction.
 */
function setupGlobeControls() {
  // Drawer close button
  const closeBtn = document.getElementById("drawerCloseBtn");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      stopKiosk();
      const drawer = document.getElementById("airportDrawer");
      if (drawer) drawer.hidden = true;
      selectedAirport = null;
    });
  }

  // Zoom to airport button
  const zoomBtn = document.getElementById("drawerZoomBtn");
  if (zoomBtn) {
    zoomBtn.addEventListener("click", () => {
      stopKiosk();
      if (selectedAirport && viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(
            selectedAirport.longitude,
            selectedAirport.latitude - 1.5,
            2500000
          ),
          duration: 1.5,
        });
      }
    });
  }

  // Region View Buttons
  const btnGlobal = document.getElementById("btnViewGlobal");
  if (btnGlobal) {
    btnGlobal.addEventListener("click", () => {
      stopKiosk();
      if (viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(-30.0, 15.0, 24000000),
          duration: 1.5,
        });
      }
    });
  }

  // Americas (combined North & South America)
  const btnAmericas = document.getElementById("btnViewAmericas");
  if (btnAmericas) {
    btnAmericas.addEventListener("click", () => {
      stopKiosk();
      if (viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(-75.0, 5.0, 16000000),
          duration: 1.5,
        });
      }
    });
  }

  // North America
  const btnNorthAmerica = document.getElementById("btnViewNorthAmerica");
  if (btnNorthAmerica) {
    btnNorthAmerica.addEventListener("click", () => {
      stopKiosk();
      if (viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(-96.0, 38.0, 8500000),
          duration: 1.5,
        });
      }
    });
  }

  // South America
  const btnSouthAmerica = document.getElementById("btnViewSouthAmerica");
  if (btnSouthAmerica) {
    btnSouthAmerica.addEventListener("click", () => {
      stopKiosk();
      if (viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(-64.0, -18.0, 9000000),
          duration: 1.5,
        });
      }
    });
  }

  // Europe
  const btnEurope = document.getElementById("btnViewEurope");
  if (btnEurope) {
    btnEurope.addEventListener("click", () => {
      stopKiosk();
      if (viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(10.0, 48.0, 6000000),
          duration: 1.5,
        });
      }
    });
  }

  // Asia-Pacific
  const btnAPAC = document.getElementById("btnViewAPAC");
  if (btnAPAC) {
    btnAPAC.addEventListener("click", () => {
      stopKiosk();
      if (viewer) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(140.0, 5.0, 16000000),
          duration: 1.5,
        });
      }
    });
  }

  // Kiosk Mode toggle
  const btnKiosk = document.getElementById("btnKioskMode");
  if (btnKiosk) {
    btnKiosk.addEventListener("click", () => {
      if (kioskActive) {
        stopKiosk();
      } else {
        startKiosk();
      }
    });
  }
}
