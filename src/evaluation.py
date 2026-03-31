from __future__ import annotations

import chess

from .config import PIECE_VALUES

MATE_SCORE = 100000
DRAW_SCORE = 0

PAWN_PST = [
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]
KNIGHT_PST = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
BISHOP_PST = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_PST = [
    0, 0, 5, 10, 10, 5, 0, 0,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    5, 10, 10, 10, 10, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]
QUEEN_PST = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]
KING_MID_PST = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
]
KING_END_PST = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]

PSTS = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
}

PHASE_WEIGHT = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
    chess.KING: 0,
}


def mirror(square: int) -> int:
    return chess.square_mirror(square)


def game_phase(board: chess.Board) -> int:
    phase = 0
    for piece_type, weight in PHASE_WEIGHT.items():
        phase += weight * (
            len(board.pieces(piece_type, chess.WHITE)) + len(board.pieces(piece_type, chess.BLACK))
        )
    return min(24, phase)


def piece_square_value(piece: chess.Piece, square: int, endgame_weight: int) -> int:
    if piece.piece_type == chess.KING:
        mid = KING_MID_PST[square] if piece.color == chess.WHITE else KING_MID_PST[mirror(square)]
        end = KING_END_PST[square] if piece.color == chess.WHITE else KING_END_PST[mirror(square)]
        value = (mid * endgame_weight + end * (24 - endgame_weight)) // 24
    else:
        table = PSTS[piece.piece_type]
        value = table[square] if piece.color == chess.WHITE else table[mirror(square)]
    return value if piece.color == chess.WHITE else -value


def material_balance(board: chess.Board) -> int:
    score = 0
    for piece_type, value in PIECE_VALUES.items():
        score += len(board.pieces(piece_type, chess.WHITE)) * value
        score -= len(board.pieces(piece_type, chess.BLACK)) * value
    return score


def piece_square_score(board: chess.Board, phase: int) -> int:
    score = 0
    for square, piece in board.piece_map().items():
        score += piece_square_value(piece, square, phase)
    return score


def bishop_pair(board: chess.Board) -> int:
    score = 0
    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += 35
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= 35
    return score


def mobility(board: chess.Board, color: chess.Color) -> int:
    saved_turn = board.turn
    board.turn = color
    moves = list(board.legal_moves)
    board.turn = saved_turn
    score = 0
    for move in moves:
        piece = board.piece_at(move.from_square)
        if piece is None:
            continue
        if piece.piece_type == chess.KNIGHT:
            score += 4
        elif piece.piece_type == chess.BISHOP:
            score += 5
        elif piece.piece_type == chess.ROOK:
            score += 3
        elif piece.piece_type == chess.QUEEN:
            score += 2
        else:
            score += 1
    return score


def mobility_score(board: chess.Board) -> int:
    return mobility(board, chess.WHITE) - mobility(board, chess.BLACK)


def pawn_structure(board: chess.Board, color: chess.Color) -> int:
    pawns = list(board.pieces(chess.PAWN, color))
    files = [chess.square_file(square) for square in pawns]
    score = 0

    for file_idx in range(8):
        count = files.count(file_idx)
        if count > 1:
            score -= 15 * (count - 1)

    for square in pawns:
        file_idx = chess.square_file(square)
        rank = chess.square_rank(square) if color == chess.WHITE else 7 - chess.square_rank(square)
        adjacent_files = {file_idx - 1, file_idx + 1}
        has_support = any(chess.square_file(pawn) in adjacent_files for pawn in pawns)
        if not has_support:
            score -= 10

        passed = True
        for enemy in board.pieces(chess.PAWN, not color):
            enemy_file = chess.square_file(enemy)
            if abs(enemy_file - file_idx) > 1:
                continue
            enemy_rank = chess.square_rank(enemy) if color == chess.WHITE else 7 - chess.square_rank(enemy)
            if enemy_rank > rank:
                passed = False
                break
        if passed:
            score += 22 + rank * 10

    return score


def rook_file_score(board: chess.Board, color: chess.Color) -> int:
    score = 0
    own_pawns = board.pieces(chess.PAWN, color)
    enemy_pawns = board.pieces(chess.PAWN, not color)
    for rook in board.pieces(chess.ROOK, color):
        file_idx = chess.square_file(rook)
        own_on_file = any(chess.square_file(pawn) == file_idx for pawn in own_pawns)
        enemy_on_file = any(chess.square_file(pawn) == file_idx for pawn in enemy_pawns)
        if not own_on_file and not enemy_on_file:
            score += 24
        elif not own_on_file:
            score += 12
        if color == chess.WHITE and chess.square_rank(rook) == 6:
            score += 10
        if color == chess.BLACK and chess.square_rank(rook) == 1:
            score += 10
    return score


def knight_outpost_score(board: chess.Board, color: chess.Color) -> int:
    score = 0
    enemy_pawns = board.pieces(chess.PAWN, not color)
    own_pawns = board.pieces(chess.PAWN, color)
    for knight in board.pieces(chess.KNIGHT, color):
        rank = chess.square_rank(knight) if color == chess.WHITE else 7 - chess.square_rank(knight)
        if rank < 3:
            continue
        file_idx = chess.square_file(knight)
        defended = False
        for pawn in own_pawns:
            if color == chess.WHITE and chess.square_rank(pawn) == chess.square_rank(knight) - 1 and abs(chess.square_file(pawn) - file_idx) == 1:
                defended = True
            if color == chess.BLACK and chess.square_rank(pawn) == chess.square_rank(knight) + 1 and abs(chess.square_file(pawn) - file_idx) == 1:
                defended = True
        if not defended:
            continue
        attacked_by_pawn = False
        for pawn in enemy_pawns:
            pawn_file = chess.square_file(pawn)
            pawn_rank = chess.square_rank(pawn)
            if color == chess.WHITE and pawn_rank > chess.square_rank(knight) and abs(pawn_file - file_idx) == 1:
                attacked_by_pawn = True
            if color == chess.BLACK and pawn_rank < chess.square_rank(knight) and abs(pawn_file - file_idx) == 1:
                attacked_by_pawn = True
        if not attacked_by_pawn:
            score += 18
    return score


def center_control_score(board: chess.Board) -> int:
    centers = (chess.D4, chess.E4, chess.D5, chess.E5)
    score = 0
    for square in centers:
        if board.is_attacked_by(chess.WHITE, square):
            score += 8
        if board.is_attacked_by(chess.BLACK, square):
            score -= 8
    return score


def development_score(board: chess.Board) -> int:
    score = 0
    if board.piece_at(chess.B1) != chess.Piece(chess.KNIGHT, chess.WHITE):
        score += 10
    if board.piece_at(chess.G1) != chess.Piece(chess.KNIGHT, chess.WHITE):
        score += 10
    if board.piece_at(chess.C1) != chess.Piece(chess.BISHOP, chess.WHITE):
        score += 8
    if board.piece_at(chess.F1) != chess.Piece(chess.BISHOP, chess.WHITE):
        score += 8
    if board.piece_at(chess.B8) != chess.Piece(chess.KNIGHT, chess.BLACK):
        score -= 10
    if board.piece_at(chess.G8) != chess.Piece(chess.KNIGHT, chess.BLACK):
        score -= 10
    if board.piece_at(chess.C8) != chess.Piece(chess.BISHOP, chess.BLACK):
        score -= 8
    if board.piece_at(chess.F8) != chess.Piece(chess.BISHOP, chess.BLACK):
        score -= 8
    return score


def king_safety(board: chess.Board, color: chess.Color, phase: int) -> int:
    if phase <= 6:
        return 0
    king_square = board.king(color)
    if king_square is None:
        return -MATE_SCORE

    score = 0
    file_idx = chess.square_file(king_square)
    rank_idx = chess.square_rank(king_square)
    step = 1 if color == chess.WHITE else -1
    shield_rank = rank_idx + step

    if 0 <= shield_rank < 8:
        for delta_file in (-1, 0, 1):
            current_file = file_idx + delta_file
            if not 0 <= current_file < 8:
                continue
            square = chess.square(current_file, shield_rank)
            piece = board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == chess.PAWN:
                score += 12
            else:
                score -= 10

    enemy = not color
    zone = board.attacks(king_square)
    zone |= chess.BB_SQUARES[king_square]
    attackers = 0
    pressure = 0
    for square, piece in board.piece_map().items():
        if piece.color != enemy:
            continue
        if board.attacks(square) & zone:
            attackers += 1
            if piece.piece_type == chess.QUEEN:
                pressure += 18
            elif piece.piece_type == chess.ROOK:
                pressure += 14
            elif piece.piece_type == chess.BISHOP:
                pressure += 10
            elif piece.piece_type == chess.KNIGHT:
                pressure += 10
    score -= attackers * 10 + pressure

    if board.has_kingside_castling_rights(color) or board.has_queenside_castling_rights(color):
        score += 10

    return score


def king_tropism(board: chess.Board, color: chess.Color) -> int:
    enemy_king = board.king(not color)
    if enemy_king is None:
        return 0
    score = 0
    for square in board.pieces(chess.QUEEN, color):
        score += max(0, 14 - chess.square_distance(square, enemy_king)) * 3
    for square in board.pieces(chess.ROOK, color):
        score += max(0, 14 - chess.square_distance(square, enemy_king)) * 2
    for square in board.pieces(chess.BISHOP, color):
        score += max(0, 14 - chess.square_distance(square, enemy_king))
    for square in board.pieces(chess.KNIGHT, color):
        score += max(0, 12 - chess.square_distance(square, enemy_king)) * 2
    return score


def evaluate(board: chess.Board) -> int:
    outcome = board.outcome(claim_draw=False)
    if outcome is not None:
        if outcome.winner is None:
            return DRAW_SCORE
        return MATE_SCORE if outcome.winner == chess.WHITE else -MATE_SCORE
    if board.can_claim_draw():
        return 0

    phase = game_phase(board)
    score = 0
    score += material_balance(board)
    score += piece_square_score(board, phase)
    score += mobility_score(board)
    score += bishop_pair(board)
    score += pawn_structure(board, chess.WHITE)
    score -= pawn_structure(board, chess.BLACK)
    score += rook_file_score(board, chess.WHITE)
    score -= rook_file_score(board, chess.BLACK)
    score += knight_outpost_score(board, chess.WHITE)
    score -= knight_outpost_score(board, chess.BLACK)
    score += center_control_score(board)
    if phase >= 14:
        score += development_score(board)
    score += king_safety(board, chess.WHITE, phase)
    score -= king_safety(board, chess.BLACK, phase)
    score += king_tropism(board, chess.WHITE)
    score -= king_tropism(board, chess.BLACK)
    return score


def evaluate_for_side(board: chess.Board) -> int:
    score = evaluate(board)
    return score if board.turn == chess.WHITE else -score
