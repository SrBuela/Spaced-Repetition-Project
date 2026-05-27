# app.py
from flask import Flask, Response, redirect, url_for, flash, render_template, request, jsonify, send_file
from flask_login import LoginManager, login_required, current_user
from models import db, User, Deck, Card, QuizResult, LearningProgress, CardReview
from config import Config
import csv
from io import StringIO, BytesIO
from datetime import datetime, date
import pandas as pd
import zipfile
import os

# Groq for Chatbot
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Groq not installed. Run: pip install groq")

# Initialize Flask app
app = Flask(__name__, template_folder='../frontend/templates', static_folder='static')
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize Groq client
groq_client = None
if GROQ_AVAILABLE:
    try:
        # Use your Groq API key here
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("✅ Groq AI Chatbot initialized (Llama 3.3 70B)")
    except Exception as e:
        print(f"⚠️ Groq initialization failed: {e}")
        groq_client = None

# Chatbot system prompt
CHATBOT_SYSTEM_PROMPT = """You are an expert Python programming assistant for the Auxilium College Smart Study Buddy app.

Your job is to:
- Answer ANY question about Python clearly and accurately
- Generate clean, well-commented Python code on request
- Explain concepts with simple examples (beginner-friendly)
- Debug code if the user pastes it
- Suggest best practices and improvements
- Cover topics like: basics, OOP, data structures, algorithms, libraries (NumPy, Pandas, Flask, etc.), file I/O, APIs, decorators, generators, async, etc.

Response style:
- Always use proper Python code blocks with markdown formatting
- Keep explanations concise but complete
- If generating code, add a brief explanation of how it works
- If the user's question is unclear, ask for clarification
- Be friendly and encouraging to students learning Python

Keep responses under 2000 tokens for faster delivery."""

# Create database tables and demo user
with app.app_context():
    db.create_all()
    print("✅ Database tables created")
    
    # Create demo user if not exists
    if not User.query.filter_by(username='student').first():
        from werkzeug.security import generate_password_hash
        demo = User(
            username='student', 
            email='student@example.com', 
            password=generate_password_hash('study123'),
            total_points=0,
            total_studied=0,
            streak=0,
            unlocked_decks=999,
            stars=0
        )
        db.session.add(demo)
        db.session.commit()
        print("✅ Demo user created: student / study123")
        
        # Create demo deck with 10 cards
        demo_deck = Deck(name="🐍 Python Demo (10 Cards)", user_id=demo.id)
        db.session.add(demo_deck)
        db.session.commit()
        
        demo_cards = [
            ("What is Python?", "A high-level, interpreted programming language"),
            ("How do you print in Python?", "print('Hello World')"),
            ("What is a variable?", "Container for storing data values"),
            ("What is a list?", "Ordered, mutable collection"),
            ("What is a function?", "Reusable block of code"),
            ("What is a dictionary?", "Key-value pair collection"),
            ("What is a loop?", "Repeats a block of code"),
            ("What is an if statement?", "Conditional execution"),
            ("What is a class?", "Blueprint for objects"),
            ("What is inheritance?", "Child class inherits from parent"),
        ]
        
        for i, (q, a) in enumerate(demo_cards):
            algo = 'SM2' if i < 5 else 'FSRS'
            card = Card(
                question=q, 
                answer=a, 
                deck_id=demo_deck.id, 
                algorithm=algo,
                stability=2.0,
                difficulty=5.0,
                e_factor=2.5,
                interval=1,
                review_count=0,
                avg_time=0.0,
                is_mastered=False
            )
            db.session.add(card)
        db.session.commit()
        print("✅ Demo deck created with 10 cards (5 SM2, 5 FSRS)")

# ============================================================
# IMPORT ALL ROUTE MODULES
# ============================================================
from auth import register_auth_routes
from decks import register_decks_routes
from study import register_study_routes
from quiz import register_quiz_routes
from research import register_research_routes
from learning import register_learning_routes

# ============================================================
# REGISTER ALL ROUTES
# ============================================================
register_auth_routes(app)
register_decks_routes(app)
register_study_routes(app)
register_quiz_routes(app)
register_research_routes(app)
register_learning_routes(app)

# ============================================================
# HOME ROUTE
# ============================================================
@app.route('/')
def home():
    return redirect(url_for('login'))

# ============================================================
# DASHBOARD ROUTE
# ============================================================
@app.route('/dashboard')
@login_required
def dashboard():
    decks = Deck.query.filter_by(user_id=current_user.id).all()
    total_cards = sum(len(deck.cards) for deck in decks)
    total_mastered = Card.query.join(Deck).filter(
        Deck.user_id == current_user.id, 
        Card.is_mastered == True
    ).count()
    
    if current_user.total_points:
        new_stars = current_user.total_points // 100
        if new_stars != current_user.stars:
            current_user.stars = new_stars
            db.session.commit()
    
    return render_template('dashboard.html', 
                         decks=decks, 
                         total_cards=total_cards,
                         total_mastered=total_mastered,
                         user=current_user)

# ============================================================
# EXPORT ROUTES
# ============================================================

@app.route('/export')
@login_required
def export():
    """Export cards to CSV"""
    cards = Card.query.join(Deck).filter(Deck.user_id == current_user.id).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Question', 'Answer', 'Algorithm', 'Reviews', 'Avg Time (s)', 'Mastered'])
    for card in cards:
        writer.writerow([
            card.question, 
            card.answer, 
            card.algorithm, 
            card.review_count, 
            round(card.avg_time, 2), 
            'Yes' if card.is_mastered else 'No'
        ])
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename=f'cards_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.csv')
    return response

@app.route('/export/excel')
@login_required
def export_excel():
    """Export all user data to Excel file"""
    user = current_user
    decks = Deck.query.filter_by(user_id=user.id).all()
    
    cards_data = []
    reviews_data = []
    quiz_data = []
    
    for deck in decks:
        for card in deck.cards:
            cards_data.append({
                'Deck': deck.name,
                'Question': card.question,
                'Answer': card.answer,
                'Algorithm': card.algorithm,
                'Review Count': card.review_count,
                'Average Time (s)': card.avg_time,
                'Mastered': 'Yes' if card.is_mastered else 'No'
            })
            
            for review in card.reviews:
                reviews_data.append({
                    'Deck': deck.name,
                    'Question': card.question,
                    'Algorithm': card.algorithm,
                    'Rating': review.rating,
                    'Correct': 'Yes' if review.is_correct else 'No',
                    'Response Time (s)': review.response_time,
                    'Date': review.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
    
    quizzes = QuizResult.query.filter_by(user_id=user.id).all()
    for quiz in quizzes:
        deck = Deck.query.get(quiz.deck_id)
        quiz_data.append({
            'Deck': deck.name if deck else 'General Quiz',
            'Score': quiz.score,
            'Total Questions': quiz.total_questions,
            'Percentage': f"{quiz.percentage}%",
            'Time Taken (s)': quiz.time_taken,
            'Date': quiz.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        user_stats = pd.DataFrame([{
            'Username': user.username,
            'Total Points': user.total_points,
            'Stars': user.stars,
            'Streak': user.streak,
            'Cards Studied': user.total_studied,
            'Decks Available': len(decks)
        }])
        user_stats.to_excel(writer, sheet_name='User Stats', index=False)
        
        if cards_data:
            pd.DataFrame(cards_data).to_excel(writer, sheet_name='Cards', index=False)
        if reviews_data:
            pd.DataFrame(reviews_data).to_excel(writer, sheet_name='Reviews', index=False)
        if quiz_data:
            pd.DataFrame(quiz_data).to_excel(writer, sheet_name='Quiz Results', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'study_data_{user.username}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

# ============================================================
# ADMIN RESEARCH ROUTES
# ============================================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard to view all students' data"""
    if current_user.username != 'admin':
        flash('Access denied! Admin only.', 'error')
        return redirect(url_for('dashboard'))
    
    students = User.query.filter(User.username != 'admin').all()
    students_data = []
    
    for student in students:
        fsrs_cards = Card.query.join(Deck).filter(
            Deck.user_id == student.id,
            Card.algorithm == 'FSRS'
        ).all()
        
        sm2_cards = Card.query.join(Deck).filter(
            Deck.user_id == student.id,
            Card.algorithm == 'SM2'
        ).all()
        
        fsrs_reviews = CardReview.query.join(Card).join(Deck).filter(
            Deck.user_id == student.id,
            Card.algorithm == 'FSRS'
        ).all()
        
        sm2_reviews = CardReview.query.join(Card).join(Deck).filter(
            Deck.user_id == student.id,
            Card.algorithm == 'SM2'
        ).all()
        
        fsrs_correct = sum(1 for r in fsrs_reviews if r.rating >= 3)
        fsrs_retention = round((fsrs_correct / len(fsrs_reviews) * 100), 1) if fsrs_reviews else 0
        
        sm2_correct = sum(1 for r in sm2_reviews if r.rating >= 3)
        sm2_retention = round((sm2_correct / len(sm2_reviews) * 100), 1) if sm2_reviews else 0
        
        students_data.append({
            'id': student.id,
            'username': student.username,
            'email': student.email,
            'total_studied': student.total_studied,
            'total_points': student.total_points,
            'streak': student.streak,
            'fsrs_retention': fsrs_retention,
            'sm2_retention': sm2_retention,
            'fsrs_cards': len(fsrs_cards),
            'sm2_cards': len(sm2_cards),
            'fsrs_reviews': len(fsrs_reviews),
            'sm2_reviews': len(sm2_reviews),
        })
    
    total_students = len(students)
    avg_fsrs_retention = round(sum(s['fsrs_retention'] for s in students_data) / total_students, 1) if total_students > 0 else 0
    avg_sm2_retention = round(sum(s['sm2_retention'] for s in students_data) / total_students, 1) if total_students > 0 else 0
    fsrs_better = sum(1 for s in students_data if s['fsrs_retention'] > s['sm2_retention'])
    
    return render_template('admin_dashboard.html',
                         students=students_data,
                         total_students=total_students,
                         avg_fsrs_retention=avg_fsrs_retention,
                         avg_sm2_retention=avg_sm2_retention,
                         fsrs_better=fsrs_better)

@app.route('/admin/export_all')
@login_required
def admin_export_all():
    """Export ALL students' data as ZIP for research"""
    if current_user.username != 'admin':
        flash('Access denied! Admin only.', 'error')
        return redirect(url_for('dashboard'))
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        all_students = []
        users = User.query.filter(User.username != 'admin').all()
        
        for user in users:
            fsrs_cards = Card.query.join(Deck).filter(
                Deck.user_id == user.id,
                Card.algorithm == 'FSRS'
            ).all()
            
            sm2_cards = Card.query.join(Deck).filter(
                Deck.user_id == user.id,
                Card.algorithm == 'SM2'
            ).all()
            
            fsrs_reviews = CardReview.query.join(Card).join(Deck).filter(
                Deck.user_id == user.id,
                Card.algorithm == 'FSRS'
            ).all()
            
            sm2_reviews = CardReview.query.join(Card).join(Deck).filter(
                Deck.user_id == user.id,
                Card.algorithm == 'SM2'
            ).all()
            
            fsrs_correct = sum(1 for r in fsrs_reviews if r.rating >= 3)
            fsrs_retention = round((fsrs_correct / len(fsrs_reviews) * 100), 1) if fsrs_reviews else 0
            
            sm2_correct = sum(1 for r in sm2_reviews if r.rating >= 3)
            sm2_retention = round((sm2_correct / len(sm2_reviews) * 100), 1) if sm2_reviews else 0
            
            all_students.append({
                'Student ID': user.id,
                'Username': user.username,
                'Email': user.email,
                'Total Cards Studied': user.total_studied,
                'Total Points': user.total_points,
                'Streak': user.streak,
                'FSRS Retention (%)': fsrs_retention,
                'SM2 Retention (%)': sm2_retention,
                'FSRS Cards': len(fsrs_cards),
                'SM2 Cards': len(sm2_cards),
                'FSRS Reviews': len(fsrs_reviews),
                'SM2 Reviews': len(sm2_reviews),
            })
        
        if all_students:
            keys = all_students[0].keys()
            master_csv = ','.join(keys) + '\n'
            for student in all_students:
                master_csv += ','.join(str(student[k]) for k in keys) + '\n'
            zip_file.writestr(f'all_students_data_{timestamp}.csv', master_csv)
    
    zip_buffer.seek(0)
    
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'research_data_all_students_{timestamp}.zip'
    )

# ============================================================
# ADMIN RESET ROUTE
# ============================================================
@app.route('/admin/reset')
@login_required
def admin_reset():
    decks = Deck.query.filter_by(user_id=current_user.id).all()
    for deck in decks:
        for card in deck.cards:
            card.review_count = 0
            card.avg_time = 0
            card.is_mastered = False
            card.last_review = None
            card.next_review = None
            if card.algorithm == 'FSRS':
                card.stability = 2.0
                card.difficulty = 5.0
            else:
                card.e_factor = 2.5
                card.interval = 1
    
    current_user.total_studied = 0
    current_user.total_points = 0
    current_user.stars = 0
    current_user.streak = 0
    current_user.last_study_date = None
    db.session.commit()
    
    flash('✅ All your progress has been reset! You can start fresh.', 'success')
    return redirect(url_for('dashboard'))

# ============================================================
# CHATBOT ROUTE — Groq AI Python Tutor (FAST & FREE)
# ============================================================

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    """Chatbot endpoint using Groq's Llama 3.3 70B (super fast!)"""
    
    if not GROQ_AVAILABLE or groq_client is None:
        return jsonify({'error': 'Chatbot service not available. Please install groq: pip install groq'}), 503
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    try:
        # Build conversation messages
        messages = [
            {"role": "system", "content": CHATBOT_SYSTEM_PROMPT}
        ]
        
        # Add conversation history (last 10 messages max for context)
        for msg in history[-10:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Send to Groq (Llama 3.3 70B - excellent for coding!)
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            top_p=0.95,
        )
        
        reply = response.choices[0].message.content
        
        # Award 1 point for using chatbot (encourages engagement)
        current_user.total_points = (current_user.total_points or 0) + 1
        db.session.commit()
        
        return jsonify({'reply': reply})

    except Exception as e:
        error_msg = str(e)
        if "API_KEY" in error_msg or "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return jsonify({'error': 'Invalid API key. Please check your Groq API key.'}), 500
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            return jsonify({'error': 'Rate limit reached. Please wait a moment and try again.'}), 429
        else:
            return jsonify({'error': f'Chatbot error: {error_msg}'}), 500

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == '__main__':
    print('\n' + '='*60)
    print('🐍 PYTHON FULL COURSE - SMART STUDY BUDDY')
    print('='*60)
    print('\n📋 FEATURES:')
    print('   ✅ FSRS vs SM-2 Algorithm Comparison')
    print('   ✅ Learning Material with Progress Tracking')
    print('   ✅ Study Mode with Timer')
    print('   ✅ Multiple Choice Quiz')
    print('   ✅ Research Dashboard')
    print('   ✅ Stars & Points System')
    print('   ✅ Export Data to Excel/CSV')
    print('   ✅ Admin Research Dashboard')
    if GROQ_AVAILABLE and groq_client:
        print('   ✅ Groq AI Chatbot (Llama 3.3 70B) - FAST & FREE!')
    else:
        print('   ⚠️ Chatbot unavailable (groq not installed)')
    print('='*60)
    print('\n👉 http://127.0.0.1:5000')
    print('📚 Demo Login: student')
    print('🔑 Password: study123')
    print('👑 Admin Login: admin')
    print('🔑 Admin Password: [create one]')
    print('='*60 + '\n')
    app.run(debug=True, host='127.0.0.1', port=5000)