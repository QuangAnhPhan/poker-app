from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Poker backend is running!"}
