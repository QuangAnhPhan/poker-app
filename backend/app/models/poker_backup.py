from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import uuid
from datetime import datetime
import random
from pokerkit import Automation, NoLimitTexasHoldem, Card as PokerKitCard
from pokerkit.state import State


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
    SHOWDOWN = "showdown"
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
    deck: List[Card] = field(default_factory=list)
    actions: List[PlayerAction] = field(default_factory=list)
    small_blind: int = 20
    big_blind: int = 40
    is_finished: bool = False
    winner_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


class Deck:
    def __init__(self):
        self.cards = []
        self.reset()
    
    def reset(self):
        """Create a fresh deck of 52 cards"""
        self.cards = []
        for suit in Suit:
            for rank in Rank:
                self.cards.append(Card(suit=suit, rank=rank))
        self.shuffle()
    
    def shuffle(self):
        """Shuffle the deck"""
        random.shuffle(self.cards)
    
    def deal_card(self) -> Optional[Card]:
        """Deal one card from the deck"""
        if self.cards:
            return self.cards.pop()
        return None
    
    def deal_cards(self, count: int) -> List[Card]:
        """Deal multiple cards from the deck"""
        cards = []
        for _ in range(count):
            card = self.deal_card()
            if card:
                cards.append(card)
        return cards


class PokerKitGameWrapper:
    """Wrapper class to bridge PokerKit's game state with our API interface"""
    
    def __init__(self, player_stacks: Dict[int, int]):
        """Initialize a new poker game using PokerKit"""
        self.game_id = str(uuid.uuid4())
        self.state = GameState(
            id=str(uuid.uuid4()),
            players=[
                Player(
                    id=i,
                    name=f"Player {i}",
                    stack=player_stacks[i],
                    hole_cards=[],
                    current_bet=0,
                    is_folded=False,
                    is_all_in=False,
                    is_dealer=(i == 6),  # Player 6 is dealer
                    is_small_blind=(i == 4),  # Player 4 is small blind
                    is_big_blind=(i == 5)   # Player 5 is big blind
                ) for i in range(1, 7)
            ],
            community_cards=[],
            pot=0,
            current_bet=40,  # Big blind amount
            stage=GameStage.PREFLOP,
            current_player=0,  # Will be set after blinds
            actions=[],
            is_finished=False,
            winner_id=None,
            dealer_position=5  # Player 6 (index 5) is dealer
        )
        self.detailed_log = []  # For detailed play log
        self.deck = Deck()
        self._setup_blinds()
    
    def _log_game_setup(self):
        """Log initial game setup details"""
        # Log player cards
        for player in self.state.players:
            if player.hole_cards:
                cards_str = ' '.join(player.hole_cards)
                self.detailed_log.append(f"Player {player.id} is dealt {cards_str}")
        
        # Log dealer and blinds
        dealer = next(p for p in self.state.players if p.is_dealer)
        small_blind = next(p for p in self.state.players if p.is_small_blind)
        big_blind = next(p for p in self.state.players if p.is_big_blind)
        
        self.detailed_log.append(f"Player {dealer.id} is the dealer")
        self.detailed_log.append(f"Player {small_blind.id} posts small blind - 20 chips")
        self.detailed_log.append(f"Player {big_blind.id} posts big blind - 40 chips")
    
    def _log_action(self, player_id: int, action: str, amount: int = 0):
        """Log detailed player action"""
        player = next(p for p in self.state.players if p.id == player_id)
        
        if action == 'fold':
            self.detailed_log.append(f"Player {player_id} folds")
        elif action == 'check':
            self.detailed_log.append(f"Player {player_id} checks")
        elif action == 'call':
            self.detailed_log.append(f"Player {player_id} calls")
        elif action == 'bet':
            self.detailed_log.append(f"Player {player_id} bets {amount} chips")
        elif action == 'raise':
            self.detailed_log.append(f"Player {player_id} raises to {amount} chips")
        elif action == 'all_in':
            self.detailed_log.append(f"Player {player_id} goes all-in")
    
    def _log_stage_transition(self, new_stage: GameStage):
        """Log stage transitions with community cards"""
        if new_stage == GameStage.FLOP and len(self.state.community_cards) >= 3:
            cards = ' '.join(self.state.community_cards[:3])
            self.detailed_log.append(f"Flop cards dealt: {cards}")
        elif new_stage == GameStage.TURN and len(self.state.community_cards) >= 4:
            card = self.state.community_cards[3]
            self.detailed_log.append(f"Turn card dealt: {card}")
        elif new_stage == GameStage.RIVER and len(self.state.community_cards) >= 5:
            card = self.state.community_cards[4]
            self.detailed_log.append(f"River card dealt: {card}")
    
    def _log_hand_completion(self, winner_id: int, pot_amount: int):
        """Log hand completion with winner and pot info"""
        hand_id = self.state.id[:8]  # First 8 chars of game ID
        self.detailed_log.append(f"Hand #{hand_id} ended")
        self.detailed_log.append(f"Final pot was {pot_amount}")
    
    def initialize_detailed_logging(self):
        """Initialize detailed logging after cards are dealt"""
        # Log player cards
        for player in self.state.players:
            if player.hole_cards:
                # Format cards properly (e.g., "KH 6S" instead of "Rank.KINGH Rank.SIXS")
                cards_str = ' '.join([f"{card.rank.value}{card.suit.value[0].upper()}" for card in player.hole_cards])
                log_entry = f"Player {player.id} is dealt {cards_str}"
                self.detailed_log.append(log_entry)
        
        # Log dealer and blinds
        dealer = next((p for p in self.state.players if p.is_dealer), None)
        small_blind = next((p for p in self.state.players if p.is_small_blind), None)
        big_blind = next((p for p in self.state.players if p.is_big_blind), None)
        
        if dealer:
            log_entry = f"Player {dealer.id} is the dealer"
            self.detailed_log.append(log_entry)
        if small_blind:
            log_entry = f"Player {small_blind.id} posts small blind - 20 chips"
            self.detailed_log.append(log_entry)
        if big_blind:
            log_entry = f"Player {big_blind.id} posts big blind - 40 chips"
            self.detailed_log.append(log_entry)
    
    def _setup_blinds(self):
        """Set dealer, small blind, and big blind positions"""
        if len(self.state.players) < 2:
            return
        
        # Set dealer position (random for first hand)
        self.state.dealer_position = 0
        
        # Set blinds
        sb_pos = (self.state.dealer_position + 1) % len(self.state.players)
        bb_pos = (self.state.dealer_position + 2) % len(self.state.players)
        
        self.state.players[self.state.dealer_position].is_dealer = True
        self.state.players[sb_pos].is_small_blind = True
        self.state.players[bb_pos].is_big_blind = True
        
        # Post blinds
        self._post_blind(sb_pos, self.state.small_blind)
        self._post_blind(bb_pos, self.state.big_blind)
        
        # Set current player (first to act preflop)
        self.state.current_player = (bb_pos + 1) % len(self.state.players)
        self.state.current_bet = self.state.big_blind
    
    def _post_blind(self, player_pos: int, amount: int):
        """Post blind bet for a player"""
        player = self.state.players[player_pos]
        bet_amount = min(amount, player.stack)
        player.stack -= bet_amount
        player.current_bet = bet_amount
        self.state.pot += bet_amount
        
        if player.stack == 0:
            player.is_all_in = True
    
    def deal_hole_cards(self):
        """Deal 2 hole cards to each player"""
        for player in self.state.players:
            # Deal 2 cards to each player
            card1 = self.deck.deal_card()
            card2 = self.deck.deal_card()
            player.hole_cards = [card1, card2]
    
    def deal_community_cards(self, count: int):
        """Deal community cards (flop=3, turn=1, river=1)"""
        cards = self.deck.deal_cards(count)
        self.state.community_cards.extend(cards)
    
    def get_valid_actions(self, player_id: int) -> List[ActionType]:
        """Get valid actions for a specific player"""
        # Get the current player who should be acting
        current_player = self.state.players[self.state.current_player]
        
        if current_player.id != player_id:
            return []
        
        player = current_player
        if player.is_folded or player.is_all_in:
            return []
        
        # Start with fold (always available)
        valid_actions = [ActionType.FOLD]
        
        # Check if player can check or call
        if player.current_bet == self.state.current_bet:
            # Player has matched current bet, can check
            valid_actions.append(ActionType.CHECK)
        else:
            # Player needs to call
            call_amount = self.state.current_bet - player.current_bet
            if call_amount <= player.stack:
                valid_actions.append(ActionType.CALL)
        
        # Check if player can bet or raise
        if player.stack > 0:
            if self.state.current_bet == 0:
                # No current bet, can bet
                valid_actions.append(ActionType.BET)
            else:
                # Current bet exists, can raise
                valid_actions.append(ActionType.RAISE)
            
            # Can always go all-in if have chips
            valid_actions.append(ActionType.ALL_IN)
        
        return valid_actions
    
    def execute_action(self, player_id: int, action: ActionType, amount: int = 0) -> bool:
        """Execute a player action"""
        # Find the current player by position index
        current_player = self.state.players[self.state.current_player]
        if current_player.id != player_id:
            return False
        
        valid_actions = self.get_valid_actions(player_id)
        if action not in valid_actions:
            return False
        
        player = current_player
        
        # Execute the action
        if action == ActionType.FOLD:
            player.is_folded = True
        
        elif action == ActionType.CHECK:
            pass  # No chips involved
        
        elif action == ActionType.CALL:
            call_amount = min(self.state.current_bet - player.current_bet, player.stack)
            player.stack -= call_amount
            player.current_bet += call_amount
            self.state.pot += call_amount
            if player.stack == 0:
                player.is_all_in = True
        
        elif action == ActionType.BET:
            bet_amount = min(amount, player.stack)
            player.stack -= bet_amount
            player.current_bet += bet_amount
            self.state.pot += bet_amount
            self.state.current_bet = player.current_bet
            if player.stack == 0:
                player.is_all_in = True
        
        elif action == ActionType.RAISE:
            raise_amount = min(amount, player.stack)
            player.stack -= raise_amount
            player.current_bet += raise_amount
            self.state.pot += raise_amount
            self.state.current_bet = player.current_bet
            if player.stack == 0:
                player.is_all_in = True
        
        elif action == ActionType.ALL_IN:
            all_in_amount = player.stack
            player.stack = 0
            player.current_bet += all_in_amount
            self.state.pot += all_in_amount
            player.is_all_in = True
            if player.current_bet > self.state.current_bet:
                self.state.current_bet = player.current_bet
        
        # Log the detailed action
        self._log_action(player_id, action, amount)
        
        # Record the action
        player_action = PlayerAction(
            player_id=player_id,
            action=action,
            amount=amount
        )
        self.state.actions.append(player_action)
        
        # Move to next player
        self._next_player()
        
        # Check if betting round is complete
        if self._is_betting_round_complete():
            self._advance_stage()
        
        return True
    
    def _next_player(self):
        """Move to the next active player"""
        for _ in range(len(self.state.players)):
            self.state.current_player = (self.state.current_player + 1) % len(self.state.players)
            player = self.state.players[self.state.current_player]
            if not player.is_folded and not player.is_all_in:
                break
    
    def _is_betting_round_complete(self) -> bool:
        """Check if the current betting round is complete"""
        active_players = [p for p in self.state.players if not p.is_folded]
        
        # If only one player left, round is complete
        if len(active_players) <= 1:
            return True
        
        # Check if all active players have matched the current bet or are all-in
        for player in active_players:
            if not player.is_all_in and player.current_bet != self.state.current_bet:
                return False
        
        return True
    
    def _advance_stage(self):
        """Advance to the next stage of the game"""
        # Check if only one player remains active - if so, they win immediately
        active_players = [p for p in self.state.players if not p.is_folded]
        if len(active_players) <= 1:
            self._determine_winner()
            return
        
        # Reset current bets for next round
        for player in self.state.players:
            player.current_bet = 0
        self.state.current_bet = 0
        
        if self.state.stage == GameStage.PREFLOP:
            self.state.stage = GameStage.FLOP
            self.deal_community_cards(3)  # Flop: 3 cards
        elif self.state.stage == GameStage.FLOP:
            self.state.stage = GameStage.TURN
            self.deal_community_cards(1)  # Turn: 1 card
        elif self.state.stage == GameStage.TURN:
            self.state.stage = GameStage.RIVER
            self.deal_community_cards(1)  # River: 1 card
        elif self.state.stage == GameStage.RIVER:
            self.state.stage = GameStage.SHOWDOWN
            self._determine_winner()
            return
        
        # Check if there are any players who can still act
        players_who_can_act = [p for p in active_players if not p.is_all_in]
        
        if len(players_who_can_act) == 0:
            # No one can act anymore - auto-advance through remaining stages
            self._auto_advance_to_showdown()
        else:
            # Set first player to act (first active player after dealer)
            self._set_first_to_act()
    
    def _auto_advance_to_showdown(self):
        """Automatically advance through remaining stages when no one can act"""
        print(f"Auto-advancing from {self.state.stage} - no players can act")
        
        # Deal remaining community cards based on current stage
        if self.state.stage == GameStage.PREFLOP:
            # Deal flop, turn, and river all at once
            self.state.stage = GameStage.FLOP
            self.deal_community_cards(3)  # Flop
            self.state.stage = GameStage.TURN
            self.deal_community_cards(1)  # Turn
            self.state.stage = GameStage.RIVER
            self.deal_community_cards(1)  # River
        elif self.state.stage == GameStage.FLOP:
            # Deal turn and river
            self.state.stage = GameStage.TURN
            self.deal_community_cards(1)  # Turn
            self.state.stage = GameStage.RIVER
            self.deal_community_cards(1)  # River
        elif self.state.stage == GameStage.TURN:
            # Deal river
            self.state.stage = GameStage.RIVER
            self.deal_community_cards(1)  # River
        
        # Move to showdown and determine winner
        self.state.stage = GameStage.SHOWDOWN
        self._determine_winner()
    
    def _set_first_to_act(self):
        """Set the first player to act in a betting round"""
        start_pos = (self.state.dealer_position + 1) % len(self.state.players)
        for i in range(len(self.state.players)):
            pos = (start_pos + i) % len(self.state.players)
            player = self.state.players[pos]
            if not player.is_folded and not player.is_all_in:
                self.state.current_player = pos
                break
    
    def _determine_winner(self):
        """Determine the winner using pokerkit for proper hand evaluation"""
        from pokerkit import Automation, NoLimitTexasHoldem
        
        active_players = [p for p in self.state.players if not p.is_folded]
        
        if len(active_players) == 1:
            # Only one player left - they win by default
            winner = active_players[0]
            winner.stack += self.state.pot
            self.state.winner_id = winner.id
            self.state.winner_reason = f"{winner.name} wins by default (all others folded)"
            print(f"WINNER: {winner.name} wins {self.state.pot} chips by default (all others folded)")
        else:
            # Multiple players - use pokerkit for proper hand evaluation
            try:
                from pokerkit import Card as PokerKitCard, StandardLookup
                
                # Create lookup instance
                lookup = StandardLookup()
                
                # Evaluate each player's hand using pokerkit's hand evaluation
                player_evaluations = []
                
                for player in active_players:
                    if len(player.hole_cards) >= 2 and len(self.state.community_cards) == 5:
                        # Create 7-card hand (2 hole + 5 community)
                        hole_cards_str = f"{player.hole_cards[0]}{player.hole_cards[1]}"
                        community_str = ''.join(str(card) for card in self.state.community_cards)
                        full_hand_str = hole_cards_str + community_str
                        
                        # Parse cards using pokerkit
                        cards = list(PokerKitCard.parse(full_hand_str))
                        
                        # Evaluate the 7-card hand to find best 5-card hand
                        entry = lookup.get_entry_or_none(cards)
                        
                        if entry:
                            player_evaluations.append((player, entry.index, entry.label, cards))
                            print(f"Player {player.name}: {hole_cards_str} + {community_str} = {entry.label} (index: {entry.index})")
                        else:
                            # Fallback for hands that can't be evaluated
                            player_evaluations.append((player, 0, "Unknown", cards))
                            print(f"Player {player.name}: {hole_cards_str} + {community_str} = Could not evaluate")
                    else:
                        # Fallback for incomplete hands
                        player_evaluations.append((player, 0, "Incomplete", []))
                
                if player_evaluations:
                    # Find the player with the best hand (highest index in StandardLookup - higher is better)
                    winner_player, winner_index, winner_label, winner_cards = max(player_evaluations, key=lambda x: x[1])
                    
                    winner_player.stack += self.state.pot
                    self.state.winner_id = winner_player.id
                    self.state.winner_reason = f"{winner_player.name} wins with {winner_label}"
                    print(f"WINNER: {winner_player.name} wins {self.state.pot} chips with {winner_label} (index: {winner_index})")
                else:
                    # No valid evaluations
                    winner = active_players[0]
                    winner.stack += self.state.pot
                    self.state.winner_id = winner.id
                    self.state.winner_reason = f"{winner.name} wins (no valid hands to evaluate)"
                    print(f"WINNER: {winner.name} wins {self.state.pot} chips (no valid hands)")
                
            except Exception as e:
                # Fallback to simple evaluation if pokerkit fails
                print(f"Pokerkit evaluation failed: {e}, using fallback")
                best_player = max(active_players, key=lambda p: self._evaluate_hand_simple(p))
                best_player.stack += self.state.pot
                self.state.winner_id = best_player.id
                self.state.winner_reason = f"{best_player.name} wins (fallback evaluation)"
                print(f"WINNER: {best_player.name} wins {self.state.pot} chips (fallback evaluation)")
        
        self.state.stage = GameStage.FINISHED
        self.state.is_finished = True
    
    def _evaluate_hand_simple(self, player):
        """Simple hand evaluation fallback"""
        if not player.hole_cards:
            return 0
        return max(self._card_value(card) for card in player.hole_cards)
    
    def _card_value(self, card):
        """Convert card rank to numeric value for comparison"""
        rank_values = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
            "J": 11, "Q": 12, "K": 13, "A": 14
        }
        return rank_values.get(card.rank, 0)
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state as a dictionary"""
        from dataclasses import asdict
        
        # Serialize players with hole_cards as strings
        players_data = []
        for player in self.state.players:
            player_dict = asdict(player)
            # Convert hole_cards from Card objects to strings
            player_dict["hole_cards"] = [str(card) for card in player.hole_cards]
            players_data.append(player_dict)
        
        # Get valid actions for current player
        current_player = self.state.players[self.state.current_player] if not self.state.is_finished else None
        valid_actions = self.get_valid_actions(current_player.id) if current_player else []
        

        
        return {
            "id": self.state.id,
            "players": players_data,
            "community_cards": [str(card) for card in self.state.community_cards],
            "pot": self.state.pot,
            "current_bet": self.state.current_bet,
            "stage": self.state.stage,
            "current_player": self.state.current_player,
            "actions": [asdict(action) for action in self.state.actions],
            "is_finished": self.state.is_finished,
            "winner_id": self.state.winner_id,
            "winner_reason": getattr(self.state, 'winner_reason', None),
            "valid_actions": [action.value for action in valid_actions],
            "detailed_log": self.detailed_log
        }
