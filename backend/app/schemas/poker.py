from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.models.poker import ActionType, GameStage


class StartGameRequest(BaseModel):
    player_stacks: Dict[int, int]  # player_id -> stack_amount


class PlayerActionRequest(BaseModel):
    player_id: int
    action: ActionType
    amount: int = 0


class PlayerResponse(BaseModel):
    id: int
    name: str
    stack: int
    hole_cards: List[str] = []
    current_bet: int = 0
    is_folded: bool = False
    is_all_in: bool = False
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False


class ActionResponse(BaseModel):
    player_id: int
    action: ActionType
    amount: int = 0
    timestamp: datetime


class GameStateResponse(BaseModel):
    id: str
    players: List[PlayerResponse]
    community_cards: List[str]
    pot: int
    current_bet: int
    stage: GameStage
    current_player: int
    actions: List[ActionResponse]
    is_finished: bool
    winner_id: Optional[int] = None
    winner_reason: Optional[str] = None
    valid_actions: List[ActionType] = []
    detailed_log: List[str] = []


class HandHistoryResponse(BaseModel):
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
    created_at: str
    finished_at: Optional[str]


class ErrorResponse(BaseModel):
    error: str
    message: str
