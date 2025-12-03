# indicator/views.py
import os
import io
import json
import pandas as pd
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.urls import reverse
from .utils.adx import compute_adx

UPLOAD_DIR = getattr(settings, 'MEDIA_ROOT', None) or os.path.join(settings.BASE_DIR, 'media')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def index(request):
    """Upload page"""
    return render(request, 'indicator/index.html')

def process_and_render(request):
    """
    POST: receives uploaded CSV (OHLC), runs compute_adx, saves processed CSV to media,
    and redirects to results page which will render the plot.
    """
    if request.method != 'POST':
        return redirect('indicator:index')

    csv_file = request.FILES.get('file')
    if csv_file is None:
        return render(request, 'indicator/index.html', {'error': 'No file uploaded'})

    # Read CSV to pandas - allow common separators
    try:
        df = pd.read_csv(csv_file)
    except Exception:
        # fallback read_excel if CSV disguised as Excel
        csv_file.seek(0)
        df = pd.read_excel(csv_file)

    # compute ADX
    df_out = compute_adx(df)

    # save processed CSV to media with a deterministic filename
    out_path = os.path.join(UPLOAD_DIR, 'processed_adx_output.csv')
    df_out.to_csv(out_path, index=False)

    # store minimal context in session: path and columns for plotting
    request.session['processed_path'] = out_path
    # prepare series for plotly: ADX, +DI14, -DI14
    plot_data = {
        'x': df_out.index.tolist(),
        'ADX': df_out['ADX'].fillna('').tolist(),
        '+DI14': df_out['+DI14'].fillna('').tolist(),
        '-DI14': df_out['-DI14'].fillna('').tolist(),
        'columns': df_out.columns.tolist(),
    }
    request.session['plot_data'] = plot_data

    return redirect('indicator:results')

def results(request):
    plot_data = request.session.get('plot_data')
    if not plot_data:
        return redirect('indicator:index')

    # pass JSON to template
    plot_json = json.dumps(plot_data)
    return render(request, 'indicator/results.html', {'plot_json': plot_json})

def download_processed(request):
    out_path = request.session.get('processed_path') or os.path.join(UPLOAD_DIR, 'processed_adx_output.csv')
    if not os.path.exists(out_path):
        return HttpResponse("Processed file not found", status=404)
    # Serve as attachment
    filename = os.path.basename(out_path)
    response = FileResponse(open(out_path, 'rb'), as_attachment=True, filename=filename)
    return response
