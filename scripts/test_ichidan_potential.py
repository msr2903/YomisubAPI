import sys
from pathlib import Path

# Add src to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.verb import deconjugate_verb, Auxiliary, Conjugation

def test_ichidan_potential():
    test_cases = [
        # (Conjugated form, Base word, Type2)
        ("食べれる", "食べる", True),
        ("食べれない", "食べる", True),
        ("食べれた", "食べる", True),
        ("食べれなかった", "食べる", True),
        ("食べれば", "食べる", True), # Note: This is conditional, not ra-nuki potential. Potential conditional would be 食べれれば
        ("食べれます", "食べる", True),
        ("食べれません", "食べる", True),
        ("見れる", "見る", True),
        ("見れない", "見る", True),
        ("見れた", "見る", True),
        ("見れる", "見る", True),
        ("信じれる", "信じる", True),
        ("起きれる", "起きる", True),
        ("変えれる", "変える", True),
        ("教えれる", "教える", True),
        ("辞めれる", "辞める", True),
    ]

    print(f"{'Conjugated':<15} | {'Base Expected':<10} | {'Found?':<8} | {'Details'}")
    print("-" * 70)

    for conjugated, base, is_type2 in test_cases:
        results = deconjugate_verb(conjugated, base, type2=is_type2)
        found = any(Auxiliary.RERU_RARERU in r.auxiliaries for r in results)
        
        # Also check if it's found as a direct conjugation (which might happen if it's misidentified)
        # But for ra-nuki, it should definitely be under RERU_RARERU auxiliary.
        
        details = ""
        if results:
            detail_list = []
            for r in results:
                aux_str = " + ".join(a.name for a in r.auxiliaries) if r.auxiliaries else "DIRECT"
                detail_list.append(f"[{aux_str} ({r.conjugation.name})]")
            details = ", ".join(detail_list)
        else:
            details = "NOT FOUND"

        print(f"{conjugated:<15} | {base:<10} | {str(found):<8} | {details}")

if __name__ == "__main__":
    test_ichidan_potential()
