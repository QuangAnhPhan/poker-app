import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.models.poker import ActionType

client = TestClient(app)

class TestPokerAPI:
    """Test suite for Poker API endpoints"""
    
    def test_start_game_success(self):
        """Test successful game start"""
        response = client.post("/api/start-game", json={
            "player_stacks": {
                "1": 1000,
                "2": 1000,
                "3": 1000,
                "4": 1000,
                "5": 1000,
                "6": 1000
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify game state structure
        assert "id" in data
        assert "players" in data
        assert "stage" in data
        assert "pot" in data
        assert "current_bet" in data
        assert "current_player" in data
        assert "is_finished" in data
        
        # Verify 6 players created
        assert len(data["players"]) == 6
        
        # Verify initial game state
        assert data["stage"] == "preflop"
        assert data["pot"] == 60  # Small blind (20) + Big blind (40)
        assert data["current_bet"] == 40  # Big blind amount
        assert not data["is_finished"]
        
        # Verify each player has hole cards
        for player in data["players"]:
            assert len(player["hole_cards"]) == 2
            assert player["stack"] in [960, 980, 1000]  # Accounting for blinds
    
    def test_start_game_invalid_players(self):
        """Test game start with invalid number of players"""
        response = client.post("/api/start-game", json={
            "player_stacks": {
                "1": 1000,
                "2": 1000
            }  # Only 2 players, should be 6
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_execute_action_fold(self):
        """Test fold action execution"""
        # Start a game first
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        current_player = game_data["players"][game_data["current_player"]]
        
        # Execute fold action
        response = client.post(f"/api/games/{game_id}/action", json={
            "player_id": current_player["id"],
            "action": ActionType.FOLD,
            "amount": 0
        })
        
        assert response.status_code == 200
        updated_data = response.json()
        
        # Verify player is folded
        folded_player = next(p for p in updated_data["players"] if p["id"] == current_player["id"])
        assert folded_player["is_folded"]
        
        # Verify current player changed
        assert updated_data["current_player"] != game_data["current_player"]
    
    def test_execute_action_call(self):
        """Test call action execution"""
        # Start a game
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        current_player = game_data["players"][game_data["current_player"]]
        
        # Execute call action
        response = client.post(f"/api/games/{game_id}/action", json={
            "player_id": current_player["id"],
            "action": ActionType.CALL,
            "amount": 0
        })
        
        assert response.status_code == 200
        updated_data = response.json()
        
        # Verify player called (current_bet should match game's current_bet)
        calling_player = next(p for p in updated_data["players"] if p["id"] == current_player["id"])
        assert calling_player["current_bet"] == game_data["current_bet"]
    
    def test_execute_action_bet(self):
        """Test bet action execution"""
        # Start a game and get to a state where betting is possible
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        
        # Find a player who can bet (not in blinds position)
        current_player = game_data["players"][game_data["current_player"]]
        
        # Execute raise action (since there's already a big blind bet)
        response = client.post(f"/api/games/{game_id}/action", json={
            "player_id": current_player["id"],
            "action": ActionType.RAISE,
            "amount": 80  # Raise to 80 (40 more than current bet)
        })
        
        assert response.status_code == 200
        updated_data = response.json()
        
        # Verify bet was placed
        betting_player = next(p for p in updated_data["players"] if p["id"] == current_player["id"])
        assert betting_player["current_bet"] == 80
        assert updated_data["current_bet"] == 80
    
    def test_execute_action_invalid_player(self):
        """Test action execution with invalid player"""
        # Start a game
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        
        # Try to execute action with wrong player
        response = client.post(f"/api/games/{game_id}/action", json={
            "player_id": 999,  # Invalid player ID
            "action": ActionType.FOLD,
            "amount": 0
        })
        
        assert response.status_code == 400
    
    def test_get_game_state(self):
        """Test getting game state"""
        # Start a game
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        
        # Get game state
        response = client.get(f"/api/games/{game_id}")
        
        assert response.status_code == 200
        retrieved_data = response.json()
        
        # Verify it matches the original game data
        assert retrieved_data["id"] == game_id
        assert len(retrieved_data["players"]) == 6
        assert retrieved_data["stage"] == "preflop"
    
    def test_get_nonexistent_game(self):
        """Test getting state of non-existent game"""
        response = client.get("/api/games/nonexistent-id")
        
        assert response.status_code == 404
    
    def test_reset_game(self):
        """Test game reset"""
        # Start a game
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        
        # Execute some actions to change game state
        current_player = game_data["players"][game_data["current_player"]]
        client.post(f"/api/games/{game_id}/action", json={
            "player_id": current_player["id"],
            "action": ActionType.FOLD,
            "amount": 0
        })
        
        # Reset game
        response = client.post(f"/api/games/{game_id}/reset")
        
        assert response.status_code == 200
        
        # Verify game no longer exists
        get_response = client.get(f"/api/games/{game_id}")
        assert get_response.status_code == 404
    
    def test_get_hand_histories_empty(self):
        """Test getting hand histories when none exist"""
        response = client.get("/api/hand-histories")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_complete_game_flow(self):
        """Test a complete game flow from start to finish"""
        # Start game
        start_response = client.post("/api/start-game", json={
            "player_stacks": {str(i): 1000 for i in range(1, 7)}
        })
        game_data = start_response.json()
        game_id = game_data["id"]
        
        # Play through preflop - fold all players except one
        for i in range(5):  # Fold 5 players, leaving 1
            current_player = game_data["players"][game_data["current_player"]]
            
            response = client.post(f"/api/games/{game_id}/action", json={
                "player_id": current_player["id"],
                "action": ActionType.FOLD,
                "amount": 0
            })
            
            assert response.status_code == 200
            game_data = response.json()
            
            if game_data["is_finished"]:
                break
        
        # Verify game finished
        assert game_data["is_finished"]
        assert game_data["winner_id"] is not None
        
        # Verify hand history was created
        histories_response = client.get("/api/hand-histories")
        assert histories_response.status_code == 200
        histories = histories_response.json()
        assert len(histories) > 0
        
        # Find our game's history
        our_history = next((h for h in histories if h["game_id"] == game_id), None)
        assert our_history is not None
        assert our_history["winner_player_id"] == game_data["winner_id"]
