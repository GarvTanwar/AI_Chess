import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
import os
from typing import Optional
import chess
import chess.engine
from dotenv import load_dotenv
from bots import botConfig


load_dotenv()

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")
DEFAULT_DEPTH = int(os.getenv("ENGINE_DEFAULT_DEPTH", "12"))
DEFAULT_MOVETIME = int(os.getenv("ENGINE_DEFAULT_MOVETIME", "300"))

class engineManager:
    def __init__(self, engine_path: str):
        if not engine_path:
            raise RuntimeError(
                "STOCKFISH_PATH is not set."
            )
        
        self.engine_path = engine_path
        self._engine: Optional[chess.engine.SimpleEngine] = None
    
    def _ensure(self):
        if self._engine is None:
            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            except FileNotFoundError as e:
                raise RuntimeError (
                    f"Could not start Stockfish at '{self.engine_path}'. "
                ) from e
    
    def close(self):
        if self._engine:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
    
    def engine_name(self) -> str:
        self._ensure()

        try:
            return self._engine.id.get("name", "stockfish")
        except Exception:
            return "stockfish"
        
    def analyze_bestmove(self, board: chess.Board, bot: botConfig) -> chess.Move:
        self._ensure()

        self._engine.configure({
            "UCI_LimitStrength": True,
            "UCI_Elo": int(bot.elo),
        })

        limit = chess.engine.Limit(
            depth = bot.depth if bot.depth is not None else DEFAULT_DEPTH,
            nodes = bot.nodes,
            time = (bot.movetime_ms if bot.movetime_ms is not None else DEFAULT_MOVETIME) / 1000.0,
        )

        try:
            result =self._engine.play(board, limit)
        except chess.engine.EngineTerminatedError as e:
            self.close()
            self._ensure()
            result = self._engine.play(board, limit)
        except chess.engine.EngineError as e:
            raise RuntimeError(f"Engine error: {e}") from e
        
        if result.move is None:
            raise RuntimeError(
                "Engine did not return a move."
            )
        
        return result.move

ENGINE = engineManager(STOCKFISH_PATH)