# indicator/utils/adx.py
import numpy as np
import pandas as pd

def compute_adx(df, period=14):
    """
    Compute ADX, +DI, -DI, and supporting columns to match the provided Excel formulas exactly.
    Adjusted indexing to match the Excel anchor rows used in the solution file.
    """
    df = df.copy().reset_index(drop=True)
    cols_lower = {c.lower(): c for c in df.columns}
    for needed in ['high', 'low', 'close']:
        if needed not in cols_lower:
            raise ValueError("Input dataframe must contain columns: High, Low, Close")
    H = df[cols_lower['high']].astype(float)
    L = df[cols_lower['low']].astype(float)
    C = df[cols_lower['close']].astype(float)

    prev_close = C.shift(1)
    prev_high = H.shift(1)
    prev_low = L.shift(1)

    n = len(df)
    df['TR'] = np.nan
    df['+DM'] = 0.0
    df['-DM'] = 0.0
    df['TR14'] = np.nan
    df['+DM14'] = np.nan
    df['-DM14'] = np.nan
    df['+DI14'] = np.nan
    df['-DI14'] = np.nan
    df['DX'] = np.nan
    df['ADX'] = np.nan

    # Raw TR (start at index 1 since prev_close available from index 1)
    for i in range(n):
        if i == 0:
            df.at[i, 'TR'] = np.nan
            continue
        tr_candidates = [
            H.iat[i] - L.iat[i],
            abs(H.iat[i] - prev_close.iat[i]) if not np.isnan(prev_close.iat[i]) else np.nan,
            abs(L.iat[i] - prev_close.iat[i]) if not np.isnan(prev_close.iat[i]) else np.nan,
        ]
        df.at[i, 'TR'] = np.nanmax(np.array(tr_candidates, dtype=float))

    up_move = H - prev_high
    down_move = prev_low - L
    df['+DM'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    df['-DM'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # INDEX MAPPING ADJUSTED:
    # raw TR first meaningful at pandas index = 1 (Excel row 2->3 mapping used by your Excel)
    first_raw_idx = 1
    # first smoothed sums (TR14 etc) located at pandas index = period (14)
    first_smooth_idx = period         # 14
    # first ADX at pandas index = first_smooth_idx + period (28)
    first_adx_idx = first_smooth_idx + period - 1  # 28

    if n <= first_smooth_idx:
        return df

    # Initial sums: sum raw TR from first_raw_idx..first_smooth_idx inclusive (14 values)
    df.at[first_smooth_idx, 'TR14'] = df['TR'].iloc[first_raw_idx:first_smooth_idx+1].sum()
    df.at[first_smooth_idx, '+DM14'] = df['+DM'].iloc[first_raw_idx:first_smooth_idx+1].sum()
    df.at[first_smooth_idx, '-DM14'] = df['-DM'].iloc[first_raw_idx:first_smooth_idx+1].sum()

    # Wilder smoothing thereafter
    for i in range(first_smooth_idx+1, n):
        prev_TR14 = df.at[i-1, 'TR14']
        prev_pDM14 = df.at[i-1, '+DM14']
        prev_nDM14 = df.at[i-1, '-DM14']

        df.at[i, 'TR14'] = prev_TR14 - (prev_TR14 / period) + df.at[i, 'TR']
        df.at[i, '+DM14'] = prev_pDM14 - (prev_pDM14 / period) + df.at[i, '+DM']
        df.at[i, '-DM14'] = prev_nDM14 - (prev_nDM14 / period) + df.at[i, '-DM']

    mask_tr14 = df['TR14'].notna() & (df['TR14'] != 0)
    df.loc[mask_tr14, '+DI14'] = 100.0 * (df.loc[mask_tr14, '+DM14'] / df.loc[mask_tr14, 'TR14'])
    df.loc[mask_tr14, '-DI14'] = 100.0 * (df.loc[mask_tr14, '-DM14'] / df.loc[mask_tr14, 'TR14'])

    di_sum = df['+DI14'] + df['-DI14']
    di_diff = (df['+DI14'] - df['-DI14']).abs()
    mask_dx = di_sum != 0
    df.loc[mask_dx, 'DX'] = 100.0 * (di_diff.loc[mask_dx] / di_sum.loc[mask_dx])

    # ADX initial value: average of DX[first_smooth_idx .. first_adx_idx] inclusive
    if n > first_adx_idx:
        df.at[first_adx_idx, 'ADX'] = df['DX'].iloc[first_smooth_idx:first_adx_idx+1].mean()

        for i in range(first_adx_idx+1, n):
            prev_adx = df.at[i-1, 'ADX']
            current_dx = df.at[i, 'DX']
            if np.isnan(prev_adx) or np.isnan(current_dx):
                df.at[i, 'ADX'] = np.nan
            else:
                df.at[i, 'ADX'] = (prev_adx * (period - 1) + current_dx) / period

    return df
