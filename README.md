<p align="center">
  <img src="images/hero.png" width="240" alt="Watch face preview from the Digital template on Amazfit Active 2 Round">
</p>

<h1 align="center">WatchFace Studio</h1>

<p align="center">
  <strong>Graphical watch face editor — build, test, and export your watch face without writing code.</strong><br>
  Amazfit Active 2 Round · 466×466 · Zepp OS 5
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Zepp%20OS%205-ff6b3d?style=flat-square" alt="Zepp OS 5">
  <img src="https://img.shields.io/badge/API-4.2-8e8e93?style=flat-square" alt="API 4.2">
  <img src="https://img.shields.io/badge/device-Amazfit%20Active%202%20Round-141416?style=flat-square" alt="Amazfit Active 2 Round">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version 1.0.0">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/harness-31%2F31-success?style=flat-square" alt="31/31 harness tests">
  <img src="https://img.shields.io/badge/status-hobby%20project-blueviolet?style=flat-square" alt="Hobby project status">
</p>

> [!WARNING]
> **Target device:** WatchFace Studio is built and tuned exclusively for the **Amazfit Active 2 Round (466×466)**. It has not been tested on other watches. Other Zepp OS models may work, but layout, fonts, hands, and text alignment are not guaranteed.

> [!NOTE]
> **Hobby project, iteratively created with AI assistance.** This is not a commercial, audited product. The code has been tested where possible, but always verify the watch face on your own watch before publishing it.

---

## ✨ What is WatchFace Studio?

WatchFace Studio is a desktop **WYSIWYG** editor for Zepp OS watch faces. Instead of writing `index.js` manually, you drag elements onto a 466×466 canvas, configure properties in the side panel, and immediately see the result. You can export the finished watch face into a `.zpk` developer package or a source ZIP used to create a watch face for everyday use.

| | |
|---|---|
| 🖥️ Editor | PySide6, dark interface, 1:1 canvas matching the watch screen |
| 🎛️ Elements | 11 types: text, data, weather, hands, rings, shortcuts, and more |
| 👁️ Preview | `F5` mode, realistic sample data, PNG and animated GIF export |
| 📦 Export | `.zpk` for installation in developer mode and source ZIP for amazfitwatchfaces |
| ⌚ Device | Amazfit Active 2 Round, 466×466, Zepp OS 5.0 / API 4.2 |
| 🧩 Project | Clean `project.json` + `assets/` folder, no database and no cloud |

---

## ⚡ How it works in 30 seconds

1. 🚀 **Launch the editor** via `run.bat` or `python main.py`.

2. 🧱 **Choose a template** — Digital, Minimal, Sport, Weather, or Blank — and add the required elements.
3. 🎨 **Arrange the watch face** on the canvas: drag elements, resize using handles, adjust properties and layer order.
4. 👁️ **Check the preview** (`F5`), randomize data using the **Randomize data** button, and save as PNG or GIF.
5. 📦 **Export** (`Ctrl+E` for `.zpk`) or select **Export source ZIP**.

```text
project.json + assets/
        │
        ├──▶ render.py ──────▶ preview 466×466 · PNG / GIF
        │
        └──▶ codegen.py ─────▶ app.json · app.js · watchface/index.js · assets/
                    │
                    ▼
            exporter.py ─┬──▶ .zpk  (device.zip + app-side.zip, preview mode)
                        └──▶ source ZIP (flat, production mode)
📸 ScreenshotsScreenshots show the interface and demonstration data. The preview and Preview.png inside the package are generated using the same renderer.🚀 Quick StartRequirements🪟 Windows 10/11🐍 Python 3.11+ (tested on 3.15)📦 PySide6-Essentials and Pillow from requirements.txt⌚ Amazfit Active 2 Round for testing on the deviceInstallation and executionPowerShellcd path\to\watchfaceeditor
python -m pip install -r requirements.txt
python main.py
Alternatively, double-click run.bat — on the first launch, it will create a .venv, install dependencies, and then start the editor.Quick quality checkPowerShellpython -m pip install ruff
python -m ruff check wfeditor main.py tools
python -m compileall -q wfeditor main.py tools
ruff is not part of the application dependencies — it is an optional development tool.Installing the watch face on the watchCtrl+E creates a .zpk file. This is a package in preview mode intended for testing and installation via the Zepp developer mode.Installation requires Zepp App 6.6.0+, the same account on your phone and watch, along with an external tool or QR code. The editor does not generate an installation QR code.The target watch face — visible in the watch face list and removable from the watch — is built from the source ZIP uploaded to amazfitwatchfaces.com. Only the package returned by that service is intended for regular installation.[!IMPORTANT]The .zpk from the editor is unsigned and not meant for distribution. Do not install third-party .zpk packages — install only your own builds.🧩 FeaturesAreaWhat you get🧱 Templates5 starting points: Digital, Minimal, Sport, Weather, Blank🧰 Elements11 types: time, date, text, data, ring, bar, weather icon, hands, status, image, shortcut📊 Data34 sources across 4 groups: Activity, Health, Weather, System🌤️ Weather29 built-in icons, custom sets (folder with 29 PNG files), temperature, humidity, UV, AQI, pressure, sunrise, and sunset🕰️ HandsHour, minute, second, and center cap overlay — each can be replaced separately⭕ ProgressRing and bar for 10 sources: steps, calories, distance, heart rate, battery, PAI, standing time, stress, SpO₂, sleep🚀 Shortcuts61 system and sports apps launched via tap🔔 StatusBluetooth, Do Not Disturb, lock, and active alarm🔤 Typography7 built-in fonts + import of custom TTF/OTF fonts🖱️ CanvasDragging, 8 handles, grid, snapping, undo/redo, duplication, layers, and locking📐 ScalingOptional content scaling along with the frame, per-widget basis↔️ Alignment9 text alignments (left/center/right × top/middle/bottom), consistent across the editor and export🖼️ ImagesScaling in premultiplied alpha color space — no white borders and no discrepancies between editor and device👁️ PreviewF5, random data, PNG save, and 24-frame GIF animation📦 Export.zpk for developer mode and flat source ZIP for amazfitwatchfaces🗂️ ProjectName, author, appId, version, background, simple AOD screen, image and font importAnalog HandsThe Hands element renders four images: hour hand, minute hand, second hand, and center cap overlay. The bounding box defines the area containing the hands, and their center point serves as the rotation axis.A new element defaults to covering the entire screen (0, 0, 466, 466).The Fit to watch face button sets the bounding box to full screen — this is the safest option.Each hand has its own file selection. A selected file takes precedence over the set, and Default restores the set setting.You can also import an entire folder containing hour.png and minute.png (optionally second.png and cap.png).The built-in set consists of four 400×400 images with the rotation axis in the center. Custom hands should point upwards and share a common square canvas.Export saves the hands as standard IMG widgets with pos_x/pos_y, center_x/center_y, and angle — not as IMG_POINTER, which may be ignored on the device.Ring and Progress BarThe ring has two points on the canvas: the center point controls the radius, and the point on the arc controls the thickness. Dragging left or right also updates the values in the property panel. The progress bar uses the same data sources and displays the completion percentage.Content ScalingThe option Scale content along with the frame works per element:✅ checked — the frame is red, and the handles resize the text or image; the export receives these exact values,⬜ unchecked — only the widget area changes, while the saved text/image size remains unchanged.Text scaling uses a single scale factor for both axes so that letters are not distorted. Horizontal and vertical alignment are calculated identically in the editor, preview, and generated index.js.Fonts and Polish CharactersThe editor registers the specific font file, reads its family, style, and weight via QRawFont, and renders text using the specified typeface. As a result, Regular, Medium, and Bold look identical in the editor, preview, and on the watch. Built-in fonts include a full set of Polish characters; when importing a custom TTF/OTF, verify that it contains the required glyphs.🧠 How it works?The editor is organized into layers: project model, renderer, code generator, and exporter. Each of them uses the same input data, ensuring that the preview and package stay in sync.1. Project Modelwfeditor/model.py stores Project and Element as dataclasses. The project is saved to project.json, while images and fonts are saved to assets/. Change history (undo/redo) lives solely in memory and is not written to disk.A new, unsaved watch face is temporarily stored in %TEMP%\WatchFaceStudio\projects. Upon Save As, the editor suggests the projects/ directory in the repository, but you can choose any location. The projects/ directory is gitignored.2. Rendererwfeditor/render.py renders the watch face via QPainter within a logical 466×466 layout. The same renderer handles:the editor canvas and F5 preview,the Preview.png image inside the package,PNG export and GIF animation.The preview scales the entire view while maintaining aspect ratios rather than scaling individual elements — which is why the layout remains identical regardless of window size. The renderer also supports sample data, value randomization, and weather icon replacement.3. Code Generatorwfeditor/codegen.py translates the project into Zepp OS files:app.json — device configuration, designWidth, permissions, and packageInfo,app.js — application bootstrap,watchface/index.js — widgets, sensors, weather timer, hands, and AOD logic.The gps permission is added only when the watch face uses weather features: weather icons or data from the Weather group (city, temperature, humidity, etc.). The generator does not add network permissions.4. Assetswfeditor/resources.py plans what goes into device/assets/: element images, weather and status icons, fonts, and hand assets. File names are generated based on the source and size, making exports reproducible. Shortcut icons receive a shared transparent empty.png when needed.5. Images and Alphawfeditor/imaging.py loads, scales, and saves images in premultiplied alpha color space. Downscaling and upscaling do not blend colors with a transparent background, preventing white edges from appearing. This exact pipeline is used in both the editor and the packaging process.6. Exporterwfeditor/exporter.py builds the device/ tree, then:.zpk — packages device.zip and app-side.zip, sets mode: "preview" and lockscreen: 1,Source ZIP — packages the contents of device/ without a subdirectory, sets mode: "production" and lockscreen: 0.Both variants include a 314×314 Preview.png, matching what the watch face list expects.📦 What goes into export.zpk (dev)Source ZIPPurposeTesting and installation in developer modeamazfitwatchfaces → production watch faceLayoutdevice.zip + app-side.zipFlat device/ contents (no subdirectory)app.jsonmode: "preview", lockscreen: 1mode: "production", lockscreen: 0PlatformAmazfit Active 2Amazfit Active 2watchface/index.js✅✅Images and fonts✅✅Preview.png 314×314✅✅app-side/app.json✅❌Weather / GPSonly when weather is usedonly when weather is used⌨️ Keyboard ShortcutsShortcutActionCtrl+NNew watch faceCtrl+OOpen projectCtrl+SSaveCtrl+Shift+SSave asCtrl+EExport .zpkF5Preview watch faceCtrl+Z / Ctrl+YUndo / redoCtrl+DDuplicate elementDeleteDelete selected elementShift + arrow keysMove by 10 pxCtrl + dragTemporarily disable grid snapping🧰 TechnologiesLayerTechnologyRoleLanguagePython 3.11+Editor logic and exportInterfacePySide6-Essentials / Qt 6Windows, panels, canvas, dialogsRenderingQPainter, QRawFontPreview, text, hands, ringsImagesPillow + QtPremultiplied alpha scaling, PNG, GIFModelJSON + dataclassesproject.json, elements, settingsExportzipfile, tempfile.zpk and source ZIPPlatformZepp OS 5 / API 4.2hmUI, hmSensor, DeviceRuntimeCore.WatchFaceTestsExternal Node harness + PySide6 scriptsindex.js runtime, UI, rendering, export (outside repo)🗂️ Repository StructurePlaintext.
├── main.py                    # application entry point
├── run.bat                    # Windows: venv + dependencies + start
├── requirements.txt           # PySide6-Essentials, Pillow
├── README.md
├── images/                    # screenshots for README
├── assets/
│   ├── fonts/                 # 7 built-in TTF fonts
│   ├── hands/                 # hour/minute/second/cap 400×400
│   ├── status/                # Bluetooth, DND, lock, alarm icons
│   └── weather/               # 29 weather icons
├── tools/
│   └── make_assets.py         # built-in asset generator
├── wfeditor/
│   ├── main.py                # QApplication, theme, initial project
│   ├── constants.py           # device, data, weather, shortcuts, fonts
│   ├── model.py               # Project, Element, templates, asset import
│   ├── render.py              # preview, text, hands, GIF
│   ├── codegen.py             # app.json, app.js, watchface/index.js
│   ├── resources.py           # asset plan for the package
│   ├── imaging.py             # premultiplied alpha
│   ├── exporter.py            # .zpk and source ZIP
│   ├── templates/
│   │   └── app.js             # Zepp OS bootstrap
│   └── ui/
│       ├── mainwindow.py      # menu, toolbars, export, shortcuts
│       ├── canvas.py          # canvas, handles, grid, ring
│       ├── inspector.py       # element properties
│       ├── layers.py          # layer list
│       ├── palette.py         # adding elements and assets
│       ├── dialogs.py         # new project, settings, preview
│       └── theme.py           # Qt dark theme
├── projects/                  # user projects (gitignored)
└── .gitignore
🧪 TestsThe repository does not contain a tests directory — during development, an external harness and scripts executed in %TEMP% were used. They are not part of the repository, so the results below describe the latest state of work rather than a ready CI pipeline.PowerShellpython -m ruff check wfeditor main.py tools
python -m compileall -q wfeditor main.py tools
Verified areas:✅ 31/31 Node harness checks executing the generated index.js: weather, hands, fonts, and asset existence,✅ structure and manifests of app.json/app.js, .zpk packages, and source ZIPs,✅ templates, adding and duplicating elements, layers, undo/redo,✅ hands: role-based selection, file priority over set, "Default", fit to watch face,✅ ring: radius and thickness dragging, field synchronization,✅ content scaling and export of identical values,✅ 3×3 text alignment, Polish characters, Regular/Medium/Bold,✅ two weather elements with the same and different icon sets,✅ PNG/GIF preview with random data,✅ .zpk structure, preview mode, lockscreen: 1, 4 hand assets 466×466, center_x: 233, no IMG_POINTER,✅ source ZIP: flat layout, mode: "production", Amazfit Active 2 platform.What is missing:❌ CI and tests inside the repository,❌ visual regression tests,❌ full verification on physical watch hardware: hand movement, watch face list position, trash icon, and full alignment conformity,❌ tests on other watch models.🛠️ Limitations and Trade-offsSingle device. The entire layout is designed for 466×466. designWidth is fixed, and other resolutions require separate profiles and testing.No image digits. Time and date are rendered via fonts rather than a 0–9 image set. This simplifies the editor but limits styling options.Simplified AOD. Project settings allow choosing a color and time for the Always-On Display; this is not a full, independent AOD layout.Weather before synchronization. The city name shows -- and the icon shows "unknown" until the watch downloads data.Hands require properly set frames. Rotation is calculated relative to the frame center, and the set is scaled to fit inside it. The frame should be square and centered on the watch face; otherwise, the hands will appear smaller or the axis won't align — use Fit to watch face.Custom fonts may lack Polish characters. The editor warns about this, but does not fix missing glyphs..zpk is for developer mode. The final, removable watch face is only generated from the source ZIP on amazfitwatchfaces.Not everything verified on hardware. Hands as IMG, watch face list fixes, trash icon, and text alignment have been verified in code, preview, and exported files — but not every single item has been tested on a physical watch.Tests outside repo, no CI. Quality relies on the harness, temporary scripts, and manual checks rather than a reproducible pipeline.No LICENSE file. Add a chosen license before publishing as open source.🔒 Security and Privacy🚫 The desktop application does not send data to the network and contains no telemetry.💾 Projects, images, and fonts remain local — in project.json and assets/.🔐 The repository contains no accounts, tokens, or Zepp/Amazfit login data.📡 The generated app.json does not add network permissions. The only conditional permission is gps, required for weather: icons or weather data.⚠️ .zpk packages are unsigned. Install only your own builds and only in developer mode.🧪 Imported images and fonts are copied to the project — make sure they come from a trusted source before importing.🗺️ Roadmap[ ] Add support for another watch profile only after hardware testing[ ] Add a full, independent AOD layout[ ] Add image digits[ ] Add more hand sets and weather icon sets[ ] Add a short GIF demo to the README[ ] Add a LICENSE file📄 LicenseThere is no LICENSE file in the repository. If you want to share the project as open source, add a license of your choice — such as MIT.🙏 AcknowledgmentsQt for Python / PySide6 — interface and rendererPillow — images and GIFZepp OS Developers Documentation — watch face and device APIamazfitwatchfaces.com community — package format and watch face publishingBuilt-in fonts: Rajdhani, Chakra Petch, Michroma, Bebas NeueAI as a partner in iterative project creation⚠️ DisclaimerA hobby project, unaffiliated with Zepp Health or Amazfit. Built exclusively for the Amazfit Active 2 Round (466×466) and untested on other watches. Use at your own risk. Before publishing or using the watch face daily, verify its appearance, hand behavior, and installation on your own device.
<FollowUp>
Czy potrzebujesz pomocnych wskazówek dotyczących modyfikacji kodu lub eksportu tego projektu?
</FollowUp>
