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
            
            # Store initial player positions when bets are available
            self._store_initial_positions()
            
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
    
    def _store_initial_positions(self):
        """Store player positions when game starts and bet data is available"""
        self.player_positions = {
            'dealer': None,
            'small_blind': None,
            'big_blind': None
        }
        
        try:
            if self.pokerkit_state and hasattr(self.pokerkit_state, 'bets') and self.pokerkit_state.bets:
                # Find positions based on initial bet amounts
                for i, bet in enumerate(self.pokerkit_state.bets):
                    bet_amount = int(bet)
                    player_id = i + 1
                    
                    if bet_amount == 20:  # Small blind
                        self.player_positions['small_blind'] = player_id
                    elif bet_amount == 40:  # Big blind
                        self.player_positions['big_blind'] = player_id
                
                # Calculate dealer position (1 position before small blind)
                if self.player_positions['small_blind'] is not None:
                    sb_index = self.player_positions['small_blind'] - 1  # Convert to 0-based
                    dealer_index = (sb_index - 1) % 6  # 1 position before SB
                    self.player_positions['dealer'] = dealer_index + 1  # Convert back to 1-based
                
        except Exception as e:
            print(f"Error storing initial positions: {e}")
            import traceback
            traceback.print_exc()
    
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
            

            
            # Determine player positions using stored positions (captured at game start)
            is_dealer = False
            is_small_blind = False
            is_big_blind = False
            
            # Use stored positions if available
            if hasattr(self, 'player_positions') and self.player_positions:
                if self.player_positions['dealer'] == player_id:
                    is_dealer = True
                elif self.player_positions['small_blind'] == player_id:
                    is_small_blind = True
                elif self.player_positions['big_blind'] == player_id:
                    is_big_blind = True
            
            # Fallback: If no stored positions available, try to detect from current state
            # (This should rarely happen since positions are stored at game start)
            if not (is_dealer or is_small_blind or is_big_blind):
                if player_id == 1:  # Only log once
                    print(f"Warning: No stored positions found, using fallback detection")
            
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
                current_player = self.pokerkit_state.actor_index + 1
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
        
        # Determine dealer position dynamically
        dealer_position = 0  # Default
        for player in players:
            if player.is_dealer:
                dealer_position = player.id
                break
        
        # Preserve existing actions if state already exists
        existing_actions = []
        existing_winner_id = None
        existing_winner_reason = ""
        existing_created_at = datetime.now()
        
        if hasattr(self, 'state') and self.state:
            existing_actions = getattr(self.state, 'actions', [])
            existing_winner_id = getattr(self.state, 'winner_id', None)
            existing_winner_reason = getattr(self.state, 'winner_reason', "")
            existing_created_at = getattr(self.state, 'created_at', datetime.now())
        
        return GameState(
            id=self.game_id,
            players=players,
            community_cards=community_cards,
            pot=pot,
            current_bet=current_bet,
            stage=stage,
            dealer_position=dealer_position,
            current_player=current_player,
            actions=existing_actions,  # Preserve existing actions
            small_blind=20,
            big_blind=40,
            is_finished=is_finished,
            winner_id=existing_winner_id,  # Preserve winner info
            winner_reason=existing_winner_reason,
            created_at=existing_created_at  # Preserve creation time
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
        if not self.pokerkit_state:
            return False
        
        player_index = player_id - 1  # Convert to 0-based indexing
        
        # Verify it's this player's turn
        try:
            current_actor = getattr(self.pokerkit_state, 'actor_index', None)
            
            if current_actor != player_index:
                return False
        except Exception as turn_error:
            print(f"Error checking player turn: {turn_error}")
            return False
        
        try:
            # Execute action using PokerKit
            if action == ActionType.FOLD:
                if self.pokerkit_state.can_fold():
                    self.pokerkit_state.fold()
                    self._log_action(player_id, "fold")
                else:
                    return False
                    
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
                    else:
                        return False
                else:
                    return False
                    
            elif action == ActionType.CALL:
                if self.pokerkit_state.can_check_or_call():
                    call_amount = 0
                    if hasattr(self.pokerkit_state, 'checking_or_calling_amount'):
                        call_amount = self.pokerkit_state.checking_or_calling_amount
                    self.pokerkit_state.check_or_call()
                    self._log_action(player_id, "call", call_amount)
                else:
                    return False
                    
            elif action in [ActionType.BET, ActionType.RAISE]:
                if hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to'):
                    if self.pokerkit_state.can_complete_bet_or_raise_to(amount):
                        self.pokerkit_state.complete_bet_or_raise_to(amount)
                        action_name = "bet" if action == ActionType.BET else "raise"
                        self._log_action(player_id, action_name, amount)
                    else:
                        return False
                else:
                    return False
                    
            elif action == ActionType.ALL_IN:
                if hasattr(self.pokerkit_state, 'stacks'):
                    all_in_amount = self.pokerkit_state.stacks[player_index]
                    if (all_in_amount > 0 and 
                        hasattr(self.pokerkit_state, 'can_complete_bet_or_raise_to') and
                        self.pokerkit_state.can_complete_bet_or_raise_to(all_in_amount)):
                        self.pokerkit_state.complete_bet_or_raise_to(all_in_amount)
                        self._log_action(player_id, "all_in", all_in_amount)
                    else:
                        return False
                else:
                    return False
            else:
                return False
            
            # Update our API state
            self.state = self._create_api_state()
            
            # Check if we need to deal community cards or finish the hand
            self._handle_automatic_progression()
            
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
            # Check multiple conditions for game completion
            game_should_end = False
            
            # Condition 1: PokerKit status indicates completion
            if hasattr(self.pokerkit_state, 'status') and not self.pokerkit_state.status:
                game_should_end = True
            
            # Condition 2: No more actions possible (all players folded except one)
            active_players = 0
            for i in range(6):
                if hasattr(self.pokerkit_state, 'statuses') and self.pokerkit_state.statuses:
                    try:
                        if self.pokerkit_state.statuses[i] != 0:  # Player is still active
                            active_players += 1
                    except:
                        pass
            
            if active_players <= 1:
                game_should_end = True
            
            # Condition 3: River completed and no more betting rounds
            board_count = len(self.pokerkit_state.board_cards) if hasattr(self.pokerkit_state, 'board_cards') and self.pokerkit_state.board_cards else 0
            if board_count >= 5:  # River completed
                # Check if no more actions are possible
                can_act = False
                if hasattr(self.pokerkit_state, 'actor_index') and self.pokerkit_state.actor_index is not None:
                    can_act = True
                
                if not can_act:
                    game_should_end = True
            
            if game_should_end:
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
            
            print(f"DEBUG: PokerKit statuses: {getattr(self.pokerkit_state, 'statuses', 'Not available')}")
            print(f"DEBUG: PokerKit hole_cards length: {len(getattr(self.pokerkit_state, 'hole_cards', []))}")
            
            for i in range(6):
                has_cards = (hasattr(self.pokerkit_state, 'hole_cards') and 
                            self.pokerkit_state.hole_cards and 
                            i < len(self.pokerkit_state.hole_cards) and
                            self.pokerkit_state.hole_cards[i] and
                            len(self.pokerkit_state.hole_cards[i]) == 2)
                
                if has_cards:
                    # Check if player is still active (not folded)
                    # Default to FOLDED for safety - only mark active if we can confirm they're not folded
                    is_active = False
                    
                    if hasattr(self.pokerkit_state, 'statuses') and self.pokerkit_state.statuses:
                        try:
                            if i < len(self.pokerkit_state.statuses):
                                # In PokerKit, status != 0 means active (not folded)
                                is_active = self.pokerkit_state.statuses[i] != 0
                                print(f"DEBUG: Player {i+1} status: {self.pokerkit_state.statuses[i]}, active: {is_active}")
                            else:
                                print(f"DEBUG: Player {i+1} index out of range for statuses")
                        except Exception as e:
                            print(f"DEBUG: Error checking status for player {i+1}: {e}")
                            is_active = False  # Default to folded on error
                    else:
                        print(f"DEBUG: No statuses available, checking our internal fold tracking")
                        # Fallback: check our internal game state for fold status
                        if i < len(self.state.players):
                            is_active = not self.state.players[i].is_folded
                            print(f"DEBUG: Player {i+1} internal fold status: {self.state.players[i].is_folded}, active: {is_active}")
                    
                    if is_active:
                        active_players.append(i)
                        print(f"DEBUG: Added Player {i+1} to active players")
                    else:
                        print(f"DEBUG: Player {i+1} is folded, not adding to active players")
            
            if not active_players:
                print("No active players found for winner determination")
                return
            
            print(f"DEBUG: Active players: {[p+1 for p in active_players]}")
            
            # If only one active player, they win by default
            if len(active_players) == 1:
                winner_index = active_players[0]
                winner_id = winner_index + 1
            else:
                # Multiple active players - use PokerKit's native winner determination
                winner_index = self._evaluate_showdown_with_pokerkit(active_players)
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
            self.state.pot = pot_amount  # ✅ FIX: Store the actual pot amount in game state
            self.state.is_finished = True
            self.state.stage = GameStage.FINISHED
            
            print(f"GAME MARKED AS FINISHED: winner_id={winner_id}, pot_amount={pot_amount}")
            print(f"Game state is_finished: {self.state.is_finished}")
            print(f"Game state pot: {self.state.pot}")
            
            # Update player stacks in game state to match PokerKit + winner adjustment
            for i in range(6):
                self.state.players[i].stack = self.player_stacks[i + 1]
            
            # Refresh the entire game state to ensure position data is current
            self.state = self._create_api_state()
            # Re-apply the winner and finish state (since _create_api_state might reset these)
            self.state.winner_id = winner_id
            self.state.winner_reason = f"{self.player_names[winner_id]} wins the hand"
            self.state.pot = pot_amount
            self.state.is_finished = True
            self.state.stage = GameStage.FINISHED
            

            
            self._log_hand_completion(winner_id, pot_amount)
            print(f"WINNER: {self.player_names[winner_id]} wins {pot_amount} chips")
            
        except Exception as e:
            print(f"Error determining winner: {e}")
            import traceback
            traceback.print_exc()
            
    def _evaluate_showdown_with_pokerkit(self, active_player_indices: List[int]) -> int:
        """Use PokerKit to evaluate the showdown and determine the winner"""
        print(f"DEBUG: _evaluate_showdown_with_pokerkit called with active players: {active_player_indices}")
        try:
            # Check if we have board cards
            has_board_cards_attr = hasattr(self.pokerkit_state, 'board_cards')
            board_cards = self.pokerkit_state.board_cards if has_board_cards_attr else None
            print(f"DEBUG: has_board_cards_attr: {has_board_cards_attr}, board_cards: {board_cards}")
            
            # Special case for preflop all-in (no community cards)
            if has_board_cards_attr and not board_cards:
                # Use PokerKit's native all-in evaluation capabilities
                try:
                    # Look for showdown-related methods
                    pokerkit_attrs = [attr for attr in dir(self.pokerkit_state) if not attr.startswith('_')]
                    showdown_attrs = [attr for attr in pokerkit_attrs if 'showdown' in attr.lower()]
                    
                    # Use showdown_indices for PokerKit-native winner determination
                    for attr in showdown_attrs:
                        if hasattr(self.pokerkit_state, attr):
                            attr_value = getattr(self.pokerkit_state, attr)
                            
                            # Use showdown_indices - PokerKit's internal hand strength ordering
                            if attr == 'showdown_indices' and attr_value:
                                # Find the first player in showdown_indices who is also active
                                for showdown_player in attr_value:
                                    if showdown_player in active_player_indices:
                                        return showdown_player + 1  # Convert to 1-indexed
                    

                    
                    # Fallback: Check payoffs for winner determination
                    if hasattr(self.pokerkit_state, 'payoffs') and self.pokerkit_state.payoffs:
                        payoffs = self.pokerkit_state.payoffs
                        if payoffs and len(payoffs) > 0:
                            best_payoff = max(payoffs)
                            if best_payoff > 0:
                                for i, payoff in enumerate(payoffs):
                                    if payoff == best_payoff and i in active_player_indices:
                                        return i + 1
                    
                except Exception:
                    # Fall through to standard evaluation
                    pass
            
            # Standard evaluation for non-preflop or if preflop evaluation failed
            # Try to use PokerKit's showdown_winners if available
            if hasattr(self.pokerkit_state, 'showdown_winners') and self.pokerkit_state.showdown_winners:
                winners = self.pokerkit_state.showdown_winners
                
                # Find the first winner that's in our active players list
                for winner_index in winners:
                    if winner_index in active_player_indices:
                        return winner_index + 1  # Convert to 1-indexed
                
                # If no winner found in active players, return first winner
                if winners:
                    return winners[0] + 1  # Convert to 1-indexed
            
            # Fallback: Check payoffs to determine winner
            if hasattr(self.pokerkit_state, 'payoffs') and self.pokerkit_state.payoffs:
                payoffs = self.pokerkit_state.payoffs
                
                # Find player with positive payoff (winner)
                for i, payoff in enumerate(payoffs):
                    if payoff > 0 and i in active_player_indices:
                        return i + 1  # Convert to 1-indexed
            
            # If no winner found, return first active player as fallback
            return active_player_indices[0] + 1  # Convert to 1-indexed
            
        except Exception as e:
            # Fall back to first active player
            return active_player_indices[0] + 1  # Convert to 1-indexed
        

    # Custom preflop all-in evaluation removed - using PokerKit's native functionality
    
    def _calculate_preflop_hand_strength(self, hole_cards):
        """Calculate preflop hand strength using PokerKit card objects"""
        try:
            if not hole_cards or len(hole_cards) != 2:
                return -1
            
            # Convert PokerKit cards to rank values
            rank_values = []
            for card in hole_cards:
                card_str = str(card)
                
                # Extract rank from various PokerKit card string formats
                rank_char = ''
                if '(' in card_str and ')' in card_str:
                    # Format like "EIGHT OF HEARTS (8h)"
                    rank_suit = card_str.split('(')[1].split(')')[0]
                    rank_char = rank_suit[0].upper()
                elif '[' in card_str and ']' in card_str:
                    # Format like "[3s]"
                    rank_suit = card_str.strip('[]')
                    rank_char = rank_suit[0].upper()
                elif len(card_str) >= 1:
                    # Simple format like "8h" or just "8"
                    rank_char = card_str[0].upper()
                
                # Convert rank character to numeric value
                if rank_char == 'A': rank_values.append(14)
                elif rank_char == 'K': rank_values.append(13)
                elif rank_char == 'Q': rank_values.append(12)
                elif rank_char == 'J': rank_values.append(11)
                elif rank_char == 'T': rank_values.append(10)
                elif rank_char.isdigit(): rank_values.append(int(rank_char))
                else:
                    # Try to extract from full card name
                    card_lower = card_str.lower()
                    if 'ace' in card_lower: rank_values.append(14)
                    elif 'king' in card_lower: rank_values.append(13)
                    elif 'queen' in card_lower: rank_values.append(12)
                    elif 'jack' in card_lower: rank_values.append(11)
                    elif 'ten' in card_lower: rank_values.append(10)
                    elif 'nine' in card_lower: rank_values.append(9)
                    elif 'eight' in card_lower: rank_values.append(8)
                    elif 'seven' in card_lower: rank_values.append(7)
                    elif 'six' in card_lower: rank_values.append(6)
                    elif 'five' in card_lower: rank_values.append(5)
                    elif 'four' in card_lower: rank_values.append(4)
                    elif 'three' in card_lower: rank_values.append(3)
                    elif 'two' in card_lower: rank_values.append(2)
            
            if len(rank_values) != 2:
                return -1
            
            # Sort ranks high to low
            rank_values.sort(reverse=True)
            
            # Calculate hand strength
            if rank_values[0] == rank_values[1]:  # Pair
                return 1000 + rank_values[0]  # Pair (e.g. pair of aces = 1014)
            else:  # High card
                return (rank_values[0] * 15) + rank_values[1]  # High card (e.g. AK = 14*15+13 = 223)
                
        except Exception as e:
            print(f"DEBUG: Error calculating preflop hand strength: {e}")
            return -1
    
    # PokerKit-only evaluation methods below

    def _pokerkit_card_to_api_card(self, pokerkit_card):
        """Convert a PokerKit card to our API card format"""
        try:
            card_str = str(pokerkit_card)
            
            # Extract rank and suit from the card string
            if '(' in card_str and ')' in card_str:
                # Format like "EIGHT OF HEARTS (8h)"
                rank_suit = card_str.split('(')[1].split(')')[0]
                rank_char = rank_suit[0].upper()
                suit_char = rank_suit[1].lower()
            elif '[' in card_str and ']' in card_str:
                # Format like "[3s]"
                rank_suit = card_str.strip('[]')
                rank_char = rank_suit[0].upper()
                suit_char = rank_suit[1].lower()
            elif len(card_str) >= 2:
                # Simple format like "8h"
                rank_char = card_str[0].upper()
                suit_char = card_str[1].lower()
            else:
                return None
            
            # Map rank character to our Rank enum
            rank_map = {
                '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
                '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
                'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 'K': Rank.KING, 'A': Rank.ACE
            }
            
            # Map suit character to our Suit enum
            suit_map = {
                's': Suit.SPADES, 'h': Suit.HEARTS, 'd': Suit.DIAMONDS, 'c': Suit.CLUBS
            }
            
            if rank_char not in rank_map or suit_char not in suit_map:
                return None
                
            return Card(rank=rank_map[rank_char], suit=suit_map[suit_char])
            
        except Exception as e:
            return None

    # Manual hand evaluation methods removed - using PokerKit-only evaluation
    def _log_action(self, player_id: int, action: str, amount: int = 0):
        """Log player action for hand history tracking"""
        try:
            # Create action record using existing PlayerAction dataclass
            action_type = ActionType(action)  # Convert string to ActionType enum
            action_record = PlayerAction(
                player_id=player_id,
                action=action_type,
                amount=amount,
                timestamp=datetime.now()
            )
            
            # Add to game state actions
            self.state.actions.append(action_record)
            
        except Exception as e:
            print(f"ERROR in _log_action: {e}")
        
        # Also add to detailed log for play log display
        player_name = self.player_names.get(player_id, f"Player {player_id}")
        if amount > 0:
            self.detailed_log.append({
                'type': 'player_action',
                'player_name': player_name,
                'action': action,
                'amount': amount
            })
        else:
            self.detailed_log.append({
                'type': 'player_action', 
                'player_name': player_name,
                'action': action,
                'amount': 0
            })
    
    def _log_hand_completion(self, winner_id: int, pot_amount: int):
        """Log hand completion with winner and pot info"""
        self.detailed_log.append(f"Final pot was {pot_amount}")
        self.detailed_log.append(f"Player {winner_id} calls")
        self.detailed_log.append(f"Hand #{self.game_id[:8]}-{datetime.now().strftime('%m%d%Y')}-{datetime.now().strftime('%H%M')} ended")
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state as a dictionary"""
        from dataclasses import asdict
        
        # Update our API state (but preserve finished state and actions if already set)
        if not self.state.is_finished:
            # Preserve existing actions before recreating state
            existing_actions = self.state.actions if hasattr(self.state, 'actions') else []
            
            self.state = self._create_api_state()
            
            # Restore preserved actions
            self.state.actions = existing_actions
        
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
                        if stage.lower() == 'flop':
                            detailed_log_strings.append(f"Flop cards dealt: {''.join(community_cards)}")
                        elif stage.lower() == 'turn':
                            # For turn, show only the new card (4th card)
                            if len(community_cards) >= 4:
                                detailed_log_strings.append(f"Turn card dealt: {community_cards[3]}")
                        elif stage.lower() == 'river':
                            # For river, show only the new card (5th card)
                            if len(community_cards) >= 5:
                                detailed_log_strings.append(f"River card dealt: {community_cards[4]}")
                        else:
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
    

