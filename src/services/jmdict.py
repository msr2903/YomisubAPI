"""
JMdict-based dictionary service using jmdict-simplified JSON.

This replaces jamdict with a faster, pure-Python dictionary lookup
using the jmdict-simplified project's JSON format.

Download the dictionary:
  curl -L https://github.com/scriptin/jmdict-simplified/releases/latest/download/jmdict-eng-3.5.0.json.gz -o data/jmdict-eng.json.gz
  gunzip data/jmdict-eng.json.gz
"""

import gzip
import json
from functools import lru_cache
from pathlib import Path
from typing import Self


class JMDictionary:
    """
    Fast Japanese-English dictionary using jmdict-simplified JSON.
    
    Builds an in-memory index for O(1) lookups by kanji/kana.
    """
    
    def __init__(self, dict_path: Path | str | None = None) -> None:
        """
        Initialize the dictionary.
        
        Args:
            dict_path: Path to jmdict-eng.json or jmdict-eng.json.gz
                       If None, searches common locations.
        """
        self._index_kanji: dict[str, list[dict]] = {}
        self._index_kana: dict[str, list[dict]] = {}
        self._loaded = False
        
        if dict_path:
            self._load(Path(dict_path))
        else:
            self._find_and_load()
    
    def _find_and_load(self) -> None:
        """Find dictionary file in common locations."""
        search_paths = [
            Path(__file__).parent.parent.parent / "data" / "jmdict-eng.json",
            Path(__file__).parent.parent.parent / "data" / "jmdict-eng.json.gz",
            Path.home() / ".jmdict" / "jmdict-eng.json",
            Path("/app/data/jmdict-eng.json"),
        ]
        
        for path in search_paths:
            if path.exists():
                self._load(path)
                return
        
        # No dictionary found - will use empty index
        print(f"⚠️ JMdict not found. Searched: {[str(p) for p in search_paths]}")
        print("  Download: curl -L https://github.com/scriptin/jmdict-simplified/releases/latest/download/jmdict-eng-3.5.0.json.gz -o data/jmdict-eng.json.gz && gunzip data/jmdict-eng.json.gz")
    
    def _load(self, path: Path) -> None:
        """Load and index the dictionary."""
        print(f"📚 Loading JMdict from {path}...")
        
        # Handle gzipped files
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        
        # Build index
        words = data.get("words", [])
        for entry in words:
            # Index by kanji forms
            for kanji in entry.get("kanji", []):
                text = kanji.get("text", "")
                if text:
                    if text not in self._index_kanji:
                        self._index_kanji[text] = []
                    self._index_kanji[text].append(entry)
            
            # Index by kana forms
            for kana in entry.get("kana", []):
                text = kana.get("text", "")
                if text:
                    if text not in self._index_kana:
                        self._index_kana[text] = []
                    self._index_kana[text].append(entry)
        
        self._loaded = True
        print(f"✓ Loaded {len(words)} entries ({len(self._index_kanji)} kanji, {len(self._index_kana)} kana)")
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_instance(cls) -> Self:
        """Get or create a singleton instance."""
        return cls()
    
    def lookup(self, word: str) -> str | None:
        """
        Look up a word and return its English meaning.
        
        Args:
            word: Japanese word (kanji or kana)
        
        Returns:
            English meaning string, or None if not found.
        """
        # Try kanji index first, then kana
        entries = self._index_kanji.get(word) or self._index_kana.get(word)
        
        if not entries:
            return None
        
        # Get first entry's first sense's first gloss
        entry = entries[0]
        senses = entry.get("sense", [])
        
        if not senses:
            return None
        
        # Collect glosses from first sense
        glosses = []
        for gloss in senses[0].get("gloss", []):
            text = gloss.get("text", "")
            if text:
                glosses.append(text)
        
        if glosses:
            return "; ".join(glosses[:3])  # Limit to 3 meanings
        
        return None
    
    def lookup_full(self, word: str) -> list[dict] | None:
        """
        Look up a word and return all matching entries.
        
        Returns raw entry data for advanced use cases.
        """
        return self._index_kanji.get(word) or self._index_kana.get(word)
    
    @property
    def is_loaded(self) -> bool:
        """Check if dictionary was successfully loaded."""
        return self._loaded
