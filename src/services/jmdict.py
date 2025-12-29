"""
JMdict-based dictionary service using jmdict-simplified JSON.

This replaces jamdict with a faster, pure-Python dictionary lookup
using the jmdict-simplified project's JSON format.

The dictionary is automatically downloaded from the latest release
if not found locally.
"""

import gzip
import json
import re
import unicodedata
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Self


# GitHub API endpoint for latest release
JMDICT_RELEASES_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"
JMDICT_DOWNLOAD_PATTERN = r"jmdict-eng-\d+\.\d+\.\d+\.json\.gz"
JMNEDICT_DOWNLOAD_PATTERN = r"jmnedict-all-.*\.json\.zip"


class JMDictionary:
    """
    Fast Japanese-English dictionary using jmdict-simplified JSON.
    
    Builds an in-memory index for O(1) lookups by kanji/kana.
    Automatically downloads the latest version if not found.
    """
    
    def __init__(self, dict_path: Path | str | None = None) -> None:
        """
        Initialize the dictionary.
        
        Args:
            dict_path: Path to jmdict-eng.json or jmdict-eng.json.gz
                       If None, searches common locations or downloads latest.
        """
        self._index_kanji: dict[str, list[dict]] = {}
        self._index_kana: dict[str, list[dict]] = {}
        self._index_names_kanji: dict[str, list[dict]] = {}
        self._index_names_kana: dict[str, list[dict]] = {}
        
        self._loaded = False
        self._version: str | None = None
        
        if dict_path:
            self._load(Path(dict_path))
        else:
            self._find_and_load()
            self._find_and_load_names()
    
    def _find_and_load(self) -> None:
        """Find dictionary file in common locations or download if not found."""
        data_dir = Path(__file__).parent.parent.parent / "data"
        
        search_paths = [
            data_dir / "jmdict-eng.json",
            data_dir / "jmdict-eng.json.gz",
            Path.home() / ".jmdict" / "jmdict-eng.json",
            Path("/app/data/jmdict-eng.json"),
            Path("/app/data/jmdict-eng.json.gz"),
        ]
        
        # Also search for versioned files
        if data_dir.exists():
            for f in data_dir.glob("jmdict-eng-*.json*"):
                search_paths.insert(0, f)
        
        for path in search_paths:
            if path.exists():
                self._load(path)
                return
        
        # No dictionary found - try to download
        print("📥 JMdict not found locally. Attempting to download latest version...")
        try:
            self._download_latest(data_dir)
        except Exception as e:
            print(f"⚠️ Failed to download JMdict: {e}")
            print("  Manual download: curl -L https://github.com/scriptin/jmdict-simplified/releases/latest/download/jmdict-eng-3.5.0.json.gz -o data/jmdict-eng.json.gz")
    
    def _get_latest_release_info(self, pattern: str) -> tuple[str, str] | None:
        """
        Get the latest release download URL and version from GitHub API.
        
        Returns:
            Tuple of (download_url, version) or None if failed.
        """
        try:
            req = urllib.request.Request(
                JMDICT_RELEASES_API,
                headers={"User-Agent": "YomisubAPI", "Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                
                version = data.get("tag_name", "unknown")
                assets = data.get("assets", [])
                
                # Find the requested file
                for asset in assets:
                    name = asset.get("name", "")
                    if re.match(pattern, name):
                        return asset.get("browser_download_url"), version
                
                print(f"⚠️ No English dictionary found in release assets")
                return None
        except Exception as e:
            print(f"⚠️ Failed to fetch release info: {e}")
            return None
    
    def _download_latest(self, data_dir: Path) -> None:
        """Download the latest JMdict from GitHub releases."""
        release_info = self._get_latest_release_info(JMDICT_DOWNLOAD_PATTERN)
        
        if not release_info:
            raise RuntimeError("Could not find latest release info")
        
        download_url, version = release_info
        print(f"📦 Downloading JMdict {version}...")
        
        # Create data directory if needed
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Download file
        target_path = data_dir / "jmdict-eng.json.gz"
        
        req = urllib.request.Request(download_url, headers={"User-Agent": "YomisubAPI"})
        with urllib.request.urlopen(req, timeout=300) as response:  # 5 min timeout for large file
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            with open(target_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        pct = (downloaded / total_size) * 100
                        print(f"\r   Downloaded: {downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB ({pct:.1f}%)", end="", flush=True)
        
        print()  # New line after download progress
        print(f"✅ Downloaded to {target_path}")
        
        # Load the downloaded file
        self._load(target_path)
        self._version = version
    
    def _load(self, path: Path) -> None:
        """Load and index the dictionary."""
        print(f"📚 Loading JMdict from {path}...")
        
        # Extract version from filename if possible
        match = re.search(r"jmdict-eng-(\d+\.\d+\.\d+)", path.name)
        if match:
            self._version = match.group(1)
        
        # Handle gzipped files
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        
        # Get version from file metadata if available
        if "version" in data:
            self._version = data["version"]
        
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
        version_str = f" (v{self._version})" if self._version else ""
        print(f"✓ Loaded {len(words)} entries ({len(self._index_kanji)} kanji, {len(self._index_kana)} kana){version_str}")
    
    def _find_and_load_names(self) -> None:
        """Find name dictionary file in common locations or download."""
        data_dir = Path(__file__).parent.parent.parent / "data"
        
        search_paths = [
            data_dir / "jmnedict-eng.json",
            data_dir / "jmnedict-eng.json.gz",
        ]
        
        if data_dir.exists():
            for f in data_dir.glob("jmnedict-eng-*.json*"):
                search_paths.insert(0, f)
        
        for path in search_paths:
            if path.exists():
                try:
                    self._load_names(path)
                    return
                except Exception as e:
                    print(f"⚠️ Failed to load {path}: {e}")

        # Download
        print("📥 JMNedict (Names) not found locally. Attempting to download...")
        try:
            self._download_latest_names(data_dir)
        except Exception as e:
            print(f"⚠️ Failed to download JMNedict: {e}")

    def _download_latest_names(self, data_dir: Path) -> None:
        """Download latest JMNedict (Zip)."""
        release_info = self._get_latest_release_info(JMNEDICT_DOWNLOAD_PATTERN)
        if not release_info:
            raise RuntimeError("Could not find latest JMNedict release (zip)")
            
        download_url, version = release_info
        print(f"📦 Downloading JMNedict {version}...")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Temp zip path
        zip_path = data_dir / "jmnedict_temp.zip"
        
        req = urllib.request.Request(download_url, headers={"User-Agent": "YomisubAPI"})
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(zip_path, "wb") as f:
                while True:
                    chunk = response.read(1024*1024)
                    if not chunk: break
                    f.write(chunk)
                    
        print(f"📦 Extracting JMNedict...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Find the json file inside
                json_files = [n for n in zf.namelist() if n.endswith('.json')]
                if not json_files:
                    raise RuntimeError("No JSON found in JMNedict zip")
                
                source_filename = json_files[0]
                target_path = data_dir / "jmnedict-eng.json"
                
                with zf.open(source_filename) as source, open(target_path, "wb") as target:
                    target.write(source.read())
                    
            print(f"✅ Extracted Names to {target_path}")
            self._load_names(target_path)
        finally:
            if zip_path.exists():
                zip_path.unlink()

    def _load_names(self, path: Path) -> None:
        """Load and index name dictionary."""
        print(f"📚 Loading JMNedict from {path}...")
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f: data = json.load(f)
        else:
            with open(path, encoding="utf-8") as f: data = json.load(f)
            
        words = data.get("words", [])
        for entry in words:
            entry["_is_name"] = True
            for kanji in entry.get("kanji", []):
                t = kanji.get("text", "")
                if t: 
                    if t not in self._index_names_kanji: self._index_names_kanji[t] = []
                    self._index_names_kanji[t].append(entry)
            for kana in entry.get("kana", []):
                t = kana.get("text", "")
                if t:
                    if t not in self._index_names_kana: self._index_names_kana[t] = []
                    self._index_names_kana[t].append(entry)
        print(f"✓ Loaded {len(words)} name entries")

    @classmethod
    @lru_cache(maxsize=1)
    def get_instance(cls) -> Self:
        """Get or create a singleton instance."""
        return cls()
    
    def _normalize_kana(self, text: str) -> str:
        """Normalize kana by removing dakuten/handakuten (voiced marks)."""
        if not text:
            return ""
        # NFD decomposition splits 'ば' into 'は' + dakuten
        normalized = unicodedata.normalize('NFD', text)
        # Filter out combining voiced sound marks (U+3099) and semi-voiced (U+309A)
        return "".join(c for c in normalized if c not in ('\u3099', '\u309a'))

    def _find_best_entry(self, word: str, reading: str | None = None, is_counter: bool = False, include_names: bool = False) -> dict | None:
        """Find the best matching dictionary entry."""
        entries = self._index_kanji.get(word) or self._index_kana.get(word)
        
        # If no standard entry, check names if requested
        if not entries and include_names:
            entries = self._index_names_kanji.get(word) or self._index_names_kana.get(word)
        
        if not entries:
            return None
        
        # Check if input is purely hiragana
        is_hiragana_input = all('\u3040' <= c <= '\u309f' for c in word)
        
        # Precompute normalized reading if available
        norm_reading = self._normalize_kana(reading) if reading else None

        # Find best entry: prioritize common entries and reading matches
        best_entry = None
        best_score = -1
        
        for entry in entries:
            score = 0
            
            # Check if any kanji/kana form is marked as common
            for kanji in entry.get("kanji", []):
                if kanji.get("text") == word and kanji.get("common"):
                    score += 10
            for kana in entry.get("kana", []):
                if kana.get("common"):
                    score += 5
                kana_text = kana.get("text")
                if reading and kana_text == reading:
                    score += 20  # Strong preference for reading match
                elif norm_reading and kana_text and self._normalize_kana(kana_text) == norm_reading:
                    score += 18  # Near-exact phonetic match
            
            senses = entry.get("sense", [])
            
            # Prioritize 'usually kana' entries if input is hiragana
            if senses and is_hiragana_input:
                misc = senses[0].get("misc", [])
                if "uk" in misc:
                    score += 15

            # Boost counter entries if word is used as a counter
            if is_counter and senses:
                # Check if any sense has 'ctr' POS
                for sense in senses:
                    if "ctr" in sense.get("partOfSpeech", []):
                        score += 50
                        break

            if score > best_score:
                best_score = score
                best_entry = entry
        
        return best_entry or entries[0]

    def lookup(self, word: str, reading: str | None = None, is_counter: bool = False) -> str | None:
        """Look up meaning (string only). Names excluded."""
        entry = self._find_best_entry(word, reading, is_counter, include_names=False)
        if not entry:
            return None
        
        # Handle Name entries
        if entry.get("_is_name"):
            translations = entry.get("translation", [])
            if not translations:
                return None
            
            t = translations[0]
            # v3.6.1 structure: translation -> translation -> text
            texts = [x.get("text", "") for x in t.get("translation", [])]
            if not texts:
                return None
                
            meaning = "; ".join(texts[:3])
            return meaning

        senses = entry.get("sense", [])
        if not senses:
            return None
            
        # If we looked for a counter, prioritize the counter sense gloss
        target_senses = senses
        if is_counter:
            counter_senses = [s for s in senses if "ctr" in s.get("partOfSpeech", [])]
            if counter_senses:
                target_senses = counter_senses

        glosses = [g.get("text", "") for g in target_senses[0].get("gloss", []) if g.get("text")]
        return "; ".join(glosses[:3]) if glosses else None

    # Common name suffixes to try stripping
    _NAME_SUFFIXES = ("さん", "先生", "様", "君", "ちゃん", "殿", "氏", "さま")
    
    def lookup_details(self, word: str, reading: str | None = None, is_counter: bool = False) -> dict | None:
        """Look up meaning and tags. Includes names."""
        entry = self._find_best_entry(word, reading, is_counter, include_names=True)
        
        # If not found, try stripping name suffixes (田中さん → 田中)
        if not entry:
            for suffix in self._NAME_SUFFIXES:
                if word.endswith(suffix) and len(word) > len(suffix):
                    base_word = word[:-len(suffix)]
                    entry = self._find_best_entry(base_word, None, is_counter, include_names=True)
                    if entry and entry.get("_is_name"):
                        # Found a name! Add suffix info to the result
                        break
        
        if not entry:
            return None
            
        # Handle Name entries
        if entry.get("_is_name"):
            translations = entry.get("translation", [])
            if not translations:
                return None
            
            t = translations[0]
            # v3.6.1 structure: translation -> translation -> text
            texts = [x.get("text", "") for x in t.get("translation", [])]
            if not texts:
                return None
            
            meaning = "; ".join(texts[:3])
            tags = {"Name"}
            
            # Add name types (surname, given name, etc) - key is "type"
            for nt in t.get("type", []):
                tags.add(nt.title())
                
            return {"meaning": meaning, "tags": sorted(list(tags))}

        senses = entry.get("sense", [])
        if not senses:
            return None
        
        # If we looked for a counter, prioritize the counter sense
        target_sense = senses[0]
        if is_counter:
            counter_senses = [s for s in senses if "ctr" in s.get("partOfSpeech", [])]
            if counter_senses:
                target_sense = counter_senses[0]

        glosses = [g.get("text", "") for g in target_sense.get("gloss", []) if g.get("text")]
        meaning = "; ".join(glosses[:3]) if glosses else None
        
        # Extract tags (from the chosen sense AND generic entry tags if needed)
        # We'll use target_sense for specific tags, but common/uk might be on others? 
        # Simpler to just use target_sense for POS/Misc
        tags = set()
        
        # POS tags mapping
        POS_TAGS = {
            "vt": "Transitive",
            "vi": "Intransitive",
            "uk": "Usually Kana",
            "ctr": "Counter",
        }
        for pos in target_sense.get("partOfSpeech", []):
            if pos in POS_TAGS:
                tags.add(POS_TAGS[pos])
            elif "adj" in pos:
                tags.add("Adjective")

        # Misc/Field tags
        MISC_TAGS = {
            "uk": "Usually Kana",
            "sl": "Slang",
            "col": "Colloquial",
            "hon": "Honorific",
            "hum": "Humble",
            "abbr": "Abbreviation",
            "comp": "Computer", 
            "med": "Medical",
            "food": "Food",
        }
        
        for m in target_sense.get("misc", []) + target_sense.get("field", []):
            if m in MISC_TAGS:
                tags.add(MISC_TAGS[m])

        return {
            "meaning": meaning,
            "tags": sorted(list(tags))
        }
    
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
    
    @property
    def version(self) -> str | None:
        """Get the JMDict version if known."""
        return self._version
