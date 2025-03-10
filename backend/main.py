from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
from typing import List
from uuid import uuid4
import firebase_admin
import os
from firebase_admin import credentials, firestore

cred = credentials.Certificate("rutinasejercicios-6c3a5-firebase-adminsdk-fbsvc-f964c09ba7.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()

port = int(os.environ.get("PORT", 8000))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Challenge(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    target: int
    progress: int

class ChallengeCreate(BaseModel):
    user_id: str
    name: str
    description: str
    target: conint(ge=0) 

@app.get("/get_challenges", response_model=List[Challenge])
def get_challenges(user_id: str):
    challenges_ref = db.collection('challenges').where('user_id', '==', user_id).stream()
    
    user_challenges = []
    for challenge in challenges_ref:
        challenge_data = challenge.to_dict()
        user_challenges.append(Challenge(
            id=challenge.id,
            user_id=challenge_data['user_id'],
            name=challenge_data['name'],
            description=challenge_data['description'],
            target=challenge_data['target'],
            progress=challenge_data['progress']
        ))
    
    if not user_challenges:
        raise HTTPException(status_code=404, detail="No challenges found for this user")
    
    return user_challenges

@app.post("/add_challenge", response_model=Challenge)
def add_challenge(challenge: ChallengeCreate):
    new_challenge_ref = db.collection('challenges').add({
        'user_id': challenge.user_id,
        'name': challenge.name,
        'description': challenge.description,
        'target': challenge.target,
        'progress': 0 
    })

    new_challenge = new_challenge_ref.get()
    
    return Challenge(
        id=new_challenge.id,
        user_id=challenge.user_id,
        name=challenge.name,
        description=challenge.description,
        target=challenge.target,
        progress=0
    )

@app.post("/update_progress/{challenge_id}")
def update_progress(challenge_id: str, progress: int):
    if progress < 0:
        raise HTTPException(status_code=400, detail="Progress cannot be negative")
    
    challenge_ref = db.collection('challenges').document(challenge_id)
    challenge = challenge_ref.get()
    
    if not challenge.exists:
        raise HTTPException(status_code=404, detail="Challenge not found")
    

    new_progress = min(challenge.to_dict()['progress'] + progress, challenge.to_dict()['target'])
    challenge_ref.update({'progress': new_progress})
    
    return {"message": f"Progress updated for challenge {challenge_id}!", "progress": new_progress}

@app.get("/get_progress/{challenge_id}")
def get_progress(challenge_id: str):
    challenge_ref = db.collection('challenges').document(challenge_id)
    challenge = challenge_ref.get()
    
    if not challenge.exists:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    challenge_data = challenge.to_dict()
    return {
        "challenge": challenge_data['name'],
        "progress": challenge_data['progress'],
        "target": challenge_data['target']
    }

@app.delete("/delete_challenge/{challenge_id}")
def delete_challenge(challenge_id: str):
    challenge_ref = db.collection('challenges').document(challenge_id)
    challenge = challenge_ref.get()
    
    if not challenge.exists:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    challenge_ref.delete()
    
    return {"message": f"Desafío con ID {challenge_id} eliminado"}
