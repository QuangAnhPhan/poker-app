# app/db/connection.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pokerdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_connection():
    """Get a raw PostgreSQL connection using psycopg2"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def create_tables():
    """Create database tables using raw SQL"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create hand_history table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS hand_history (
            id VARCHAR(255) PRIMARY KEY,
            players_data JSONB NOT NULL,
            community_cards JSONB NOT NULL,
            actions JSONB NOT NULL,
            pot_size INTEGER NOT NULL,
            winner_id INTEGER,
            stage VARCHAR(50) NOT NULL,
            dealer_position INTEGER NOT NULL,
            small_blind INTEGER NOT NULL,
            big_blind INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        );
        """
        
        cursor.execute(create_table_query)
        conn.commit()
        
        print("Database tables created successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()
