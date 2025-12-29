
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from services.verb import _conjugate_auxiliary, Auxiliary, Conjugation, deconjugate_verb

# Test what POTENTIAL produces for 食べる
print("Testing POTENTIAL auxiliary conjugation for 食べる (ichidan):")
for conj in Conjugation:
    try:
        result = _conjugate_auxiliary("食べる", Auxiliary.POTENTIAL, conj, type2=True)
        print(f"  {conj.name}: {result}")
    except ValueError as e:
        print(f"  {conj.name}: ValueError - {e}")

print("\nTesting POTENTIAL + MASU combinations:")
# POTENTIAL returns a new verb, then we apply MASU
try:
    potential_forms = _conjugate_auxiliary("食べる", Auxiliary.POTENTIAL, Conjugation.DICTIONARY, type2=True)
    print(f"  POTENTIAL DICTIONARY: {potential_forms}")
    
    # Now apply MASU to the potential form
    for pf in potential_forms:
        masu_neg = _conjugate_auxiliary(pf, Auxiliary.MASU, Conjugation.NEGATIVE, type2=True)
        print(f"  {pf} + MASU NEGATIVE: {masu_neg}")
except Exception as e:
    print(f"  Error: {e}")

print("\nTesting deconjugate_verb for 食べれません -> 食べる:")
results = deconjugate_verb("食べれません", "食べる", type2=True, max_aux_depth=3)
if results:
    for r in results:
        print(f"  Aux: {r.auxiliaries}, Conj: {r.conjugation}")
else:
    print("  No results found!")
