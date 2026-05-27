# study.py - RESEARCH VERSION (No deck locking, free access to all decks)
from flask import render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from models import db, Deck, Card, CardReview
from fsrs import FSRS, SM2

def register_study_routes(app):
    
    @app.route('/study/<int:deck_id>')
    @login_required
    def study_select(deck_id):
        deck = Deck.query.get(deck_id)
        if not deck or deck.user_id != current_user.id:
            return redirect(url_for('dashboard'))
        
        # RESEARCH MODE: No deck locking - free access to all decks
        cards = Card.query.filter_by(deck_id=deck.id).all()
        fsrs = sum(1 for c in cards if c.algorithm == 'FSRS')
        sm2 = sum(1 for c in cards if c.algorithm == 'SM2')
        return render_template('study_select.html', deck=deck, cards=cards, fsrs=fsrs, sm2=sm2)

    @app.route('/study/start/<int:deck_id>/<algo>')
    @login_required
    def study_start(deck_id, algo):
        deck = Deck.query.get(deck_id)
        if not deck or deck.user_id != current_user.id:
            return redirect(url_for('dashboard'))
        cards = Card.query.filter_by(deck_id=deck.id).all()
        if algo != 'all':
            cards = [c for c in cards if c.algorithm == algo]
        if not cards:
            flash('No cards!', 'error')
            return redirect(url_for('study_select', deck_id=deck_id))
        session['study_cards'] = [c.id for c in cards]
        session['study_idx'] = 0
        session['study_correct'] = 0
        session['study_points_earned'] = 0
        session['study_start_time'] = datetime.now().isoformat()
        return redirect(url_for('study_card'))

    @app.route('/study/card')
    @login_required
    def study_card():
        cards = session.get('study_cards', [])
        idx = session.get('study_idx', 0)
        total = len(cards)
        
        if idx >= total:
            correct = session.get('study_correct', 0)
            points_earned = session.get('study_points_earned', 0)
            session.pop('study_cards', None)
            session.pop('study_idx', None)
            session.pop('study_correct', None)
            session.pop('study_points_earned', None)
            session.pop('study_start_time', None)
            return render_template('study_done.html', total=total, correct=correct,
                                  acc=round(correct/total*100,1) if total>0 else 0,
                                  points_earned=points_earned)
        
        card = Card.query.get(cards[idx])
        return render_template('study_card.html', card=card, idx=idx, total=total)

    @app.route('/study/next')
    @login_required
    def study_next():
        session['study_idx'] = session.get('study_idx', 0) + 1
        return redirect(url_for('study_card'))

    @app.route('/rate/<int:card_id>/<int:rating>/<float:rt>')
    @login_required
    def rate(card_id, rating, rt):
        print("="*50)
        print(f"🔵 RATE FUNCTION CALLED")
        print(f"   Card ID: {card_id}")
        print(f"   Rating: {rating}")
        print(f"   Response Time: {rt}")
        print(f"   User: {current_user.username}")
        print(f"   Current Points BEFORE: {current_user.total_points}")
        print("="*50)
        
        # Get the card
        card = Card.query.get(card_id)
        if not card:
            print(f"❌ Card {card_id} not found!")
            return 'Card not found', 404
        
        # Verify ownership
        deck = Deck.query.get(card.deck_id)
        if not deck or deck.user_id != current_user.id:
            print(f"❌ Permission denied!")
            return 'Permission denied', 403
        
        print(f"✅ Card: {card.question[:50]}...")
        print(f"   Algorithm: {card.algorithm}")
        print(f"   Current review_count: {card.review_count}")
        print(f"   Current avg_time: {card.avg_time}")
        
        # Prepare card data for algorithm (using getattr for safety)
        card_data = {
            'stability': getattr(card, 'stability', 2.0),
            'difficulty': getattr(card, 'difficulty', 5.0),
            'e_factor': getattr(card, 'e_factor', 2.5),
            'interval': getattr(card, 'interval', 1),
            'last_review': card.last_review,
            'review_count': card.review_count or 0
        }
        
        # Apply the appropriate algorithm
        if card.algorithm == 'FSRS':
            print("   🧠 Using FSRS algorithm")
            scheduler = FSRS()
            updated_card, next_review = scheduler.review_card(card_data, rating, datetime.now())
            
            # Update FSRS fields
            card.stability = updated_card['stability']
            card.difficulty = updated_card['difficulty']
            card.last_review = updated_card['last_review']
            card.next_review = updated_card['next_review']
            card.review_count = updated_card['review_count']
            
            print(f"   FSRS - New stability: {card.stability:.2f}, difficulty: {card.difficulty:.2f}")
            
        else:  # SM2
            print("   📊 Using SM-2 algorithm")
            scheduler = SM2()
            updated_card, next_review = scheduler.review_card(card_data, rating, datetime.now())
            
            # Update SM-2 fields
            card.e_factor = updated_card['e_factor']
            card.interval = updated_card['interval']
            card.last_review = updated_card['last_review']
            card.next_review = updated_card['next_review']
            card.review_count = updated_card['review_count']
            
            print(f"   SM-2 - New E-factor: {card.e_factor:.2f}, interval: {card.interval}")
        
        # Update average response time
        if card.avg_time == 0:
            card.avg_time = rt
        else:
            card.avg_time = (card.avg_time + rt) / 2
        
        print(f"   Updated avg_time: {card.avg_time:.2f}s")
        
        # Track correct answers
        if rating >= 3:
            session['study_correct'] = session.get('study_correct', 0) + 1
            print(f"   ✅ Correct answer! Total correct in session: {session['study_correct']}")
            
            # Master after 3 good ratings
            if card.review_count >= 3:
                card.is_mastered = True
                print(f"   🏆 Card is now MASTERED!")
        
        # ========== UPDATE USER STATS ==========
        old_studied = current_user.total_studied
        current_user.total_studied = (current_user.total_studied or 0) + 1
        print(f"   User total_studied: {old_studied} → {current_user.total_studied}")
        
        # ========== UPDATE POINTS ==========
        points = rating * 5
        old_points = current_user.total_points or 0
        current_user.total_points = old_points + points
        session['study_points_earned'] = session.get('study_points_earned', 0) + points
        
        print(f"   💰 Points earned this card: +{points}")
        print(f"   💰 Session points total: {session['study_points_earned']}")
        print(f"   💰 User total_points: {old_points} → {current_user.total_points}")
        
        # ========== STREAK CALCULATION ==========
        today = date.today()
        last_study = None
        
        if current_user.last_study_date:
            try:
                if isinstance(current_user.last_study_date, str):
                    last_study = datetime.fromisoformat(current_user.last_study_date).date()
                else:
                    last_study = current_user.last_study_date
            except Exception as e:
                print(f"   ⚠️ Error parsing last_study_date: {e}")
                last_study = None
        
        old_streak = current_user.streak or 0
        
        if last_study == today:
            print(f"   📅 Already studied today. Streak remains: {old_streak}")
        elif last_study == today - timedelta(days=1):
            current_user.streak = old_streak + 1
            print(f"   🔥 Streak increased! {old_streak} → {current_user.streak}")
        elif last_study is None:
            current_user.streak = 1
            print(f"   🎉 First study session! Streak started: 1")
        else:
            days_missed = (today - last_study).days
            current_user.streak = 1
            print(f"   ⚠️ Streak reset! Missed {days_missed} day(s). New streak: 1")
        
        current_user.last_study_date = today.isoformat()
        print(f"   📅 Last study date: {current_user.last_study_date}")
        
        # Update stars (every 100 points = 1 star)
        new_stars = current_user.total_points // 100
        if new_stars > (current_user.stars or 0):
            old_stars = current_user.stars or 0
            current_user.stars = new_stars
            print(f"   ⭐ Stars increased! {old_stars} → {current_user.stars}")
        
        # ========== SAVE REVIEW FOR RESEARCH ==========
        review = CardReview(
            card_id=card.id,
            user_id=current_user.id,
            rating=rating,
            response_time=rt,
            created_at=datetime.now()
        )
        db.session.add(review)
        print(f"   📝 Review saved (Rating: {rating})")
        
        # ========== SAVE TO DATABASE ==========
        try:
            db.session.commit()
            print("✅ Database COMMIT successful!")
            print(f"💰 FINAL POINTS: {current_user.total_points}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error: {e}")
            return 'Database error', 500
        
        print("="*50)
        return 'OK'