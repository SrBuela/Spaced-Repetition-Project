# models.py - Complete Working Version
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    # Points and Progress
    total_points = db.Column(db.Integer, default=0, nullable=False)
    total_studied = db.Column(db.Integer, default=0, nullable=False)
    streak = db.Column(db.Integer, default=0, nullable=False)
    last_study_date = db.Column(db.String(20), default=None)
    
    # Deck Access (RESEARCH MODE: All decks unlocked)
    unlocked_decks = db.Column(db.Integer, default=999, nullable=False)
    
    # Achievements
    stars = db.Column(db.Integer, default=0, nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_id(self):
        return str(self.id)
    
    def add_points(self, points):
        """Add points and update stars automatically"""
        self.total_points = (self.total_points or 0) + points
        # Update stars (1 star per 100 points)
        new_stars = self.total_points // 100
        if new_stars > (self.stars or 0):
            self.stars = new_stars
        return self.total_points
    
    def update_streak(self):
        """Update study streak based on last study date"""
        from datetime import date, timedelta
        today = date.today()
        
        if self.last_study_date:
            try:
                last_date = datetime.fromisoformat(self.last_study_date).date()
                if last_date == today:
                    return self.streak
                elif last_date == today - timedelta(days=1):
                    self.streak = (self.streak or 0) + 1
                else:
                    self.streak = 1
            except:
                self.streak = 1
        else:
            self.streak = 1
        
        self.last_study_date = today.isoformat()
        return self.streak
    
    def update_stars(self):
        """Update stars based on total points"""
        new_stars = self.total_points // 100 if self.total_points else 0
        if new_stars != self.stars:
            self.stars = new_stars
            return True
        return False
    
    def __repr__(self):
        return f'<User {self.username} | Points: {self.total_points} | Stars: {self.stars} | Streak: {self.streak}>'


class Deck(db.Model):
    __tablename__ = 'decks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100), default='Python')
    difficulty = db.Column(db.String(20), default='Beginner')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    cards = db.relationship('Card', backref='deck', lazy=True, cascade='all, delete-orphan')
    
    @property
    def mastered_count(self):
        """Number of mastered cards in this deck"""
        return sum(1 for card in self.cards if card.is_mastered)
    
    @property
    def progress_percent(self):
        """Progress percentage for this deck"""
        if not self.cards:
            return 0
        return (self.mastered_count / len(self.cards)) * 100
    
    @property
    def fsrs_count(self):
        """Number of FSRS cards in this deck"""
        return sum(1 for card in self.cards if card.algorithm == 'FSRS')
    
    @property
    def sm2_count(self):
        """Number of SM-2 cards in this deck"""
        return sum(1 for card in self.cards if card.algorithm == 'SM2')
    
    @property
    def fsrs_mastered(self):
        """Number of mastered FSRS cards in this deck"""
        return sum(1 for card in self.cards if card.algorithm == 'FSRS' and card.is_mastered)
    
    @property
    def sm2_mastered(self):
        """Number of mastered SM-2 cards in this deck"""
        return sum(1 for card in self.cards if card.algorithm == 'SM2' and card.is_mastered)
    
    def __repr__(self):
        return f'<Deck {self.name} | Cards: {len(self.cards)} | Mastered: {self.mastered_count}>'


class Card(db.Model):
    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)
    algorithm = db.Column(db.String(10), default='SM2')  # 'SM2' or 'FSRS'
    
    # Common fields
    last_review = db.Column(db.DateTime, default=None)
    next_review = db.Column(db.DateTime, default=None)
    review_count = db.Column(db.Integer, default=0)
    avg_time = db.Column(db.Float, default=0.0)
    is_mastered = db.Column(db.Boolean, default=False)
    
    # SM-2 specific fields
    e_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=1)
    
    # FSRS specific fields
    stability = db.Column(db.Float, default=2.0)
    difficulty = db.Column(db.Float, default=5.0)
    
    def get_retention_rate(self):
        """Calculate retention rate based on reviews"""
        from models import CardReview
        reviews = CardReview.query.filter_by(card_id=self.id).all()
        if not reviews:
            return 0
        correct = sum(1 for r in reviews if r.rating >= 3)
        return (correct / len(reviews)) * 100
    
    def __repr__(self):
        return f'<Card {self.question[:30]} | Algorithm: {self.algorithm} | Mastered: {self.is_mastered}>'


class QuizResult(db.Model):
    __tablename__ = 'quiz_results'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    percentage = db.Column(db.Float, nullable=False, default=0.0)
    time_taken = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='quiz_results')
    deck = db.relationship('Deck', backref='quiz_results')
    
    @property
    def grade(self):
        """Return letter grade based on percentage"""
        if self.percentage >= 90:
            return 'A+'
        elif self.percentage >= 80:
            return 'A'
        elif self.percentage >= 70:
            return 'B'
        elif self.percentage >= 60:
            return 'C'
        elif self.percentage >= 50:
            return 'D'
        else:
            return 'F'
    
    def __repr__(self):
        return f'<QuizResult Score: {self.score}/{self.total_questions} ({self.percentage}%)>'


class LearningProgress(db.Model):
    __tablename__ = 'learning_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    progress_percent = db.Column(db.Float, default=0.0)
    
    # Relationships
    user = db.relationship('User', backref='learning_progress')
    deck = db.relationship('Deck', backref='learning_progress')
    
    def __repr__(self):
        return f'<LearningProgress User:{self.user_id} Deck:{self.deck_id} Progress:{self.progress_percent}%>'


class CardReview(db.Model):
    __tablename__ = 'card_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1=Again, 2=Hard, 3=Good, 4=Easy
    response_time = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    card = db.relationship('Card', backref='reviews')
    user = db.relationship('User', backref='card_reviews')
    
    @property
    def is_correct(self):
        """Returns True if rating is 3 or 4 (Good or Easy)"""
        return self.rating >= 3
    
    @property
    def rating_text(self):
        """Returns text description of rating"""
        return {1: 'Again', 2: 'Hard', 3: 'Good', 4: 'Easy'}.get(self.rating, 'Unknown')
    
    @property
    def points_earned(self):
        """Points earned for this review"""
        return self.rating * 5
    
    def __repr__(self):
        return f'<CardReview Card:{self.card_id} Rating:{self.rating_text} Time:{self.response_time}s>'


# ========== HELPER FUNCTIONS FOR RESEARCH ==========

def get_user_research_data(user_id):
    """Get comprehensive research data for a user"""
    
    # Get card statistics by algorithm
    fsrs_cards = Card.query.join(Deck).filter(
        Deck.user_id == user_id,
        Card.algorithm == 'FSRS'
    ).all()
    
    sm2_cards = Card.query.join(Deck).filter(
        Deck.user_id == user_id,
        Card.algorithm == 'SM2'
    ).all()
    
    # Get review statistics
    fsrs_reviews = CardReview.query.join(Card).join(Deck).filter(
        Deck.user_id == user_id,
        Card.algorithm == 'FSRS'
    ).all()
    
    sm2_reviews = CardReview.query.join(Card).join(Deck).filter(
        Deck.user_id == user_id,
        Card.algorithm == 'SM2'
    ).all()
    
    # Calculate retention rates
    fsrs_retention = 0
    if fsrs_reviews:
        correct = sum(1 for r in fsrs_reviews if r.rating >= 3)
        fsrs_retention = (correct / len(fsrs_reviews)) * 100
    
    sm2_retention = 0
    if sm2_reviews:
        correct = sum(1 for r in sm2_reviews if r.rating >= 3)
        sm2_retention = (correct / len(sm2_reviews)) * 100
    
    # Calculate average response times
    fsrs_avg_time = 0
    if fsrs_reviews:
        fsrs_avg_time = sum(r.response_time for r in fsrs_reviews) / len(fsrs_reviews)
    
    sm2_avg_time = 0
    if sm2_reviews:
        sm2_avg_time = sum(r.response_time for r in sm2_reviews) / len(sm2_reviews)
    
    return {
        'fsrs': {
            'total_cards': len(fsrs_cards),
            'mastered': sum(1 for c in fsrs_cards if c.is_mastered),
            'total_reviews': len(fsrs_reviews),
            'retention_rate': round(fsrs_retention, 1),
            'avg_response_time': round(fsrs_avg_time, 2)
        },
        'sm2': {
            'total_cards': len(sm2_cards),
            'mastered': sum(1 for c in sm2_cards if c.is_mastered),
            'total_reviews': len(sm2_reviews),
            'retention_rate': round(sm2_retention, 1),
            'avg_response_time': round(sm2_avg_time, 2)
        }
    }


def get_user_achievements(user):
    """Get list of achievements earned by user"""
    achievements = []
    
    if user.total_studied >= 10:
        achievements.append("📚 10 Cards Studied")
    if user.total_studied >= 50:
        achievements.append("📚 50 Cards Studied")
    if user.total_studied >= 100:
        achievements.append("🏆 100 Cards Studied - Bronze")
    if user.total_studied >= 250:
        achievements.append("🏆 250 Cards Studied - Silver")
    if user.total_studied >= 500:
        achievements.append("🏆 500 Cards Studied - GOLDEN!")
    
    if user.streak >= 7:
        achievements.append(f"🔥 {user.streak} Day Streak")
    if user.streak >= 30:
        achievements.append("🏆 30 Day Streak - Legendary!")
    
    if user.total_points >= 1000:
        achievements.append("⭐ 1000 Points Achieved")
    if user.total_points >= 5000:
        achievements.append("⭐ 5000 Points - Master!")
    
    return achievements