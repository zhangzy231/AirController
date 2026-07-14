[app]

# (str) Title of your application
title = AirController

# (str) Package name
package.name = aircontroller

# (str) Package domain (needed for android/ios packaging)
package.domain = com.aircontroller

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests,.venv,__pycache__

# (list) List of exclusions using pattern matching
source.exclude_patterns = _*.py

# (str) Application versioning
version = 1.0.0

# (str) Application requirements (comma separated)
requirements = python3, kivy==2.2.1, pyjnius, certifi

# (str) Supported orientations (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (str) Full source of the application (default: src/main.py)
main_file = main.py

# (list) Permissions
android.permissions = INTERNET, TRANSMIT_IR

# (int) Target Android API
android.api = 33

# (int) Minimum API required
android.minapi = 24

# (bool) Accept Android SDK license
android.accept_sdk_license = True

# (list) Android features required
android.features = android.hardware.consumerir

# (bool) Indicate if the application must be fullscreen
fullscreen = 0

# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/icon.png

# (str) Log level: trace, debug, info, warning, error, critical
log_level = 1

# (int) Log window size (0 to disable, >1 to set)
log_window = 0

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Timeout in seconds for build operations
build_timeout = 3600

# (str) python-for-android branch
p4a.branch = develop

# (str) NDK version (r25c is known compatible with Kivy)
android.ndk = 25.2.9519653
