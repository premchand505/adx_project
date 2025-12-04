# indicator/views.py
import os
import json
import math
import numpy as np
import pandas as pd
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import FileResponse
from .utils.adx import compute_adx

# Ensure a media dir exists for storing processed CSVs
UPLOAD_DIR = getattr(settings, 'MEDIA_ROOT', None) or os.path.join(settings.BASE_DIR, 'media')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def index(request):
    """Render the upload page."""
    return render(request, 'indicator/index.html')


def process_and_render(request):
    """
    Handle uploaded CSV/Excel, compute ADX, save processed CSV and store plot-ready JSON in session.
    Implements downsampling for large datasets to improve readability.
    """
    if request.method != 'POST':
        return redirect('indicator:index')

    csv_file = request.FILES.get('file')
    if csv_file is None:
        return render(request, 'indicator/index.html', {'error': 'No file uploaded'})

    # Read CSV to pandas - allow Excel fallback
    try:
        df = pd.read_csv(csv_file)
    except Exception:
        csv_file.seek(0)
        df = pd.read_excel(csv_file)

    # compute ADX (full dataset)
    df_out = compute_adx(df)

    # save processed CSV to media with deterministic filename (you can change to UUID if needed)
    out_path = os.path.join(UPLOAD_DIR, 'processed_adx_output.csv')
    df_out.to_csv(out_path, index=False)

    # Decide whether to use Date column for x axis
    date_col = None
    for c in df_out.columns:
        if c.lower() == 'date':
            date_col = c
            break

    # DOWN-SAMPLING (only for plotting) to keep chart readable when many rows exist
    n = len(df_out)
    max_points = 350  # target maximum points to plot
    if n > max_points:
        step = int(math.ceil(n / float(max_points)))
        df_plot = df_out.iloc[::step].reset_index(drop=True)
    else:
        df_plot = df_out.copy().reset_index(drop=True)
        step = 1

    # prepare x values 
    if date_col:
        x_vals = df_plot[date_col].astype(str).tolist()
    else:
        x_vals = (df_plot.index + 1).astype(str).tolist()

   
    def clean_series(series_obj):
        if series_obj is None:
            return [None] * len(df_plot)
        out = []
        for v in series_obj:
            if pd.isna(v):
                out.append(None)
            else:
                try:
                    out.append(float(v))
                except Exception:
                    out.append(None)
        return out


    plot_data = {
        'x': x_vals,
        'ADX': clean_series(df_plot.get('ADX')),
        '+DI14': clean_series(df_plot.get('+DI14')),
        '-DI14': clean_series(df_plot.get('-DI14')),
        'full_length': n,
        'downsample_step': step,
    }

    #Compute latest (most-recent, from full df_out) summary values to display above chart
    latest = {}
    #get last non-null values
    def last_non_null(s):
        try:
            arr = s.dropna().values
            return float(arr[-1]) if len(arr) > 0 else None
        except Exception:
            return None

    latest['ADX'] = last_non_null(df_out.get('ADX', pd.Series(dtype=float)))
    latest['+DI14'] = last_non_null(df_out.get('+DI14', pd.Series(dtype=float)))
    latest['-DI14'] = last_non_null(df_out.get('-DI14', pd.Series(dtype=float)))

    plot_data['latest'] = latest

    #store context in session
    request.session['processed_path'] = out_path
    request.session['plot_data'] = plot_data

    return redirect('indicator:results')


def results(request):
    """Render results page with the plot data previously saved in session."""
    plot_data = request.session.get('plot_data')
    if not plot_data:
        return redirect('indicator:index')

    #Pass JSON string to template (safe)
    plot_json = json.dumps(plot_data)
    return render(request, 'indicator/results.html', {'plot_json': plot_json})


def download_processed(request):
    """Serve the processed CSV as an attachment."""
    out_path = request.session.get('processed_path') or os.path.join(UPLOAD_DIR, 'processed_adx_output.csv')
    if not os.path.exists(out_path):
        return render(request, 'indicator/index.html', {'error': 'Processed file not found'})
    return FileResponse(open(out_path, 'rb'), as_attachment=True, filename=os.path.basename(out_path))
