# decks.py
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Deck, Card

def register_decks_routes(app):
    
    # ========== DASHBOARD ROUTE - COMMENTED OUT (using app.py version) ==========
    # @app.route('/dashboard')
    # def dashboard():
    #     decks = Deck.query.filter_by(user_id=current_user.id).all()
    #     total_cards = sum(len(deck.cards) for deck in decks)
    #     mastered_cards = Card.query.filter_by(is_mastered=True).join(Deck).filter(Deck.user_id == current_user.id).count()
    #     return render_template('dashboard.html', decks=decks, total_cards=total_cards, 
    #                          mastered_cards=mastered_cards, user=current_user)
    
    @app.route('/create_deck', methods=['POST'])
    @login_required
    def create_deck():
        name = request.form.get('name')
        if name:
            deck = Deck(name=name, user_id=current_user.id)
            db.session.add(deck)
            db.session.commit()
            flash(f'✅ Deck "{name}" created!', 'success')
        return redirect(url_for('dashboard'))
    
    @app.route('/delete_deck/<int:deck_id>')
    @login_required
    def delete_deck(deck_id):
        deck = Deck.query.get(deck_id)
        if deck and deck.user_id == current_user.id:
            db.session.delete(deck)
            db.session.commit()
            flash('🗑️ Deck deleted!', 'info')
        return redirect(url_for('dashboard'))
    
    @app.route('/deck/<int:deck_id>')
    @login_required
    def view_deck(deck_id):
        deck = Deck.query.get(deck_id)
        if not deck or deck.user_id != current_user.id:
            flash('Deck not found!', 'error')
            return redirect(url_for('dashboard'))
        return render_template('view_deck.html', deck=deck)
    
    @app.route('/add_card/<int:deck_id>', methods=['POST'])
    @login_required
    def add_card(deck_id):
        deck = Deck.query.get(deck_id)
        if deck and deck.user_id == current_user.id:
            question = request.form.get('question')
            answer = request.form.get('answer')
            if question and answer:
                card = Card(
                    question=question, 
                    answer=answer, 
                    deck_id=deck.id,
                    algorithm='SM2',  # Default algorithm
                    stability=2.0,
                    difficulty=5.0,
                    e_factor=2.5,
                    interval=1
                )
                db.session.add(card)
                db.session.commit()
                flash('✅ Card added!', 'success')
            else:
                flash('❌ Question and answer are required!', 'error')
        else:
            flash('❌ Deck not found!', 'error')
        return redirect(url_for('view_deck', deck_id=deck_id))
    
    @app.route('/delete_card/<int:card_id>')
    @login_required
    def delete_card(card_id):
        card = Card.query.get(card_id)
        if card and card.deck.user_id == current_user.id:
            deck_id = card.deck_id
            db.session.delete(card)
            db.session.commit()
            flash('🗑️ Card deleted!', 'info')
            return redirect(url_for('view_deck', deck_id=deck_id))
        flash('❌ Card not found!', 'error')
        return redirect(url_for('dashboard'))
    
    @app.route('/mark_mastered/<int:card_id>', methods=['GET', 'POST'])
    @login_required
    def mark_mastered(card_id):
        """Mark a card as mastered - supports both AJAX and regular requests"""
        card = Card.query.get(card_id)
        
        if not card:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Card not found'}), 404
            flash('❌ Card not found!', 'error')
            return redirect(url_for('dashboard'))
        
        if card.deck.user_id != current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Permission denied'}), 403
            flash('❌ You do not have permission!', 'error')
            return redirect(url_for('dashboard'))
        
        # Mark as mastered
        card.is_mastered = True
        db.session.commit()
        
        # For AJAX requests (from view_deck.html)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Card mastered successfully!',
                'card_id': card_id,
                'mastered_count': Card.query.filter_by(deck_id=card.deck_id, is_mastered=True).count(),
                'total_cards': Card.query.filter_by(deck_id=card.deck_id).count()
            }), 200
        
        # For regular form submissions
        flash('✅ Card marked as mastered!', 'success')
        return redirect(request.referrer or url_for('view_deck', deck_id=card.deck_id))
    
    @app.route('/unmark_mastered/<int:card_id>', methods=['GET', 'POST'])
    @login_required
    def unmark_mastered(card_id):
        """Unmark a card as mastered - supports both AJAX and regular requests"""
        card = Card.query.get(card_id)
        
        if not card:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Card not found'}), 404
            flash('❌ Card not found!', 'error')
            return redirect(url_for('dashboard'))
        
        if card.deck.user_id != current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Permission denied'}), 403
            flash('❌ You do not have permission!', 'error')
            return redirect(url_for('dashboard'))
        
        # Unmark as mastered
        card.is_mastered = False
        db.session.commit()
        
        # For AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Card unmarked successfully!',
                'card_id': card_id,
                'mastered_count': Card.query.filter_by(deck_id=card.deck_id, is_mastered=True).count(),
                'total_cards': Card.query.filter_by(deck_id=card.deck_id).count()
            }), 200
        
        # For regular form submissions
        flash('🔄 Card unmarked as mastered!', 'info')
        return redirect(request.referrer or url_for('view_deck', deck_id=card.deck_id))
    
    @app.route('/mark_multiple_mastered', methods=['POST'])
    @login_required
    def mark_multiple_mastered():
        """Mark multiple cards as mastered at once (for bulk operations)"""
        data = request.get_json()
        card_ids = data.get('card_ids', [])
        
        if not card_ids:
            return jsonify({'error': 'No cards selected'}), 400
        
        mastered_count = 0
        for card_id in card_ids:
            card = Card.query.get(card_id)
            if card and card.deck.user_id == current_user.id and not card.is_mastered:
                card.is_mastered = True
                mastered_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{mastered_count} cards marked as mastered!',
            'mastered_count': mastered_count
        }), 200
    
    @app.route('/reset_deck_mastered/<int:deck_id>')
    @login_required
    def reset_deck_mastered(deck_id):
        """Reset all cards in a deck (unmaster them)"""
        deck = Deck.query.get(deck_id)
        if deck and deck.user_id == current_user.id:
            for card in deck.cards:
                card.is_mastered = False
                card.review_count = 0
                card.avg_time = 0
            db.session.commit()
            flash('🔄 All cards in this deck have been reset!', 'success')
        else:
            flash('❌ Deck not found!', 'error')
        return redirect(url_for('view_deck', deck_id=deck_id))
    
    @app.route('/card/<int:card_id>/details')
    @login_required
    def card_details(card_id):
        """Get card details for AJAX requests"""
        card = Card.query.get(card_id)
        if not card or card.deck.user_id != current_user.id:
            return jsonify({'error': 'Card not found'}), 404
        
        return jsonify({
            'id': card.id,
            'question': card.question,
            'answer': card.answer,
            'algorithm': card.algorithm,
            'review_count': card.review_count,
            'avg_time': card.avg_time,
            'is_mastered': card.is_mastered,
            'stability': card.stability,
            'difficulty': card.difficulty,
            'e_factor': card.e_factor,
            'interval': card.interval
        }), 200