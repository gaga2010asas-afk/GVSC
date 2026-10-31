"""SAVEcode / UPcode — архивация и откат проекта."""
import os
import zipfile
from datetime import datetime

class SnapshotManager:
    def __init__(self, project_root: str, snapshots_dir: str):
        self.project_root = project_root
        self.snapshots_dir = snapshots_dir
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.snapshots_dir, f"{name}.zip")

    def save(self, name: str) -> str:
        """Сохранить снапшот всей папки проекта (кроме snapshots/)."""
        archive = self._path(name)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.project_root):
                if os.path.abspath(root).startswith(os.path.abspath(self.snapshots_dir)):
                    continue
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, self.project_root)
                    zf.write(full, rel)
        return archive

    def restore(self, name: str) -> bool:
        """Восстановить снапшот. Возвращает True при успехе."""
        archive = self._path(name)
        if not os.path.exists(archive):
            return False
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(self.project_root)
        return True

    def list(self):
        if not os.path.isdir(self.snapshots_dir):
            return []
        return [f[:-4] for f in os.listdir(self.snapshots_dir) if f.endswith(".zip")]