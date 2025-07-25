# Poker Game Backend

FastAPI backend for the Texas Hold'em poker simulation.

## Features

- 6-player Texas Hold'em poker game engine
- RESTful API endpoints for game operations
- PostgreSQL database integration
- Hand history storage
- Real-time game state management

## Installation

```bash
poetry install
```

## Running

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.
