# tests/verify_against_excel.py
import numpy as np
import pandas as pd
from indicator.utils.adx import compute_adx

# Paths (adjust if needed)
input_csv = 'Assignment1-data.csv'               # original input (you uploaded)
expected_xlsx = 'Assignment1-Solution.xlsx'     # expected solution (you uploaded)

def main():
    df_input = pd.read_csv(input_csv)
    df_expected = pd.read_excel(expected_xlsx)

    df_out = compute_adx(df_input)

    # Columns to compare - choose key ADX-related columns and the order you want
    cols_to_check = ['TR','+DM','-DM','TR14','+DM14','-DM14','+DI14','-DI14','DX','ADX']

    mismatches = []
    for col in cols_to_check:
        if col not in df_out.columns or col not in df_expected.columns:
            print("Column missing:", col)
            continue
        # align lengths
        L = min(len(df_out), len(df_expected))
        a = df_out[col].iloc[:L].to_numpy(dtype=float)
        b = df_expected[col].iloc[:L].to_numpy(dtype=float)

        # use isclose with small tolerance
        close = np.isclose(a, b, atol=1e-8, equal_nan=True)
        if not np.all(close):
            bad_idx = np.where(~close)[0]
            for i in bad_idx:
                mismatches.append((col, i, a[i], b[i]))

    if not mismatches:
        print("SUCCESS: All compared values match the Excel solution (within tolerance).")
    else:
        print("MISMATCHES found:", len(mismatches))
        for col, idx, got, expect in mismatches[:50]:
            print(f"Row {idx} Col {col}: got={got} expected={expect}")

if __name__ == '__main__':
    main()
