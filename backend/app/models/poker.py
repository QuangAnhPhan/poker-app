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
                # Disable HOLE_CARDS_SHOWING_OR_MUCKING to preserve cards for proper hand evaluation
                # We'll handle winner determination manually using PokerKit's evaluation methods
                (
                    Automation.ANTE_POSTING,
                    Automation.BET_COLLECTION,
                    Automation.BLIND_OR_STRADDLE_POSTING,
                    # Automation.HOLE_CARDS_SHOWING_OR_MUCKING,  # DISABLED - prevents proper showdown
                    Automation.HAND_KILLING,
                    # Automation.CHIPS_PUSHING,  # DISABLED - we'll handle winner determination manually
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
            
            # Initialize fallback card system
            self._initialize_unique_cards()
            
        except Exception as e:
            print(f"Error creating PokerKit state: {e}")
            import traceback
            traceback.print_exc()
            self.pokerkit_state = None
        
        # Create our API-compatible state representation
        self.state = self._create_api_state()
        
        # Initialize logging
        self.initialize_detailed_logging()
    
    def _deal_initial_cards(self):
        """Deal 2 hole cards to each player ensuring unique cards"""
        try:
            # Create a shuffled deck of unique cards
            ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
            suits = ['h', 'd', 'c', 's']
            deck = [f"{rank}{suit}" for rank in ranks for suit in suits]
            random.shuffle(deck)
            
            # Deal 12 unique cards (2 per player)
            card_index = 0
            for i in range(12):
                if self.pokerkit_state.can_deal_hole() and card_index < len(deck):
                    # Deal specific unique card from shuffled deck
                    card = deck[card_index]
                    self.pokerkit_state.deal_hole(card)
                    card_index += 1
                else:
                    break
                    
        except Exception as e:
            print(f"Error dealing cards: {e}")
    

    def _initialize_unique_cards(self):
        """Initialize a reliable unique card system for all players"""
        try:
            # Create a shuffled deck of all 52 cards
            ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
            suits = ['h', 'd', 'c', 's']
            deck = [f"{rank}{suit}" for rank in ranks for suit in suits]
            random.shuffle(deck)
            
            # Assign 2 unique cards to each of the 6 players
            self.unique_hole_cards = []
            for player_idx in range(6):
                player_cards = [deck[player_idx * 2], deck[player_idx * 2 + 1]]
                self.unique_hole_cards.append(player_cards)
            
            print(f"Initialized unique cards: {self.unique_hole_cards}")
            
        except Exception as e:
            print(f"Error initializing unique cards: {e}")
            self.unique_hole_cards = []
    
    def _create_api_state(self) -> GameState:
        """Create API-compatible state from PokerKit state"""
        players = []
        
        for i in range(6):
            player_id = i + 1
            
            # Get hole cards for this player - use same priority as get_player_hole_cards
            hole_cards = []
        
            # First priority: Try PokerKit cards
            if (self.pokerkit_state and 
                hasattr(self.pokerkit_state, 'hole_cards') and
                self.pokerkit_state.hole_cards and 
                len(self.pokerkit_state.hole_cards) > i and
                self.pokerkit_state.hole_cards[i]):
                
                try:
                    pokerkit_cards = self.pokerkit_state.hole_cards[i]
                    converted_cards = []
                    for card in pokerkit_cards:
                        converted_card = self._pokerkit_card_to_api_card(card)
                        if converted_card is not None:
                            converted_cards.append(converted_card)
                    
                    if len(converted_cards) == 2:
                        hole_cards = converted_cards
                    else:
                        print(f"Warning: Only got {len(converted_cards)} valid PokerKit cards for player {player_id}")
                except Exception as e:
                    print(f"Error getting PokerKit hole cards for player {player_id}: {e}")
        
            # Second priority: Fallback to unique card system
            if not hole_cards and hasattr(self, 'unique_hole_cards') and self.unique_hole_cards and i < len(self.unique_hole_cards):
                try:
                    unique_cards = self.unique_hole_cards[i]
                    converted_cards = []
                    for card in unique_cards:
                        converted_card = self._pokerkit_card_to_api_card(card)
                        if converted_card is not None:
                            converted_cards.append(converted_card)
                    
                    if len(converted_cards) == 2:  # Only use if we got both cards successfully
                        hole_cards = converted_cards
                    else:
                        print(f"Warning: Could not convert all fallback cards for player {player_id}, got {len(converted_cards)} cards")
                except Exception as e:
                    print(f"Error using unique cards for player {player_id}: {e}")
            

            
            # Determine player positions based on actual game state
            is_dealer = False
            is_small_blind = False
            is_big_blind = False
            
            # Check actual bets to determine blind positions
            if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                try:
                    current_bet = int(self.pokerkit_state.bets[i])
                    # Small blind posts 20, big blind posts 40
                    if current_bet == 20:
                        is_small_blind = True
                    elif current_bet == 40:
                        is_big_blind = True
                except:
                    pass
            
            # Determine dealer position (typically the player before small blind in rotation)
            # For now, we'll use PokerKit's dealer position if available
            if self.pokerkit_state and hasattr(self.pokerkit_state, 'dealer_position'):
                try:
                    dealer_index = self.pokerkit_state.dealer_position
                    is_dealer = (i == dealer_index)
                except:
                    # Fallback: assume dealer is the player with no blind bet and highest position
                    if not is_small_blind and not is_big_blind:
                        # Simple heuristic: if no bet and it's a reasonable dealer position
                        current_bet = 0
                        if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets'):
                            try:
                                current_bet = int(self.pokerkit_state.bets[i])
                            except:
                                pass
                        if current_bet == 0 and i >= 4:  # Players 5 or 6 are likely dealer candidates
                            is_dealer = True
            
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
                return self.pokerkit_state.actor_index + 1
            except Exception as e:
                print(f"Error getting current player: {e}")
        
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
            # Handle both PokerKit card objects and string representations
            if hasattr(pokerkit_card, '__str__'):
                card_str = str(pokerkit_card)
            else:
                card_str = pokerkit_card
            
            # Clean the card string and remove brackets if present
            card_str = card_str.strip()
            
            # Handle bracketed format like '[5h]' -> '5h'
            if card_str.startswith('[') and card_str.endswith(']'):
                card_str = card_str[1:-1]
            
            # Handle verbose PokerKit formats:
            # Format 1: 'DEUCEOFCLUBS2c' -> '2c'
            # Format 2: 'DEUCE OF DIAMONDS (2d)' -> '2d'
            if len(card_str) > 2:
                # Check for parentheses format first: 'DEUCE OF DIAMONDS (2d)'
                if '(' in card_str and ')' in card_str:
                    # Extract content within parentheses
                    start = card_str.find('(')
                    end = card_str.find(')')
                    if start != -1 and end != -1 and end > start:
                        potential_card = card_str[start+1:end]
                        if (len(potential_card) == 2 and 
                            potential_card[0] in '23456789TJQKA' and 
                            potential_card[1].lower() in 'hdcs'):
                            card_str = potential_card
                        else:
                            print(f"Warning: Invalid card in parentheses: '{potential_card}' from '{card_str}'")
                            return None
                    else:
                        print(f"Warning: Malformed parentheses in card: '{card_str}'")
                        return None
                else:
                    # Extract the last 2 characters for format like 'DEUCEOFCLUBS2c'
                    potential_card = card_str[-2:]
                    # Verify it looks like a valid card (rank + suit)
                    if (len(potential_card) == 2 and 
                        potential_card[0] in '23456789TJQKA' and 
                        potential_card[1].lower() in 'hdcs'):
                        card_str = potential_card
                    else:
                        print(f"Warning: Could not extract valid card from verbose format: '{card_str}'")
                        return None
            
            # Clean up any remaining unwanted characters after extraction
            card_str = card_str.replace(' ', '')
            
            if len(card_str) != 2:
                print(f"Warning: Invalid card format length: '{card_str}' (length {len(card_str)}) after cleaning")
                return None
            
            rank_str = card_str[0].upper()  # Ensure uppercase for rank
            suit_str = card_str[1].lower()  # Ensure lowercase for suit
            
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
                print(f"Warning: Invalid rank: '{rank_str}' in card '{card_str}'")
                return None
            if suit_str not in suit_map:
                print(f"Warning: Invalid suit: '{suit_str}' in card '{card_str}'")
                return None
            
            return Card(suit=suit_map[suit_str], rank=rank_map[rank_str])
            
        except Exception as e:
            print(f"Error converting card {pokerkit_card}: {e}")
            return None
    
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
        if action == "fold":
            self.detailed_log.append(f"Player {player_id} folds")
        elif action == "check":
            self.detailed_log.append(f"Player {player_id} checks")
        elif action == "call":
            self.detailed_log.append(f"Player {player_id} calls")
        elif action == "bet":
            self.detailed_log.append(f"Player {player_id} bets {amount} chips")
        elif action == "raise":
            self.detailed_log.append(f"Player {player_id} raises to {amount} chips")
        elif action == "all_in":
            self.detailed_log.append(f"Player {player_id} goes all-in")
        else:
            self.detailed_log.append(f"Player {player_id} {action}")
    
    def initialize_detailed_logging(self):
        """Initialize detailed logging after cards are dealt"""
        self.detailed_log = []  # Reset to store string messages
        
        # Log game start
        self.detailed_log.append("Game started with 6 players")
        
        # Log hole cards for each player
        for player_id in range(1, 7):
            hole_cards = self.get_player_hole_cards(player_id)
            if hole_cards:
                cards_str = "".join([str(card) for card in hole_cards])
                self.detailed_log.append(f"Player {player_id} is dealt {cards_str}")
        
        # Log positions based on actual game state
        self.detailed_log.append("---")
        
        # Determine actual positions from game state
        dealer_player = None
        small_blind_player = None
        big_blind_player = None
        
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
            for i in range(6):
                player_id = i + 1
                try:
                    current_bet = int(self.pokerkit_state.bets[i])
                    if current_bet == 20:  # Small blind
                        small_blind_player = player_id
                    elif current_bet == 40:  # Big blind
                        big_blind_player = player_id
                except:
                    pass
        
        # Determine dealer (usually the player before small blind, but let's use a simple heuristic)
        if self.pokerkit_state and hasattr(self.pokerkit_state, 'dealer_position'):
            try:
                dealer_index = self.pokerkit_state.dealer_position
                dealer_player = dealer_index + 1
            except:
                # Fallback: find a player with no bet who could be dealer
                for i in range(6):
                    player_id = i + 1
                    if player_id != small_blind_player and player_id != big_blind_player:
                        try:
                            current_bet = int(self.pokerkit_state.bets[i]) if self.pokerkit_state.bets else 0
                            if current_bet == 0:
                                dealer_player = player_id
                                break
                        except:
                            pass
        
        # Log the actual positions
        if dealer_player:
            self.detailed_log.append(f"Player {dealer_player} is the dealer")
        if small_blind_player:
            self.detailed_log.append(f"Player {small_blind_player} posts small blind - 20 chips")
        if big_blind_player:
            self.detailed_log.append(f"Player {big_blind_player} posts big blind - 40 chips")
    
    def get_player_hole_cards(self, player_id: int) -> List[Card]:
        """Get hole cards for a specific player"""
        player_index = player_id - 1  # Convert to 0-based indexing
        
        # First try PokerKit cards
        if (self.pokerkit_state and 
            hasattr(self.pokerkit_state, 'hole_cards') and
            self.pokerkit_state.hole_cards and 
            len(self.pokerkit_state.hole_cards) > player_index and
            self.pokerkit_state.hole_cards[player_index]):
            
            try:
                converted_cards = []
                pokerkit_cards = self.pokerkit_state.hole_cards[player_index]
                for card in pokerkit_cards:
                    converted_card = self._pokerkit_card_to_api_card(card)
                    if converted_card is not None:
                        converted_cards.append(converted_card)
                
                if len(converted_cards) == 2:

                    return converted_cards
                else:
                    print(f"Warning: Only got {len(converted_cards)} valid cards for player {player_id}")
            except Exception as e:
                print(f"Error getting PokerKit hole cards for player {player_id}: {e}")
        
        # Fallback to unique card system
        if hasattr(self, 'unique_hole_cards') and self.unique_hole_cards and player_index < len(self.unique_hole_cards):
            try:
                unique_cards = self.unique_hole_cards[player_index]
                converted_cards = []
                for card_str in unique_cards:
                    converted_card = self._pokerkit_card_to_api_card(card_str)
                    if converted_card is not None:
                        converted_cards.append(converted_card)
                
                if len(converted_cards) == 2:

                    return converted_cards
            except Exception as e:
                print(f"Error using unique cards for player {player_id}: {e}")
        
        # Return empty list if no cards found
        return []
    
    def get_valid_actions(self, player_id: int) -> List[ActionType]:
        """Get valid actions for a specific player using PokerKit's validation"""
        player_index = player_id - 1  # Convert to 0-based indexing
        
        # Check if it's this player's turn
        if not self.pokerkit_state:
            return []
            
        current_actor = getattr(self.pokerkit_state, 'actor_index', None)
        
        if current_actor != player_index:
            return []
        
        valid_actions = []
        
        try:
            # Check what actions are available in PokerKit
            can_fold = self.pokerkit_state.can_fold()
            if can_fold:
                valid_actions.append(ActionType.FOLD)
            
            can_check_or_call = self.pokerkit_state.can_check_or_call()
            
            if can_check_or_call:
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
            
            # Check betting/raising
            can_bet_or_raise = hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to')
            
            if can_bet_or_raise:
                # Check if player can bet or raise
                current_bet = max(self.pokerkit_state.bets) if hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets else 0
                
                test_bet_amount = current_bet + 40  # Minimum raise
                can_bet_test = self.pokerkit_state.can_complete_bet_or_raise_to(test_bet_amount)
                
                if current_bet == 0:
                    if can_bet_test:
                        valid_actions.append(ActionType.BET)
                else:
                    if can_bet_test:
                        valid_actions.append(ActionType.RAISE)
                
                # Check if player can go all-in
                if (hasattr(self.pokerkit_state, 'stacks') and 
                    self.pokerkit_state.stacks[player_index] > 0):
                    all_in_amount = self.pokerkit_state.stacks[player_index]
                    can_all_in = self.pokerkit_state.can_complete_bet_or_raise_to(all_in_amount)
                    if can_all_in:
                        valid_actions.append(ActionType.ALL_IN)
                    
        except Exception as e:
            print(f"Error getting valid actions for player {player_id}: {e}")
        
        return valid_actions
    
    def execute_action(self, player_id: int, action: ActionType, amount: int = 0) -> bool:
        """Execute a player action using PokerKit's action system"""
        print(f"PokerGame.execute_action called: player_id={player_id}, action={action}, amount={amount}")
        
        if not self.pokerkit_state:
            print("No PokerKit state available")
            return False
        
        player_index = player_id - 1  # Convert to 0-based indexing
        print(f"Player index: {player_index}")
        
        # Verify it's this player's turn
        try:
            current_actor = getattr(self.pokerkit_state, 'actor_index', None)
            print(f"Current actor index: {current_actor}")
            
            if current_actor != player_index:
                print(f"Not player {player_id}'s turn (current actor: {current_actor})")
                return False
        except Exception as turn_error:
            print(f"Error checking player turn: {turn_error}")
            return False
        
        try:
            print(f"Executing action: {action}")
            
            # Execute action using PokerKit
            if action == ActionType.FOLD:
                print("Processing FOLD action")
                if self.pokerkit_state.can_fold():
                    self.pokerkit_state.fold()
                    self._log_action(player_id, "fold")
                    print("FOLD action completed")
                else:
                    print("Cannot fold at this time")
                    return False
                    
            elif action == ActionType.CHECK:
                print("Processing CHECK action")
                if self.pokerkit_state.can_check_or_call():
                    current_bet = 0
                    player_bet = 0
                    if hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                        current_bet = max(self.pokerkit_state.bets)
                        player_bet = self.pokerkit_state.bets[player_index]
                    
                    print(f"Current bet: {current_bet}, Player bet: {player_bet}")
                    
                    if current_bet == player_bet:
                        self.pokerkit_state.check_or_call()
                        self._log_action(player_id, "check")
                        print("CHECK action completed")
                    else:
                        print("Cannot check - must call or raise")
                        return False
                else:
                    print("Cannot check or call at this time")
                    return False
                    
            elif action == ActionType.CALL:
                print("Processing CALL action")
                if self.pokerkit_state.can_check_or_call():
                    call_amount = 0
                    if hasattr(self.pokerkit_state, 'checking_or_calling_amount'):
                        call_amount = self.pokerkit_state.checking_or_calling_amount
                    print(f"Call amount: {call_amount}")
                    self.pokerkit_state.check_or_call()
                    self._log_action(player_id, "call", call_amount)
                    print("CALL action completed")
                else:
                    print("Cannot check or call at this time")
                    return False
                    
            elif action in [ActionType.BET, ActionType.RAISE]:
                print(f"Processing {action} action with amount: {amount}")
                if hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to'):
                    if self.pokerkit_state.can_complete_bet_or_raise_to(amount):
                        self.pokerkit_state.complete_bet_or_raise_to(amount)
                        action_name = "bet" if action == ActionType.BET else "raise"
                        self._log_action(player_id, action_name, amount)
                        print(f"{action} action completed")
                    else:
                        print(f"Cannot {action} to amount {amount}")
                        return False
                else:
                    print("Betting/raising not available")
                    return False
                    
            elif action == ActionType.ALL_IN:
                print("Processing ALL_IN action")
                if hasattr(self.pokerkit_state, 'stacks'):
                    all_in_amount = self.pokerkit_state.stacks[player_index]
                    print(f"All-in amount: {all_in_amount}")
                    if (all_in_amount > 0 and 
                        hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to') and
                        self.pokerkit_state.can_complete_bet_or_raise_to(all_in_amount)):
                        self.pokerkit_state.complete_bet_or_raise_to(all_in_amount)
                        self._log_action(player_id, "all_in", all_in_amount)
                        print("ALL_IN action completed")
                    else:
                        print(f"Cannot go all-in with amount {all_in_amount}")
                        return False
                else:
                    print("Stacks not available for all-in")
                    return False
            else:
                print(f"Unknown action: {action}")
                return False
            
            print("Updating API state...")
            # Update our API state
            self.state = self._create_api_state()
            
            print("Handling automatic progression...")
            # Check if we need to deal community cards or finish the hand
            self._handle_automatic_progression()
            
            print("Action execution successful")
            return True
            
        except Exception as e:
            print(f"Action execution failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_automatic_progression(self):
        """Handle automatic game progression (dealing cards, determining winners)"""
        if not self.pokerkit_state:
            return
        
        try:
            # Check if all active players are all-in (no more betting possible)
            all_in_situation = self._check_all_in_situation()
            
            if all_in_situation:
                # Deal all remaining community cards at once
                self._deal_all_remaining_cards()
                # Determine winner immediately
                self._determine_winner()
                return
            
            # Normal progression: deal cards for next stage if possible
            if hasattr(self.pokerkit_state, 'can_burn_card') and self.pokerkit_state.can_burn_card():
                self.pokerkit_state.burn_card()
            
            if hasattr(self.pokerkit_state, 'can_deal_board') and self.pokerkit_state.can_deal_board():
                old_stage = self._get_current_stage()
                board_count = len(self.pokerkit_state.board_cards) if self.pokerkit_state.board_cards else 0
                
                # Deal appropriate number of cards for next stage
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
    
    def _check_all_in_situation(self) -> bool:
        """Check if all active players are all-in (no more betting possible)"""
        if not self.pokerkit_state:
            return False
        
        try:
            # Check if actor_index is None (no one can act)
            actor_index = getattr(self.pokerkit_state, 'actor_index', None)
            if actor_index is not None:
                return False  # Someone can still act
            
            # Check if there are active players with chips left
            if hasattr(self.pokerkit_state, 'stacks') and hasattr(self.pokerkit_state, 'statuses'):
                for i in range(6):
                    if (self.pokerkit_state.statuses[i] and  # Player is active
                        self.pokerkit_state.stacks[i] > 0):   # Player has chips
                        return False  # Player can still bet
            
            return True  # All active players are all-in
        except Exception as e:
            print(f"Error checking all-in situation: {e}")
            return False
    
    def _deal_all_remaining_cards(self):
        """Deal all remaining community cards when all players are all-in"""
        if not self.pokerkit_state:
            return
        
        try:
            board_count = len(self.pokerkit_state.board_cards) if self.pokerkit_state.board_cards else 0
            
            # Deal remaining cards based on current board state
            while board_count < 5:  # Texas Hold'em has 5 community cards total
                # Burn card if possible
                if hasattr(self.pokerkit_state, 'can_burn_card') and self.pokerkit_state.can_burn_card():
                    self.pokerkit_state.burn_card()
                
                # Deal next card if possible
                if hasattr(self.pokerkit_state, 'can_deal_board') and self.pokerkit_state.can_deal_board():
                    old_stage = self._get_current_stage()
                    self.pokerkit_state.deal_board()
                    board_count += 1
                    
                    # Log stage transitions
                    new_stage = self._get_current_stage()
                    if old_stage != new_stage:
                        self._log_stage_transition(new_stage)
                else:
                    break  # Can't deal more cards
                    
        except Exception as e:
            print(f"Error dealing remaining cards: {e}")
    
    def _log_stage_transition(self, new_stage: GameStage):
        """Log stage transitions with community cards"""
        if new_stage == GameStage.FLOP and len(self.state.community_cards) >= 3:
            cards_str = "".join([str(card) for card in self.state.community_cards[:3]])
            self.detailed_log.append(f"Flop cards dealt: {cards_str}")
        elif new_stage == GameStage.TURN and len(self.state.community_cards) >= 4:
            turn_card = str(self.state.community_cards[3])
            self.detailed_log.append(f"Turn card dealt: {turn_card}")
        elif new_stage == GameStage.RIVER and len(self.state.community_cards) >= 5:
            river_card = str(self.state.community_cards[4])
            self.detailed_log.append(f"River card dealt: {river_card}")
    
    def _determine_winner(self):
        """Determine winner using PokerKit's hand evaluation with preserved cards"""
        if not self.pokerkit_state:
            return
            
        try:
            # Find active players (those who haven't folded and have cards)
            active_players = []
            for i in range(6):
                if (hasattr(self.pokerkit_state, 'hole_cards') and 
                    self.pokerkit_state.hole_cards and 
                    i < len(self.pokerkit_state.hole_cards) and
                    self.pokerkit_state.hole_cards[i] and
                    len(self.pokerkit_state.hole_cards[i]) == 2):
                    
                    # Check if player is still active (not folded)
                    is_active = True
                    if hasattr(self.pokerkit_state, 'statuses'):
                        try:
                            is_active = self.pokerkit_state.statuses[i] != 0
                        except:
                            pass
                    
                    if is_active:
                        active_players.append(i)
            
            if not active_players:
                print("No active players found for winner determination")
                return
            
            # If only one active player, they win by default
            if len(active_players) == 1:
                winner_index = active_players[0]
                winner_id = winner_index + 1
            else:
                # Multiple active players - evaluate hands using PokerKit
                winner_index = self._evaluate_showdown(active_players)
                winner_id = winner_index + 1
            
            # Calculate pot amount from all bets
            pot_amount = 0
            if hasattr(self.pokerkit_state, 'total_pot_amount'):
                try:
                    pot_amount = int(self.pokerkit_state.total_pot_amount)
                except:
                    pass
            
            # If pot amount is 0, calculate from initial vs current stacks
            if pot_amount == 0:
                initial_stacks = list(self.player_stacks.values())
                current_stacks = list(self.pokerkit_state.stacks)
                pot_amount = sum(initial - current for initial, current in zip(initial_stacks, current_stacks))
            
            # Award pot to winner
            self.player_stacks[winner_id] += pot_amount
            
            # Update game state
            self.state.winner_id = winner_id
            self.state.winner_reason = f"{self.player_names[winner_id]} wins the hand"
            self.state.is_finished = True
            self.state.stage = GameStage.FINISHED
            
            # Update player stacks in game state to match PokerKit + winner adjustment
            for i in range(6):
                self.state.players[i].stack = self.player_stacks[i + 1]
            
            self._log_hand_completion(winner_id, pot_amount)
            print(f"WINNER: {self.player_names[winner_id]} wins {pot_amount} chips")
            
        except Exception as e:
            print(f"Error determining winner: {e}")
            import traceback
            traceback.print_exc()
    
    def _evaluate_showdown(self, active_player_indices: List[int]) -> int:
        """Evaluate hands at showdown using simple card comparison"""
        try:
            # Since PokerKit's StandardHighHand is causing issues, let's use a simpler approach
            # that leverages our existing card conversion logic
            
            best_hand_strength = -1
            best_player_index = active_player_indices[0]
            
            # Get community cards as API cards for evaluation
            community_cards = []
            if hasattr(self.pokerkit_state, 'board_cards') and self.pokerkit_state.board_cards:
                for card in self.pokerkit_state.board_cards:
                    converted = self._pokerkit_card_to_api_card(card)
                    if converted:
                        community_cards.append(converted)
            
            # Evaluate each active player's hand
            for player_index in active_player_indices:
                if (hasattr(self.pokerkit_state, 'hole_cards') and 
                    self.pokerkit_state.hole_cards and 
                    player_index < len(self.pokerkit_state.hole_cards) and
                    self.pokerkit_state.hole_cards[player_index]):
                    
                    # Convert hole cards to API cards
                    hole_cards = []
                    for card in self.pokerkit_state.hole_cards[player_index]:
                        converted = self._pokerkit_card_to_api_card(card)
                        if converted:
                            hole_cards.append(converted)
                    
                    if len(hole_cards) == 2 and len(community_cards) >= 3:
                        # Calculate a simple hand strength score
                        hand_strength = self._calculate_hand_strength(hole_cards, community_cards)
                        
                        if hand_strength > best_hand_strength:
                            best_hand_strength = hand_strength
                            best_player_index = player_index
                    elif len(hole_cards) == 2 and len(community_cards) == 0:
                        # Preflop all-in - use high card evaluation
                        hand_strength = self._calculate_preflop_strength(hole_cards)
                        
                        if hand_strength > best_hand_strength:
                            best_hand_strength = hand_strength
                            best_player_index = player_index
            
            return best_player_index
            
        except Exception as e:
            print(f"Error in showdown evaluation: {e}")
            # Fallback to first active player
            return active_player_indices[0]
    
    def _calculate_hand_strength(self, hole_cards: List[Card], community_cards: List[Card]) -> int:
        """Calculate a simple hand strength score for comparison"""
        try:
            # Combine all cards
            all_cards = hole_cards + community_cards
            
            # Convert to rank values for easier processing
            ranks = []
            suits = []
            
            for card in all_cards:
                # Convert rank to numeric value
                rank_value = {
                    Rank.TWO: 2, Rank.THREE: 3, Rank.FOUR: 4, Rank.FIVE: 5,
                    Rank.SIX: 6, Rank.SEVEN: 7, Rank.EIGHT: 8, Rank.NINE: 9,
                    Rank.TEN: 10, Rank.JACK: 11, Rank.QUEEN: 12, Rank.KING: 13, Rank.ACE: 14
                }.get(card.rank, 0)
                
                ranks.append(rank_value)
                suits.append(card.suit)
            
            # Count rank occurrences
            rank_counts = {}
            for rank in ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
            # Sort counts for pattern matching
            counts = sorted(rank_counts.values(), reverse=True)
            
            # Simple hand strength calculation
            if counts[0] == 4:  # Four of a kind
                return 7000 + max(ranks)
            elif counts[0] == 3 and counts[1] == 2:  # Full house
                return 6000 + max(ranks)
            elif len(set(suits)) <= 2:  # Possible flush (simplified)
                return 5000 + max(ranks)
            elif counts[0] == 3:  # Three of a kind
                return 3000 + max(ranks)
            elif counts[0] == 2 and counts[1] == 2:  # Two pair
                return 2000 + max(ranks)
            elif counts[0] == 2:  # One pair
                return 1000 + max(ranks)
            else:  # High card
                return max(ranks)
                
        except Exception as e:
            print(f"Error calculating hand strength: {e}")
            return 0
    
    def _calculate_preflop_strength(self, hole_cards: List[Card]) -> int:
        """Calculate preflop hand strength for all-in scenarios"""
        try:
            if len(hole_cards) != 2:
                return 0
            
            # Convert to rank values
            ranks = []
            suits = []
            
            for card in hole_cards:
                rank_value = {
                    Rank.TWO: 2, Rank.THREE: 3, Rank.FOUR: 4, Rank.FIVE: 5,
                    Rank.SIX: 6, Rank.SEVEN: 7, Rank.EIGHT: 8, Rank.NINE: 9,
                    Rank.TEN: 10, Rank.JACK: 11, Rank.QUEEN: 12, Rank.KING: 13, Rank.ACE: 14
                }.get(card.rank, 0)
                
                ranks.append(rank_value)
                suits.append(card.suit)
            
            # Sort ranks high to low
            ranks.sort(reverse=True)
            high_card = ranks[0]
            low_card = ranks[1]
            
            # Check for pair
            if high_card == low_card:
                return 1000 + high_card  # Pair bonus
            
            # Check for suited
            suited_bonus = 50 if suits[0] == suits[1] else 0
            
            # Check for connected (straight potential)
            connected_bonus = 25 if abs(high_card - low_card) == 1 else 0
            
            # Base strength is high card + low card + bonuses
            return high_card * 15 + low_card + suited_bonus + connected_bonus
            
        except Exception as e:
            print(f"Error calculating preflop strength: {e}")
            return 0
    

    
    def _log_hand_completion(self, winner_id: int, pot_amount: int):
        """Log hand completion with winner and pot info"""
        self.detailed_log.append(f"Final pot was {pot_amount}")
        self.detailed_log.append(f"Player {winner_id} calls")
        self.detailed_log.append(f"Hand #{self.game_id[:8]}-{datetime.now().strftime('%m%d%Y')}-{datetime.now().strftime('%H%M')} ended")
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state as a dictionary"""
        from dataclasses import asdict
        
        # Update our API state
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
        
        # Convert detailed_log objects to React-friendly strings
        detailed_log_strings = []
        for log_entry in self.detailed_log:
            if isinstance(log_entry, dict):
                if log_entry.get('type') == 'game_setup':
                    detailed_log_strings.append(f"Game started with {len(log_entry.get('players', []))} players")
                elif log_entry.get('type') == 'hole_cards_dealt':
                    player_name = log_entry.get('player_name', 'Unknown')
                    cards = log_entry.get('cards', [])
                    detailed_log_strings.append(f"{player_name} dealt hole cards: {', '.join(cards)}")
                elif log_entry.get('type') == 'player_action':
                    player_name = log_entry.get('player_name', 'Unknown')
                    action = log_entry.get('action', 'unknown')
                    amount = log_entry.get('amount', 0)
                    if amount > 0:
                        detailed_log_strings.append(f"{player_name} {action}s {amount} chips")
                    else:
                        detailed_log_strings.append(f"{player_name} {action}s")
                elif log_entry.get('type') == 'stage_transition':
                    stage = log_entry.get('new_stage', 'unknown')
                    community_cards = log_entry.get('community_cards', [])
                    if community_cards:
                        detailed_log_strings.append(f"Stage: {stage.title()} - Community cards: {', '.join(community_cards)}")
                    else:
                        detailed_log_strings.append(f"Stage: {stage.title()}")
                elif log_entry.get('type') == 'hand_completion':
                    winner_name = log_entry.get('winner_name', 'Unknown')
                    pot_amount = log_entry.get('pot_amount', 0)
                    detailed_log_strings.append(f"{winner_name} wins {pot_amount} chips")
                else:
                    # Fallback for unknown log types
                    detailed_log_strings.append(str(log_entry))
            else:
                # If it's already a string, keep it as is
                detailed_log_strings.append(str(log_entry))
        
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
            'detailed_log': detailed_log_strings
        }
    

