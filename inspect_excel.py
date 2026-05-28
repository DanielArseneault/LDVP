import pandas as pd
from pathlib import Path
path = Path('LDVP - Statistiques annuelles.xlsx')
print('exists', path.exists())
xl = pd.ExcelFile(path)
print('sheets', xl.sheet_names)
for name in xl.sheet_names:
    print('---', name, '---')
    df = xl.parse(name, nrows=10)
    print(df.head().to_csv(index=False))
