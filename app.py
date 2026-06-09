import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import random
import string
import PyPDF2
from werkzeug.utils import secure_filename
from ml_model import generate_multiple_quizzes

app = Flask(__name__)
app.secret_key = "super_secret_fyp_key" 

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# DATABASE CONNECTION
# ==========================================
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "@iAmYar02"), 
        database=os.environ.get("DB_NAME", "quiz_db"),
        port=os.environ.get("DB_PORT", 3306)
    )

def generate_share_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def extract_text_from_pdf(path):
    text = ""
    with open(path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# AUTH & PROFILE ROUTES
# ==========================================
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND role = %s", (request.form['email'], request.form['role']))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], request.form['password']):
            session.update({'user_id': user['id'], 'email': user['email'], 'role': user['role']})
            return redirect(url_for('dashboard') if user['role'] == 'teacher' else url_for('student_home'))
        flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        full_name = request.form['full_name']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password, role, full_name) VALUES (%s, %s, %s, %s)",
                           (email, password, role, full_name))
            conn.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash("That email is already registered.", "danger")
        finally:
            cursor.close()
            conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        cursor.execute("UPDATE users SET full_name = %s, bio = %s WHERE id = %s", (request.form['full_name'], request.form['bio'], session['user_id']))
        conn.commit()
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('profile.html', user=user)

# ==========================================
# TEACHER ROUTES
# ==========================================
@app.route('/teacher_dashboard')
@login_required
def dashboard():
    if session.get('role') != 'teacher': return redirect(url_for('student_home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT share_code, type, COUNT(*) as total_questions FROM quizzes WHERE is_practice = 0 GROUP BY share_code, type")
    quizzes = cursor.fetchall()
    cursor.execute("SELECT s.student_name, s.score, s.total_questions, s.date_taken, q.share_code FROM student_scores s JOIN quizzes q ON s.quiz_id = q.id WHERE q.is_practice = 0 ORDER BY s.date_taken DESC")
    scores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('teacher_dashboard.html', quizzes=quizzes, scores=scores)

@app.route('/view_questions/<share_code>')
@login_required
def view_questions(share_code):
    if session.get('role') != 'teacher': return redirect(url_for('student_home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM quizzes WHERE share_code = %s", (share_code,))
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    if not questions: return "No questions found.", 404
    return render_template('view_questions.html', questions=questions, share_code=share_code)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    file = request.files['document']
    if file and file.filename.endswith('.pdf'):
        path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(path)
        text = extract_text_from_pdf(path)
        os.remove(path)
        data = generate_multiple_quizzes(text, request.form['q_type'], int(request.form['num_questions']))
        conn = get_db_connection()
        cursor = conn.cursor()
        code = generate_share_code()
        for item in data:
            if 'options' in item: random.shuffle(item['options'])
            cursor.execute("INSERT INTO quizzes (generated_question, target_answer, options, type, share_code, is_practice, creator_email) VALUES (%s, %s, %s, %s, %s, 0, %s)", 
                           (item['question'], item['answer'], "|".join(item['options']) if item.get('options') else None, request.form['q_type'], code, session['email']))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for('dashboard'))

# ==========================================
# STUDENT ROUTES
# ==========================================
@app.route('/student_dashboard')
@login_required
def student_home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name FROM users WHERE id = %s", (session['user_id'],))
    user_row = cursor.fetchone()
    my_name = user_row['full_name'] if user_row and user_row['full_name'] else session['email']
    
    cursor.execute("""
        SELECT s.score, s.total_questions, s.date_taken, q.share_code, q.type, q.is_practice
        FROM student_scores s
        JOIN quizzes q ON s.quiz_id = q.id
        WHERE s.student_name = %s
        ORDER BY s.date_taken DESC
    """, (my_name,))
    scores = cursor.fetchall()
    cursor.execute("SELECT share_code, type, COUNT(*) as total_questions FROM quizzes WHERE is_practice = 1 AND creator_email = %s GROUP BY share_code, type", (session['email'],))
    practice = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('student_dashboard.html', scores=scores, practice_quizzes=practice)

@app.route('/student_generate', methods=['POST'])
@login_required
def student_generate():
    file = request.files['document']
    if file and file.filename.endswith('.pdf'):
        path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(path)
        text = extract_text_from_pdf(path)
        os.remove(path)
        data = generate_multiple_quizzes(text, request.form['q_type'], int(request.form['num_questions']))
        conn = get_db_connection()
        cursor = conn.cursor()
        code = generate_share_code()
        for item in data:
            if 'options' in item: random.shuffle(item['options'])
            cursor.execute("INSERT INTO quizzes (generated_question, target_answer, options, type, share_code, is_practice, creator_email) VALUES (%s, %s, %s, %s, %s, 1, %s)", 
                           (item['question'], item['answer'], "|".join(item['options']) if item.get('options') else None, request.form['q_type'], code, session['email']))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for('student_home'))

@app.route('/join_quiz', methods=['POST'])
@login_required
def join_quiz():
    return redirect(url_for('take_quiz', share_code=request.form['share_code'].strip().upper()))

@app.route('/take_quiz/<share_code>', methods=['GET', 'POST'])
@login_required
def take_quiz(share_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, email FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    name = user['full_name'] if user['full_name'] and user['full_name'].strip() != "" else user['email']
    
    cursor.execute("SELECT * FROM quizzes WHERE share_code = %s", (share_code,))
    questions = cursor.fetchall()
    
    if not questions:
        conn.close()
        return "Quiz not found!", 404
        
    if request.method == 'POST':
        score = sum(1 for q in questions if request.form.get(f"question_{q['id']}") and request.form.get(f"question_{q['id']}").strip() == q['target_answer'].strip())
        cursor.execute("SELECT id FROM quizzes WHERE share_code = %s LIMIT 1", (share_code,))
        quiz_batch = cursor.fetchone()
        
        cursor.execute("INSERT INTO student_scores (student_name, score, total_questions, quiz_id) VALUES (%s, %s, %s, %s)",
                       (name, score, len(questions), quiz_batch['id']))
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('submission_success.html', name=name, score=score, total=len(questions))
    
    cursor.close()
    conn.close()
    return render_template('student_quiz.html', questions=questions, share_code=share_code, student_name=name)

@app.route('/delete_test/<share_code>', methods=['POST'])
@login_required
def delete_test(share_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quizzes WHERE share_code = %s", (share_code,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('student_home'))

if __name__ == '__main__':
    # Get Render's assigned port, or default to 5000 for local testing
    port = int(os.environ.get("PORT", 5000))
    # Bind to 0.0.0.0 to allow external connections
    app.run(host="0.0.0.0", port=port, debug=False)
