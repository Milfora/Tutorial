from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'changeme'
DATABASE = 'database.db'

# Database utilities

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    pdf BLOB,
                    markups TEXT,
                    scale REAL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                 )''')
    conn.commit()
    conn.close()

# Helper functions

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_first_request
def setup():
    init_db()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('projects'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('projects'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error='User already exists')
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/projects')
def projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects WHERE user_id=?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('projects.html', projects=projects)

@app.route('/projects/new', methods=['POST'])
def new_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    name = request.form.get('name', 'New Project')
    conn = get_db_connection()
    conn.execute('INSERT INTO projects (user_id, name, scale) VALUES (?, ?, ?)', (session['user_id'], name, 1.0))
    conn.commit()
    project_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return redirect(url_for('edit_project', project_id=project_id))

@app.route('/projects/<int:project_id>')
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id=? AND user_id=?', (project_id, session['user_id'])).fetchone()
    conn.close()
    if project is None:
        return redirect(url_for('projects'))
    return render_template('editor.html', project=project)

@app.route('/projects/<int:project_id>/save', methods=['POST'])
def save_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    markups = request.form['markups']
    scale = request.form['scale']
    pdf_file = request.files.get('pdf')
    conn = get_db_connection()
    if pdf_file:
        pdf_data = pdf_file.read()
        conn.execute('UPDATE projects SET pdf=?, markups=?, scale=? WHERE id=? AND user_id=?',
                     (pdf_data, markups, scale, project_id, session['user_id']))
    else:
        conn.execute('UPDATE projects SET markups=?, scale=? WHERE id=? AND user_id=?',
                     (markups, scale, project_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('projects'))

@app.route('/projects/<int:project_id>/pdf')
def project_pdf(project_id):
    conn = get_db_connection()
    project = conn.execute('SELECT pdf FROM projects WHERE id=? AND user_id=?', (project_id, session['user_id'])).fetchone()
    conn.close()
    if project and project['pdf']:
        pdf_path = f'tmp_{project_id}.pdf'
        with open(pdf_path, 'wb') as f:
            f.write(project['pdf'])
        resp = send_from_directory('.', pdf_path)
        os.remove(pdf_path)
        return resp
    return '', 404

@app.route('/projects/<int:project_id>/data')
def project_data(project_id):
    conn = get_db_connection()
    project = conn.execute('SELECT markups, scale FROM projects WHERE id=? AND user_id=?', (project_id, session['user_id'])).fetchone()
    conn.close()
    if project:
        return jsonify(dict(markups=project['markups'] or '', scale=project['scale']))
    return jsonify({}), 404

if __name__ == '__main__':
    app.run(debug=True)
