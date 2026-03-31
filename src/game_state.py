from __future__ import annotations

import time
from dataclasses import dataclass, field

import chess

from .ai import SearchStats, SearchTrace
from .config import PIECE_VALUES


@dataclass
class GameOverState:
    over: bool = False
    title: str = ""
    detail: str = ""
    winner: bool | None = None


@dataclass
class AnalysisEntry:
    ply: int
    color: chess.Color
    move_uci: str
    move_san: str
    depth_reached: int
    nodes: int
    best_score: int
    traces: list[SearchTrace] = field(default_factory=list)


class ChessGame:
    def __init__(self, seconds: int = 300, human_color: chess.Color = chess.WHITE, mode: str = "pvm") -> None:
        self.seconds = seconds
        self.human_color = human_color
        self.mode = mode
        self.board = chess.Board()
        self.selected_square: int | None = None
        self.legal_targets: list[int] = []
        self.last_move: chess.Move | None = None
        self.pending_promotion_from: int | None = None
        self.pending_promotion_to: int | None = None
        self.timers = {chess.WHITE: float(seconds), chess.BLACK: float(seconds)}
        self.last_tick = time.time()
        self.result = GameOverState()
        self.timer_history: list[dict[chess.Color, float]] = []
        self.analysis_entries: list[AnalysisEntry] = []

    def restart(self, seconds: int | None = None, human_color: chess.Color | None = None, mode: str | None = None) -> None:
        if seconds is not None:
            self.seconds = seconds
        if human_color is not None:
            self.human_color = human_color
        if mode is not None:
            self.mode = mode

        self.board.reset()
        self.selected_square = None
        self.legal_targets = []
        self.last_move = None
        self.pending_promotion_from = None
        self.pending_promotion_to = None
        self.timers = {chess.WHITE: float(self.seconds), chess.BLACK: float(self.seconds)}
        self.last_tick = time.time()
        self.result = GameOverState()
        self.timer_history = []
        self.analysis_entries = []

    def color_is_human(self, color: chess.Color) -> bool:
        return self.mode == "pvm" and color == self.human_color

    def update_clock(self) -> None:
        if self.result.over:
            return

        now = time.time()
        elapsed = now - self.last_tick
        self.last_tick = now

        side = self.board.turn
        self.timers[side] = max(0.0, self.timers[side] - elapsed)
        if self.timers[side] > 0:
            return

        winner = not side
        winner_name = "White" if winner == chess.WHITE else "Black"
        loser_name = "White" if side == chess.WHITE else "Black"
        self.result = GameOverState(True, f"{winner_name} wins on time", f"{loser_name} flag fell.", winner)

    def set_selected(self, square: int | None) -> None:
        self.selected_square = square
        self.legal_targets = []
        if square is None:
            return
        self.legal_targets = [move.to_square for move in self.board.legal_moves if move.from_square == square]

    def click_square(self, square: int) -> bool:
        if self.result.over or not self.color_is_human(self.board.turn):
            return False

        piece = self.board.piece_at(square)

        if self.selected_square is None:
            if piece and piece.color == self.human_color:
                self.set_selected(square)
            return False

        if piece and piece.color == self.human_color:
            self.set_selected(square)
            return False

        move = self._resolve_move(self.selected_square, square)
        if move is None:
            self.set_selected(None)
            return False

        if self._needs_promotion(self.selected_square, square):
            self.pending_promotion_from = self.selected_square
            self.pending_promotion_to = square
            self.set_selected(None)
            return False

        played = self.push_move(move)
        self.set_selected(None)
        return played

    def choose_promotion(self, piece_type: int) -> bool:
        if self.pending_promotion_from is None or self.pending_promotion_to is None:
            return False

        move = chess.Move(self.pending_promotion_from, self.pending_promotion_to, promotion=piece_type)
        self.pending_promotion_from = None
        self.pending_promotion_to = None
        return self.push_move(move)

    def cancel_promotion(self) -> None:
        self.pending_promotion_from = None
        self.pending_promotion_to = None

    def _needs_promotion(self, from_sq: int, to_sq: int) -> bool:
        piece = self.board.piece_at(from_sq)
        if piece is None or piece.piece_type != chess.PAWN:
            return False
        rank = chess.square_rank(to_sq)
        return rank == 0 or rank == 7

    def _resolve_move(self, from_sq: int, to_sq: int) -> chess.Move | None:
        for move in self.board.legal_moves:
            if move.from_square == from_sq and move.to_square == to_sq:
                if move.promotion and move.promotion != chess.QUEEN:
                    continue
                return move
        return None

    def push_move(self, move: chess.Move) -> bool:
        if move not in self.board.legal_moves:
            return False

        self.timer_history.append(
            {
                chess.WHITE: self.timers[chess.WHITE],
                chess.BLACK: self.timers[chess.BLACK],
            }
        )
        self.board.push(move)
        self.last_move = move
        self.selected_square = None
        self.legal_targets = []
        self.pending_promotion_from = None
        self.pending_promotion_to = None
        self.last_tick = time.time()
        self.update_result()
        return True

    def record_ai_analysis(self, board_before: chess.Board, move: chess.Move, stats: SearchStats) -> None:
        try:
            move_san = board_before.san(move)
        except Exception:
            move_san = move.uci()

        traces = [
            SearchTrace(
                depth=trace.depth,
                eval_cp=trace.eval_cp,
                best_move_uci=trace.best_move_uci,
                nodes=trace.nodes,
                pv=list(trace.pv),
            )
            for trace in stats.traces
        ]

        self.analysis_entries.append(
            AnalysisEntry(
                ply=len(board_before.move_stack) + 1,
                color=board_before.turn,
                move_uci=move.uci(),
                move_san=move_san,
                depth_reached=stats.depth_reached,
                nodes=stats.nodes,
                best_score=stats.best_score,
                traces=traces,
            )
        )

    def analysis_for_color(self, color: chess.Color) -> list[AnalysisEntry]:
        return [entry for entry in self.analysis_entries if entry.color == color]

    def undo_pair(self) -> None:
        if self.result.over or not self.board.move_stack:
            return

        self.board.pop()
        if self.timer_history:
            last = self.timer_history.pop()
            self.timers[chess.WHITE] = last[chess.WHITE]
            self.timers[chess.BLACK] = last[chess.BLACK]

        if self.board.move_stack:
            self.board.pop()
            if self.timer_history:
                last = self.timer_history.pop()
                self.timers[chess.WHITE] = last[chess.WHITE]
                self.timers[chess.BLACK] = last[chess.BLACK]

        self.last_move = self.board.peek() if self.board.move_stack else None
        self.selected_square = None
        self.legal_targets = []
        self.pending_promotion_from = None
        self.pending_promotion_to = None
        self.result = GameOverState()
        self.last_tick = time.time()

        if len(self.analysis_entries) >= 2:
            self.analysis_entries = self.analysis_entries[:-2]
        else:
            self.analysis_entries = []

    def claim_draw(self) -> None:
        if self.result.over or not self.board.can_claim_draw():
            return
        self.result = GameOverState(True, "Draw claimed", "Draw claimed by repetition or fifty-move rule.", None)

    def update_result(self) -> None:
        if self.result.over:
            return

        outcome = self.board.outcome(claim_draw=True)
        if outcome is None:
            return

        termination = outcome.termination
        winner = outcome.winner
        self.result.over = True
        self.result.winner = winner

        if termination == chess.Termination.CHECKMATE:
            if winner == chess.WHITE:
                self.result.title = "White wins by checkmate"
                self.result.detail = "Black is checkmated."
            else:
                self.result.title = "Black wins by checkmate"
                self.result.detail = "White is checkmated."
            return

        if termination == chess.Termination.STALEMATE:
            self.result.title = "Draw by stalemate"
            self.result.detail = "No legal moves remain."
            return

        if termination == chess.Termination.INSUFFICIENT_MATERIAL:
            self.result.title = "Draw by insufficient material"
            self.result.detail = "No mating material remains."
            return

        if termination == chess.Termination.FIVEFOLD_REPETITION:
            self.result.title = "Draw by repetition"
            self.result.detail = "Fivefold repetition occurred."
            return

        if termination == chess.Termination.THREEFOLD_REPETITION:
            self.result.title = "Draw by repetition"
            self.result.detail = "Threefold repetition was claimed."
            return

        if termination == chess.Termination.SEVENTYFIVE_MOVES:
            self.result.title = "Draw by 75-move rule"
            self.result.detail = "Automatic draw."
            return

        if termination == chess.Termination.FIFTY_MOVES:
            self.result.title = "Draw by 50-move rule"
            self.result.detail = "Draw was claimed."
            return

        if winner is None:
            self.result.title = "Draw"
            self.result.detail = termination.name.replace("_", " ").title()
            return

        winner_name = "White" if winner == chess.WHITE else "Black"
        self.result.title = f"{winner_name} wins"
        self.result.detail = termination.name.replace("_", " ").title()

    def captured_pieces(self) -> dict[chess.Color, list[str]]:
        start_counts = {
            chess.WHITE: {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1},
            chess.BLACK: {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1},
        }
        current_counts = {
            chess.WHITE: {piece: len(self.board.pieces(piece, chess.WHITE)) for piece in start_counts[chess.WHITE]},
            chess.BLACK: {piece: len(self.board.pieces(piece, chess.BLACK)) for piece in start_counts[chess.BLACK]},
        }

        symbol_map = {
            chess.PAWN: "p",
            chess.KNIGHT: "n",
            chess.BISHOP: "b",
            chess.ROOK: "r",
            chess.QUEEN: "q",
        }
        captured = {chess.WHITE: [], chess.BLACK: []}

        for color in (chess.WHITE, chess.BLACK):
            for piece_type, total in start_counts[color].items():
                missing = total - current_counts[color][piece_type]
                captured[color].extend([symbol_map[piece_type]] * missing)

        return captured

    def material_advantage(self) -> tuple[int, int]:
        white_loss = 0
        black_loss = 0
        start_counts = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}

        for piece_type, total in start_counts.items():
            white_missing = total - len(self.board.pieces(piece_type, chess.WHITE))
            black_missing = total - len(self.board.pieces(piece_type, chess.BLACK))
            white_loss += white_missing * PIECE_VALUES[piece_type]
            black_loss += black_missing * PIECE_VALUES[piece_type]

        return black_loss - white_loss, white_loss - black_loss

    def side_name(self, color: chess.Color) -> str:
        return "WHITE" if color == chess.WHITE else "BLACK"
