from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List
import uuid

app = FastAPI(title="Exercise 2 - Users + Notes")


# --------- Models ---------
class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class UserResponse(BaseModel):
    id: str
    username: str


class NoteCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class NotesResponse(BaseModel):
    user_id: str
    notes: List[str]


# --------- In-memory "DB" ---------
# user_id -> {"id": str, "username": str, "notes": [str, ...]}
users_by_id: Dict[str, Dict] = {}
# username -> user_id
user_id_by_username: Dict[str, str] = {}


# --------- Helpers ---------
def get_user_or_404(user_id: str) -> Dict:
    user = users_by_id.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# --------- Routes ---------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest):
    username = payload.username.strip()

    if username in user_id_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    user_id = str(uuid.uuid4())
    users_by_id[user_id] = {"id": user_id, "username": username, "notes": []}
    user_id_by_username[username] = user_id

    return {"id": user_id, "username": username}


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    user = get_user_or_404(user_id)
    return {"id": user["id"], "username": user["username"]}


@app.post("/users/{user_id}/notes", response_model=NotesResponse, status_code=status.HTTP_201_CREATED)
def add_note(user_id: str, payload: NoteCreateRequest):
    user = get_user_or_404(user_id)
    note_text = payload.text.strip()
    user["notes"].append(note_text)
    return {"user_id": user_id, "notes": user["notes"]}


@app.get("/users/{user_id}/notes", response_model=NotesResponse)
def read_notes(user_id: str):
    user = get_user_or_404(user_id)
    return {"user_id": user_id, "notes": user["notes"]}