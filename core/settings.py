import os
import json

class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.abspath("gvsc_settings.json")
        self.defaults = {
            "language": "ru",
            "theme": "dark",
            "font_size": 12,
            "auto_save": True,
            "show_hidden": False,
            "vibe_auto_scroll": True,
            "last_project": "" # <-- НОВАЯ НАСТРОЙКА
        }
        self.settings = self.load()

    def load(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return {**self.defaults, **json.load(f)}
            except:
                return self.defaults
        return self.defaults

    def save(self):
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def get(self, key):
        return self.settings.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def load_locale(self):
        lang = self.get("language")
        locale_path = os.path.abspath(os.path.join("assets", "locales", f"{lang}.json"))
        
        if os.path.exists(locale_path):
            try:
                with open(locale_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}