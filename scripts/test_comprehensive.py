#!/usr/bin/env python3
"""Comprehensive test: names, onomatopoeia, and sentences."""
import urllib.request
import json

URL = "http://localhost:8000/analyze_full"

# Test cases
TESTS = [
    # === NAMES ===
    ("田中さんは医者です", "Name + sentence"),
    ("鈴木先生が来ました", "Name (surname) + came"),
    ("山田太郎という人", "Full name (given+surname)"),
    
    # === ONOMATOPOEIA ===
    ("ドキドキしている", "Heartbeat sound"),
    ("雨がザーザー降っている", "Rain sound"),
    ("犬がワンワン吠えた", "Dog bark"),
    ("キラキラ光っている", "Sparkling"),
    ("彼女はニコニコ笑った", "Smiling"),
    ("ペラペラ話す", "Fluent speaking"),
    
    # === COMPLEX SENTENCES ===
    ("日本語を勉強することができません", "Can't study Japanese"),
    ("明日雨が降るかもしれません", "It might rain tomorrow"),
    ("食べなければならない", "Must eat"),
    ("行かないほうがいいです", "Better not to go"),
    ("彼は学生ではありません", "He is not a student"),
    
    # === MIXED ===
    ("佐藤さんがドキドキしながら話した", "Name + onomatopoeia + verb"),
    ("高橋先輩はペラペラ英語を話すことができる", "Name + fluent + can speak English"),
]

def test(text, description):
    try:
        req = urllib.request.Request(
            URL,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
        
        print(f"\n{'='*60}")
        print(f"📝 {text}")
        print(f"   ({description})")
        print("-"*60)
        
        for p in data.get("phrases", []):
            surface = p["surface"]
            pos = p["pos"]
            meaning = p.get("meaning") or ""
            grammar = p.get("grammar_note") or ""
            tags = p.get("tags", [])
            conj = p.get("conjugation", {})
            conj_sum = conj.get("summary", "") if conj else ""
            
            # Format output
            line = f"  {surface: <12} [{pos: <8}]"
            
            if meaning:
                line += f" = {meaning[:25]}..."[:40] if len(meaning) > 25 else f" = {meaning}"
            
            if tags:
                line += f" {tags}"
            
            if grammar:
                line += f" 【{grammar}】"
            
            if conj_sum:
                line += f" → {conj_sum}"
            
            print(line)
            
    except Exception as e:
        print(f"❌ Error for '{text}': {e}")

def main():
    print("🧪 COMPREHENSIVE TEST: Names, Onomatopoeia, Sentences")
    print("="*60)
    
    for text, desc in TESTS:
        test(text, desc)
    
    print("\n" + "="*60)
    print("✅ Testing complete!")

if __name__ == "__main__":
    main()
