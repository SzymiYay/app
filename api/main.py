import urllib
import os
import sqlalchemy
import databases
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



host_server = os.environ.get('HOST_SERVER', 'localhost')
db_server_post = urllib.parse.quote_plus(os.environ.get('DB_SERVER_PORT', '5432'))
database_name = os.environ.get('DATABASE_NAME', 'iot_db')
db_username = urllib.parse.quote_plus(os.environ.get('DB_USERNAME', 'postgres'))
db_password = urllib.parse.quote_plus(os.environ.get('DB_PASSWORD', 'postgres'))
ssl_mode = urllib.parse.quote_plus(os.environ.get('SSL_MODE', 'prefer'))
DATABASE_URL = f'postgresql://{db_username}:{db_password}@{host_server}:{db_server_post}/{database_name}?sslmode={ssl_mode}'

metadata = sqlalchemy.MetaData()

notes = sqlalchemy.Table(
    "notes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("text", sqlalchemy.String),
    sqlalchemy.Column("completed", sqlalchemy.Boolean),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, pool_size=3, max_overflow=0
)

metadata.create_all(engine)

class NoteIn(BaseModel):
    text: str
    completed: bool

class Note(BaseModel):
    id: int
    text: str
    completed: bool

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database = databases.Database(DATABASE_URL)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/notes/", response_model=Note)
async def create_note(note: NoteIn):
    query = notes.insert().values(text=note.text, completed=note.completed)
    last_record_id = await database.execute(query)
    return {**note.dict(), "id": last_record_id}

@app.get("/notes/", response_model=list[Note])
async def read_notes():
    query = notes.select()
    return await database.fetch_all(query)

@app.get("/notes/{note_id}/", response_model=Note)
async def read_notes(note_id: int):
    query = notes.select().where(notes.c.id == note_id)
    return await database.fetch_one(query)

@app.put("/notes/{note_id}/", response_model=Note)
async def update_notes(note_id: int, note: NoteIn):
    query = (
        notes
        .update()
        .where(notes.c.id == note_id)
        .values(text=note.text, completed=note.completed)
        .returning(*notes.c)
    )
    return await database.fetch_one(query)

@app.delete("/notes/{note_id}/", response_model=None)
async def delete_notes(note_id: int):
    query = notes.delete().where(notes.c.id == note_id)
    return await database.execute(query)