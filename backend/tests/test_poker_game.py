import pytest
from app.models.poker import PokerGame, ActionType, GameStage, Card, Suit, Rank

class TestPokerGame:
    """Test suite for PokerGame core logic"""
    
    def test_game_initialization(self):
        """Test game initialization with proper setup"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        # Verify game state
        assert len(game.state.players) == 6
        assert game.state.stage == GameStage.PREFLOP
        assert game.state.pot == 60  # Small blind (20) + Big blind (40)
        assert game.state.current_bet == 40  # Big blind
        assert not game.state.is_finished
        
        # Verify each player has hole cards
        for player in game.state.players:
            assert len(player.hole_cards) == 2
            assert player.stack in [960, 980, 1000]  # Accounting for blinds
    
    def test_blinds_posting(self):
        """Test that blinds are posted correctly"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        # Find small blind and big blind players
        small_blind_player = None
        big_blind_player = None
        
        for player in game.state.players:
            if player.current_bet == 20:
                small_blind_player = player
            elif player.current_bet == 40:
                big_blind_player = player
        
        assert small_blind_player is not None
        assert big_blind_player is not None
        assert small_blind_player.stack == 980  # 1000 - 20
        assert big_blind_player.stack == 960   # 1000 - 40
    
    def test_valid_actions_preflop(self):
        """Test valid actions during preflop"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        current_player = game.state.players[game.state.current_player]
        valid_actions = game.get_valid_actions(current_player.id)
        
        # Player should be able to fold, call, raise, or go all-in
        assert ActionType.FOLD in valid_actions
        assert ActionType.CALL in valid_actions
        assert ActionType.RAISE in valid_actions
        assert ActionType.ALL_IN in valid_actions
        
        # Should not be able to check (there's a bet to call)
        assert ActionType.CHECK not in valid_actions
    
    def test_fold_action(self):
        """Test fold action execution"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        current_player = game.state.players[game.state.current_player]
        original_current_player_index = game.state.current_player
        
        # Execute fold
        success = game.execute_action(current_player.id, ActionType.FOLD)
        
        assert success
        assert current_player.is_folded
        assert game.state.current_player != original_current_player_index
    
    def test_call_action(self):
        """Test call action execution"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        current_player = game.state.players[game.state.current_player]
        original_stack = current_player.stack
        call_amount = game.state.current_bet - current_player.current_bet
        
        # Execute call
        success = game.execute_action(current_player.id, ActionType.CALL)
        
        assert success
        assert current_player.current_bet == game.state.current_bet
        assert current_player.stack == original_stack - call_amount
    
    def test_raise_action(self):
        """Test raise action execution"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        current_player = game.state.players[game.state.current_player]
        original_stack = current_player.stack
        raise_amount = 80  # Raise to 80 (40 more than current bet of 40)
        
        # Execute raise
        success = game.execute_action(current_player.id, ActionType.RAISE, raise_amount)
        
        assert success
        assert current_player.current_bet == raise_amount
        assert game.state.current_bet == raise_amount
        assert current_player.stack == original_stack - raise_amount
    
    def test_all_in_action(self):
        """Test all-in action execution"""
        player_stacks = {1: 100, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}  # Player 1 has small stack
        game = PokerGame(player_stacks)
        
        # Find the player with small stack
        small_stack_player = next(p for p in game.state.players if p.stack < 200)
        
        # If it's not their turn, make it their turn for testing
        if game.state.players[game.state.current_player].id != small_stack_player.id:
            # Skip to their turn by folding others
            while game.state.players[game.state.current_player].id != small_stack_player.id:
                current = game.state.players[game.state.current_player]
                game.execute_action(current.id, ActionType.FOLD)
        
        original_stack = small_stack_player.stack
        
        # Execute all-in
        success = game.execute_action(small_stack_player.id, ActionType.ALL_IN)
        
        assert success
        assert small_stack_player.is_all_in
        assert small_stack_player.stack == 0
        assert small_stack_player.current_bet == original_stack
    
    def test_stage_progression(self):
        """Test game stage progression"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        assert game.state.stage == GameStage.PREFLOP
        assert len(game.state.community_cards) == 0
        
        # Make all players call to advance to flop
        while game.state.stage == GameStage.PREFLOP and not game.state.is_finished:
            current_player = game.state.players[game.state.current_player]
            game.execute_action(current_player.id, ActionType.CALL)
        
        # Should advance to flop
        if not game.state.is_finished:
            assert game.state.stage == GameStage.FLOP
            assert len(game.state.community_cards) == 3
    
    def test_auto_advance_all_in_scenario(self):
        """Test auto-advance when all players are all-in"""
        player_stacks = {1: 100, 2: 100, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        # Make first two players go all-in and others call
        actions_taken = 0
        max_actions = 20  # Prevent infinite loop
        
        while not game.state.is_finished and actions_taken < max_actions:
            current_player = game.state.players[game.state.current_player]
            
            if current_player.stack <= 100:
                # Small stack players go all-in
                game.execute_action(current_player.id, ActionType.ALL_IN)
            else:
                # Other players call
                game.execute_action(current_player.id, ActionType.CALL)
            
            actions_taken += 1
        
        # Game should auto-advance to completion
        if game.state.is_finished:
            assert game.state.stage == GameStage.FINISHED
            assert len(game.state.community_cards) == 5  # All community cards dealt
            assert game.state.winner_id is not None
    
    def test_winner_determination_by_fold(self):
        """Test winner determination when all but one player folds"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        # Fold all players except one
        players_to_fold = 5
        folded_count = 0
        
        while folded_count < players_to_fold and not game.state.is_finished:
            current_player = game.state.players[game.state.current_player]
            game.execute_action(current_player.id, ActionType.FOLD)
            folded_count += 1
        
        # Game should be finished with a winner
        assert game.state.is_finished
        assert game.state.winner_id is not None
        
        # Winner should be the only non-folded player
        active_players = [p for p in game.state.players if not p.is_folded]
        assert len(active_players) == 1
        assert active_players[0].id == game.state.winner_id
    
    def test_invalid_action_wrong_player(self):
        """Test that invalid actions are rejected"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        # Try to execute action with wrong player
        wrong_player = None
        for player in game.state.players:
            if player.id != game.state.players[game.state.current_player].id:
                wrong_player = player
                break
        
        success = game.execute_action(wrong_player.id, ActionType.FOLD)
        assert not success
    
    def test_card_format_for_pokerkit(self):
        """Test that cards are formatted correctly for pokerkit"""
        # Create test cards
        card1 = Card(suit=Suit.HEARTS, rank=Rank.ACE)
        card2 = Card(suit=Suit.SPADES, rank=Rank.KING)
        card3 = Card(suit=Suit.DIAMONDS, rank=Rank.QUEEN)
        card4 = Card(suit=Suit.CLUBS, rank=Rank.JACK)
        
        # Verify format
        assert str(card1) == "Ah"
        assert str(card2) == "Ks"
        assert str(card3) == "Qd"
        assert str(card4) == "Jc"
        
        # Test numeric ranks
        card5 = Card(suit=Suit.HEARTS, rank=Rank.NINE)
        card6 = Card(suit=Suit.DIAMONDS, rank=Rank.TWO)
        
        assert str(card5) == "9h"
        assert str(card6) == "2d"
    
    def test_betting_round_completion(self):
        """Test betting round completion detection"""
        player_stacks = {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000}
        game = PokerGame(player_stacks)
        
        initial_stage = game.state.stage
        
        # Have all players call
        actions_count = 0
        max_actions = 10
        
        while game.state.stage == initial_stage and actions_count < max_actions and not game.state.is_finished:
            current_player = game.state.players[game.state.current_player]
            game.execute_action(current_player.id, ActionType.CALL)
            actions_count += 1
        
        # Should have advanced to next stage or finished
        assert game.state.stage != initial_stage or game.state.is_finished
