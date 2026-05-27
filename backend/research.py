# research.py
from flask import render_template, flash, jsonify
from flask_login import login_required, current_user
from models import db, Card, Deck, QuizResult, CardReview
from datetime import datetime

def register_research_routes(app):
    
    @app.route('/research')
    @login_required
    def research():
        # Get REAL card counts
        total_cards = Card.query.join(Deck).filter(Deck.user_id == current_user.id).count()
        fsrs_count = Card.query.join(Deck).filter(Deck.user_id == current_user.id, Card.algorithm == 'FSRS').count()
        sm2_count = Card.query.join(Deck).filter(Deck.user_id == current_user.id, Card.algorithm == 'SM2').count()
        
        # Get mastered counts
        fsrs_mastered = Card.query.join(Deck).filter(Deck.user_id == current_user.id, Card.algorithm == 'FSRS', Card.is_mastered == True).count()
        sm2_mastered = Card.query.join(Deck).filter(Deck.user_id == current_user.id, Card.algorithm == 'SM2', Card.is_mastered == True).count()
        total_mastered = fsrs_mastered + sm2_mastered
        
        # Get all reviews for the user
        fsrs_reviews = CardReview.query.join(Card).join(Deck).filter(
            Deck.user_id == current_user.id,
            Card.algorithm == 'FSRS'
        ).all()
        
        sm2_reviews = CardReview.query.join(Card).join(Deck).filter(
            Deck.user_id == current_user.id,
            Card.algorithm == 'SM2'
        ).all()
        
        # Calculate retention rate based on correct answers (rating >= 3)
        if fsrs_reviews:
            fsrs_correct = sum(1 for r in fsrs_reviews if r.rating >= 3)
            fsrs_retention = round((fsrs_correct / len(fsrs_reviews)) * 100, 1)
        else:
            fsrs_retention = 0
        
        if sm2_reviews:
            sm2_correct = sum(1 for r in sm2_reviews if r.rating >= 3)
            sm2_retention = round((sm2_correct / len(sm2_reviews)) * 100, 1)
        else:
            sm2_retention = 0
        
        # Get review stats from cards with actual reviews
        fsrs_cards = Card.query.join(Deck).filter(
            Deck.user_id == current_user.id, 
            Card.algorithm == 'FSRS', 
            Card.review_count > 0
        ).all()
        
        sm2_cards = Card.query.join(Deck).filter(
            Deck.user_id == current_user.id, 
            Card.algorithm == 'SM2', 
            Card.review_count > 0
        ).all()
        
        # Calculate FSRS stats
        if fsrs_cards:
            fsrs_avg_time = round(sum(c.avg_time for c in fsrs_cards) / len(fsrs_cards), 2)
            fsrs_reviews_avg = round(sum(c.review_count for c in fsrs_cards) / len(fsrs_cards), 1)
            fsrs_confidence = round((fsrs_retention / 100) * 5, 1) if fsrs_retention > 0 else 0
        else:
            fsrs_avg_time = 0
            fsrs_reviews_avg = 0
            fsrs_confidence = 0
        
        # Calculate SM-2 stats
        if sm2_cards:
            sm2_avg_time = round(sum(c.avg_time for c in sm2_cards) / len(sm2_cards), 2)
            sm2_reviews_avg = round(sum(c.review_count for c in sm2_cards) / len(sm2_cards), 1)
            sm2_confidence = round((sm2_retention / 100) * 5, 1) if sm2_retention > 0 else 0
        else:
            sm2_avg_time = 0
            sm2_reviews_avg = 0
            sm2_confidence = 0
        
        # Get total reviews count
        total_fsrs_reviews = len(fsrs_reviews)
        total_sm2_reviews = len(sm2_reviews)
        
        # Debug print
        print(f"\n📊 RESEARCH DATA:")
        print(f"   FSRS: {len(fsrs_cards)} cards, {total_fsrs_reviews} reviews, retention={fsrs_retention}%")
        print(f"   SM-2: {len(sm2_cards)} cards, {total_sm2_reviews} reviews, retention={sm2_retention}%")
        
        # Determine winners based on actual data
        has_fsrs_data = total_fsrs_reviews > 0
        has_sm2_data = total_sm2_reviews > 0
        
        if has_fsrs_data or has_sm2_data:
            # Retention winner (higher is better)
            if fsrs_retention > sm2_retention:
                retention_winner = "FSRS"
                retention_winner_color = "#27ae60"
            elif sm2_retention > fsrs_retention:
                retention_winner = "SM-2"
                retention_winner_color = "#27ae60"
            elif fsrs_retention == sm2_retention and fsrs_retention > 0:
                retention_winner = "Tie"
                retention_winner_color = "#f39c12"
            else:
                retention_winner = "No data yet"
                retention_winner_color = "#95a5a6"
            
            # Time winner (lower is better)
            if fsrs_avg_time < sm2_avg_time and sm2_avg_time > 0:
                time_winner = "FSRS (Faster)"
                time_winner_color = "#27ae60"
            elif sm2_avg_time < fsrs_avg_time and fsrs_avg_time > 0:
                time_winner = "SM-2 (Faster)"
                time_winner_color = "#27ae60"
            elif fsrs_avg_time == sm2_avg_time and fsrs_avg_time > 0:
                time_winner = "Tie"
                time_winner_color = "#f39c12"
            else:
                time_winner = "No data yet"
                time_winner_color = "#95a5a6"
            
            # Reviews winner (lower is better)
            if fsrs_reviews_avg < sm2_reviews_avg and sm2_reviews_avg > 0:
                reviews_winner = "FSRS"
                reviews_winner_color = "#27ae60"
            elif sm2_reviews_avg < fsrs_reviews_avg and fsrs_reviews_avg > 0:
                reviews_winner = "SM-2"
                reviews_winner_color = "#27ae60"
            elif fsrs_reviews_avg == sm2_reviews_avg and fsrs_reviews_avg > 0:
                reviews_winner = "Tie"
                reviews_winner_color = "#f39c12"
            else:
                reviews_winner = "No data yet"
                reviews_winner_color = "#95a5a6"
            
            # Confidence winner (higher is better)
            if fsrs_confidence > sm2_confidence:
                confidence_winner = "FSRS"
                confidence_winner_color = "#27ae60"
            elif sm2_confidence > fsrs_confidence:
                confidence_winner = "SM-2"
                confidence_winner_color = "#27ae60"
            elif fsrs_confidence == sm2_confidence and fsrs_confidence > 0:
                confidence_winner = "Tie"
                confidence_winner_color = "#f39c12"
            else:
                confidence_winner = "No data yet"
                confidence_winner_color = "#95a5a6"
            
            # Overall winner calculation
            fsrs_score = 0
            sm2_score = 0
            
            if fsrs_retention > sm2_retention:
                fsrs_score += 1
            elif sm2_retention > fsrs_retention:
                sm2_score += 1
            
            if fsrs_avg_time < sm2_avg_time and sm2_avg_time > 0:
                fsrs_score += 1
            elif sm2_avg_time < fsrs_avg_time and fsrs_avg_time > 0:
                sm2_score += 1
            
            if fsrs_reviews_avg < sm2_reviews_avg and sm2_reviews_avg > 0:
                fsrs_score += 1
            elif sm2_reviews_avg < fsrs_reviews_avg and fsrs_reviews_avg > 0:
                sm2_score += 1
            
            if fsrs_confidence > sm2_confidence:
                fsrs_score += 1
            elif sm2_confidence > fsrs_confidence:
                sm2_score += 1
            
            if fsrs_score > sm2_score:
                overall_winner = "FSRS"
                overall_message = "FSRS is performing better for you! 🎉 The AI-powered algorithm is optimizing your learning."
                overall_color = "#27ae60"
            elif sm2_score > fsrs_score:
                overall_winner = "SM-2"
                overall_message = "SM-2 is performing better for you! 🎉 The classic algorithm works well for your learning style."
                overall_color = "#27ae60"
            else:
                overall_winner = "Tie"
                overall_message = "Both algorithms are performing similarly. Keep studying to see which works best for you!"
                overall_color = "#f39c12"
        else:
            retention_winner = "No data yet"
            retention_winner_color = "#95a5a6"
            time_winner = "No data yet"
            time_winner_color = "#95a5a6"
            reviews_winner = "No data yet"
            reviews_winner_color = "#95a5a6"
            confidence_winner = "No data yet"
            confidence_winner_color = "#95a5a6"
            overall_winner = "No data yet"
            overall_message = "Start studying to see algorithm comparison!"
            overall_color = "#95a5a6"
        
        # Quiz stats
        quizzes = QuizResult.query.filter_by(user_id=current_user.id).all()
        total_quizzes = len(quizzes)
        avg_quiz_score = round(sum(q.percentage for q in quizzes) / total_quizzes, 1) if total_quizzes > 0 else 0
        best_quiz_score = max([q.percentage for q in quizzes]) if total_quizzes > 0 else 0
        
        # Recommendations based on data
        recommendations = []
        if fsrs_retention < 50 and total_fsrs_reviews > 0:
            recommendations.append("• Study FSRS cards more frequently to improve retention")
        if sm2_retention < 50 and total_sm2_reviews > 0:
            recommendations.append("• Review SM-2 cards regularly")
        if fsrs_avg_time > 5 and fsrs_avg_time > 0:
            recommendations.append("• Take more time to understand FSRS cards before answering")
        if sm2_avg_time > 5 and sm2_avg_time > 0:
            recommendations.append("• Take more time to understand SM-2 cards before answering")
        if total_fsrs_reviews == 0 and total_sm2_reviews == 0:
            recommendations.append("• Start studying to see algorithm comparison!")
        elif total_fsrs_reviews == 0:
            recommendations.append("• Study more FSRS cards to get accurate comparison")
        elif total_sm2_reviews == 0:
            recommendations.append("• Study more SM-2 cards to get accurate comparison")
        
        if not recommendations:
            recommendations.append("• Keep up the great work! Your learning is on track!")
            recommendations.append("• Try creating more challenging cards")
        
        # Achievements
        achievements = []
        if total_mastered >= 10:
            achievements.append("📚 10 Cards Mastered")
        if total_mastered >= 50:
            achievements.append("📚 50 Cards Mastered")
        if total_mastered >= 100:
            achievements.append("🏆 100 Cards Mastered - Bronze Cup!")
        if total_mastered >= 250:
            achievements.append("🏆 250 Cards Mastered - Silver Cup!")
        if total_mastered >= 500:
            achievements.append("🏆 500 Cards Mastered - GOLDEN CUP! 🎉")
        if current_user.streak >= 7:
            achievements.append(f"🔥 {current_user.streak} Day Streak!")
        if current_user.streak >= 30:
            achievements.append("🏆 30 Day Streak - Legendary!")
        if total_quizzes >= 10:
            achievements.append("📝 10 Quizzes Completed")
        
        has_data = current_user.total_studied > 0
        
        return render_template('research.html',
                              total_cards=total_cards,
                              total_mastered=total_mastered,
                              fsrs_count=fsrs_count,
                              sm2_count=sm2_count,
                              fsrs_mastered=fsrs_mastered,
                              sm2_mastered=sm2_mastered,
                              fsrs_retention=fsrs_retention,
                              sm2_retention=sm2_retention,
                              fsrs_avg_time=fsrs_avg_time,
                              sm2_avg_time=sm2_avg_time,
                              fsrs_reviews=fsrs_reviews_avg,
                              sm2_reviews=sm2_reviews_avg,
                              fsrs_confidence=fsrs_confidence,
                              sm2_confidence=sm2_confidence,
                              total_fsrs_reviews=total_fsrs_reviews,
                              total_sm2_reviews=total_sm2_reviews,
                              retention_winner=retention_winner,
                              retention_winner_color=retention_winner_color,
                              time_winner=time_winner,
                              time_winner_color=time_winner_color,
                              reviews_winner=reviews_winner,
                              reviews_winner_color=reviews_winner_color,
                              confidence_winner=confidence_winner,
                              confidence_winner_color=confidence_winner_color,
                              overall_winner=overall_winner,
                              overall_message=overall_message,
                              overall_color=overall_color,
                              avg_quiz_score=avg_quiz_score,
                              total_quizzes=total_quizzes,
                              best_quiz_score=best_quiz_score,
                              streak=current_user.streak or 0,
                              total_studied=current_user.total_studied or 0,
                              points=current_user.total_points or 0,
                              achievements=achievements,
                              recommendations=recommendations,
                              has_data=has_data)
    
    @app.route('/api/deck_progress/<int:deck_id>')
    @login_required
    def deck_progress(deck_id):
        """API endpoint to get real-time progress for a deck"""
        deck = Deck.query.get(deck_id)
        if not deck or deck.user_id != current_user.id:
            return jsonify({'error': 'Deck not found'}), 404
        
        # Get FSRS cards
        fsrs_cards = Card.query.filter_by(deck_id=deck.id, algorithm='FSRS').all()
        fsrs_total = len(fsrs_cards)
        fsrs_mastered = sum(1 for c in fsrs_cards if c.is_mastered)
        
        # Get SM-2 cards
        sm2_cards = Card.query.filter_by(deck_id=deck.id, algorithm='SM2').all()
        sm2_total = len(sm2_cards)
        sm2_mastered = sum(1 for c in sm2_cards if c.is_mastered)
        
        # Calculate retention from reviews
        fsrs_reviews = CardReview.query.join(Card).filter(
            Card.deck_id == deck.id,
            Card.algorithm == 'FSRS',
            CardReview.user_id == current_user.id
        ).all()
        
        sm2_reviews = CardReview.query.join(Card).filter(
            Card.deck_id == deck.id,
            Card.algorithm == 'SM2',
            CardReview.user_id == current_user.id
        ).all()
        
        fsrs_retention = 0
        if fsrs_reviews:
            correct = sum(1 for r in fsrs_reviews if r.rating >= 3)
            fsrs_retention = round((correct / len(fsrs_reviews)) * 100, 1)
        
        sm2_retention = 0
        if sm2_reviews:
            correct = sum(1 for r in sm2_reviews if r.rating >= 3)
            sm2_retention = round((correct / len(sm2_reviews)) * 100, 1)
        
        return jsonify({
            'fsrs': {
                'total': fsrs_total,
                'mastered': fsrs_mastered,
                'retention': fsrs_retention
            },
            'sm2': {
                'total': sm2_total,
                'mastered': sm2_mastered,
                'retention': sm2_retention
            }
        })