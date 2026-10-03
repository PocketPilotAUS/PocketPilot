from fastapi import FastAPI

app = FastAPI(title="PocketPilot API")

@app.get("/")
def root():
    return {"message": "PocketPilot API is running"}