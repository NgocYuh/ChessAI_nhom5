from __future__ import annotations

import time
from dataclasses import dataclass, field

import chess

from .evaluation import MATE_SCORE, evaluate, evaluate_for_side

INF = 10**9
TT_EXACT = 0
TT_ALPHA = 1
TT_BETA = 2
MAX_PLY = 64
MAX_QS_PLY = 24
ASPIRATION_WINDOW = 30
NULL_MIN_DEPTH = 3
LMP_DEPTH = 3
CHECK_EXTENSION_LIMIT = 8
FULL_DEPTH_MOVES = 3

PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

PROMOTION_SCORE = {
    None: 0,
    chess.KNIGHT: 780,
    chess.BISHOP: 820,
    chess.ROOK: 860,
    chess.QUEEN: 980,
}


@dataclass
class SearchTrace:
    depth: int
    eval_cp: int
    best_move_uci: str
    nodes: int
    pv: list[str] = field(default_factory=list)


@dataclass
class SearchStats:
    nodes: int = 0
    depth_reached: int = 0
    best_score: int = 0
    best_move_uci: str = ""
    pv: list[str] = field(default_factory=list)
    traces: list[SearchTrace] = field(default_factory=list)


@dataclass
class TTEntry:
    depth: int
    score: int
    flag: int
    best_move: chess.Move | None


class ChessAI:
    def __init__(self) -> None:
        self.tt: dict[tuple, TTEntry] = {}
        self.killers: dict[int, list[chess.Move]] = {}
        self.history: dict[tuple[int, int, int], int] = {}
        self.countermove: dict[tuple[int, int], chess.Move] = {}
        self.deadline = 0.0
        self.stats = SearchStats()
        self.pv_table: dict[int, list[chess.Move]] = {}

    def choose_move(self, board: chess.Board, max_depth: int, think_time: float) -> tuple[chess.Move | None, SearchStats]:
        self.deadline = time.time() + max(0.08, think_time)
        self.stats = SearchStats()
        self.killers.clear()
        self.history.clear()
        self.countermove.clear()
        self.pv_table.clear()

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None, self.stats

        best_move = self._fallback_move(board, legal_moves)
        best_score = evaluate_for_side(board)
        aspiration = ASPIRATION_WINDOW

        for depth in range(1, max_depth + 1):
            if self._time_up():
                break

            alpha, beta = self._initial_window(best_score, depth, aspiration)

            try:
                while True:
                    completed, move, score = self._search_root(board, depth, alpha, beta)
                    if not completed:
                        return best_move, self.stats

                    if score <= alpha:
                        alpha = -INF
                        beta = score + aspiration
                        aspiration = min(600, aspiration * 2)
                        continue

                    if score >= beta:
                        alpha = score - aspiration
                        beta = INF
                        aspiration = min(600, aspiration * 2)
                        continue

                    break
            except RecursionError:
                return best_move, self.stats

            aspiration = ASPIRATION_WINDOW
            if move is None:
                continue

            best_move = move
            best_score = score
            pv = [item.uci() for item in self.pv_table.get(0, [])]
            self.stats.depth_reached = depth
            self.stats.best_score = score
            self.stats.best_move_uci = move.uci()
            self.stats.pv = pv
            self.stats.traces.append(
                SearchTrace(
                    depth=depth,
                    eval_cp=score,
                    best_move_uci=move.uci(),
                    nodes=self.stats.nodes,
                    pv=pv,
                )
            )

        return best_move, self.stats

    def should_claim_draw(self, board: chess.Board) -> bool:
        if not board.can_claim_draw():
            return False
        score = evaluate(board)
        if board.turn == chess.WHITE:
            return score <= 0
        return score >= 0

    def _initial_window(self, best_score: int, depth: int, aspiration: int) -> tuple[int, int]:
        if depth <= 1:
            return -INF, INF
        return best_score - aspiration, best_score + aspiration

    def _search_root(self, board: chess.Board, depth: int, alpha: int, beta: int) -> tuple[bool, chess.Move | None, int]:
        original_alpha = alpha
        best_score = -INF
        best_move = None
        tt_move = self._tt_move(board)
        previous_move = board.move_stack[-1] if board.move_stack else None
        ordered = self._order_moves(board, list(board.legal_moves), 0, tt_move, previous_move)
        first_move = True

        for index, move in enumerate(ordered):
            if self._time_up():
                return False, best_move, best_score

            board.push(move)
            extension = self._extension(board, move, 0)
            next_depth = depth - 1 + extension

            if first_move:
                score = -self._negamax(board, next_depth, -beta, -alpha, 1, True, move)
                first_move = False
            else:
                reduction = self._reduction(depth, index, move, board, True)
                reduced_depth = max(0, next_depth - reduction)
                score = -self._negamax(board, reduced_depth, -alpha - 1, -alpha, 1, True, move)
                if score > alpha:
                    score = -self._negamax(board, next_depth, -beta, -alpha, 1, True, move)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
                self.pv_table[0] = [move] + self.pv_table.get(1, [])

            alpha = max(alpha, score)
            if alpha >= beta:
                break

        if best_move is not None:
            self._store_tt(board, depth, best_score, original_alpha, beta, best_move)

        return True, best_move, best_score

    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        ply: int,
        allow_null: bool,
        previous_move: chess.Move | None,
    ) -> int:
        self.stats.nodes += 1

        if self._time_up() or ply >= MAX_PLY:
            return evaluate_for_side(board)
        if ply > 0 and board.is_repetition(2):
            return 0

        outcome = board.outcome(claim_draw=False)
        if outcome is not None:
            if outcome.winner is None:
                return 0
            return -MATE_SCORE + ply
        if board.can_claim_draw():
            return 0

        alpha = max(alpha, -MATE_SCORE + ply)
        beta = min(beta, MATE_SCORE - ply)
        if alpha >= beta:
            return alpha

        in_check = board.is_check()
        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply, in_check)

        tt_move, tt_score = self._probe_tt(board, depth, alpha, beta)
        if tt_score is not None:
            return tt_score

        if tt_move is None and depth >= 6:
            self._negamax(board, max(1, depth - 2), alpha, beta, ply, False, previous_move)
            tt_move = self._tt_move(board)

        static_eval = evaluate_for_side(board)
        if self._can_try_null_move(board, depth, beta, static_eval, allow_null, in_check):
            reduction = 3 if depth >= 6 else 2
            board.push(chess.Move.null())
            try:
                score = -self._negamax(board, depth - 1 - reduction, -beta, -beta + 1, ply + 1, False, None)
            finally:
                board.pop()
            if score >= beta:
                return beta

        if not in_check and depth <= 2 and static_eval - 90 * depth >= beta:
            return static_eval

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return -MATE_SCORE + ply if in_check else 0

        ordered = self._order_moves(board, legal_moves, ply, tt_move, previous_move)
        best_score = -INF
        best_move = None
        original_alpha = alpha
        searched_moves = 0
        first_move = True

        for index, move in enumerate(ordered):
            quiet = self._is_quiet(board, move)

            if self._late_move_prune(depth, index, move, board, in_check):
                continue
            if self._futility_skip(depth, alpha, static_eval, move, board, in_check):
                continue

            board.push(move)
            extension = self._extension(board, move, ply)
            new_depth = depth - 1 + extension

            if first_move:
                score = -self._negamax(board, new_depth, -beta, -alpha, ply + 1, True, move)
                first_move = False
            else:
                reduction = self._reduction(depth, searched_moves, move, board, False)
                reduced_depth = max(0, new_depth - reduction)
                score = -self._negamax(board, reduced_depth, -alpha - 1, -alpha, ply + 1, True, move)
                if reduction > 0 and score > alpha:
                    score = -self._negamax(board, new_depth, -alpha - 1, -alpha, ply + 1, True, move)
                if score > alpha:
                    score = -self._negamax(board, new_depth, -beta, -alpha, ply + 1, True, move)
            board.pop()

            searched_moves += 1

            if score > best_score:
                best_score = score
                best_move = move
                self.pv_table[ply] = [move] + self.pv_table.get(ply + 1, [])

            alpha = max(alpha, score)
            if alpha >= beta:
                if quiet:
                    self._store_killer(ply, move)
                    self._store_history(board, move, depth)
                    if previous_move is not None:
                        self.countermove[(previous_move.from_square, previous_move.to_square)] = move
                break

        self._store_tt(board, depth, best_score, original_alpha, beta, best_move)
        return best_score

    def _quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int, in_check: bool) -> int:
        self.stats.nodes += 1

        if self._time_up() or ply >= MAX_PLY or ply >= MAX_QS_PLY:
            return evaluate_for_side(board)

        if in_check:
            moves = list(board.legal_moves)
            if not moves:
                return -MATE_SCORE + ply
            ordered = self._order_moves(board, moves, ply, self._tt_move(board), None)
            limit = min(12, len(ordered))
            best = -INF
            for move in ordered[:limit]:
                board.push(move)
                score = -self._quiescence(board, -beta, -alpha, ply + 1, board.is_check())
                board.pop()
                if score >= beta:
                    return beta
                if score > best:
                    best = score
                if score > alpha:
                    alpha = score
            return best if best != -INF else alpha

        stand_pat = evaluate_for_side(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        tactical_moves = [move for move in board.legal_moves if self._is_qsearch_move(board, move, ply)]
        ordered = self._order_moves(board, tactical_moves, ply, self._tt_move(board), None)

        for move in ordered:
            if not self._passes_qsearch_margin(board, move, stand_pat, alpha):
                continue
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, ply + 1, board.is_check())
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def _order_moves(
        self,
        board: chess.Board,
        moves: list[chess.Move],
        ply: int,
        tt_move: chess.Move | None,
        previous_move: chess.Move | None,
    ) -> list[chess.Move]:
        killer_moves = self.killers.get(ply, [])
        counter = None
        if previous_move is not None:
            counter = self.countermove.get((previous_move.from_square, previous_move.to_square))

        def move_score(move: chess.Move) -> int:
            score = 0

            if tt_move is not None and move == tt_move:
                score += 20_000_000
            if counter is not None and move == counter:
                score += 3_000_000
            if move in killer_moves:
                score += 2_500_000 - 1_000 * killer_moves.index(move)

            if board.is_capture(move):
                score += 1_500_000 + self._capture_score(board, move)
            if move.promotion is not None:
                score += 1_200_000 + PROMOTION_SCORE.get(move.promotion, 0)
            if board.gives_check(move):
                score += 180_000

            mover = board.piece_at(move.from_square)
            if mover is not None:
                score += self.history.get((mover.piece_type, move.from_square, move.to_square), 0)

            score += self._positional_move_bonus(board, move)
            return score

        return sorted(moves, key=move_score, reverse=True)

    def _capture_score(self, board: chess.Board, move: chess.Move) -> int:
        attacker = board.piece_at(move.from_square)
        victim = board.piece_at(move.to_square)
        if attacker is None:
            return 0
        victim_value = 0
        if victim is not None:
            victim_value = PIECE_VALUE[victim.piece_type]
        elif board.is_en_passant(move):
            victim_value = PIECE_VALUE[chess.PAWN]
        attacker_value = PIECE_VALUE[attacker.piece_type]
        margin = victim_value - attacker_value
        score = 20 * victim_value - attacker_value
        if board.is_attacked_by(not board.turn, move.to_square):
            score += 3 * margin
        else:
            score += 60
        return score

    def _positional_move_bonus(self, board: chess.Board, move: chess.Move) -> int:
        bonus = 0
        piece = board.piece_at(move.from_square)
        if piece is None:
            return bonus

        to_sq = move.to_square
        if to_sq in (chess.D4, chess.E4, chess.D5, chess.E5):
            bonus += 40
        elif to_sq in (chess.C3, chess.F3, chess.C6, chess.F6, chess.C4, chess.F4, chess.C5, chess.F5):
            bonus += 18

        if piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            bonus += 12
        if piece.piece_type == chess.PAWN:
            rank = chess.square_rank(to_sq) if piece.color == chess.WHITE else 7 - chess.square_rank(to_sq)
            bonus += rank * 3
        if piece.piece_type == chess.KING and board.is_castling(move):
            bonus += 160
        if piece.piece_type == chess.ROOK and chess.square_file(move.from_square) != chess.square_file(to_sq):
            bonus += 8
        return bonus

    def _extension(self, board: chess.Board, move: chess.Move, ply: int) -> int:
        if ply < CHECK_EXTENSION_LIMIT and board.is_check():
            return 1
        if move.promotion is not None:
            return 1
        if self._is_passed_pawn_push(board, move):
            return 1
        return 0

    def _reduction(self, depth: int, searched_moves: int, move: chess.Move, board: chess.Board, root: bool) -> int:
        if depth < 3:
            return 0
        if searched_moves < FULL_DEPTH_MOVES:
            return 0
        if not self._is_quiet(board, move):
            return 0
        if board.is_check():
            return 0
        reduction = 1
        if depth >= 6:
            reduction += 1
        if depth >= 8 and searched_moves >= 8:
            reduction += 1
        if root:
            reduction = max(0, reduction - 1)
        return reduction

    def _late_move_prune(self, depth: int, index: int, move: chess.Move, board: chess.Board, in_check: bool) -> bool:
        if depth > LMP_DEPTH:
            return False
        if index < 8 + 4 * depth:
            return False
        if in_check:
            return False
        if not self._is_quiet(board, move):
            return False
        return True

    def _futility_skip(self, depth: int, alpha: int, static_eval: int, move: chess.Move, board: chess.Board, in_check: bool) -> bool:
        if depth > 2 or in_check:
            return False
        if not self._is_quiet(board, move):
            return False
        margin = 100 + 120 * depth
        return static_eval + margin <= alpha

    def _is_qsearch_move(self, board: chess.Board, move: chess.Move, ply: int) -> bool:
        if board.is_capture(move) or move.promotion is not None:
            return True
        if ply <= 2 and board.gives_check(move):
            return True
        return False

    def _passes_qsearch_margin(self, board: chess.Board, move: chess.Move, stand_pat: int, alpha: int) -> bool:
        if move.promotion is not None:
            return True
        if board.gives_check(move):
            return True
        victim = board.piece_at(move.to_square)
        gain = 0
        if victim is not None:
            gain = PIECE_VALUE[victim.piece_type]
        elif board.is_en_passant(move):
            gain = PIECE_VALUE[chess.PAWN]
        return stand_pat + gain + 140 >= alpha

    def _is_passed_pawn_push(self, board: chess.Board, move: chess.Move) -> bool:
        piece = board.piece_at(move.to_square)
        if piece is None or piece.piece_type != chess.PAWN:
            return False
        file_idx = chess.square_file(move.to_square)
        rank = chess.square_rank(move.to_square) if piece.color == chess.WHITE else 7 - chess.square_rank(move.to_square)
        if rank < 4:
            return False
        for opp in board.pieces(chess.PAWN, not piece.color):
            if abs(chess.square_file(opp) - file_idx) > 1:
                continue
            opp_rank = chess.square_rank(opp) if piece.color == chess.WHITE else 7 - chess.square_rank(opp)
            if opp_rank > rank:
                return False
        return True

    def _is_quiet(self, board: chess.Board, move: chess.Move) -> bool:
        return not board.is_capture(move) and move.promotion is None and not board.gives_check(move)

    def _can_try_null_move(
        self,
        board: chess.Board,
        depth: int,
        beta: int,
        static_eval: int,
        allow_null: bool,
        in_check: bool,
    ) -> bool:
        if not allow_null:
            return False
        if in_check:
            return False
        if depth < NULL_MIN_DEPTH:
            return False
        if beta >= MATE_SCORE // 2:
            return False
        if static_eval < beta:
            return False
        if not self._has_non_pawn_material(board, board.turn):
            return False
        return True

    def _has_non_pawn_material(self, board: chess.Board, color: chess.Color) -> bool:
        for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            if board.pieces(piece_type, color):
                return True
        return False

    def _probe_tt(self, board: chess.Board, depth: int, alpha: int, beta: int) -> tuple[chess.Move | None, int | None]:
        entry = self.tt.get(self._tt_key(board))
        if entry is None or entry.depth < depth:
            return None, None
        if entry.flag == TT_EXACT:
            return entry.best_move, entry.score
        if entry.flag == TT_ALPHA and entry.score <= alpha:
            return entry.best_move, entry.score
        if entry.flag == TT_BETA and entry.score >= beta:
            return entry.best_move, entry.score
        return entry.best_move, None

    def _store_tt(self, board: chess.Board, depth: int, score: int, alpha: int, beta: int, move: chess.Move | None) -> None:
        flag = TT_EXACT
        if score <= alpha:
            flag = TT_ALPHA
        elif score >= beta:
            flag = TT_BETA
        self.tt[self._tt_key(board)] = TTEntry(depth, score, flag, move)

    def _tt_move(self, board: chess.Board) -> chess.Move | None:
        entry = self.tt.get(self._tt_key(board))
        if entry is None:
            return None
        return entry.best_move

    def _tt_key(self, board: chess.Board) -> tuple:
        ep_square = board.ep_square if board.has_legal_en_passant() else None
        return (
            board.board_fen(),
            board.turn,
            board.castling_rights,
            ep_square,
        )

    def _fallback_move(self, board: chess.Board, legal_moves: list[chess.Move]) -> chess.Move:
        ordered = self._order_moves(board, legal_moves, 0, None, board.move_stack[-1] if board.move_stack else None)
        return ordered[0]

    def _store_killer(self, ply: int, move: chess.Move) -> None:
        killers = self.killers.setdefault(ply, [])
        if move in killers:
            return
        killers.insert(0, move)
        if len(killers) > 2:
            killers.pop()

    def _store_history(self, board: chess.Board, move: chess.Move, depth: int) -> None:
        mover = board.piece_at(move.from_square)
        if mover is None:
            return
        key = (mover.piece_type, move.from_square, move.to_square)
        self.history[key] = self.history.get(key, 0) + depth * depth

    def _time_up(self) -> bool:
        return time.time() >= self.deadline
