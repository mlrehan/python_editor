import os
import json
import secrets
from typing import Optional, Dict


class GuestOwnershipManager:
    """
    Manages ownership and capability tokens for guest files in the public workspace.
    Public files are readable by everyone, but modification/deletion is restricted
    to the guest session that created them (or default starter files).
    """

    def __init__(self, metadata_path: str = "./storage/public_ownership.json"):
        self.metadata_path = os.path.abspath(metadata_path)
        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
        self._ownership: Dict[str, str] = {}  # relative_path -> guest_token
        self._load()

    def _load(self):
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self._ownership = json.load(f)
            except Exception:
                self._ownership = {}
        else:
            self._ownership = {}

    def _save(self):
        try:
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(self._ownership, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def generate_token() -> str:
        """Generates a cryptographically strong capability token for a guest session."""
        return "gst_" + secrets.token_urlsafe(24)

    def is_default_seeded_file(self, rel_path: str) -> bool:
        clean = rel_path.replace("\\", "/").strip("/").lower()
        return clean in ("readme.md", "main.py", "sample_data.csv", "getting_started.ipynb")

    def record_ownership(self, rel_path: str, guest_token: str):
        clean = rel_path.replace("\\", "/").strip("/")
        if not clean or not guest_token:
            return
        self._ownership[clean] = guest_token
        self._save()

    def remove_ownership(self, rel_path: str):
        clean = rel_path.replace("\\", "/").strip("/")
        if clean in self._ownership:
            del self._ownership[clean]
            self._save()

    def rename_ownership(self, old_path: str, new_path: str, guest_token: str):
        clean_old = old_path.replace("\\", "/").strip("/")
        clean_new = new_path.replace("\\", "/").strip("/")
        if clean_old in self._ownership:
            del self._ownership[clean_old]
        self._ownership[clean_new] = guest_token
        self._save()

    def can_modify(self, rel_path: str, guest_token: Optional[str]) -> bool:
        clean = rel_path.replace("\\", "/").strip("/")
        # Allow modifying starter files for interactive trial
        if self.is_default_seeded_file(clean):
            return True

        owner = self._ownership.get(clean)
        # If file is not claimed yet, anyone can modify it and claim it
        if not owner:
            return True

        # If file is claimed, only the creator with the capability token can modify/delete it
        if guest_token and guest_token == owner:
            return True

        return False


guest_ownership = GuestOwnershipManager()

