"""Встроенные макросы app_*, доступные VIBE-скриптам."""
import os
import shutil
import zipfile
import subprocess
import wave
import urllib3
import requests
from PyQt6.QtGui import QImage, QPainter, QColor, QPolygonF, QPen
from PyQt6.QtCore import QPointF

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MacrosAPI:
    def __init__(self, project_root: str, snapshot_mgr, linter):
        self.project_root = os.path.abspath(project_root)
        self.snapshot = snapshot_mgr
        self.linter = linter
        self.blacklist = ["format", "rd /s", "del /f", "rm -rf /", "mkfs"]

    def _full(self, path: str) -> str:
        return os.path.join(self.project_root, path)

    # ---------- Files ----------
    def app_check_exists(self, filepath: str) -> bool:
        return os.path.exists(self._full(filepath))

    def app_create_file(self, filepath: str, content: str):
        full = self._full(filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(full) else None
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[GVSC] created {filepath}")

    def app_delete_file(self, filepath: str):
        full = self._full(filepath)
        if os.path.exists(full):
            os.remove(full)
            print(f"[GVSC] deleted {filepath}")

    def app_delete_folder(self, folderpath: str):
        full = self._full(folderpath)
        if os.path.exists(full):
            shutil.rmtree(full)
            print(f"[GVSC] deleted folder {folderpath}")

    def app_delete_lines(self, filepath: str, start: int, end: int):
        full = self._full(filepath)
        with open(full, "r", encoding="utf-8") as f:
            lines = f.readlines()
        del lines[start - 1:end]
        with open(full, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"[GVSC] deleted lines {start}-{end} in {filepath}")

    def app_append_file(self, filepath: str, text: str):
        full = self._full(filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(full) else None
        with open(full, "a", encoding="utf-8") as f:
            f.write(text)

    def app_read_file(self, filepath: str) -> str:
        full = self._full(filepath)
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.count('\n') + 1
        if lines > 1000:
            print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Файл {filepath} огромный ({lines} строк)!")
        return content

    def app_read_lines(self, filepath: str, start: int, end: int) -> str:
        with open(self._full(filepath), "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[max(0, start - 1):end])

    def app_replace_in_file(self, filepath: str, old: str, new: str) -> int:
        full = self._full(filepath)
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        if old not in content:
            print(f"[GVSC] WARN: '{old}' not found in {filepath}")
            return 0
        content = content.replace(old, new)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return 1

    def app_search_in_file(self, filepath: str, query: str):
        results = []
        with open(self._full(filepath), "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if query in line:
                    results.append((i, line.rstrip()))
        return results

    def app_move_file(self, src: str, dst: str):
        os.makedirs(os.path.dirname(self._full(dst)) or self.project_root, exist_ok=True)
        shutil.move(self._full(src), self._full(dst))
        print(f"[GVSC] moved {src} -> {dst}")

    def app_copy_file(self, src: str, dst: str):
        full_src = self._full(src)
        full_dst = self._full(dst)
        os.makedirs(os.path.dirname(full_dst) or self.project_root, exist_ok=True)
        if os.path.isdir(full_src):
            if os.path.exists(full_dst):
                shutil.rmtree(full_dst)
            shutil.copytree(full_src, full_dst)
        else:
            shutil.copy2(full_src, full_dst)
        print(f"[GVSC] copied {src} -> {dst}")

    # ---------- Network ----------
    def app_download(self, url: str, save_path: str):
        full = self._full(save_path)
        os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(full) else None
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            r = requests.get(url, stream=True, headers=headers, timeout=20, verify=False)
            r.raise_for_status()
            with open(full, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[GVSC] ✅ Скачано: {save_path}")
        except Exception as e:
            print(f"❌ [GVSC] Ошибка скачивания {url}: {e}")
            raise e

    def app_unzip(self, zip_path: str, extract_path: str):
        with zipfile.ZipFile(self._full(zip_path), 'r') as zf:
            zf.extractall(self._full(extract_path))
        print(f"[GVSC] unzipped {zip_path}")

    # ---------- PAI STUDIO (Audio & Visual) ----------
    def app_generate_image(self, paicode: str, save_path: str, width: int = 800, height: int = 600):
        full_path = self._full(save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True) if os.path.dirname(full_path) else None
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            env = {}
            exec(paicode, env)
            if "generate_vector_2d" in env:
                env["generate_vector_2d"](painter)
            elif "generate_voxel_3d" in env:
                voxels = env["generate_voxel_3d"](None)
                if voxels:
                    cube_w, cube_h = width / 32, height / 32
                    cubes = []
                    for z in range(32):
                        for y in range(32):
                            for x in range(32):
                                if voxels[z][y][x]:
                                    cubes.append((x, y, z, QColor(*voxels[z][y][x])))
                    cubes.sort(key=lambda c: c[0] + c[1] + c[2])
                    for x, y, z, color in cubes:
                        pos_x = (x - y) * cube_w / 2 + width / 2
                        pos_y = (x + y) * cube_h / 4 - z * cube_h / 2 + height / 2
                        painter.setBrush(color.lighter(120))
                        painter.setPen(QPen(color.darker(200), 1))
                        painter.drawPolygon(QPolygonF([QPointF(pos_x, pos_y - cube_h/2), QPointF(pos_x + cube_w/2, pos_y), QPointF(pos_x, pos_y + cube_h/2), QPointF(pos_x - cube_w/2, pos_y)]))
                        painter.setBrush(color.darker(130))
                        painter.drawPolygon(QPolygonF([QPointF(pos_x - cube_w/2, pos_y), QPointF(pos_x, pos_y + cube_h/2), QPointF(pos_x, pos_y + cube_h), QPointF(pos_x - cube_w/2, pos_y + cube_h/2)]))
                        painter.setBrush(color.darker(150))
                        painter.drawPolygon(QPolygonF([QPointF(pos_x, pos_y + cube_h/2), QPointF(pos_x + cube_w/2, pos_y), QPointF(pos_x + cube_w/2, pos_y + cube_h/2), QPointF(pos_x, pos_y + cube_h)]))
        except Exception as e:
            print(f"[GVSC] PAI Error: {e}")
        finally:
            painter.end()
        image.save(full_path, "PNG")
        print(f"[GVSC] Generated Image: {save_path}")

    def app_generate_sound(self, paicode: str, save_path: str, duration: float = 1.0, sample_rate: int = 44100):
        import numpy as np
        full_path = self._full(save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True) if os.path.dirname(full_path) else None
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        try:
            env = {}
            exec(paicode, env)
            if "generate_wave" not in env:
                print("[GVSC] Audio Error: В коде нет функции 'generate_wave(t, sample_rate)'!")
                return
            wave_data = env["generate_wave"](t, sample_rate)
            wave_data = np.array(wave_data)
            max_val = np.max(np.abs(wave_data))
            if max_val > 0:
                wave_data = wave_data / max_val
            pcm_data = (wave_data * 32767).astype(np.int16)
            with wave.open(full_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_data.tobytes())
            print(f"[GVSC] Generated Sound: {save_path} ({duration} сек)")
        except Exception as e:
            print(f"[GVSC] Audio Error: {e}")

    # ---------- Engine Integration (Meta Files) ----------
    def app_create_meta_file(self, filepath: str, engine: str):
        full = self._full(filepath)
        if engine.lower() == "godot":
            meta_path = full + ".import"
            content = f"[remap]\n\nimporter=\"texture\"\ntype=\"CompressedTexture2D\"\npath=\"{os.path.basename(filepath)}\"\n"
            with open(meta_path, "w", encoding="utf-8") as f: f.write(content)
        elif engine.lower() == "unity":
            meta_path = full + ".meta"
            content = "fileFormatVersion: 2\nguid: 00000000000000000000000000000000\n"
            with open(meta_path, "w", encoding="utf-8") as f: f.write(content)
        print(f"[GVSC] Meta file created for {filepath} ({engine})")

    # ---------- Snapshots ----------
    def app_save_code(self, name: str):
        self.snapshot.save(name)
        print(f"[GVSC] SAVEcode: {name}")

    def app_restore_code(self, name: str):
        ok = self.snapshot.restore(name)
        print(f"[GVSC] UPcode: {name} -> {'OK' if ok else 'NOT FOUND'}")

    # ---------- Sandboxed Terminal ----------
    def app_run_terminal(self, command: str):
        cmd_lower = command.lower()
        if any(bad in cmd_lower for bad in self.blacklist):
            print(f"🛑 [GVSC SECURITY] Blocked dangerous command: {command}")
            return
        r = subprocess.run(command, shell=True, cwd=self.project_root, capture_output=True, text=True)
        print(r.stdout)
        if r.stderr:
            print(r.stderr)

    def app_get_project_tree(self):
        tree = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "snapshots"]
            for f in files:
                tree.append(os.path.relpath(os.path.join(root, f), self.project_root))
        return tree