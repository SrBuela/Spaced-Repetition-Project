# reset_complete.py
from app import app, db
from models import User, Deck, Card, QuizResult, LearningProgress
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    print("=" * 50)
    print("RESETTING DATABASE")
    print("=" * 50)
    
    # Drop all tables
    print("Dropping all tables...")
    db.drop_all()
    
    # Create all tables
    print("Creating all tables...")
    db.create_all()
    print("✅ All tables created")
    
    # Create demo user
    print("\nCreating demo user...")
    demo_user = User(
        username='student',
        email='student@example.com',
        password=generate_password_hash('study123'),
        total_points=0,
        total_studied=0,
        streak=0,
        unlocked_decks=1,
        stars=0,
        created_at=datetime.utcnow()
    )
    db.session.add(demo_user)
    db.session.commit()
    print(f"✅ Demo user created: student / study123 (ID: {demo_user.id})")
    
    # Create demo deck
    print("\nCreating demo deck...")
    demo_deck = Deck(
        name="🐍 Python Basics",
        description="Learn the fundamentals of Python programming",
        user_id=demo_user.id,
        subject="Programming",
        difficulty="Beginner",
        created_at=datetime.utcnow()
    )
    db.session.add(demo_deck)
    db.session.commit()
    print(f"✅ Demo deck created: {demo_deck.name} (ID: {demo_deck.id})")
    
    # Create demo cards
    print("\nCreating demo cards...")
    demo_cards = [
        ("What is Python?", "A high-level, interpreted programming language known for its readability."),
        ("Who created Python?", "Guido van Rossum, and it was first released in 1991."),
        ("How do you print something in Python?", "Using the print() function: print('Hello World')"),
        ("What is a variable in Python?", "A container for storing data values. Example: x = 5"),
        ("What are the basic data types in Python?", "int, float, str, bool, list, tuple, dict, set"),
        ("What is a list in Python?", "An ordered, mutable collection that can hold mixed data types."),
        ("How do you create a function?", "Using the 'def' keyword: def my_function():")
    ]
    
    for i, (question, answer) in enumerate(demo_cards):
        # Alternate between SM2 and FSRS
        algorithm = 'FSRS' if i % 2 == 0 else 'SM2'
        
        card = Card(
            question=question,
            answer=answer,
            deck_id=demo_deck.id,
            algorithm=algorithm,
            review_count=0,
            avg_time=0.0,
            is_mastered=False,
            # FSRS fields
            stability=2.0,
            difficulty=5.0,
            # SM2 fields
            e_factor=2.5,
            interval=1
        )
        db.session.add(card)
    
    db.session.commit()
    print(f"✅ Created {len(demo_cards)} cards ({sum(1 for i in range(len(demo_cards)) if i % 2 == 0)} FSRS, {sum(1 for i in range(len(demo_cards)) if i % 2 != 0)} SM2)")
    
    # Verify everything
    print("\n" + "=" * 50)
    print("VERIFICATION")
    print("=" * 50)
    print(f"Users: {User.query.count()}")
    print(f"Decks: {Deck.query.count()}")
    print(f"Cards: {Card.query.count()}")
    print(f"QuizResults: {QuizResult.query.count()}")
    print(f"LearningProgress: {LearningProgress.query.count()}")
    
    print("\n" + "=" * 50)
    print("✅ DATABASE RESET COMPLETE!")
    print("=" * 50)
    print("\n📚 Login Credentials:")
    print("   URL: http://127.0.0.1:5000")
    print("   Username: student")
    print("   Password: study123")
    print("\n🎯 Features ready:")
    print("   ✅ Study Mode (SM2 & FSRS algorithms)")
    print("   ✅ Quiz Mode")
    print("   ✅ Learning Materials")
    print("   ✅ Progress Tracking")
    print("=" * 50)