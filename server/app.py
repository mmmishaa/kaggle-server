from fastapi import FastAPI

app = FastAPI(title='Kaggle Server')

@app.get("/health")
def health_check():
    return {"status": "ok"}