from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.models.poker import PokerGame, ActionType
from app.schemas.poker import (
    StartGameRequest, PlayerActionRequest, GameStateResponse, 
    HandHistoryResponse, ErrorResponse
)
from app.repository.poker_repository import PokerRepository

router = APIRouter(prefix="/api/poker", tags=["poker"])

# In-memory game storage (in production, use Redis or similar)
active_games: Dict[str, PokerGame] = {}


@router.post("/start", response_model=GameStateResponse)
async def start_game(request: StartGameRequest):
    """Start a new poker game with specified player stacks"""
    try:
        print(f"\n=== STARTING NEW GAME ===")
        print(f"Player stacks: {request.player_stacks}")
        
        # Validate player stacks
        if len(request.player_stacks) != 6:
            raise HTTPException(status_code=400, detail="Game requires exactly 6 players")
        
        for player_id, stack in request.player_stacks.items():
            if stack <= 0:
                raise HTTPException(status_code=400, detail=f"Player {player_id} must have positive stack")
        
        # Create new game (PokerKit integration handles card dealing and logging automatically)
        game = PokerGame(request.player_stacks)
        game_id = game.game_id
        
        # Store game in memory
        active_games[game_id] = game
        
        # Get valid actions for current player
        current_actor = getattr(game.pokerkit_state, 'actor_index', None)
        if current_actor is not None:
            # Convert from 0-based to 1-based player ID
            current_player_id = current_actor + 1
            valid_actions = game.get_valid_actions(current_player_id)
        else:
            valid_actions = []
        
        # Return game state
        game_state = game.get_game_state()
        game_state["valid_actions"] = valid_actions
        
        return GameStateResponse(**game_state)
        
    except Exception as e:
        import traceback
        print('ERROR in /api/poker/start:', e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/game/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    """Get current state of an active game"""
    try:
        if game_id not in active_games:
            raise HTTPException(status_code=404, detail="Game not found")
        
        game = active_games[game_id]
        
        # Get valid actions for current player (handle finished games)
        if game.state.is_finished:
            valid_actions = []
        else:
            current_actor = getattr(game.pokerkit_state, 'actor_index', None)
            if current_actor is not None:
                # Convert from 0-based to 1-based player ID
                current_player_id = current_actor + 1
                valid_actions = game.get_valid_actions(current_player_id)
            else:
                valid_actions = []
        
        # Get game state
        game_state = game.get_game_state()
        game_state["valid_actions"] = valid_actions
        
        # Temporary debug: Check if backend detects finished state
        if not game_state.get('valid_actions') and game_state.get('stage') == 'finished':
            print(f"DEBUG: Game appears finished but is_finished={game_state.get('is_finished')}")
        
        return GameStateResponse(**game_state)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f'ERROR in /api/poker/game/{game_id}:', e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/game/{game_id}/action", response_model=GameStateResponse)
async def execute_action(game_id: str, request: PlayerActionRequest):
    """Execute a player action in the game"""
    try:
        if game_id not in active_games:
            raise HTTPException(status_code=404, detail="Game not found")
        
        game = active_games[game_id]
        
        # Convert string action to ActionType enum
        try:
            from app.models.poker import ActionType
            action_map = {
                "fold": ActionType.FOLD,
                "check": ActionType.CHECK,
                "call": ActionType.CALL,
                "bet": ActionType.BET,
                "raise": ActionType.RAISE,
                "all_in": ActionType.ALL_IN
            }
            
            if request.action.lower() not in action_map:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unknown action: {request.action}"
                )
            
            action_enum = action_map[request.action.lower()]
            
        except Exception as conversion_error:
            raise HTTPException(status_code=500, detail=f"Error converting action: {str(conversion_error)}")
        
        # Validate action
        try:
            valid_actions = game.get_valid_actions(request.player_id)
            print(f"Valid actions for player {request.player_id}: {valid_actions}")
        except Exception as validation_error:
            print(f"Error getting valid actions: {validation_error}")
            raise HTTPException(status_code=500, detail=f"Error validating actions: {str(validation_error)}")
        
        if action_enum not in valid_actions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid action {action_enum} for player {request.player_id}. Valid actions: {valid_actions}"
            )
        
        # Execute action
        try:
            print(f"Attempting to execute action: {action_enum}")
            success = game.execute_action(request.player_id, action_enum, request.amount or 0)
            print(f"Action execution result: {success}")
        except Exception as exec_error:
            print(f"Error executing action: {exec_error}")
            raise HTTPException(status_code=500, detail=f"Error executing action: {str(exec_error)}")
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to execute action")
        
        # Check if game is finished and save to database
        print(f"Checking if game is finished: game.state.is_finished = {game.state.is_finished}")
        
        if game.state.is_finished:
            print(f"GAME IS FINISHED! Attempting to save hand history for game {game_id}")
            try:
                repo = PokerRepository()
                hand_history = repo.save_hand_history(game)
                print(f"✅ HAND HISTORY SAVED: {hand_history.id} - Winner: {game.state.winner_id}, Pot: {game.state.pot}")
                print(f"   Players data saved with positions: {[f'P{p['id']}({"D" if p['is_dealer'] else "SB" if p['is_small_blind'] else "BB" if p['is_big_blind'] else ""})' for p in hand_history.players_data]}")
            except Exception as e:
                print(f"❌ ERROR saving hand history: {e}")
                import traceback
                traceback.print_exc()
            # DON'T remove from active games immediately - frontend needs to display final state
            # Game will be cleaned up when user starts a new game or explicitly resets
            print(f"Game {game_id} finished but kept in active_games for final state display")
        else:
            print(f"Game {game_id} is NOT finished yet, continuing...")
        
        # Get valid actions for next player
        try:
            if not game.state.is_finished:
                current_actor = getattr(game.pokerkit_state, 'actor_index', None)
                if current_actor is not None:
                    # Convert from 0-based to 1-based player ID
                    current_player_id = current_actor + 1
                    valid_actions = game.get_valid_actions(current_player_id)
                else:
                    valid_actions = []
            else:
                valid_actions = []
        except Exception as next_actions_error:
            print(f"Error getting next valid actions: {next_actions_error}")
            valid_actions = []
        
        try:
            game_state = game.get_game_state()
            game_state["valid_actions"] = valid_actions
            print(f"Returning game state with {len(game_state.get('players', []))} players")
        except Exception as state_error:
            print(f"ERROR in execute_action: {state_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error getting game state: {str(state_error)}")
        
        return GameStateResponse(**game_state)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print('ERROR in /api/poker/start:', e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/game/{game_id}/valid-actions/{player_id}")
async def get_valid_actions(game_id: str, player_id: int):
    """Get valid actions for a specific player"""
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = active_games[game_id]
    valid_actions = game.get_valid_actions(player_id)
    
    return {"player_id": player_id, "valid_actions": valid_actions}


@router.delete("/game/{game_id}")
async def reset_game(game_id: str):
    """Reset/delete an active game"""
    if game_id in active_games:
        del active_games[game_id]
        return {"message": "Game reset successfully"}
    else:
        raise HTTPException(status_code=404, detail="Game not found")


@router.get("/history", response_model=List[HandHistoryResponse])
async def get_hand_history(limit: int = 50):
    """Get hand history from database"""
    repo = PokerRepository()
    histories = repo.get_all_hand_histories(limit)
    
    return [HandHistoryResponse(
        id=h.id,
        players_data=h.players_data,
        community_cards=h.community_cards,
        actions=h.actions,
        pot_size=h.pot_size,
        winner_id=h.winner_id,
        stage=h.stage,
        dealer_position=h.dealer_position,
        small_blind=h.small_blind,
        big_blind=h.big_blind,
        created_at=h.created_at.isoformat() if h.created_at else "",
        finished_at=h.finished_at.isoformat() if h.finished_at else None
    ) for h in histories]


@router.get("/history/{hand_id}", response_model=HandHistoryResponse)
async def get_specific_hand_history(hand_id: str):
    """Get specific hand history by ID"""
    repo = PokerRepository()
    history = repo.get_hand_history(hand_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Hand history not found")
    
    return HandHistoryResponse(
        id=history.id,
        players_data=history.players_data,
        community_cards=history.community_cards,
        actions=history.actions,
        pot_size=history.pot_size,
        winner_id=history.winner_id,
        stage=history.stage,
        dealer_position=history.dealer_position,
        small_blind=history.small_blind,
        big_blind=history.big_blind,
        created_at=history.created_at.isoformat() if history.created_at else "",
        finished_at=history.finished_at.isoformat() if history.finished_at else None
    )


@router.get("/active-games")
async def get_active_games():
    """Get list of active game IDs"""
    return {"active_games": list(active_games.keys())}
