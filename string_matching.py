import re
from rapidfuzz import process, fuzz

# Input lists
invoice = [
    'TVS M6x25 Screw',
    'TVS M6x1 Sunloc Nut',
    'Fevitite Rapid & Clear 36GMS(140)',
    'Grease Nipple M12',
    'PVC Conector',
    'Taparia Screw Driver 862-150(94)',
    'Screw Driver Striking(8x210)(DN)140',
    'TVS M6x35 Screw',
    'TVS M6x1 Sunloc Nut'
]

po = [
    'Bolt (M6x25) 30170035',
    'Nut M6. 30170230',
    'Fevitite (Araldite). 30100084',
    'Grease Nipple Small. 30100125',
    'PVC Connectoer 3. 30170254',
    'Screw Driver 2In1. 40210467',
    'Screw Driver. 50210154',
    'Bolt&Nut M6x35. 30170395',
    'Nut M6. 30170230'
]

# Text cleaning function
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return text.strip()

# Preprocess
cleaned_invoice = [clean_text(item) for item in invoice]
cleaned_po = [clean_text(item) for item in po]

# Matching
matches = []
for i, po_item in enumerate(cleaned_po):
    best_match, score, matched_index = process.extractOne(
        po_item,
        cleaned_invoice,
        scorer=fuzz.token_sort_ratio
    )
    matches.append({
        'po_item': po[i],
        'matched_invoice_item': invoice[matched_index],
        'score': score
    })

# Display results
print("\nMatched Results:")
for match in matches:
    print(f"PO: {match['po_item']}\n→ Invoice: {match['matched_invoice_item']}\n→ Score: {match['score']}\n")
