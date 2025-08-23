import pandas as pd
from werkzeug.utils import secure_filename
import os
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.jinja_env.globals.update(float=float)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return None  # No user system for now


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')
@app.route('/signup')
def signup():
    return render_template('signup.html')
@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/about')
def about():
    return render_template('about.html')

# In-memory datasets
datasets = {'2023': None, '2024': None}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def compare_client(client_id):
    result = {
        'client_id': client_id,
        '2023': None,
        '2024': None,
        'status': None
    }
    try:
        # 2023
        if datasets['2023'] is not None:
            df = datasets['2023']
            client_2023 = df[df['N°'] == int(client_id)]
            if not client_2023.empty:
                result['2023'] = client_2023.iloc[0]['Classe']
            else:
                result['2023'] = "Not found"
        else:
            result['2023'] = "Not found"
        # 2024
        if datasets['2024'] is not None:
            df = datasets['2024']
            client_2024 = df[df['N°'] == int(client_id)]
            if not client_2024.empty:
                result['2024'] = client_2024.iloc[0]['Classe']
            else:
                result['2024'] = "Not found"
        else:
            result['2024'] = "Not found"
        # Status
        if isinstance(result['2023'], (int, float)) and isinstance(result['2024'], (int, float)):
            if result['2023'] < result['2024']:
                result['status'] = "Class increased"
            elif result['2023'] > result['2024']:
                result['status'] = "Class decreased"
            else:
                result['status'] = "Class remained the same"
        elif result['2023'] == "Not found" and result['2024'] != "Not found":
            result['status'] = "New contract in 2024"
        elif result['2023'] != "Not found" and result['2024'] == "Not found":
            result['status'] = "Contract ended after 2023"
        else:
            result['status'] = "None"
    except Exception as e:
        flash(f'Error processing client data: {str(e)}', 'danger')
    return result


@app.route('/compare', methods=['GET', 'POST'])
def compare():
    result = None
    if request.method == 'POST':
        # Handle file upload
        if 'file' in request.files and request.form.get('year'):
            file = request.files['file']
            year = request.form.get('year')
            if file and allowed_file(file.filename) and year in datasets:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    df = pd.read_csv(filepath)
                    datasets[year] = df
                    flash(f'Dataset for {year} loaded successfully!', 'success')
                except Exception as e:
                    flash(f'Error loading dataset: {str(e)}', 'danger')
            else:
                flash('Invalid file or year.', 'danger')
        # Handle client lookup
        elif 'client_id' in request.form:
            client_id = request.form.get('client_id')
            if client_id:
                result = compare_client(client_id)
            else:
                flash('Please enter a client number.', 'warning')
    return render_template('compare.html', datasets=datasets, result=result)
@app.route('/class_stats', methods=['GET', 'POST'])
def class_stats():
    stats = None
    imgs = []
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            df = pd.read_csv(file)
            stats = df.groupby(['Classe_2024', 'comparison'])['count'].sum().unstack(fill_value=0)
            # Generate one plot per class
            for classe in stats.index:
                plt.figure(figsize=(6,4))
                stats.loc[classe].plot(kind='bar', color=['#7abf4b', '#f39c12', '#2980b9', '#c0392b'])
                plt.title(f'Origins for Classe {classe} (2024)')
                plt.xlabel('Origin')
                plt.ylabel('Count')
                plt.tight_layout()
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                img = base64.b64encode(buf.getvalue()).decode('utf-8')
                imgs.append({'classe': classe, 'img': img})
                plt.close()
    return render_template('class_stats.html', stats=stats, imgs=imgs)
if __name__ == '__main__':
    app.run(debug=True)