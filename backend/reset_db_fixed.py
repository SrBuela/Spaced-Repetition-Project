# reset_db_fixed.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

# Create a minimal app configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_study.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Import models AFTER creating app
from models import db, User, Deck, Card
db.init_app(app)

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    
    print("Creating all tables...")
    db.create_all()
    
    print("Creating test user...")
    test_user = User(
        username='student',
        email='student@example.com',
        password_hash=generate_password_hash('study123'),
        total_points=0,
        total_studied=0,
        streak=0,
        unlocked_decks=1,
        created_at=datetime.utcnow()
    )
    db.session.add(test_user)
    db.session.commit()
    print(f"✅ User created with ID: {test_user.id}")
    
    print("Creating test deck...")
    test_deck = Deck(
        name='Python Basics',
        description='Learn Python fundamentals',
        user_id=test_user.id,
        subject='Programming',
        difficulty='Beginner',
        created_at=datetime.utcnow()
    )
    db.session.add(test_deck)
    db.session.commit()
    print(f"✅ Deck created with ID: {test_deck.id}")
    
    print("Creating test cards...")
    cards_data = [
        ("What is Python?", "A high-level, interpreted programming language"),
        ("Who created Python?", "Guido van Rossum"),
        ("When was Python created?", "1991"),
        ("What is PEP 8?", "Python's style guide for writing clean code"),
        ("Is Python compiled or interpreted?", "Interpreted language")
    ]
    
    for question, answer in cards_data:
        card = Card(
            question=question,
            answer=answer,
            deck_id=test_deck.id,
            algorithm='SM2',
            e_factor=2.5,
            interval=1,
            review_count=0,
            avg_time=0.0,
            is_mastered=False,
            stability=2.0,
            difficulty=5.0
        )
        db.session.add(card)
    
    db.session.commit()
    print(f"✅ Created {len(cards_data)} cards")
    
    # Verify
    print("\n" + "="*50)
    print("✅ DATABASE RESET COMPLETE!")
    print(f"   User: student (password: study123)")
    print(f"   Decks: {Deck.query.count()}")
    print(f"   Cards: {Card.query.count()}")
    print("="*50)