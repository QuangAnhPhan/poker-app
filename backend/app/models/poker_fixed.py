from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import uuid
from datetime import datetime
import random
from pokerkit import Automation, NoLimitTexasHoldem, Card as PokerKitCard


class Suit(str, Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"


class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"  # Changed from "10" to "T" for PokerKit compatibility
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


@dataclass
class Card:
    suit: Suit
    rank: Rank
    
    def __str__(self):
        # Convert to PokerKit format (e.g., "Th" instead of "10h")
        suit_map = {"hearts": "h", "diamonds": "d", "clubs": "c", "spades": "s"}
        return f"{self.rank.value}{suit_map[self.suit.value]}"


class ActionType(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


class GameStage(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    FINISHED = "finished"


@dataclass
class PlayerAction:
    player_id: int
    action: ActionType
    amount: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Player:
    id: int
    name: str
    stack: int
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: int = 0
    is_folded: bool = False
    is_all_in: bool = False
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False


@dataclass
class GameState:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    players: List[Player] = field(default_factory=list)
    community_cards: List[Card] = field(default_factory=list)
    pot: int = 0
    current_bet: int = 0
    stage: GameStage = GameStage.PREFLOP
    dealer_position: int = 0
    current_player: int = 0
    actions: List[PlayerAction] = field(default_factory=list)
    small_blind: int = 20
    big_blind: int = 40
    is_finished: bool = False
    winner_id: Optional[int] = None
    winner_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class PokerGame:
    """PokerKit-based poker game implementation with proper error handling"""
    
    def __init__(self, player_stacks: Dict[int, int]):
        """Initialize a new poker game using PokerKit"""
        self.game_id = str(uuid.uuid4())
        self.detailed_log = []  # For detailed play log
        self.player_stacks = player_stacks
        self.player_names = {i: f"Player {i}" for i in range(1, 7)}
        
        # Create PokerKit state with 6 players
        starting_stacks = tuple(player_stacks[i] for i in range(1, 7))
        
        try:
            self.pokerkit_state = NoLimitTexasHoldem.create_state(
                # Automations
                (
                    Automation.ANTE_POSTING,
                    Automation.BET_COLLECTION,
                    Automation.BLIND_OR_STRADDLE_POSTING,
                    Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
                    Automation.HAND_KILLING,
                    Automation.CHIPS_PUSHING,
                    Automation.CHIPS_PULLING,
                ),
                False,  # Uniform antes?
                {},     # Antes (none for our game)
                (20, 40),  # Blinds (small blind: 20, big blind: 40)
                40,     # Min-bet
                starting_stacks,  # Starting stacks
                6,      # Number of players
            )
            
            # Deal hole cards to all players (2 cards each)
            self._deal_initial_cards()
            
        except Exception as e:
            print(f"Error creating PokerKit state: {e}")
            # Fallback to basic state
            self.pokerkit_state = None
        
        # Create our API-compatible state representation
        self.state = self._create_api_state()
        
        # Initialize logging
        self.initialize_detailed_logging()
    
    def _deal_initial_cards(self):
        """Deal 2 hole cards to each player using PokerKit's dealing mechanism"""
        try:
            # Deal 2 cards to each of the 6 players
            cards_to_deal = []
            
            # Generate a shuffled deck for dealing
            ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
            suits = ['h', 'd', 'c', 's']
            deck = [f"{rank}{suit}" for rank in ranks for suit in suits]
            random.shuffle(deck)
            
            # Deal 12 cards (2 per player)
            for i in range(12):
                if self.pokerkit_state.can_deal_hole():
                    card = deck[i]
                    self.pokerkit_state.deal_hole(card)
                    
        except Exception as e:
            print(f"Error dealing cards: {e}")
    
    def _create_api_state(self) -> GameState:
        """Create API-compatible state from PokerKit state"""
        players = []
        
        for i in range(6):
            player_id = i + 1
            
            # Get hole cards for this player
            hole_cards = []
            if (self.pokerkit_state and 
                hasattr(self.pokerkit_state, 'hole_cards') and 
                self.pokerkit_state.hole_cards and 
                len(self.pokerkit_state.hole_cards) > i and
                self.pokerkit_state.hole_cards[i]):
                
                try:
                    hole_cards = [self._pokerkit_card_to_api_card(card) 
                                 for card in self.pokerkit_state.hole_cards[i]]
                except Exception as e:
                    print(f"Error converting hole cards for player {player_id}: {e}")
                    hole_cards = []
            
            # Determine player positions
            is_dealer = (i == 5)  # Player 6 (index 5) is dealer
            is_small_blind = (i == 3)  # Player 4 (index 3) is small blind
            is_big_blind = (i == 4)   # Player 5 (index 4) is big blind
            
            # Get current stack from PokerKit or use initial value
            current_stack = self.player_stacks[player_id]
            if self.pokerkit_state and hasattr(self.pokerkit_state, 'stacks'):
                try:
                    current_stack = int(self.pokerkit_state.stacks[i])
                except:
                    pass
            
            # Get current bet
            current_bet = 0
            if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                try:
                    current_bet = int(self.pokerkit_state.bets[i])
                except:
                    pass
            
            # Check if player is folded
            is_folded = False
            if self.pokerkit_state and hasattr(self.pokerkit_state, 'statuses'):
                try:
                    is_folded = self.pokerkit_state.statuses[i] == 0
                except:
                    pass
            
            player = Player(
                id=player_id,
                name=self.player_names[player_id],
                stack=current_stack,
                hole_cards=hole_cards,
                current_bet=current_bet,
                is_folded=is_folded,
                is_all_in=current_stack == 0 and not is_folded,
                is_dealer=is_dealer,
                is_small_blind=is_small_blind,
                is_big_blind=is_big_blind
            )
            players.append(player)
        
        # Get community cards
        community_cards = []
        if (self.pokerkit_state and 
            hasattr(self.pokerkit_state, 'board_cards') and 
            self.pokerkit_state.board_cards):
            try:
                community_cards = [self._pokerkit_card_to_api_card(card) 
                                 for card in self.pokerkit_state.board_cards]
            except Exception as e:
                print(f"Error converting community cards: {e}")
        
        # Determine current stage
        stage = self._get_current_stage()
        
        # Get current player
        current_player = 1  # Default to player 1
        if (self.pokerkit_state and 
            hasattr(self.pokerkit_state, 'actor_index') and 
            self.pokerkit_state.actor_index is not None):
            try:
                current_player = self.pokerkit_state.actor_index + 1  # Convert to 1-based indexing
            except:
                pass
        
        # Calculate pot
        pot = 60  # Default (small blind + big blind)
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
            try:
                pot = sum(self.pokerkit_state.bets)
            except:
                pass
        
        # Calculate current bet
        current_bet = 40  # Default (big blind)
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
            try:
                current_bet = max(self.pokerkit_state.bets)
            except:
                pass
        
        # Check if game is finished
        is_finished = False
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'status'):
            try:
                is_finished = not self.pokerkit_state.status
            except:
                pass
        
        return GameState(
            id=self.game_id,
            players=players,
            community_cards=community_cards,
            pot=pot,
            current_bet=current_bet,
            stage=stage,
            dealer_position=6,  # Player 6 is dealer
            current_player=current_player,
            actions=[],
            small_blind=20,
            big_blind=40,
            is_finished=is_finished,
            winner_id=None,
            winner_reason="",
            created_at=datetime.now()
        )
    
    def _pokerkit_card_to_api_card(self, pokerkit_card) -> Card:
        """Convert PokerKit card to our API card format with proper error handling"""
        try:
            # PokerKit card string format is like "Ah", "Kd", "Ts", etc.
            card_str = str(pokerkit_card)
            
            if len(card_str) != 2:
                raise ValueError(f"Invalid card format: {card_str}")
            
            rank_str = card_str[0]
            suit_str = card_str[1].lower()  # Convert to lowercase for consistency
            
            # Map rank
            rank_map = {
                '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
                '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
                'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 'K': Rank.KING, 'A': Rank.ACE
            }
            
            # Map suit (handle both upper and lowercase)
            suit_map = {
                'h': Suit.HEARTS, 'd': Suit.DIAMONDS, 'c': Suit.CLUBS, 's': Suit.SPADES
            }
            
            if rank_str not in rank_map:
                raise ValueError(f"Invalid rank: {rank_str}")
            if suit_str not in suit_map:
                raise ValueError(f"Invalid suit: {suit_str}")
            
            return Card(suit=suit_map[suit_str], rank=rank_map[rank_str])
            
        except Exception as e:
            print(f"Error converting card {pokerkit_card}: {e}")
            # Return a default card as fallback
            return Card(suit=Suit.HEARTS, rank=Rank.ACE)
    
    def _get_current_stage(self) -> GameStage:
        """Determine current game stage from PokerKit state"""
        if not self.pokerkit_state or not hasattr(self.pokerkit_state, 'board_cards'):
            return GameStage.PREFLOP
        
        try:
            if not self.pokerkit_state.board_cards:
                return GameStage.PREFLOP
            elif len(self.pokerkit_state.board_cards) == 3:
                return GameStage.FLOP
            elif len(self.pokerkit_state.board_cards) == 4:
                return GameStage.TURN
            elif len(self.pokerkit_state.board_cards) == 5:
                return GameStage.RIVER
            else:
                return GameStage.FINISHED
        except:
            return GameStage.PREFLOP
    
    def _log_game_setup(self):
        """Log initial game setup details"""
        setup_info = {
            "type": "game_setup",
            "game_id": self.game_id,
            "players": [
                {
                    "id": i,
                    "name": self.player_names[i],
                    "stack": self.player_stacks[i],
                    "position": "Dealer" if i == 6 else "Small Blind" if i == 4 else "Big Blind" if i == 5 else "Player"
                }
                for i in range(1, 7)
            ],
            "blinds": {"small_blind": 20, "big_blind": 40},
            "timestamp": datetime.now().isoformat()
        }
        self.detailed_log.append(setup_info)
    
    def _log_action(self, player_id: int, action: str, amount: int = 0):
        """Log detailed player action"""
        pot = 60  # Default
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
            try:
                pot = sum(self.pokerkit_state.bets)
            except:
                pass
        
        action_info = {
            "type": "player_action",
            "player_id": player_id,
            "player_name": self.player_names[player_id],
            "action": action,
            "amount": amount,
            "pot_after": pot,
            "stage": self._get_current_stage().value,
            "timestamp": datetime.now().isoformat()
        }
        self.detailed_log.append(action_info)
    
    def initialize_detailed_logging(self):
        """Initialize detailed logging after cards are dealt"""
        self._log_game_setup()
        
        # Log hole cards for each player
        for player_id in range(1, 7):
            hole_cards = self.get_player_hole_cards(player_id)
            if hole_cards:
                card_info = {
                    "type": "hole_cards_dealt",
                    "player_id": player_id,
                    "player_name": self.player_names[player_id],
                    "cards": [str(card) for card in hole_cards],
                    "timestamp": datetime.now().isoformat()
                }
                self.detailed_log.append(card_info)
    
    def get_player_hole_cards(self, player_id: int) -> List[Card]:
        """Get hole cards for a specific player"""
        player_index = player_id - 1  # Convert to 0-based indexing
        
        if (self.pokerkit_state and 
            hasattr(self.pokerkit_state, 'hole_cards') and
            self.pokerkit_state.hole_cards and 
            len(self.pokerkit_state.hole_cards) > player_index and
            self.pokerkit_state.hole_cards[player_index]):
            
            try:
                return [self._pokerkit_card_to_api_card(card) 
                       for card in self.pokerkit_state.hole_cards[player_index]]
            except Exception as e:
                print(f"Error getting hole cards for player {player_id}: {e}")
        
        return []
    
    def get_valid_actions(self, player_id: int) -> List[ActionType]:
        """Get valid actions for a specific player using PokerKit's validation"""
        player_index = player_id - 1  # Convert to 0-based indexing
        
        # Check if it's this player's turn
        if (not self.pokerkit_state or
            not hasattr(self.pokerkit_state, 'actor_index') or 
            self.pokerkit_state.actor_index != player_index):
            return []
        
        valid_actions = []
        
        try:
            # Check what actions are available in PokerKit
            if self.pokerkit_state.can_fold():
                valid_actions.append(ActionType.FOLD)
            
            if self.pokerkit_state.can_check_or_call():
                # Determine if it's check or call based on current bet
                current_bet = 0
                player_bet = 0
                
                if hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                    current_bet = max(self.pokerkit_state.bets)
                    player_bet = self.pokerkit_state.bets[player_index]
                
                if current_bet == player_bet:
                    valid_actions.append(ActionType.CHECK)
                else:
                    valid_actions.append(ActionType.CALL)
            
            if hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to'):
                # Check if player can bet or raise
                current_bet = 0
                if hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                    current_bet = max(self.pokerkit_state.bets)
                
                if current_bet == 0:
                    valid_actions.append(ActionType.BET)
                else:
                    valid_actions.append(ActionType.RAISE)
                
                # Check if player can go all-in
                if (hasattr(self.pokerkit_state, 'stacks') and 
                    self.pokerkit_state.stacks[player_index] > 0):
                    valid_actions.append(ActionType.ALL_IN)
                    
        except Exception as e:
            print(f"Error getting valid actions for player {player_id}: {e}")
            # Return basic actions as fallback
            valid_actions = [ActionType.FOLD, ActionType.CALL]
        
        return valid_actions
    
    def execute_action(self, player_id: int, action: ActionType, amount: int = 0) -> bool:
        """Execute a player action using PokerKit's action system"""
        if not self.pokerkit_state:
            print("No PokerKit state available")
            return False
        
        player_index = player_id - 1  # Convert to 0-based indexing
        
        # Verify it's this player's turn
        if (not hasattr(self.pokerkit_state, 'actor_index') or 
            self.pokerkit_state.actor_index != player_index):
            print(f"Not player {player_id}'s turn")
            return False
        
        try:
            # Execute action using PokerKit
            if action == ActionType.FOLD:
                if self.pokerkit_state.can_fold():
                    self.pokerkit_state.fold()
                    self._log_action(player_id, "fold")
                    
            elif action == ActionType.CHECK:
                if self.pokerkit_state.can_check_or_call():
                    current_bet = 0
                    player_bet = 0
                    if hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                        current_bet = max(self.pokerkit_state.bets)
                        player_bet = self.pokerkit_state.bets[player_index]
                    
                    if current_bet == player_bet:
                        self.pokerkit_state.check_or_call()
                        self._log_action(player_id, "check")
                    
            elif action == ActionType.CALL:
                if self.pokerkit_state.can_check_or_call():
                    call_amount = 0
                    if hasattr(self.pokerkit_state, 'checking_or_calling_amount'):
                        call_amount = self.pokerkit_state.checking_or_calling_amount
                    self.pokerkit_state.check_or_call()
                    self._log_action(player_id, "call", call_amount)
                    
            elif action in [ActionType.BET, ActionType.RAISE]:
                if hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to'):
                    if self.pokerkit_state.can_complete_bet_or_raise_to(amount):
                        self.pokerkit_state.complete_bet_or_raise_to(amount)
                        action_name = "bet" if action == ActionType.BET else "raise"
                        self._log_action(player_id, action_name, amount)
                    
            elif action == ActionType.ALL_IN:
                # All-in is raising to the player's entire stack
                if hasattr(self.pokerkit_state, 'stacks'):
                    all_in_amount = self.pokerkit_state.stacks[player_index]
                    if (all_in_amount > 0 and 
                        hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to') and
                        self.pokerkit_state.can_complete_bet_or_raise_to(all_in_amount)):
                        self.pokerkit_state.complete_bet_or_raise_to(all_in_amount)
                        self._log_action(player_id, "all_in", all_in_amount)
            
            # Update our API state
            self.state = self._create_api_state()
            
            # Check if we need to deal community cards or finish the hand
            self._handle_automatic_progression()
            
            return True
            
        except Exception as e:
            print(f"Action execution failed: {e}")
            return False
    
    def _handle_automatic_progression(self):
        """Handle automatic game progression (dealing cards, determining winners)"""
        if not self.pokerkit_state:
            return
        
        try:
            # Check if we need to deal community cards
            if hasattr(self.pokerkit_state, 'can_burn_card') and self.pokerkit_state.can_burn_card():
                self.pokerkit_state.burn_card()
            
            if hasattr(self.pokerkit_state, 'can_deal_board') and self.pokerkit_state.can_deal_board():
                old_stage = self._get_current_stage()
                
                # Deal appropriate number of cards for next stage
                board_count = len(self.pokerkit_state.board_cards) if self.pokerkit_state.board_cards else 0
                
                if board_count == 0:
                    # Deal flop (3 cards)
                    for _ in range(3):
                        if self.pokerkit_state.can_deal_board():
                            self.pokerkit_state.deal_board()
                elif board_count == 3:
                    # Deal turn (1 card)
                    if self.pokerkit_state.can_deal_board():
                        self.pokerkit_state.deal_board()
                elif board_count == 4:
                    # Deal river (1 card)
                    if self.pokerkit_state.can_deal_board():
                        self.pokerkit_state.deal_board()
                
                new_stage = self._get_current_stage()
                if old_stage != new_stage:
                    self._log_stage_transition(new_stage)
            
            # Check if hand is complete
            if hasattr(self.pokerkit_state, 'status') and not self.pokerkit_state.status:
                self._determine_winner()
                
        except Exception as e:
            print(f"Error in automatic progression: {e}")
    
    def _log_stage_transition(self, new_stage: GameStage):
        """Log stage transitions with community cards"""
        community_cards = []
        if (self.pokerkit_state and 
            hasattr(self.pokerkit_state, 'board_cards') and 
            self.pokerkit_state.board_cards):
            try:
                community_cards = [str(card) for card in self.pokerkit_state.board_cards]
            except:
                pass
        
        pot = 60
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
            try:
                pot = sum(self.pokerkit_state.bets)
            except:
                pass
        
        stage_info = {
            "type": "stage_transition",
            "new_stage": new_stage.value,
            "community_cards": community_cards,
            "pot": pot,
            "timestamp": datetime.now().isoformat()
        }
        self.detailed_log.append(stage_info)
    
    def _determine_winner(self):
        """Determine winner using PokerKit's built-in evaluation"""
        if not self.pokerkit_state:
            return
        
        try:
            # PokerKit automatically handles winner determination and chip distribution
            # We just need to identify who won and log it
            
            # Find the player with the highest stack increase
            final_stacks = [int(stack) for stack in self.pokerkit_state.stacks]
            initial_stacks = [self.player_stacks[i] for i in range(1, 7)]
            
            stack_changes = [final - initial for final, initial in zip(final_stacks, initial_stacks)]
            winner_index = stack_changes.index(max(stack_changes))
            winner_id = winner_index + 1
            
            pot_won = max(stack_changes)
            
            self.state.winner_id = winner_id
            self.state.winner_reason = f"{self.player_names[winner_id]} wins the hand"
            self.state.is_finished = True
            self.state.stage = GameStage.FINISHED
            
            # Update player stacks
            for i, stack in enumerate(final_stacks):
                self.state.players[i].stack = stack
            
            self._log_hand_completion(winner_id, pot_won)
            
            print(f"WINNER: {self.player_names[winner_id]} wins {pot_won} chips")
            
        except Exception as e:
            print(f"Error determining winner: {e}")
    
    def _log_hand_completion(self, winner_id: int, pot_amount: int):
        """Log hand completion with winner and pot info"""
        final_stacks = {}
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'stacks'):
            try:
                final_stacks = {i: int(self.pokerkit_state.stacks[i-1]) for i in range(1, 7)}
            except:
                final_stacks = self.player_stacks
        
        completion_info = {
            "type": "hand_completion",
            "winner_id": winner_id,
            "winner_name": self.player_names[winner_id],
            "pot_amount": pot_amount,
            "final_stacks": final_stacks,
            "timestamp": datetime.now().isoformat()
        }
        self.detailed_log.append(completion_info)
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state as a dictionary"""
        from dataclasses import asdict
        
        # Update state before returning
        self.state = self._create_api_state()
        
        # Serialize players with hole_cards as strings
        players_data = []
        for player in self.state.players:
            player_dict = asdict(player)
            player_dict['hole_cards'] = [str(card) for card in player.hole_cards]
            players_data.append(player_dict)
        
        # Serialize community cards as strings
        community_cards_data = [str(card) for card in self.state.community_cards]
        
        # Serialize actions
        actions_data = [asdict(action) for action in self.state.actions]
        
        return {
            'id': self.state.id,
            'players': players_data,
            'community_cards': community_cards_data,
            'pot': self.state.pot,
            'current_bet': self.state.current_bet,
            'stage': self.state.stage.value,
            'dealer_position': self.state.dealer_position,
            'current_player': self.state.current_player,
            'actions': actions_data,
            'small_blind': self.state.small_blind,
            'big_blind': self.state.big_blind,
            'is_finished': self.state.is_finished,
            'winner_id': self.state.winner_id,
            'winner_reason': self.state.winner_reason,
            'created_at': self.state.created_at.isoformat(),
            'detailed_log': self.detailed_log
        }
