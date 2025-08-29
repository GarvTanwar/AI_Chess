from typing import Optional 
import chess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bots import BOTS, BOTS_ID, botConfig
from schemas import (
    botOut,
    newSessionIn,
    sessionOut,
    moveIn,
    moveOut,
    Status,
    moveSideOut
)
from sessions import gameSession, SESSIONS
from engine import ENGINE

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _session_out(s: gameSession) -> sessionOut:
    return sessionOut (
        sessionId=s.id,
        botId=s.bot_id,
        fen=s.fen,
        turn="w" if s.board.turn else "b",
        pgn=s.pgn_str,
        status=_status_obj(s),
        clocks=s.clocks,
    )

def _status_obj(s: gameSession) -> Status:
    st = s.status()

    return Status (
        inCheck=st["inCheck"],
        gameOver=st["gameOver"],
        winner=st["winner"],
        reason=st["reason"],
    )

@app.get("/health")
def health():
    return {"ok": True, "engine": ENGINE.engine_name()}

@app.get("/bots", response_model=list[botOut])
def list_bots():
    return [botOut(id=b.id, name=b.name, elo=b.elo) for b in BOTS]

@app.post('/session', response_model=sessionOut)
def create_session(payload: newSessionIn):
    if payload.botId not in BOTS_ID:
        raise HTTPException(status_code=400, detail="BotNotFound")
    
    bot: botConfig = BOTS_ID[payload.botId]

    s = SESSIONS.create(
        bot_id = bot.id,
        initial_fen = payload.initialFEN,
        clocks = (payload.clocks.dict() if payload.clocks else None)
    )

    if payload.color == "black":
        board = s.board
        best = ENGINE.analyze_bestmove(board, bot)
        s.push_move(best.uci())
    
    return _session_out(s)

@app.get("/session/{session_id}", response_model=sessionOut)
def get_session(session_id: str):
    try:
        s = SESSIONS.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="SessionNotFound")
    return _session_out(s)

@app.post("/move", response_model=moveOut)
def make_move(payload: moveIn):
    try:
        s = SESSIONS.get(payload.sessionId)
    except KeyError:
        raise HTTPException(status_code=404, detail="SessionNotFound")

    bot: botConfig = BOTS_ID[s.bot_id]

    try:
        user_san = s.push_move(payload.uci)
    except ValueError:
        raise HTTPException(status_code=400, detail="IllegalMove")

    status_after_user = s.status()
    if status_after_user["gameOver"]:
        return moveOut(
            user=moveSideOut(uci=payload.uci, san=user_san),
            bot=None,
            fen=s.fen,
            pgn=s.pgn_str,
            status=_status_obj(s),
            clocks=s.clocks,
        )

    board_before_bot = s.board
    best = ENGINE.analyze_bestmove(board_before_bot, bot)
    bot_san = board_before_bot.san(best)
    s.push_move(best.uci())

    return moveOut(
        user=moveSideOut(uci=payload.uci, san=user_san),
        bot=moveSideOut(uci=best.uci(), san=bot_san),
        fen=s.fen,
        pgn=s.pgn_str,
        status=_status_obj(s),
        clocks=s.clocks,
    )

@app.post('/undo', response_model=sessionOut)
def undo(payload: dict):
    session_id: Optional[str] = payload.get("sessionId")

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing sessionId")
    
    try:
        s = SESSIONS.undo_fullmove(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="SessionNotFound")
    return _session_out(s)

@app.post('/resign')
def resign(payload: dict):
    session_id: Optional[str] = payload.get("sessionId")

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing sessionId")
    
    try:
        _ = SESSIONS.resign(session_id, winner="black")
    except KeyError:
        raise HTTPException(status_code=404, detail="SessionNotFound")
    
    return {
        "sessionId": session_id,
        "status": {
            "inCheck": False,
            "gameOver": True,
            "winner": "black",
            "reason": "resign",
        }
    }

@app.get("/pgn/{session_id}")
def export_pgn(session_id: str):
    try:
        s = SESSIONS.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="SessionNotFound")
    return {"pgn": s.pgn_str}
