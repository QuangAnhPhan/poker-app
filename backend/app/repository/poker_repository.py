import psycopg2
import json
from typing import List, Optional
from app.models.database import HandHistory
from app.models.poker import PokerGame
from datetime import datetime
from app.db.connection import get_connection


class PokerRepository:
    def __init__(self):
        pass
    
    def save_hand_history(self, game: PokerGame) -> HandHistory:
        """Save completed hand to database using raw SQL"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data
            players_data = [{
                "id": p.id,
                "name": p.name,
                "initial_stack": p.stack + sum(a.amount for a in game.state.actions if a.player_id == p.id and a.action in ['bet', 'raise', 'call']),
                "final_stack": p.stack,
                "hole_cards": [str(card) for card in p.hole_cards],
                "is_dealer": p.is_dealer,
                "is_small_blind": p.is_small_blind,
                "is_big_blind": p.is_big_blind,
                "is_folded": p.is_folded,
                "is_all_in": p.is_all_in
            } for p in game.state.players]
            
            community_cards = [str(card) for card in game.state.community_cards]
            actions = [{
                "player_id": a.player_id,
                "action": a.action,
                "amount": a.amount,
                "timestamp": a.timestamp.isoformat()
            } for a in game.state.actions]
            
            finished_at = datetime.now() if game.state.is_finished else None
            
            # Insert using raw SQL
            insert_query = """
                INSERT INTO hand_history (
                    id, players_data, community_cards, actions, pot_size, 
                    winner_id, stage, dealer_position, small_blind, big_blind, 
                    created_at, finished_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                game.state.id,
                json.dumps(players_data),
                json.dumps(community_cards),
                json.dumps(actions),
                game.state.pot,
                game.state.winner_id,
                game.state.stage.value,
                game.state.dealer_position,
                game.state.small_blind,
                game.state.big_blind,
                game.state.created_at,
                finished_at
            ))
            
            conn.commit()
            
            # Create and return HandHistory object
            hand_history = HandHistory(
                id=game.state.id,
                players_data=players_data,
                community_cards=community_cards,
                actions=actions,
                pot_size=game.state.pot,
                winner_id=game.state.winner_id,
                stage=game.state.stage.value,
                dealer_position=game.state.dealer_position,
                small_blind=game.state.small_blind,
                big_blind=game.state.big_blind,
                created_at=game.state.created_at,
                finished_at=finished_at
            )
            
            return hand_history
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_hand_history(self, hand_id: str) -> Optional[HandHistory]:
        """Get specific hand history by ID using raw SQL"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            select_query = """
                SELECT id, players_data, community_cards, actions, pot_size, 
                       winner_id, stage, dealer_position, small_blind, big_blind, 
                       created_at, finished_at
                FROM hand_history 
                WHERE id = %s
            """
            
            cursor.execute(select_query, (hand_id,))
            row = cursor.fetchone()
            
            if row:
                return HandHistory.from_db_row(row)
            return None
            
        finally:
            cursor.close()
            conn.close()
    
    def get_all_hand_histories(self, limit: int = 50) -> List[HandHistory]:
        """Get all hand histories, most recent first using raw SQL"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            select_query = """
                SELECT id, players_data, community_cards, actions, pot_size, 
                       winner_id, stage, dealer_position, small_blind, big_blind, 
                       created_at, finished_at
                FROM hand_history 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            
            cursor.execute(select_query, (limit,))
            rows = cursor.fetchall()
            
            return [HandHistory.from_db_row(row) for row in rows]
            
        finally:
            cursor.close()
            conn.close()
    
    def delete_hand_history(self, hand_id: str) -> bool:
        """Delete a hand history using raw SQL"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            delete_query = "DELETE FROM hand_history WHERE id = %s"
            cursor.execute(delete_query, (hand_id,))
            
            deleted_rows = cursor.rowcount
            conn.commit()
            
            return deleted_rows > 0
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
