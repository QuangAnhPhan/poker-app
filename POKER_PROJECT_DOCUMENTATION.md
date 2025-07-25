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

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.9+ (for local backend development)

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
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

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

## Error Handling

### Backend Error Handling
- **PokerKit Integration**: Graceful fallback for PokerKit errors
- **Action Validation**: Clear error messages for invalid actions
- **Database Errors**: Proper exception handling for DB operations

### Frontend Error Handling
- **API Errors**: User-friendly error messages
- **Network Issues**: Retry logic and loading states
- **Invalid Actions**: Disabled buttons for invalid moves

## Testing Strategy

### Backend Testing
- **Unit Tests**: Test individual game logic components
- **Integration Tests**: Test API endpoints with real database
- **PokerKit Integration**: Verify proper integration with poker engine

### Frontend Testing
- **Component Tests**: Test individual React components
- **Integration Tests**: Test user workflows
- **API Integration**: Mock API responses for reliable testing

## Performance Considerations

### Backend Optimizations
- **In-Memory Game Storage**: Active games stored in memory for fast access
- **Database Connection Pooling**: Efficient database connections
- **PokerKit Caching**: Reuse PokerKit instances when possible

### Frontend Optimizations
- **Polling Strategy**: 2-second intervals balance responsiveness and performance
- **Component Memoization**: Prevent unnecessary re-renders
- **Lazy Loading**: Load hand history on demand

## Security Considerations

### Current Implementation
- **Input Validation**: All inputs validated on both frontend and backend
- **Action Validation**: PokerKit prevents invalid game actions
- **Type Safety**: TypeScript prevents type-related vulnerabilities

### Production Considerations
- **Authentication**: Add user authentication system
- **Rate Limiting**: Prevent API abuse
- **HTTPS**: Secure communication in production
- **Database Security**: Proper connection security and query parameterization

## Troubleshooting

### Common Issues

#### 1. PokerKit Card Format Issues
**Problem**: Cards not displaying correctly
**Solution**: Ensure card format uses "T" for Ten (not "10")
```python
# Correct format
Card(suit=Suit.HEARTS, rank=Rank.TEN)  # Displays as "Th"
```

#### 2. Game State Synchronization
**Problem**: Frontend not updating
**Solution**: Check polling interval and API connectivity

#### 3. Invalid Action Errors
**Problem**: Actions rejected by backend
**Solution**: Verify action validation logic matches PokerKit requirements

### Debug Mode
Enable detailed logging by setting environment variables:
```bash
POKER_DEBUG=true
POKERKIT_VERBOSE=true
```

## Future Enhancements

### Planned Features
1. **Multi-table Support**: Support multiple concurrent games
2. **Tournament Mode**: Implement tournament structure
3. **Player Statistics**: Track player performance over time
4. **Replay System**: Replay completed hands step-by-step
5. **Mobile Optimization**: Improve mobile user experience
6. **Real-time Multiplayer**: WebSocket-based real-time updates

### Technical Improvements
1. **Redis Integration**: Replace in-memory storage with Redis
2. **WebSocket Support**: Real-time bidirectional communication
3. **Microservices**: Split into smaller, focused services
4. **Monitoring**: Add application monitoring and metrics
5. **CI/CD Pipeline**: Automated testing and deployment

## Contributing

### Code Style
- **Python**: Follow PEP 8 guidelines
- **TypeScript**: Use ESLint and Prettier configurations
- **Git**: Use conventional commit messages

### Pull Request Process
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request with clear description

## License

This project is developed as a coding exercise and is not intended for commercial use.

---

*Last Updated: January 2025*
*Version: 2.0 (PokerKit Integration)*
