from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "WatchfaceCreator"
APP_VERSION = "1.0.0"
APP_TITLE = "WatchfaceCreator - Amazfit Active 2 (Round)"

ROOT_DIR = Path(__file__).resolve().parent.parent
BUILTIN_DIR = ROOT_DIR / "assets"
BUILTIN_FONTS_DIR = BUILTIN_DIR / "fonts"
BUILTIN_WEATHER_DIR = BUILTIN_DIR / "weather"
BUILTIN_STATUS_DIR = BUILTIN_DIR / "status"
BUILTIN_HANDS_DIR = BUILTIN_DIR / "hands"
PROJECTS_DIR = ROOT_DIR / "projects"
TEMPLATES_DIR = ROOT_DIR / "wfeditor" / "templates"
SETTINGS_ORG = "WatchfaceCreator"
SETTINGS_APP = "WatchfaceCreator"

DEVICE = {
    "id": "active2-round",
    "name": "Amazfit Active 2 (Round)",
    "width": 466,
    "height": 466,
    "preview_size": 314,
    "design_width": 466,
    "device_sources": [
        8913152,
        8913153,
        8913155,
        8913159,
        10092800,
        10092801,
        10092803,
        10092807,
    ],
    "os_version": "5.0",
    "api_level": "4.2",
}

SAFE_MARGIN = 14
GRID_STEP = 10

# Nazwa platformy w app.json. Oficjalne paczki i serwis amazfitwatchfaces
# używają krótkiej nazwy "Amazfit Active 2" (bez dopisku Round).
PLATFORM_NAME = "Amazfit Active 2"

HAND_ROLES = ("hour", "minute", "second", "cap")
HAND_REQUIRED = ("hour", "minute")
HAND_FILES = {
    "hour": "hour.png",
    "minute": "minute.png",
    "second": "second.png",
    "cap": "cap.png",
}
HAND_LABELS = {
    "hour": "Wskazówka godzinowa",
    "minute": "Wskazówka minutowa",
    "second": "Wskazówka sekundowa",
    "cap": "Nakładka (oś)",
}

FONT_CHOICES = [
    ("Systemowa (zegarek)", ""),
    ("Rajdhani Regular", "fonts/Rajdhani-Regular.ttf"),
    ("Rajdhani Medium", "fonts/Rajdhani-Medium.ttf"),
    ("Rajdhani Bold", "fonts/Rajdhani-Bold.ttf"),
    ("Chakra Petch Regular", "fonts/ChakraPetch-Regular.ttf"),
    ("Chakra Petch Bold", "fonts/ChakraPetch-Bold.ttf"),
    ("Michroma", "fonts/Michroma-Regular.ttf"),
    ("Bebas Neue", "fonts/BebasNeue-Regular.ttf"),
]

BUILTIN_FONTS = [
    "Rajdhani-Regular.ttf",
    "Rajdhani-Medium.ttf",
    "Rajdhani-Bold.ttf",
    "ChakraPetch-Regular.ttf",
    "ChakraPetch-Bold.ttf",
    "Michroma-Regular.ttf",
    "BebasNeue-Regular.ttf",
]

WEATHER_FILES = [
    "00_cloudy.png",
    "01_shower.png",
    "02_snow_shower.png",
    "03_sunny.png",
    "04_overcast.png",
    "05_light_rain.png",
    "06_light_snow.png",
    "07_moderate_rain.png",
    "08_moderate_snow.png",
    "09_heavy_snow.png",
    "10_heavy_rain.png",
    "11_sandstorm.png",
    "12_sleet.png",
    "13_fog.png",
    "14_haze.png",
    "15_thundershower.png",
    "16_snowstorm.png",
    "17_dust.png",
    "18_extraordinary_rainstorm.png",
    "19_rain_with_hail.png",
    "20_thundershowers_with_hail.png",
    "21_heavy_rainstorm.png",
    "22_sand_blowing.png",
    "23_strong_sandstorm.png",
    "24_rainstorm.png",
    "25_unknown.png",
    "26_cloudy_at_night.png",
    "27_shower_at_night.png",
    "28_clear_night.png",
]

WEATHER_LABELS_PL = [
    "Pochmurno",
    "Przelotny deszcz",
    "Przelotny śnieg",
    "Słonecznie",
    "Zachmurzenie",
    "Lekki deszcz",
    "Lekki śnieg",
    "Umiarkowany deszcz",
    "Umiarkowany śnieg",
    "Intensywny śnieg",
    "Intensywny deszcz",
    "Burza piaskowa",
    "Deszcz ze śniegiem",
    "Mgła",
    "Smog",
    "Burza z deszczem",
    "Zamieć śnieżna",
    "Pył",
    "Ekstremalny deszcz",
    "Deszcz z gradem",
    "Burza z gradem",
    "Ulewa",
    "Wiatr z piaskiem",
    "Silna burza piaskowa",
    "Nawałnica",
    "Nieznana",
    "Pochmurno (noc)",
    "Przelotny deszcz (noc)",
    "Bezchmurnie (noc)",
]

STATUS_FILES = {
    "bluetooth": "status/bluetooth.png",
    "dnd": "status/dnd.png",
    "lock": "status/lock.png",
    "alarm": "status/alarm.png",
}

STATUS_LABELS = {
    "bluetooth": "Bluetooth rozłączony",
    "dnd": "Nie przeszkadzać",
    "lock": "Blokada ekranu",
    "alarm": "Alarm aktywny",
}

STATUS_TYPES = {
    "bluetooth": "hmUI.system_status.DISCONNECT",
    "dnd": "hmUI.system_status.DISTURB",
    "lock": "hmUI.system_status.LOCK",
    "alarm": "hmUI.system_status.CLOCK",
}

DATA_GROUPS = {
    "Aktywność": [
        "steps",
        "steps_target",
        "calories",
        "calories_target",
        "distance",
        "stand",
        "floor",
        "fat_burning",
        "training_load",
        "vo2max",
    ],
    "Zdrowie": [
        "heart",
        "pai",
        "stress",
        "spo2",
        "sleep",
        "readiness",
        "recovery_time",
        "bio_charge",
        "body_temp",
    ],
    "Pogoda": [
        "city",
        "weather_temp",
        "weather_low",
        "weather_high",
        "humidity",
        "uvi",
        "aqi",
        "pressure",
        "altitude",
        "sun_rise",
        "sun_set",
    ],
    "System": [
        "battery",
        "alarm_time",
        "countdown",
        "stopwatch",
    ],
}

DATA_SOURCES = {
    "steps": {
        "label": "Kroki",
        "type": "hmUI.data_type.STEP",
        "sample": "8670",
        "unit": "",
        "range": (0, 99999),
        "sensor": "STEP",
        "expr": "step.current",
        "target": "step.target",
        "pad": 0,
    },
    "steps_target": {
        "label": "Cel kroków",
        "type": "hmUI.data_type.STEP_TARGET",
        "sample": "10000",
        "unit": "",
        "range": (0, 99999),
        "sensor": "STEP",
        "expr": "step.target",
        "pad": 0,
    },
    "calories": {
        "label": "Kalorie",
        "type": "hmUI.data_type.CAL",
        "sample": "280",
        "unit": "kcal",
        "range": (0, 9999),
        "sensor": "CALORIE",
        "expr": "calorie.current",
        "target": "calorie.target",
        "pad": 0,
    },
    "calories_target": {
        "label": "Cel kalorii",
        "type": "hmUI.data_type.CAL_TARGET",
        "sample": "2000",
        "unit": "kcal",
        "range": (0, 9999),
        "sensor": "CALORIE",
        "expr": "calorie.target",
        "pad": 0,
    },
    "distance": {
        "label": "Dystans",
        "type": "hmUI.data_type.DISTANCE",
        "sample": "5.30",
        "unit": "km",
        "range": (0, 99.99),
        "sensor": "DISTANCE",
        "expr": "distance.current",
        "pad": 0,
    },
    "heart": {
        "label": "Tętno",
        "type": "hmUI.data_type.HEART",
        "sample": "86",
        "unit": "bpm",
        "range": (30, 220),
        "sensor": "HEART",
        "expr": "heart.last",
        "target": "200",
        "pad": 0,
    },
    "pai": {
        "label": "PAI (dziś)",
        "type": "hmUI.data_type.PAI_DAILY",
        "sample": "45",
        "unit": "",
        "range": (0, 75),
        "sensor": "PAI",
        "expr": "pai.dailypai",
        "target": "100",
        "pad": 0,
    },
    "stand": {
        "label": "Godziny stania",
        "type": "hmUI.data_type.STAND",
        "sample": "8",
        "unit": "",
        "range": (0, 12),
        "sensor": "STAND",
        "expr": "stand.current",
        "target": "stand.target",
        "pad": 0,
    },
    "battery": {
        "label": "Bateria",
        "type": "hmUI.data_type.BATTERY",
        "sample": "75",
        "unit": "%",
        "range": (0, 100),
        "sensor": "BATTERY",
        "expr": "battery.current",
        "target": "100",
        "pad": 0,
    },
    "stress": {
        "label": "Stres",
        "type": "hmUI.data_type.STRESS",
        "sample": "35",
        "unit": "",
        "range": (0, 100),
        "sensor": "STRESS",
        "expr": "stress.current",
        "target": "100",
        "pad": 0,
    },
    "spo2": {
        "label": "SpO2",
        "type": "hmUI.data_type.SPO2",
        "sample": "98",
        "unit": "%",
        "range": (50, 100),
        "sensor": "SPO2",
        "expr": "spo2.current",
        "target": "100",
        "pad": 0,
    },
    "floor": {
        "label": "Piętra",
        "type": "hmUI.data_type.FLOOR",
        "sample": "12",
        "unit": "",
        "range": (0, 999),
        "sensor": None,
        "pad": 0,
    },
    "fat_burning": {
        "label": "Spalanie tłuszczu (min)",
        "type": "hmUI.data_type.FAT_BURNING",
        "sample": "45",
        "unit": "min",
        "range": (0, 999),
        "sensor": None,
        "pad": 0,
    },
    "training_load": {
        "label": "Obciążenie treningowe",
        "type": "hmUI.data_type.TRAINING_LOAD",
        "sample": "480",
        "unit": "",
        "range": (0, 999),
        "sensor": None,
        "pad": 0,
    },
    "vo2max": {
        "label": "VO2max",
        "type": "hmUI.data_type.VO2MAX",
        "sample": "48",
        "unit": "",
        "range": (15, 65),
        "sensor": None,
        "pad": 0,
    },
    "sleep": {
        "label": "Sen (HH:MM)",
        "type": "hmUI.data_type.SLEEP",
        "sample": "7:32",
        "unit": "",
        "range": (0, 1440),
        "sensor": "SLEEP",
        "expr": "(sleep.stop - sleep.start)",
        "target": "480",
        "pad": 0,
    },
    "readiness": {
        "label": "Gotowość",
        "type": "hmUI.data_type.READINESS",
        "sample": "82",
        "unit": "",
        "range": (0, 100),
        "sensor": None,
        "pad": 0,
    },
    "recovery_time": {
        "label": "Czas regeneracji",
        "type": "hmUI.data_type.RECOVERY_TIME",
        "sample": "24",
        "unit": "h",
        "range": (0, 97),
        "sensor": None,
        "pad": 0,
    },
    "bio_charge": {
        "label": "BioCharge",
        "type": "hmUI.data_type.BIO_CHARGE",
        "sample": "70",
        "unit": "",
        "range": (0, 100),
        "sensor": None,
        "pad": 0,
    },
    "body_temp": {
        "label": "Temperatura ciała",
        "type": "hmUI.data_type.BODY_TEMP",
        "sample": "36.6",
        "unit": "°C",
        "range": (30, 45),
        "sensor": None,
        "pad": 0,
    },
    "city": {
        "label": "Lokalizacja (miasto)",
        "type": None,
        "sample": "Warszawa",
        "unit": "",
        "range": (0, 0),
        "sensor": None,
        "pad": 0,
    },
    "weather_temp": {
        "label": "Temperatura (pogoda)",
        "type": "hmUI.data_type.WEATHER_CURRENT",
        "sample": "22",
        "unit": "°C",
        "range": (-40, 60),
        "sensor": None,
        "pad": 0,
    },
    "weather_low": {
        "label": "Temperatura min.",
        "type": "hmUI.data_type.WEATHER_LOW",
        "sample": "16",
        "unit": "°C",
        "range": (-40, 60),
        "sensor": None,
        "pad": 0,
    },
    "weather_high": {
        "label": "Temperatura max.",
        "type": "hmUI.data_type.WEATHER_HIGH",
        "sample": "27",
        "unit": "°C",
        "range": (-40, 60),
        "sensor": None,
        "pad": 0,
    },
    "humidity": {
        "label": "Wilgotność",
        "type": "hmUI.data_type.HUMIDITY",
        "sample": "42",
        "unit": "%",
        "range": (0, 100),
        "sensor": None,
        "pad": 0,
    },
    "uvi": {
        "label": "UV",
        "type": "hmUI.data_type.UVI",
        "sample": "4",
        "unit": "",
        "range": (0, 11),
        "sensor": None,
        "pad": 0,
    },
    "aqi": {
        "label": "AQI",
        "type": "hmUI.data_type.AQI",
        "sample": "26",
        "unit": "",
        "range": (0, 500),
        "sensor": None,
        "pad": 0,
    },
    "pressure": {
        "label": "Ciśnienie",
        "type": "hmUI.data_type.ALTIMETER",
        "sample": "1013",
        "unit": "hPa",
        "range": (0, 1200),
        "sensor": None,
        "pad": 0,
    },
    "altitude": {
        "label": "Wysokość",
        "type": "hmUI.data_type.ALTITUDE",
        "sample": "120",
        "unit": "m",
        "range": (0, 99999),
        "sensor": None,
        "pad": 0,
    },
    "sun_rise": {
        "label": "Wschód słońca",
        "type": "hmUI.data_type.SUN_RISE",
        "sample": "06:30",
        "unit": "",
        "range": (0, 1440),
        "sensor": None,
        "pad": 0,
    },
    "sun_set": {
        "label": "Zachód słońca",
        "type": "hmUI.data_type.SUN_SET",
        "sample": "18:30",
        "unit": "",
        "range": (0, 1440),
        "sensor": None,
        "pad": 0,
    },
    "alarm_time": {
        "label": "Alarm (HH:MM)",
        "type": "hmUI.data_type.ALARM_CLOCK",
        "sample": "07:00",
        "unit": "",
        "range": (0, 1440),
        "sensor": None,
        "pad": 0,
    },
    "countdown": {
        "label": "Minutnik",
        "type": "hmUI.data_type.COUNT_DOWN",
        "sample": "10",
        "unit": "",
        "range": (0, 99),
        "sensor": None,
        "pad": 0,
    },
    "stopwatch": {
        "label": "Stoper",
        "type": "hmUI.data_type.STOP_WATCH",
        "sample": "12",
        "unit": "",
        "range": (0, 99),
        "sensor": None,
        "pad": 0,
    },
}

# Liczba klatek dla pasków postępu z własnymi obrazami i łukiem. Zegarek
# podmienia obraz przy każdej zmianie poziomu, a podgląd używa tej samej
# liczby klatek, więc wygląd jest identyczny.
PROGRESS_BAR_FRAMES = 51

PROGRESS_SOURCES = {
    "steps": ("step", "STEP", "step.current", "step.target"),
    "calories": ("calorie", "CALORIE", "calorie.current", "calorie.target"),
    "distance": ("distance", "DISTANCE", "distance.current", "10"),
    "heart": ("heart", "HEART", "heart.last", "200"),
    "battery": ("battery", "BATTERY", "battery.current", "100"),
    "pai": ("pai", "PAI", "pai.dailypai", "100"),
    "stand": ("stand", "STAND", "stand.current", "stand.target"),
    "stress": ("stress", "STRESS", "stress.current", "100"),
    "spo2": ("spo2", "SPO2", "spo2.current", "100"),
    "sleep": ("sleep", "SLEEP", "(sleep.stop - sleep.start)", "480"),
}

SHORTCUT_CATALOG = [
    ("Aktywność", [
        ("Steps", "Aktywność / kroki", "hmApp.startApp({url: 'activityAppScreen', native: true });"),
        ("HeartRete", "Puls", "hmApp.startApp({url: 'heart_app_Screen', native: true });"),
        ("PAI", "PAI", "hmApp.startApp({url: 'PAI_app_Screen', native: true });"),
        ("Stress", "Stres", "hmApp.startApp({url: 'StressHomeScreen', native: true });"),
        ("Sleep", "Sen", "hmApp.startApp({url: 'Sleep_HomeScreen', native: true });"),
        ("SPO2", "SpO2", "hmApp.startApp({url: 'spo_HomeScreen', native: true });"),
        ("OneKey", "Pomiar jednym dotknięciem", "hmApp.startApp({url: 'oneKeyAppScreen', native: true });"),
        ("WeekActivity", "Aktywność tygodnia", "hmApp.startApp({url: 'activityWeekShowScreen', native: true });"),
        ("SportList", "Lista sportów", "hmApp.startApp({url: 'SportListScreen', native: true });"),
        ("Sport", "Ostatni trening", "hmApp.startApp({url: 'SportScreen', native: true });"),
        ("SportRecord", "Historia treningów", "hmApp.startApp({url: 'SportRecordListScreen', native: true });"),
        ("SportStatus", "Status treningu", "hmApp.startApp({url: 'SportStatusScreen', native: true });"),
        ("Readiness", "Gotowość", "hmApp.startApp({url: 'readinessAppScreen', native: true });"),
        ("BioCharge", "BioCharge", "hmApp.startApp({url: 'BioChargeHomeScreen', native: true });"),
        ("BodyComposition", "Skład ciała", "hmApp.startApp({url: 'BodyCompositionResultScreen', native: true });"),
        ("Respiration", "Oddychanie", "hmApp.startApp({url: 'RespirationwidgetScreen', native: true });"),
        ("NightMonitor", "Monitoring snu", "hmApp.startApp({url: 'oneKeyNightMonitorScreen', native: true });"),
    ]),
    ("Aplikacje", [
        ("Alarm", "Alarm", "hmApp.startApp({url: 'AlarmInfoScreen', native: true });"),
        ("Schedule", "Kalendarz", "hmApp.startApp({url: 'ScheduleCalScreen', native: true });"),
        ("ScheduleList", "Harmonogram", "hmApp.startApp({url: 'ScheduleListScreen', native: true });"),
        ("ToDoList", "Lista zadań", "hmApp.startApp({url: 'todoListScreen', native: true });"),
        ("WorldClock", "Czas światowy", "hmApp.startApp({url: 'WorldClockScreen', native: true });"),
        ("PhoneMusic", "Muzyka (telefon)", "hmApp.startApp({url: 'PhoneMusicCtrlScreen', native: true });"),
        ("LocalMusic", "Muzyka (zegarek)", "hmApp.startApp({url: 'LocalMusicScreen', native: true });"),
        ("FlashLight", "Latarka", "hmApp.startApp({url: 'FlashLightScreen', native: true });"),
        ("Weather", "Pogoda", "hmApp.startApp({url: 'WeatherScreen', native: true });"),
        ("Sunset", "Wschód / zachód", "hmApp.startApp({url: 'TideScreen', native: true });"),
        ("Compass", "Kompas", "hmApp.startApp({url: 'CompassScreen', native: true });"),
        ("Map", "Mapa offline", "hmApp.startApp({url: 'OfflineMapScreen', native: true });"),
        ("Baro", "Barometr", "hmApp.startApp({url: 'BaroAltimeterScreen', native: true });"),
        ("StopWatch", "Stoper", "hmApp.startApp({url: 'StopWatchScreen', native: true });"),
        ("CountDown", "Minutnik", "hmApp.startApp({url: 'CountdownAppScreen', native: true });"),
        ("Timer", "Timer", "hmApp.startApp({url: 'TomatoMainScreen', native: true });"),
        ("ClubCards", "Karty klubowe", "hmApp.startApp({url: 'ClubCardsScreen', native: true });"),
        ("VoiceMemo", "Notatka głosowa", "hmApp.startApp({url: 'VoiceMemoScreen', native: true });"),
        ("Camera", "Aparat", "hmApp.startApp({url: 'HidcameraScreen', native: true });"),
        ("Menstrual", "Kalendarz kobiecy", "hmApp.startApp({url: 'menstrualAppScreen', native: true });"),
    ]),
    ("System", [
        ("Settings", "Ustawienia", "hmApp.startApp({url: 'Settings_homeScreen', native: true });"),
        ("Display", "Ekran / jasność", "hmApp.startApp({url: 'Settings_displayBrightScreen', native: true });"),
        ("DND", "Nie przeszkadzać", "hmApp.startApp({url: 'Settings_dndScreen', native: true });"),
        ("AOD", "Ustawienia AOD", "hmApp.startApp({url: 'Settings_standbyModelScreen', native: true });"),
        ("AODStyle", "Styl AOD", "hmApp.startApp({url: 'Settings_standbyHomeScreen', native: true });"),
        ("Light", "Jasność", "hmApp.startApp({url: 'Settings_lightAdjustScreen', native: true });"),
        ("System", "System", "hmApp.startApp({url: 'Settings_systemScreen', native: true });"),
        ("LowBattery", "Oszczędzanie baterii", "hmApp.startApp({url: 'LowBatteryScreen', native: true });"),
        ("SaveMode", "Prosty tryb", "hmApp.startApp({url: 'PowerSaveModeScreen', native: true });"),
        ("AppPermission", "Uprawnienia aplikacji", "hmApp.startApp({url: 'Settings_permissionAppsScreen', native: true });"),
        ("BatteryManager", "Statystyki baterii", "hmApp.startApp({url: 'Settings_batteryManagerScreen', native: true });"),
        ("ControlCenter", "Edycja centrum sterowania", "hmApp.startApp({url: 'ControlCenterEditScreen', native: true });"),
        ("AppList", "Lista aplikacji", "hmApp.startApp({url: 'AppListScreen', native: true });"),
        ("DragList", "Ikony aplikacji", "hmApp.startApp({url: 'DragListScreen', native: true });"),
        ("MoreList", "Menu więcej", "hmApp.startApp({url: 'MoreListScreen', native: true });"),
        ("WatchFace", "Wybór tarczy", "hmApp.startApp({url: 'WatchFaceScreen', native: true });"),
        ("WidgetEdit", "Edycja widżetów", "hmApp.startApp({url: 'WidgetEditScreen', native: true });"),
        ("Phone", "Telefon", "hmApp.startApp({url: 'PhoneHomeScreen', native: true });"),
        ("Contacts", "Kontakty", "hmApp.startApp({url: 'PhoneContactsScreen', native: true });"),
        ("RecentCall", "Ostatnie połączenia", "hmApp.startApp({url: 'PhoneRecentCallScreen', native: true });"),
        ("DialCall", "Wybór numeru", "hmApp.startApp({url: 'DialCallScreen', native: true });"),
        ("FindPhone", "Znajdź telefon", "hmApp.startApp({url: 'FindPhoneScreen', native: true });"),
        ("MorningNews", "Poranne powitanie", "hmApp.startApp({url: 'MorningGreetingCoverScreen', native: true });"),
        ("ReStart", "Restart", "hmApp.startApp({url: 'HmReStartScreen', native: true });"),
    ]),
]

SHORTCUT_BY_KEY = {
    key: {"label": label, "js": js, "group": group}
    for group, items in SHORTCUT_CATALOG
    for key, label, js in items
}

WEEKDAYS = {
    "pl": {
        "full": ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"],
        "short": ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"],
    },
    "en": {
        "full": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "short": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    },
}

MONTHS = {
    "pl": {
        "full": [
            "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
            "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
        ],
        "short": ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"],
    },
    "en": {
        "full": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        "short": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}

DEFAULT_COLORS = [
    "#FFFFFF", "#000000", "#FFD54A", "#FF8A3D", "#FF5252", "#FF4FA3",
    "#C77DFF", "#7C6BFF", "#4D9BFF", "#35C4FF", "#2EE6C8", "#2EE66B",
    "#9BE36B", "#B8C0CC", "#7A8798", "#374151",
]


def rgba_to_int(value: str, alpha: int = 255) -> int:
    value = (value or "#FFFFFF").strip()
    value = value.removeprefix("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) == 8:
        value = value[2:]
    value = value.ljust(6, "0")[:6]
    return (int(alpha) << 24) | int(value, 16)


def int_to_rgba(value: int) -> tuple[str, int]:
    alpha = (value >> 24) & 0xFF
    return f"#{value & 0xFFFFFF:06X}", alpha


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = (value or "#FFFFFF").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    value = value.ljust(6, "0")[:6]
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def ensure_dirs() -> None:
    for path in (PROJECTS_DIR, TEMPLATES_DIR):
        os.makedirs(path, exist_ok=True)
