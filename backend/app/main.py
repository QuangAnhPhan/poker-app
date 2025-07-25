from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import get_connection, create_tables
from app.api.poker import router as poker_router

# Create FastAPI app
app = FastAPI(
    title="Poker Game API",
    description="Texas Hold'em Poker Game Backend",
    version="1.0.0"
)

# Add CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "Content-Type",
        "Authorization",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
    ],
)

# Include routers
app.include_router(poker_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    create_tables()

@app.get("/")
def root():
    try:
        conn = get_connection()
        conn.close()
        return {
            "message": "Poker Game API is running!",
            "status": "PostgreSQL connected successfully!"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
