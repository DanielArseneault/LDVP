import pandas as pd
from pathlib import Path
import json
path = Path('LDVP - Statistiques annuelles.xlsx')
result = {'exists': path.exists(), 'sheets': []}
if path.exists():
    xl = pd.ExcelFile(path)
    for name in xl.sheet_names:
        df = xl.parse(name, nrows=5)
        result['sheets'].append({'name': name, 'rows': df.astype(str).fillna('').head(5).to_dict(orient='records')})
with open('inspect_json.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('wrote inspect_json.json')
