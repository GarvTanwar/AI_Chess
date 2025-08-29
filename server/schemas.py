from typing import Literal, Optional
from pydantic import BaseModel, Field

class clock(BaseModel):
    whiteMs: int = Field(..., ge=0, description="White time left in ms")
    blackMs: int = Field(..., ge=0, description="Black time left in ms")
    incMs: int = Field(0, ge=0, description="Increment per move in ms")

class Status(BaseModel):
    inCheck: bool
    gameOver: bool
    winner: Optional[Literal["white","black","draw"]] = None
    reason: Optional[
        Literal["checkmate", "stalemate", "resign", "timeout", "threefold", "50move"]
    ] = None

class botOut(BaseModel):
    id: str
    name: str
    elo: int


class newSessionIn(BaseModel):
    botId: str
    color: Literal["white","black","auto"] = "white"
    initialFEN: Optional[str] = Field(
        None, description='FEN string or "startpos" (default if None)'
    )
    clocks: Optional[clock] = None

class sessionOut(BaseModel):
    sessionId: str
    botId: str
    fen: str
    turn: Literal["w", "b"]
    pgn: str
    status: Status
    clocks: Optional[clock] = None


class moveIn(BaseModel):
    sessionId: str
    uci: str = Field(..., min_length=4, description="UCI move string")


class moveSideOut(BaseModel):
    uci: str
    san: str

class moveOut(BaseModel):
    user: Optional[moveSideOut] = None
    bot: Optional[moveSideOut] = None
    fen: str
    pgn: str
    status: Status
    clocks: Optional[clock] = None

class errorResponse(BaseModel):
    error: str
    details: Optional[str] = None