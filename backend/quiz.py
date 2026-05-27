# quiz.py - RESEARCH VERSION (No deck locking)
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from datetime import datetime
import random
from models import db, Deck, Card, QuizResult, CardReview

def register_quiz_routes(app):
    
    @app.route('/quiz')
    @login_required
    def quiz_select():
        # Get quiz statistics for the user
        quizzes = QuizResult.query.filter_by(user_id=current_user.id).all()
        quizzes_taken = len(quizzes)
        avg_score = round(sum(q.percentage for q in quizzes) / quizzes_taken, 1) if quizzes_taken > 0 else 0
        best_score = max([q.percentage for q in quizzes]) if quizzes_taken > 0 else 0
        
        # Get all decks for the user
        user_decks = Deck.query.filter_by(user_id=current_user.id).order_by(Deck.id).all()
        
        return render_template('quiz_select.html', 
                              quizzes_taken=quizzes_taken,
                              avg_score=avg_score,
                              best_score=best_score,
                              user_decks=user_decks)

    @app.route('/quiz/start/deck/<int:deck_id>')
    @login_required
    def quiz_start_deck(deck_id):
        # Get the deck by its ID
        deck = Deck.query.get(deck_id)
        
        # Check if deck exists and belongs to current user
        if not deck:
            flash('Deck not found!', 'error')
            return redirect(url_for('quiz_select'))
        
        if deck.user_id != current_user.id:
            flash('This deck does not belong to you!', 'error')
            return redirect(url_for('quiz_select'))
        
        # Get all cards from this deck
        cards = Card.query.filter_by(deck_id=deck.id).all()
        
        if len(cards) == 0:
            flash(f'No cards in deck "{deck.name}"!', 'error')
            return redirect(url_for('quiz_select'))
        
        # RESEARCH MODE: No deck locking - use all cards
        selected = cards[:25]
        num = len(selected)
        
        # Store deck_id in session for results
        session['quiz_deck_id'] = deck_id
        
        quiz_cards = []
        for card in selected:
            # Get wrong options from other cards in the same deck
            other_cards = [c for c in cards if c.id != card.id]
            wrong_options = random.sample(other_cards, min(3, len(other_cards)))
            wrong_answers = [c.answer for c in wrong_options]
            while len(wrong_answers) < 3:
                wrong_answers.append("None of the above")
            options = wrong_answers + [card.answer]
            random.shuffle(options)
            quiz_cards.append({
                'id': card.id,
                'question': card.question,
                'correct_answer': card.answer,
                'options': options,
                'deck_name': deck.name,
                'algorithm': card.algorithm
            })
        
        session['quiz_cards'] = quiz_cards
        session['quiz_idx'] = 0
        session['quiz_answers'] = []
        session['quiz_start'] = datetime.now().isoformat()
        session['quiz_limit'] = {25: 720, 50: 1500, 100: 2700}.get(num, 600)
        session['quiz_deck_name'] = deck.name
        
        return redirect(url_for('quiz_take'))

    @app.route('/quiz/start/all/<int:num>')
    @login_required
    def quiz_start_all(num):
        cards = Card.query.join(Deck).filter(Deck.user_id == current_user.id).all()
        
        if len(cards) < num:
            flash(f'Not enough cards! You have only {len(cards)} cards.', 'error')
            return redirect(url_for('quiz_select'))
        
        selected = random.sample(cards, num)
        quiz_cards = []
        
        for card in selected:
            other_cards = [c for c in cards if c.id != card.id]
            wrong_options = random.sample(other_cards, min(3, len(other_cards)))
            wrong_answers = [c.answer for c in wrong_options]
            while len(wrong_answers) < 3:
                wrong_answers.append("None of the above")
            options = wrong_answers + [card.answer]
            random.shuffle(options)
            quiz_cards.append({
                'id': card.id,
                'question': card.question,
                'correct_answer': card.answer,
                'options': options,
                'algorithm': card.algorithm
            })
        
        session['quiz_cards'] = quiz_cards
        session['quiz_idx'] = 0
        session['quiz_answers'] = []
        session['quiz_start'] = datetime.now().isoformat()
        session['quiz_limit'] = {10: 300, 25: 720, 50: 1500}.get(num, 600)
        session['quiz_deck_name'] = f"{num} Question Quiz"
        
        # For general quiz, use the first deck_id
        first_deck = Deck.query.filter_by(user_id=current_user.id).first()
        if first_deck:
            session['quiz_deck_id'] = first_deck.id
        else:
            # If no decks exist, create a default one
            default_deck = Deck(name="General Quiz", user_id=current_user.id)
            db.session.add(default_deck)
            db.session.commit()
            session['quiz_deck_id'] = default_deck.id
        
        return redirect(url_for('quiz_take'))

    @app.route('/quiz/take')
    @login_required
    def quiz_take():
        cards = session.get('quiz_cards', [])
        idx = session.get('quiz_idx', 0)
        if idx >= len(cards):
            return redirect(url_for('quiz_results'))
        start = datetime.fromisoformat(session.get('quiz_start', datetime.now().isoformat()))
        elapsed = int((datetime.now() - start).total_seconds())
        left = max(0, session.get('quiz_limit', 600) - elapsed)
        if left <= 0:
            return redirect(url_for('quiz_results'))
        card = cards[idx]
        deck_name = session.get('quiz_deck_name', 'General Quiz')
        return render_template('quiz_take.html', card=card, options=card['options'], 
                              current=idx+1, total=len(cards), time_left=left, deck_name=deck_name)

    @app.route('/quiz/answer', methods=['POST'])
    @login_required
    def quiz_answer():
        user_ans = request.form.get('answer', '').strip()
        cards = session.get('quiz_cards', [])
        idx = session.get('quiz_idx', 0)
        answers = session.get('quiz_answers', [])
        if idx < len(cards):
            card = cards[idx]
            correct = user_ans.lower() == card['correct_answer'].lower()
            answers.append({
                'question': card['question'], 
                'user': user_ans, 
                'correct_answer': card['correct_answer'], 
                'correct': correct,
                'options': card['options'],
                'deck_name': card.get('deck_name', 'General'),
                'algorithm': card.get('algorithm', 'Unknown')
            })
            session['quiz_answers'] = answers
            session['quiz_idx'] = idx + 1
        return redirect(url_for('quiz_take'))

    @app.route('/quiz/results')
    @login_required
    def quiz_results():
        answers = session.get('quiz_answers', [])
        total = len(answers)
        correct = sum(1 for a in answers if a['correct'])
        percent = (correct / total * 100) if total > 0 else 0
        start = datetime.fromisoformat(session.get('quiz_start', datetime.now().isoformat()))
        taken = int((datetime.now() - start).total_seconds())
        minutes = taken // 60
        seconds = taken % 60
        
        # Calculate algorithm performance in quiz
        fsrs_questions = [a for a in answers if a.get('algorithm') == 'FSRS']
        sm2_questions = [a for a in answers if a.get('algorithm') == 'SM2']
        
        fsrs_correct = sum(1 for a in fsrs_questions if a['correct'])
        sm2_correct = sum(1 for a in sm2_questions if a['correct'])
        
        fsrs_percent = round((fsrs_correct / len(fsrs_questions) * 100), 1) if fsrs_questions else 0
        sm2_percent = round((sm2_correct / len(sm2_questions) * 100), 1) if sm2_questions else 0
        
        if percent >= 90:
            msg, emoji, color = "🏆 EXCELLENT!", "🎉", "#27ae60"
        elif percent >= 70:
            msg, emoji, color = "🎯 GOOD JOB!", "👍", "#3498db"
        elif percent >= 50:
            msg, emoji, color = "📚 KEEP GOING!", "💪", "#f39c12"
        else:
            msg, emoji, color = "🌱 NEXT TIME!", "🌟", "#e74c3c"
        
        # Save quiz result
        deck_id = session.get('quiz_deck_id', 1)
        
        result = QuizResult(
            user_id=current_user.id,
            deck_id=deck_id,
            score=correct,
            total_questions=total,
            percentage=percent,
            time_taken=taken,
            created_at=datetime.now()
        )
        db.session.add(result)
        db.session.commit()
        
        # Award points
        points_earned = correct * 10
        current_user.total_points = (current_user.total_points or 0) + points_earned
        db.session.commit()
        
        # Clear session
        session.pop('quiz_cards', None)
        session.pop('quiz_idx', None)
        session.pop('quiz_answers', None)
        session.pop('quiz_start', None)
        session.pop('quiz_deck_name', None)
        session.pop('quiz_deck_id', None)
        
        return render_template('quiz_result.html', score=correct, total=total,
                              percentage=round(percent,1), time_min=minutes, time_sec=seconds,
                              message=msg, emoji=emoji, color=color, answers=answers,
                              points_earned=points_earned,
                              fsrs_percent=fsrs_percent, sm2_percent=sm2_percent,
                              fsrs_count=len(fsrs_questions), sm2_count=len(sm2_questions))