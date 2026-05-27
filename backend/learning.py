# learning.py - Remove deck locking
from flask import render_template
from flask_login import login_required, current_user
from models import db, Deck, Card

def register_learning_routes(app):
    
    @app.route('/learning')
    @login_required
    def learning_material():
        # Get all decks (no locking - all accessible)
        decks = Deck.query.filter_by(user_id=current_user.id).order_by(Deck.id).all()
        
        total_cards = sum(len(deck.cards) for deck in decks)
        total_mastered = Card.query.join(Deck).filter(
            Deck.user_id == current_user.id,
            Card.is_mastered == True
        ).count()
        
        # Update stars based on points
        if current_user.total_points:
            new_stars = current_user.total_points // 100
            if new_stars != current_user.stars:
                current_user.stars = new_stars
                db.session.commit()
        
        return render_template('learning_material.html',
                             decks=decks,
                             total_cards=total_cards,
                             total_mastered=total_mastered,
                             user=current_user)