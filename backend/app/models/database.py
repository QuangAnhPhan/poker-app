from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


@dataclass
class HandHistory:
    id: str
    players_data: List[Dict[str, Any]]
    community_cards: List[str]
    actions: List[Dict[str, Any]]
    pot_size: int
    winner_id: Optional[int]
    stage: str
    dealer_position: int
    small_blind: int
    big_blind: int
    created_at: datetime
    finished_at: Optional[datetime] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "players_data": self.players_data,
            "community_cards": self.community_cards,
            "actions": self.actions,
            "pot_size": self.pot_size,
            "winner_id": self.winner_id,
            "stage": self.stage,
            "dealer_position": self.dealer_position,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None
        }
    
    @classmethod
    def from_db_row(cls, row: tuple):
        """Create HandHistory from database row"""
        return cls(
            id=row[0],
            players_data=row[1] if row[1] else [],  # JSONB already parsed
            community_cards=row[2] if row[2] else [],  # JSONB already parsed
            actions=row[3] if row[3] else [],  # JSONB already parsed
            pot_size=row[4],
            winner_id=row[5],
            stage=row[6],
            dealer_position=row[7],
            small_blind=row[8],
            big_blind=row[9],
            created_at=row[10],
            finished_at=row[11]
        )
