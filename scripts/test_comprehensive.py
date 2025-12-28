import urllib.request
import json
import sys

API_URL = "http://localhost:8000/analyze_simple"

TEST_SENTENCES = [
    # --- Previous Tests ---
    ("Tricky Vocab (本, こと)", "本を読んで、新しいことを学ぶ。"),
    ("Tricky Vocab (できる)", "日本語ができるようになりたい。"),
    ("Causative-Passive", "母に野菜を食べさせられた。"),
    ("Casual (ちゃう)", "宿題を忘れちゃった。"),
    ("Casual (なきゃ)", "もう行かなきゃ。"),
    
    # --- New Extended Tests ---
    
    # 9. Honorifics (Sonkeigo/Kenjougo)
    ("Honorific (おっしゃる)", "先生がそうおっしゃいました。"),
    ("Humble (参る)", "明日、そちらへ参ります。"),
    ("Polite (召し上がる)", "お昼はもう召し上がりましたか？"),
    
    # 10. Dialect (Kansai-ben)
    ("Dialect (あかん)", "それはあかんよ。"),
    ("Dialect (ホンマ)", "ホンマに？"),
    
    # 11. Onomatopoeia
    ("Onomatopoeia (ドキドキ)", "心臓がドキドキしている。"),
    ("Onomatopoeia (ペラペラ)", "彼女は英語がペラペラだ。"),
    
    # 12. Particles & Questions
    ("Casual Question", "これ、食べる？"),
    ("Emphasis (よ/ね)", "いい天気ですね。そうですよ。"),
    
    # 13. Long Sentence
    ("Long Sentence", "日本に住んでいる間に、色々な場所へ旅行に行きたいと思っています。"),
    
    # 14. Potential Negative Casual
    ("Potential Neg Casual", "全然聞こえない。"),
]

def run_tests():
    print(f"🌍 Testing API at {API_URL}\n")
    
    success_count = 0
    
    for category, text in TEST_SENTENCES:
        print(f"🔹 {category}: {text}")
        try:
            req = urllib.request.Request(
                API_URL, 
                data=json.dumps({"text": text}).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as response:
                data = json.load(response)
            
            # Print vocabulary with tags
            for v in data["vocabulary"]:
                tags = v.get('tags', [])
                tags_str = f" {tags}" if tags else ""
                hint_str = f" [{v['conjugation_hint']}]" if v.get('conjugation_hint') else ""
                
                # Check for noteworthy tags
                if "Honorific" in tags or "Humble" in tags or "Slang" in tags or "Onomatopoeia" in tags:
                    tags_str = f" \033[93m{tags}\033[0m" # Yellow highlight
                
                print(f"   - {v['word']} ({v['base']}): {v['meaning'][:30]}...{hint_str}{tags_str}")
            print("")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")

    print(f"✅ Completed {success_count}/{len(TEST_SENTENCES)} tests.")

if __name__ == "__main__":
    run_tests()
