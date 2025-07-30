# Poker Project Documentation

## Overview

This is a full-stack Texas Hold'em poker simulation application that allows users to play a complete 6-player poker game from start to finish. The project implements standard Texas Hold'em rules with proper betting rounds, hand evaluation, and winner determination.

## Architecture

### Tech Stack
- **Frontend**: Next.js + React + TypeScript + shadcn/ui
- **Backend**: FastAPI + Python + PostgreSQL
- **Poker Engine**: PokerKit library for game logic and validation
- **Deployment**: Docker Compose

### Project Structure
```
poker-app/
├── frontend/                 # Next.js React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── lib/            # API client and utilities
│   │   └── types/          # TypeScript type definitions
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── api/            # API route handlers
│   │   ├── models/         # Game logic and data models
│   │   ├── schemas/        # Pydantic schemas for API
│   │   └── repository/     # Database operations
├── docker-compose.yml       # Container orchestration
└── POKER_PROJECT_DOCUMENTATION.md
```

## Game Rules & Configuration

### Basic Rules
- **Players**: 6-player game (6-max)
- **Blinds**: Small blind: 20 chips, Big blind: 40 chips
- **No ante**
- **Betting Rounds**: Preflop → Flop → Turn → River
- **Standard Texas Hold'em rules apply**

### Game Flow
1. **Setup**: Players start with configurable chip stacks
2. **Deal**: Each player receives 2 hole cards
3. **Betting Rounds**: 
   - Preflop (after hole cards)
   - Flop (3 community cards)
   - Turn (4th community card)
   - River (5th community card)
4. **Showdown**: Best 5-card hand wins
5. **Winner Determination**: Automatic using PokerKit's hand evaluation

## Core Components

### Backend Components

#### 1. PokerGame Class (`backend/app/models/poker.py`)
The main game engine that integrates with PokerKit for reliable poker logic.

**Key Features:**
- **PokerKit Integration**: Uses `NoLimitTexasHoldem` class for state management
- **Action Validation**: All player actions validated through PokerKit
- **Automatic Progression**: Handles betting rounds and card dealing
- **Hand Evaluation**: Uses PokerKit's built-in hand evaluation system
- **Detailed Logging**: Comprehensive play log for debugging and history

**Key Methods:**
- `execute_action()`: Process player actions (fold, check, call, bet, raise, all-in)
- `get_valid_actions()`: Get available actions for current player
- `get_game_state()`: Return current game state for API
- `_determine_winner()`: Handle winner determination at showdown

#### 2. API Routes (`backend/app/api/poker.py`)
RESTful API endpoints for frontend communication.

**Endpoints:**
- `POST /api/poker/start`: Start new game with player stacks
- `POST /api/poker/{game_id}/action`: Execute player action
- `GET /api/poker/{game_id}/actions/{player_id}`: Get valid actions
- `DELETE /api/poker/{game_id}/reset`: Reset/delete game
- `GET /api/poker/history`: Get hand history from database
- `GET /api/poker/games`: Get active games list

#### 3. Data Models
**Card System:**
```python
class Card:
    suit: Suit  # hearts, diamonds, clubs, spades
    rank: Rank  # 2-9, T, J, Q, K, A (T = Ten for PokerKit compatibility)
```

**Player Model:**
```python
class Player:
    id: int
    name: str
    stack: int
    hole_cards: List[Card]
    current_bet: int
    is_folded: bool
    is_all_in: bool
    # Position indicators
    is_dealer: bool
    is_small_blind: bool
    is_big_blind: bool
```

**Game State:**
```python
class GameState:
    id: str
    players: List[Player]
    community_cards: List[Card]
    pot: int
    current_bet: int
    stage: GameStage  # preflop, flop, turn, river, finished
    current_player: int
    actions: List[PlayerAction]
    winner_id: Optional[int]
```

### Frontend Components

#### 1. Main Game Component (`frontend/src/components/PokerGame.tsx`)
Central component that orchestrates the entire game interface.

**Features:**
- **Real-time Updates**: Polls backend every 2 seconds for game state
- **Winner Modal**: Shows winner when hand completes
- **Error Handling**: Displays user-friendly error messages
- **State Management**: Manages game state, loading states, and UI interactions

#### 2. Game Setup (`frontend/src/components/GameSetup.tsx`)
Allows users to configure initial player stacks and start new games.

#### 3. Action Controls (`frontend/src/components/ActionControls.tsx`)
Provides betting interface with validation.

**Features:**
- **Dynamic Action Buttons**: Only shows valid actions (fold, check, call, bet, raise, all-in)
- **Bet Amount Controls**: ±40 chip increment buttons
- **Input Validation**: Prevents invalid bet amounts
- **Responsive Design**: Adapts to different screen sizes

#### 4. Play Log (`frontend/src/components/PlayLog.tsx`)
Real-time display of game actions and events.

**Displays:**
- Player actions (fold, check, call, bet, raise)
- Betting round transitions
- Community card reveals
- Winner announcements
- Pot distributions

#### 5. Hand History (`frontend/src/components/HandHistory.tsx`)
Shows completed hands from database with expandable details.

## Key Features

### 1. PokerKit Integration
The project leverages the PokerKit library for reliable poker game logic:

```python
# Initialize PokerKit state
self.pokerkit_state = NoLimitTexasHoldem.create_state(
    automations=(
        Automation.ANTE_POSTING,
        Automation.BET_COLLECTION,
        Automation.BLIND_OR_STRADDLE_POSTING,
        Automation.HAND_KILLING,
        Automation.CHIPS_PULLING,
    ),
    # ... other parameters
)
```

**Benefits:**
- **Reliable Action Validation**: All moves validated by proven poker engine
- **Automatic Betting Management**: Handles blinds, pot collection, etc.
- **Professional Hand Evaluation**: Accurate winner determination
- **Edge Case Handling**: Covers complex scenarios like all-ins, side pots

### 2. Real-time Game Updates
Frontend polls backend every 2 seconds to maintain synchronized game state across all players.

### 3. Comprehensive Logging
Detailed play log captures every action for debugging and user experience:
```
Game started with 6 players
Player 1 (BTN) dealt: [Hidden Cards]
Player 2 (SB) posts small blind: 20 chips
Player 3 (BB) posts big blind: 40 chips
Player 4 calls 40 chips
...
```

### 4. Database Persistence
Completed hands are automatically saved to PostgreSQL database with full game details.

### 5. Input Validation
- **Frontend**: Prevents invalid actions through UI controls
- **Backend**: Double validation using PokerKit's action system
- **Type Safety**: TypeScript ensures type correctness

## API Reference

### Start Game
```http
POST /api/poker/start
Content-Type: application/json

{
  "player_stacks": {
    "1": 1000,
    "2": 1000,
    "3": 1000,
    "4": 1000,
    "5": 1000,
    "6": 1000
  }
}
```

### Execute Action
```http
POST /api/poker/{game_id}/action
Content-Type: application/json

{
  "player_id": 1,
  "action": "bet",
  "amount": 100
}
```

### Get Game State
```http
GET /api/poker/{game_id}/state
```

## Development Setup

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd poker-app

# Start with Docker Compose
docker compose up

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development
```bash
# Backend
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Database Schema

### hands Table
Stores completed poker hands with full game state:
- `id`: Unique hand identifier
- `game_id`: Game session identifier
- `winner_id`: Winning player ID
- `pot_amount`: Final pot size
- `players_data`: JSON with player information
- `community_cards`: JSON with community cards
- `actions_log`: JSON with all player actions
- `created_at`: Hand completion timestamp
