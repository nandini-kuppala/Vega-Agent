from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.user_routes import router as user_router
from routes.profile_routes import router as profile_router

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ashacareerguide.streamlit.app/"],  # Change this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Including routers with correct prefix
app.include_router(user_router, prefix="/api/users", tags=["Users"])
app.include_router(profile_router, prefix="/api/profiles", tags=["Profiles"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the ASHA API!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
