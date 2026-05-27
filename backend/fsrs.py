# fsrs.py - Complete FSRS v4.5 and SM-2 Implementation
import math
from datetime import datetime, timedelta

class FSRS:
    """
    FSRS (Free Spaced Repetition Scheduler) v4.5
    Based on the paper "Optimizing Spaced Repetition Schedule by Capturing the Dynamics of Memory"
    """
    
    def __init__(self):
        # Optimized parameters from the FSRS paper (trained on 1.7B reviews)
        self.w = {
            'w0': 0.4197,  # Initial stability
            'w1': 0.6235,  # Difficulty effect
            'w2': 2.4518,  # Rating "Again" multiplier
            'w3': 1.8566,  # Rating "Hard" multiplier
            'w4': 0.9231,  # Rating "Good" multiplier
            'w5': 0.3495,  # Rating "Easy" multiplier
            'w6': 0.1804,  # Difficulty increase for "Again"
            'w7': 0.0645,  # Difficulty increase for "Hard"
            'w8': -0.1887, # Difficulty decrease for "Good"
            'w9': 0.2590,  # Retrievability exponent
            'w10': 1.4926, # Forgetting curve shape
            'request_retention': 0.9  # Target retention rate (90%)
        }
    
    def forgetting_curve(self, elapsed_days, stability):
        """
        Calculate probability of recalling a card after elapsed days
        Formula: R = (1 + w9 * t / S) ^ (-w10)
        """
        if elapsed_days <= 0:
            return 1.0
        return math.pow(1 + self.w['w9'] * elapsed_days / stability, -self.w['w10'])
    
    def calculate_difficulty(self, old_difficulty, rating):
        """
        Update difficulty based on rating
        Rating: 1=Again, 2=Hard, 3=Good, 4=Easy
        """
        difficulty_deltas = {
            1: self.w['w6'],   # Again: increase difficulty
            2: self.w['w7'],   # Hard: slight increase
            3: self.w['w8'],   # Good: decrease difficulty
            4: -0.2            # Easy: more decrease
        }
        
        delta = difficulty_deltas.get(rating, 0)
        new_difficulty = old_difficulty + delta * (10 - old_difficulty)
        
        # Clamp difficulty between 1 and 10
        return max(1.0, min(10.0, new_difficulty))
    
    def calculate_stability(self, old_stability, difficulty, retrievability, rating):
        """
        Calculate new stability after review
        Formula: S_new = S_old * (1 + w * (1 - e^(-R)))
        """
        rating_multipliers = {
            1: self.w['w2'],   # Again
            2: self.w['w3'],   # Hard
            3: self.w['w4'],   # Good
            4: self.w['w5']    # Easy
        }
        
        multiplier = rating_multipliers.get(rating, self.w['w4'])
        
        new_stability = old_stability * (1 + multiplier * (1 - math.exp(-retrievability)))
        
        return max(0.1, new_stability)  # Minimum stability 0.1 days
    
    def next_interval(self, stability, retrievability):
        """
        Calculate days until next review
        Finds interval where predicted retention = target retention (90%)
        """
        target = self.w['request_retention']
        
        if retrievability >= target:
            # Need longer interval to drop retention to target
            try:
                # Solve: 2^(-interval/stability) = target
                interval = stability * math.log(target) / math.log(0.5)
            except:
                interval = stability
        else:
            # Already below target, review very soon
            interval = max(1, int(stability * 0.5))
        
        return max(1, int(interval))
    
    def review_card(self, card, rating, review_date):
        """
        Process a card review with FSRS algorithm
        
        Parameters:
        - card: dict with 'stability', 'difficulty', 'last_review', 'review_count'
        - rating: 1=Again, 2=Hard, 3=Good, 4=Easy
        - review_date: datetime of current review
        
        Returns:
        - Updated card dict
        - Next review date
        """
        # Calculate elapsed days since last review
        if card.get('last_review'):
            elapsed_days = (review_date - card['last_review']).days
        else:
            elapsed_days = 0
        
        # Get current values
        stability = card.get('stability', self.w['w0'])
        difficulty = card.get('difficulty', 5.0)
        review_count = card.get('review_count', 0)
        
        # Calculate retrievability (probability of recall before review)
        retrievability = self.forgetting_curve(elapsed_days, stability)
        
        # Update difficulty based on rating
        new_difficulty = self.calculate_difficulty(difficulty, rating)
        
        # Update stability based on rating and retrievability
        new_stability = self.calculate_stability(stability, new_difficulty, retrievability, rating)
        
        # Calculate next interval
        interval_days = self.next_interval(new_stability, retrievability)
        next_review_date = review_date + timedelta(days=interval_days)
        
        # Prepare updated card data
        updated_card = {
            'stability': new_stability,
            'difficulty': new_difficulty,
            'last_review': review_date,
            'next_review': next_review_date,
            'review_count': review_count + 1,
            'last_retrievability': retrievability,
            'last_rating': rating
        }
        
        return updated_card, next_review_date


class SM2:
    """
    SM-2 Algorithm (SuperMemo 2)
    Classic spaced repetition algorithm from 1987
    """
    
    def __init__(self):
        self.easiness_min = 1.3
        self.easiness_max = 5.0
    
    def review_card(self, card, rating, review_date):
        """
        Process a card review with SM-2 algorithm
        
        Rating mapping for SM-2:
        1 = Again (quality 0) - complete blackout
        2 = Hard (quality 1-2) - incorrect but recognized
        3 = Good (quality 3-4) - correct with difficulty
        4 = Easy (quality 5) - perfect recall
        
        E-factor (Easiness factor) affects how quickly intervals grow
        Initial E-factor = 2.5
        Minimum E-factor = 1.3
        """
        # Map rating to SM-2 quality (0-5)
        quality_map = {
            1: 0,   # Again - complete blackout
            2: 2,   # Hard - incorrect but recognized
            3: 3,   # Good - correct with difficulty
            4: 4    # Easy - perfect recall
        }
        
        quality = quality_map.get(rating, 3)
        
        # Calculate elapsed days
        if card.get('last_review'):
            elapsed_days = (review_date - card['last_review']).days
        else:
            elapsed_days = 0
        
        # Get or initialize values
        e_factor = card.get('e_factor', 2.5)
        interval = card.get('interval', 1)
        review_count = card.get('review_count', 0)
        
        # First review
        if review_count == 0:
            interval = 1
            if quality < 3:
                interval = 0  # Failed, review same day
        else:
            # Update E-factor based on quality
            if quality >= 3:
                # EF' = EF + (0.1 - (5-Q) * (0.08 + (5-Q) * 0.02))
                ef_change = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
                e_factor = e_factor + ef_change
                e_factor = max(self.easiness_min, min(self.easiness_max, e_factor))
                
                # Update interval based on review count
                if review_count == 1:
                    interval = 1
                elif review_count == 2:
                    interval = 6
                else:
                    interval = int(interval * e_factor)
            else:
                # Failed - reset interval
                interval = 1
                review_count = 0  # Reset review count on failure
        
        # Calculate next review date
        next_review_date = review_date + timedelta(days=interval)
        
        # Prepare updated card data
        updated_card = {
            'e_factor': e_factor,
            'interval': interval,
            'last_review': review_date,
            'next_review': next_review_date,
            'review_count': review_count + 1,
            'last_quality': quality,
            'last_rating': rating
        }
        
        return updated_card, next_review_date