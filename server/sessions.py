import json
import uuid
from typing import Optional, List, Dict, Any

import chess
import chess.pgn
import redis

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def _redis() -> redis.Redis:
    return redis.Redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)


def _build_board(initial_fen: Optional[str], moves: List[str]) -> chess.Board:
    board = chess.Board() if not initial_fen or initial_fen == "startpos" else chess.Board(initial_fen)
    for u in moves:
        mv = chess.Move.from_uci(u)
        if mv not in board.legal_moves:
            raise ValueError(f"Illegal stored move {u} for current position.")
        board.push(mv)
    return board


def _build_pgn(moves: List[str], initial_fen: Optional[str]) -> str:
    game = chess.pgn.Game()
    temp_board = chess.Board() if not initial_fen or initial_fen == "startpos" else chess.Board(initial_fen)
    if initial_fen and initial_fen != "startpos":
        game.setup(chess.Board(initial_fen))
    node = game
    for u in moves:
        mv = chess.Move.from_uci(u)
        node = node.add_variation(mv)
        temp_board.push(mv)
    return str(game)


class gameSession:
    def __init__(self, redis_client: redis.Redis, key: str, doc: Dict[str, Any]):
        self.r = redis_client
        self.key = key
        self.doc = doc

    @property
    def id(self) -> str:
        return self.doc["id"]

    @property
    def bot_id(self) -> str:
        return self.doc["bot_id"]

    @property
    def clocks(self) -> Optional[dict]:
        return self.doc.get("clocks")

    @property
    def moves(self) -> List[str]:
        return self.doc.get("moves", [])

    @property
    def initial_fen(self) -> Optional[str]:
        return self.doc.get("initial_fen")

    @property
    def board(self) -> chess.Board:
        return _build_board(self.initial_fen, self.moves)

    @property
    def fen(self) -> str:
        return self.board.fen()

    @property
    def turn(self) -> str:
        return "w" if self.board.turn else "b"

    @property
    def pgn_str(self) -> str:
        return _build_pgn(self.moves, self.initial_fen)

    def push_move(self, move_uci: str) -> str:
        board = self.board
        mv = chess.Move.from_uci(move_uci)
        if mv not in board.legal_moves:
            raise ValueError("IllegalMove")
        san = board.san(mv)
        self.doc.setdefault("moves", []).append(move_uci)
        self._persist()
        return san

    def status(self) -> dict:
        board = self.board
        winner = None
        reason = None
        if board.is_checkmate():
            winner = "white" if not board.turn else "black"
            reason = "checkmate"
        elif board.is_stalemate():
            winner = "draw"; reason = "stalemate"
        elif board.is_fifty_moves():
            winner = "draw"; reason = "50move"
        elif board.can_claim_threefold_repetition():
            winner = "draw"; reason = "threefold"

        return {
            "inCheck": board.is_check(),
            "gameOver": winner is not None,
            "winner": winner,
            "reason": reason,
        }

    def _persist(self):
        self.r.set(self.key, json.dumps(self.doc))


class sessionStore:
    PREFIX = "sess:"

    def __init__(self):
        self.r = _redis()

    def _key(self, session_id: str) -> str:
        return f"{self.PREFIX}{session_id}"

    def create(self, bot_id: str, initial_fen: Optional[str], clocks: Optional[dict]) -> gameSession:
        sid = str(uuid.uuid4())
        doc = {
            "id": sid,
            "bot_id": bot_id,
            "initial_fen": initial_fen if initial_fen else "startpos",
            "moves": [],
            "clocks": clocks or None,
        }
        self.r.set(self._key(sid), json.dumps(doc))
        return gameSession(self.r, self._key(sid), doc)

    def get(self, session_id: str) -> gameSession:
        raw = self.r.get(self._key(session_id))
        if not raw:
            raise KeyError("SessionNotFound")
        doc = json.loads(raw)
        return gameSession(self.r, self._key(session_id), doc)

    def resign(self, session_id: str, winner: str) -> gameSession:
        return self.get(session_id)

    def undo_fullmove(self, session_id: str) -> gameSession:
        s = self.get(session_id)
        mv = s.doc.get("moves", [])
        if mv: mv.pop()  
        if mv: mv.pop()  
        s.doc["moves"] = mv
        s._persist()
        return s

SESSIONS = sessionStore()