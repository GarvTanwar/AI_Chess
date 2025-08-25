from dataclasses import dataclass

@dataclass
class botConfig:
    id: str
    name: str
    elo: int
    depth: int | None = None
    nodes: int | None = None
    movetime_ms: int | None = 250
    multipv: int = 1


BOTS: list[botConfig] = [
    botConfig(id="penny", name="Penny the Starter", elo=700, depth=6, movetime_ms=160, multipv=2),
    botConfig(id="nelson", name="Nelson the Rookie", elo=900, depth=8, movetime_ms=200, multipv=2),
    botConfig(id="sophia", name="Sophia the Club Player", elo=1200, depth=10, movetime_ms=250, multipv=2),
    botConfig(id="dmitri", name="Dmitri the Tactician", elo=1600, depth=12, movetime_ms=300, multipv=1),
    botConfig(id="houyifan", name="Hou Yifan the Expert", elo=2000, depth=14, movetime_ms=300, multipv=1),
    botConfig(id="magnus", name="Magnus the Master", elo=2300, depth=None, movetime_ms=400, multipv=1),
]

BOTS_ID = {b.id: b for b in BOTS}