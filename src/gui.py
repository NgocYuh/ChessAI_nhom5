from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass

import chess
import pygame

from .ai import ChessAI
from .config import (
    ACCENT,
    ANALYSIS_BLACK,
    ANALYSIS_WHITE,
    BG,
    BOARD_SIZE,
    BUTTON,
    BUTTON_ALT,
    BUTTON_DANGER,
    BUTTON_OK,
    BUTTON_WARN,
    CAPTURE,
    CARD_BG,
    CHECK,
    DARK,
    DIFFICULTIES,
    FPS,
    GAME_MODES,
    HEIGHT,
    LIGHT,
    MOVE_DOT,
    MUTED,
    PANEL_ALT,
    PANEL_BG,
    PANEL_WIDTH,
    SELECT,
    SQUARE,
    TEXT,
    TIME_CONTROLS,
    WIDTH,
)
from .evaluation import evaluate
from .game_state import ChessGame


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    color: tuple[int, int, int]
    text_color: tuple[int, int, int] = TEXT
    enabled: bool = True

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        fill = self.color if self.enabled else (90, 90, 90)
        text_color = self.text_color if self.enabled else (170, 170, 170)
        pygame.draw.rect(screen, fill, self.rect, border_radius=12)
        text = font.render(self.label, True, text_color)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.enabled and self.rect.collidepoint(pos)


class ChessApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("NHÓM 5-CHESS GAME AI")
        self.windowed_size = (WIDTH, HEIGHT)
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE | pygame.WINDOWMAXIMIZED)
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()
        self.display_rect = self._compute_display_rect()
        self.clock = pygame.time.Clock()

        self.font_brand = self._make_font(32, bold=True)
        self.font_title = self._make_font(24, bold=True)
        self.font_big = self._make_font(20, bold=True)
        self.font = self._make_font(17, bold=True)
        self.font_small = self._make_font(15)
        self.font_tiny = self._make_font(13)

        self.scene = "menu"
        self.selected_mode = GAME_MODES["PLAYER VS MACHINE"]
        self.selected_time = "5 MIN"
        self.selected_difficulty = "MEDIUM"
        self.white_difficulty = "MEDIUM"
        self.black_difficulty = "MEDIUM"
        self.human_color = chess.WHITE
        self.team_members = [
            "Vũ Hoàng Long (24133035)",
            "Nguyễn Trung Khang (24133028)",
            "Hồ Trọng Sơn (24133049)",
            "Hoàng Ngọc Huy (24133023)",
        ]

        self.game = ChessGame(TIME_CONTROLS[self.selected_time], self.human_color, self.selected_mode)
        self.white_ai = ChessAI()
        self.black_ai = ChessAI()
        self.analysis_selected = {chess.WHITE: 0, chess.BLACK: 0}
        self.analysis_scroll = {chess.WHITE: 0, chess.BLACK: 0}
        self.piece_images = self._load_piece_images()
        self.promo_rects: list[tuple[pygame.Rect, int]] = []
        self.result_overlay_hidden = False
        self.result_close_button: Button | None = None

    def run(self) -> None:
        while True:
            if self.scene == "menu":
                self._menu_loop()
            elif self.scene == "analysis":
                self._analysis_loop()
            else:
                self._game_loop()

    def _handle_window_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED, pygame.WINDOWRESIZED):
            self.display_rect = self._compute_display_rect()
            return True
        return False

    def _menu_loop(self) -> None:
        center_x = WIDTH // 2

        while self.scene == "menu":
            mode_buttons = [
                Button(pygame.Rect(center_x - 235, 118, 220, 48), "PLAYER VS MACHINE", BUTTON_OK if self.selected_mode == "pvm" else BUTTON_ALT),
                Button(pygame.Rect(center_x + 15, 118, 220, 48), "MACHINE VS MACHINE", BUTTON_WARN if self.selected_mode == "mvm" else BUTTON_ALT),
            ]
            diff_buttons = [
                Button(pygame.Rect(center_x - 250 + i * 170, 388, 150, 44), name, {"EASY": BUTTON_OK, "MEDIUM": BUTTON_WARN, "HARD": BUTTON_DANGER}[name])
                for i, name in enumerate(DIFFICULTIES)
            ]
            side_buttons = [
                Button(pygame.Rect(center_x - 188, 494, 176, 42), "PLAY WHITE", BUTTON_OK if self.human_color == chess.WHITE else BUTTON_ALT),
                Button(pygame.Rect(center_x + 12, 494, 176, 42), "PLAY BLACK", BUTTON_DANGER if self.human_color == chess.BLACK else BUTTON_ALT),
            ]
            white_ai_buttons = [
                Button(pygame.Rect(center_x - 250 + i * 170, 384, 150, 42), name, BUTTON if self.white_difficulty == name else BUTTON_ALT)
                for i, name in enumerate(DIFFICULTIES)
            ]
            black_ai_buttons = [
                Button(pygame.Rect(center_x - 250 + i * 170, 474, 150, 42), name, BUTTON if self.black_difficulty == name else BUTTON_ALT)
                for i, name in enumerate(DIFFICULTIES)
            ]
            time_buttons = [
                Button(pygame.Rect(center_x - 250 + i * 170, 596, 150, 42), name, BUTTON if name == self.selected_time else BUTTON_ALT)
                for i, name in enumerate(TIME_CONTROLS)
            ]
            start_btn = Button(pygame.Rect(center_x - 210, 666, 420, 48), "START GAME", BUTTON_OK)

            for event in pygame.event.get():
                if self._handle_window_event(event):
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = self._map_mouse_pos(event.pos)

                    if mode_buttons[0].hit(pos):
                        self.selected_mode = "pvm"
                    elif mode_buttons[1].hit(pos):
                        self.selected_mode = "mvm"

                    for btn in diff_buttons:
                        if btn.hit(pos):
                            self.selected_difficulty = btn.label

                    for btn in white_ai_buttons:
                        if btn.hit(pos):
                            self.white_difficulty = btn.label

                    for btn in black_ai_buttons:
                        if btn.hit(pos):
                            self.black_difficulty = btn.label

                    for btn in time_buttons:
                        if btn.hit(pos):
                            self.selected_time = btn.label

                    if side_buttons[0].hit(pos):
                        self.human_color = chess.WHITE
                    elif side_buttons[1].hit(pos):
                        self.human_color = chess.BLACK

                    if start_btn.hit(pos):
                        self.game.restart(TIME_CONTROLS[self.selected_time], self.human_color, self.selected_mode)
                        self.analysis_selected = {chess.WHITE: 0, chess.BLACK: 0}
                        self.analysis_scroll = {chess.WHITE: 0, chess.BLACK: 0}
                        self.result_overlay_hidden = False
                        self.result_close_button = None
                        self.scene = "game"
                        return

            self.screen.fill(BG)
            self._draw_menu_background_decor()
            self._draw_center_text("NHÓM 5-CHESS GAME AI", 44, self.font_brand, ACCENT)
            self._draw_center_text("GAME MODE", 92, self.font_title, TEXT)

            for btn in mode_buttons:
                btn.draw(self.screen, self.font)

            self._draw_team_card(center_x)

            if self.selected_mode == "pvm":
                self._draw_center_text("BOT DIFFICULTY", 358, self.font_title, TEXT)
                for btn in diff_buttons:
                    if btn.label == self.selected_difficulty:
                        pygame.draw.rect(self.screen, SELECT, btn.rect.inflate(8, 8), border_radius=14)
                    btn.draw(self.screen, self.font)

                self._draw_center_text("PLAYER SIDE", 468, self.font_title, TEXT)
                for btn in side_buttons:
                    btn.draw(self.screen, self.font)
            else:
                self._draw_center_text("WHITE AI DIFFICULTY", 354, self.font_title, TEXT)
                for btn in white_ai_buttons:
                    btn.draw(self.screen, self.font)

                self._draw_center_text("BLACK AI DIFFICULTY", 444, self.font_title, TEXT)
                for btn in black_ai_buttons:
                    btn.draw(self.screen, self.font)


            self._draw_center_text("TIME CONTROL", 576, self.font_title, TEXT)
            for btn in time_buttons:
                btn.draw(self.screen, self.font)

            start_btn.draw(self.screen, self.font_big)

            self._present()
            self.clock.tick(FPS)

    def _game_loop(self) -> None:
        while self.scene == "game":
            self.game.update_clock()
            self.game.update_result()

            for event in pygame.event.get():
                if self._handle_window_event(event):
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.scene = "menu"
                        return
                    if event.key == pygame.K_F11:
                        self._toggle_maximize()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_game_click(self._map_mouse_pos(event.pos))

            if not self.game.result.over and not self.game.color_is_human(self.game.board.turn):
                board_before = self.game.board.copy(stack=True)
                ai = self.white_ai if board_before.turn == chess.WHITE else self.black_ai
                difficulty = self.selected_difficulty if self.selected_mode == "pvm" else (self.white_difficulty if board_before.turn == chess.WHITE else self.black_difficulty)
                cfg = DIFFICULTIES[difficulty]

                self._draw_game(thinking=True)
                self._present()
                pygame.event.pump()

                move, stats = ai.choose_move(board_before, cfg["depth"], cfg["think_time"])

                if move is None:
                    if ai.should_claim_draw(self.game.board):
                        self.game.claim_draw()
                else:
                    self.game.push_move(move)
                    self.game.record_ai_analysis(board_before, move, stats)

            self._draw_game(thinking=False)
            self._present()
            self.clock.tick(FPS)

    def _analysis_loop(self) -> None:
        while self.scene == "analysis":
            white_entries = self.game.analysis_for_color(chess.WHITE)
            black_entries = self.game.analysis_for_color(chess.BLACK)

            menu_btn = Button(pygame.Rect(WIDTH - 176, 18, 150, 40), "MAIN MENU", BUTTON_DANGER)
            back_btn = Button(pygame.Rect(WIDTH - 176, 66, 150, 40), "BACK BOARD", BUTTON)
            white_trace_rect = self._analysis_trace_rect(26, 118, 510, 616)
            black_trace_rect = self._analysis_trace_rect(564, 118, 510, 616)

            for event in pygame.event.get():
                if self._handle_window_event(event):
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.scene = "game"
                        return
                    if event.key == pygame.K_F11:
                        self._toggle_maximize()
                    if event.key == pygame.K_w:
                        self.analysis_selected[chess.WHITE] = max(0, self.analysis_selected[chess.WHITE] - 1)
                        self.analysis_scroll[chess.WHITE] = 0
                    if event.key == pygame.K_s:
                        self.analysis_selected[chess.WHITE] = min(max(0, len(white_entries) - 1), self.analysis_selected[chess.WHITE] + 1)
                        self.analysis_scroll[chess.WHITE] = 0
                    if event.key == pygame.K_UP:
                        self.analysis_selected[chess.BLACK] = max(0, self.analysis_selected[chess.BLACK] - 1)
                        self.analysis_scroll[chess.BLACK] = 0
                    if event.key == pygame.K_DOWN:
                        self.analysis_selected[chess.BLACK] = min(max(0, len(black_entries) - 1), self.analysis_selected[chess.BLACK] + 1)
                        self.analysis_scroll[chess.BLACK] = 0

                if event.type == pygame.MOUSEWHEEL:
                    mouse_pos = self._map_mouse_pos(pygame.mouse.get_pos())
                    if white_trace_rect.collidepoint(mouse_pos):
                        self._scroll_analysis_trace(chess.WHITE, white_entries, -event.y)
                    elif black_trace_rect.collidepoint(mouse_pos):
                        self._scroll_analysis_trace(chess.BLACK, black_entries, -event.y)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mapped_pos = self._map_mouse_pos(event.pos)
                    if menu_btn.hit(mapped_pos):
                        self.scene = "menu"
                        return
                    if back_btn.hit(mapped_pos):
                        self.scene = "game"
                        return

            self.screen.fill(BG)
            self._draw_center_text("POST-GAME ANALYSIS", 26, self.font_title, TEXT)
            menu_btn.draw(self.screen, self.font)
            back_btn.draw(self.screen, self.font)
            self._draw_analysis_column(26, 118, 510, 616, chess.WHITE, white_entries, self.analysis_selected[chess.WHITE])
            self._draw_analysis_column(564, 118, 510, 616, chess.BLACK, black_entries, self.analysis_selected[chess.BLACK])
            self._present()
            self.clock.tick(FPS)

    def _draw_analysis_column(self, x: int, y: int, w: int, h: int, color: chess.Color, entries: list, selected: int) -> None:
        panel_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=16)

        header_color = ANALYSIS_WHITE if color == chess.WHITE else ANALYSIS_BLACK
        header_rect = pygame.Rect(x + 12, y + 12, w - 24, 52)
        pygame.draw.rect(self.screen, header_color, header_rect, border_radius=12)

        title = "WHITE ENGINE" if color == chess.WHITE else "BLACK ENGINE"
        hint = "W / S" if color == chess.WHITE else "UP / DOWN"
        self.screen.blit(self.font_big.render(title, True, TEXT), (header_rect.x + 14, header_rect.y + 9))
        summary = self.font_small.render(f"{len(entries)} recorded moves", True, TEXT)
        self.screen.blit(summary, (header_rect.x + 14, header_rect.y + 30))
        hint_text = self.font_small.render(hint, True, TEXT)
        self.screen.blit(hint_text, (header_rect.right - hint_text.get_width() - 14, header_rect.y + 17))

        list_rect = pygame.Rect(x + 12, y + 76, w - 24, 228)
        pygame.draw.rect(self.screen, PANEL_ALT, list_rect, border_radius=12)
        self.screen.blit(self.font_small.render("MOVE LIST", True, MUTED), (list_rect.x + 10, list_rect.y + 8))

        start = max(0, min(selected - 3, max(0, len(entries) - 6)))
        visible = entries[start:start + 6]
        for row_index, entry in enumerate(visible):
            real_index = start + row_index
            row_rect = pygame.Rect(list_rect.x + 8, list_rect.y + 30 + row_index * 32, list_rect.w - 16, 26)
            row_fill = (88, 96, 120) if real_index == selected else CARD_BG
            pygame.draw.rect(self.screen, row_fill, row_rect, border_radius=8)

            eval_text = self._format_eval(entry.best_score)
            meta_text = f"d{entry.depth_reached} • {self._format_nodes(entry.nodes)}"
            meta_surface = self.font_tiny.render(meta_text, True, MUTED)
            eval_surface = self.font_small.render(eval_text, True, ACCENT if entry.best_score >= 0 else (255, 190, 190))

            reserved_right = max(meta_surface.get_width(), 76) + 140
            move_width = max(120, row_rect.w - 20 - reserved_right)
            move_text = self._fit_text(self._format_analysis_move(entry), self.font_small, move_width)

            self.screen.blit(self.font_small.render(move_text, True, TEXT), (row_rect.x + 10, row_rect.y + 5))
            self.screen.blit(eval_surface, (row_rect.right - 120, row_rect.y + 5))
            self.screen.blit(meta_surface, (row_rect.right - meta_surface.get_width() - 10, row_rect.y + 7))

        detail_rect = pygame.Rect(x + 12, y + 318, w - 24, h - 330)
        pygame.draw.rect(self.screen, PANEL_ALT, detail_rect, border_radius=12)

        if not entries:
            self.screen.blit(self.font.render("No engine records for this side.", True, MUTED), (detail_rect.x + 14, detail_rect.y + 18))
            return

        entry = entries[min(selected, len(entries) - 1)]
        board_before = self._board_before_entry(entry)
        latest_pv = entry.traces[-1].pv if entry.traces else []

        move_line = self._fit_text(self._format_analysis_move(entry), self.font_big, detail_rect.w - 28)
        uci_line = f"Move path: {self._format_move_arrow(entry.move_uci)}"
        engine_line = f"Engine score: {self._format_eval(entry.best_score)}"

        self.screen.blit(self.font_big.render(move_line, True, TEXT), (detail_rect.x + 14, detail_rect.y + 14))
        self.screen.blit(self.font_small.render(self._fit_text(uci_line, self.font_small, detail_rect.w - 28), True, MUTED), (detail_rect.x + 14, detail_rect.y + 42))
        self.screen.blit(self.font_small.render(engine_line, True, ACCENT if entry.best_score >= 0 else (255, 190, 190)), (detail_rect.x + 14, detail_rect.y + 62))

        stats = [
            ("DEPTH REACHED", str(entry.depth_reached)),
            ("NODES", self._format_nodes(entry.nodes)),
            ("ENGINE SCORE", self._format_eval(entry.best_score)),
        ]
        card_w = (detail_rect.w - 40) // 3
        for idx, (label, value) in enumerate(stats):
            card_x = detail_rect.x + 14 + idx * (card_w + 6)
            card_y = detail_rect.y + 94
            card_rect = pygame.Rect(card_x, card_y, card_w, 48)
            pygame.draw.rect(self.screen, CARD_BG, card_rect, border_radius=10)
            self.screen.blit(self.font_tiny.render(label, True, MUTED), (card_rect.x + 10, card_rect.y + 7))
            value_text = self._fit_text(value, self.font_small, card_rect.w - 20)
            self.screen.blit(self.font_small.render(value_text, True, TEXT), (card_rect.x + 10, card_rect.y + 24))

        self.screen.blit(self.font_small.render("BEST CHOICE AT EACH DEPTH", True, ACCENT), (detail_rect.x + 14, detail_rect.y + 164))
        trace_rect = self._analysis_trace_rect(x, y, w, h)
        pygame.draw.rect(self.screen, CARD_BG, trace_rect, border_radius=10)

        row_height = 34
        visible_rows = max(1, trace_rect.h // row_height)
        max_scroll = max(0, len(entry.traces) - visible_rows)
        self.analysis_scroll[color] = max(0, min(self.analysis_scroll[color], max_scroll))
        scroll = self.analysis_scroll[color]

        if not entry.traces:
            self.screen.blit(self.font_small.render("No depth-by-depth data stored.", True, MUTED), (trace_rect.x + 10, trace_rect.y + 10))
            return

        for idx, trace in enumerate(entry.traces[scroll:scroll + visible_rows]):
            row_y = trace_rect.y + 6 + idx * row_height
            row_rect = pygame.Rect(trace_rect.x + 6, row_y, trace_rect.w - 14, 30)
            pygame.draw.rect(self.screen, PANEL_ALT, row_rect, border_radius=8)
            self._draw_trace_row(row_rect, trace)

        if max_scroll > 0:
            thumb_h = max(24, int(trace_rect.h * visible_rows / len(entry.traces)))
            thumb_y = trace_rect.y + int((trace_rect.h - thumb_h) * scroll / max_scroll)
            pygame.draw.rect(self.screen, (108, 114, 138), pygame.Rect(trace_rect.right - 6, thumb_y, 4, thumb_h), border_radius=3)

    def _handle_game_click(self, pos: tuple[int, int]) -> None:
        if self.game.result.over and not self.result_overlay_hidden:
            if self.result_close_button and self.result_close_button.hit(pos):
                self.result_overlay_hidden = True
            return

        if self.game.pending_promotion_from is not None:
            self._handle_promotion_click(pos)
            return

        if pos[0] < BOARD_SIZE:
            square = self._mouse_to_square(pos)
            self.game.click_square(square)
            return

        buttons = self._side_buttons()
        if buttons["undo"].hit(pos):
            self.game.undo_pair()
            self.result_overlay_hidden = False
        elif buttons["switch"].hit(pos) and self.selected_mode == "pvm":
            self.human_color = not self.human_color
            self.game.restart(TIME_CONTROLS[self.selected_time], self.human_color, self.selected_mode)
            self.result_overlay_hidden = False
            self.result_close_button = None
        elif buttons["restart"].hit(pos):
            self.game.restart(TIME_CONTROLS[self.selected_time], self.human_color, self.selected_mode)
            self.result_overlay_hidden = False
            self.result_close_button = None
        elif buttons["menu"].hit(pos):
            self.scene = "menu"
        elif buttons["claim"].hit(pos):
            self.game.claim_draw()
            self.result_overlay_hidden = False
        elif buttons["analysis"].hit(pos):
            self.scene = "analysis"

    def _side_buttons(self) -> dict[str, Button]:
        base_x = BOARD_SIZE + 32
        return {
            "undo": Button(pygame.Rect(base_x, 430, PANEL_WIDTH - 64, 44), "UNDO MOVE", BUTTON_ALT),
            "switch": Button(pygame.Rect(base_x, 486, PANEL_WIDTH - 64, 44), "SWITCH SIDE", BUTTON, enabled=self.selected_mode == "pvm"),
            "restart": Button(pygame.Rect(base_x, 542, PANEL_WIDTH - 64, 44), "RESTART", BUTTON_OK),
            "menu": Button(pygame.Rect(base_x, 598, PANEL_WIDTH - 64, 44), "MAIN MENU", BUTTON_DANGER),
            "claim": Button(pygame.Rect(base_x, 654, PANEL_WIDTH - 64, 34), "CLAIM DRAW", BUTTON_WARN, enabled=self.game.board.can_claim_draw() and not self.game.result.over),
            "analysis": Button(pygame.Rect(base_x, 698, PANEL_WIDTH - 64, 34), "POST-GAME ANALYSIS", BUTTON, enabled=bool(self.game.analysis_entries)),
        }

    def _draw_game(self, thinking: bool) -> None:
        self.result_close_button = None
        self.screen.fill(BG)
        self._draw_board()
        self._draw_side_panel(thinking)
        if self.game.pending_promotion_from is not None:
            self._draw_promotion_overlay()
        if self.game.result.over and not self.result_overlay_hidden:
            self._draw_result_overlay()

    def _draw_board(self) -> None:
        for rank in range(8):
            for file_idx in range(8):
                rect = pygame.Rect(file_idx * SQUARE, rank * SQUARE, SQUARE, SQUARE)
                color = LIGHT if (rank + file_idx) % 2 == 0 else DARK
                pygame.draw.rect(self.screen, color, rect)

        if self.game.last_move:
            for sq in (self.game.last_move.from_square, self.game.last_move.to_square):
                x, y = self._square_to_xy(sq)
                pygame.draw.rect(self.screen, (250, 246, 170), pygame.Rect(x, y, SQUARE, SQUARE), 4)

        if self.game.board.is_check():
            king_sq = self.game.board.king(self.game.board.turn)
            if king_sq is not None:
                x, y = self._square_to_xy(king_sq)
                pygame.draw.rect(self.screen, CHECK, pygame.Rect(x, y, SQUARE, SQUARE), 6)

        if self.game.selected_square is not None:
            x, y = self._square_to_xy(self.game.selected_square)
            pygame.draw.rect(self.screen, SELECT, pygame.Rect(x, y, SQUARE, SQUARE), 6)
            for sq in self.game.legal_targets:
                cx, cy = self._square_to_xy(sq)
                center = (cx + SQUARE // 2, cy + SQUARE // 2)
                if self.game.board.piece_at(sq):
                    pygame.draw.circle(self.screen, CAPTURE, center, 18, 4)
                else:
                    pygame.draw.circle(self.screen, MOVE_DOT, center, 10)

        for square, piece in self.game.board.piece_map().items():
            x, y = self._square_to_xy(square)
            self._draw_piece_sprite(piece, x, y)

        for file_idx in range(8):
            file_label = self.font_small.render(chr(ord("a") + file_idx), True, (235, 235, 235))
            self.screen.blit(file_label, (file_idx * SQUARE + 6, BOARD_SIZE - 18))
        for rank_idx in range(8):
            rank_label = self.font_small.render(str(8 - rank_idx), True, (235, 235, 235))
            self.screen.blit(rank_label, (4, rank_idx * SQUARE + 2))

    def _draw_side_panel(self, thinking: bool) -> None:
        panel = pygame.Rect(BOARD_SIZE, 0, PANEL_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, PANEL_BG, panel)

        mode_text = "PLAYER VS MACHINE" if self.selected_mode == "pvm" else "MACHINE VS MACHINE"
        turn_text = "White's Turn" if self.game.board.turn == chess.WHITE else "Black's Turn"
        self.screen.blit(self.font.render(mode_text, True, ACCENT), (BOARD_SIZE + 24, 24))
        self.screen.blit(self.font_title.render(turn_text, True, TEXT), (BOARD_SIZE + 24, 52))

        if self.selected_mode == "pvm":
            info = f"You: {self.game.side_name(self.human_color)} | Bot: {self.selected_difficulty}"
        else:
            info = f"White AI: {self.white_difficulty} | Black AI: {self.black_difficulty}"
        self.screen.blit(self.font_small.render(info, True, MUTED), (BOARD_SIZE + 24, 84))

        if thinking and not self.game.result.over:
            self.screen.blit(self.font_small.render("Engine is thinking...", True, MUTED), (BOARD_SIZE + 24, 108))

        self._draw_clock(BOARD_SIZE + 24, 138, chess.WHITE)
        self._draw_clock(BOARD_SIZE + 24, 188, chess.BLACK)
        self._draw_eval_box(BOARD_SIZE + 24, 250)
        self._draw_captured_box(BOARD_SIZE + 24, 318)

        for button in self._side_buttons().values():
            button.draw(self.screen, self.font)

    def _draw_clock(self, x: int, y: int, color: chess.Color) -> None:
        rect = pygame.Rect(x, y, PANEL_WIDTH - 48, 38)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=10)
        label = "WHITE" if color == chess.WHITE else "BLACK"
        text = f"{label}: {self._format_time(self.game.timers[color])}"
        color_text = ACCENT if self.game.board.turn == color and not self.game.result.over else TEXT
        self.screen.blit(self.font.render(text, True, color_text), (x + 12, y + 9))

    def _draw_eval_box(self, x: int, y: int) -> None:
        rect = pygame.Rect(x, y, PANEL_WIDTH - 48, 54)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=12)
        score = evaluate(self.game.board)
        self.screen.blit(self.font.render(f"Engine Eval: {score / 100:+.2f}", True, TEXT), (x + 12, y + 10))
        info = "Positive = White better | Negative = Black better"
        self.screen.blit(self.font_small.render(info, True, MUTED), (x + 12, y + 31))

    def _draw_captured_box(self, x: int, y: int) -> None:
        rect = pygame.Rect(x, y, PANEL_WIDTH - 48, 92)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=12)

        captured = self.game.captured_pieces()
        white_adv, black_adv = self.game.material_advantage()

        self.screen.blit(self.font_small.render("Captured by White", True, TEXT), (x + 12, y + 10))
        self.screen.blit(self.font_small.render("Captured by Black", True, TEXT), (x + 12, y + 50))

        self._draw_piece_line(x + 126, y + 4, [sym for sym in captured[chess.BLACK]], white_adv)
        self._draw_piece_line(x + 126, y + 44, [sym.upper() for sym in captured[chess.WHITE]], black_adv)

    def _draw_piece_line(self, x: int, y: int, symbols: list[str], advantage: int) -> None:
        for i, sym in enumerate(symbols[:10]):
            self._draw_small_piece_sprite(sym, x + 10 + i * 20, y + 12)
        if advantage > 0:
            adv_text = self.font_small.render(f"+{advantage // 100}", True, ACCENT)
            self.screen.blit(adv_text, (x + 214, y + 6))

    def _draw_promotion_overlay(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(260, 270, 500, 130)
        pygame.draw.rect(self.screen, PANEL_BG, box, border_radius=18)
        self.screen.blit(self.font_title.render("Choose Promotion", True, TEXT), (410, 290))

        color = self.game.board.turn
        choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        self.promo_rects = []

        for i, piece_type in enumerate(choices):
            rect = pygame.Rect(312 + i * 95, 334, 70, 42)
            pygame.draw.rect(self.screen, BUTTON, rect, border_radius=12)
            symbol = chess.Piece(piece_type, color).symbol()
            self._draw_small_piece_sprite(symbol, rect.centerx, rect.centery)
            self.promo_rects.append((rect, piece_type))

    def _draw_result_overlay(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(220, 230, 540, 180)
        pygame.draw.rect(self.screen, PANEL_BG, box, border_radius=18)

        close_btn = Button(pygame.Rect(box.right - 54, box.y + 14, 36, 30), "X", BUTTON_DANGER)
        close_btn.draw(self.screen, self.font)
        self.result_close_button = close_btn

        title = self.font_title.render(self.game.result.title, True, TEXT)
        detail = self.font.render(self.game.result.detail, True, MUTED)
        hint = self.font_small.render("Use POST-GAME ANALYSIS to compare both engines after the match.", True, TEXT)
        close_hint = self.font_small.render("Close to view the final board position.", True, MUTED)

        self.screen.blit(title, title.get_rect(center=(490, 280)))
        self.screen.blit(detail, detail.get_rect(center=(490, 318)))
        self.screen.blit(hint, hint.get_rect(center=(490, 352)))
        self.screen.blit(close_hint, close_hint.get_rect(center=(490, 380)))

    def _handle_promotion_click(self, pos: tuple[int, int]) -> None:
        for rect, piece_type in self.promo_rects:
            if rect.collidepoint(pos):
                self.game.choose_promotion(piece_type)
                return
        self.game.cancel_promotion()

    def _mouse_to_square(self, pos: tuple[int, int]) -> int:
        file_idx = pos[0] // SQUARE
        rank_idx = pos[1] // SQUARE
        if self.human_color == chess.WHITE:
            return chess.square(file_idx, 7 - rank_idx)
        return chess.square(7 - file_idx, rank_idx)

    def _square_to_xy(self, square: int) -> tuple[int, int]:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        if self.human_color == chess.WHITE:
            return file_idx * SQUARE, (7 - rank_idx) * SQUARE
        return (7 - file_idx) * SQUARE, rank_idx * SQUARE

    def _draw_center_text(self, text: str, y: int, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, text_surface.get_rect(center=(WIDTH // 2, y)))

    def _draw_menu_background_decor(self) -> None:
        top_bar = pygame.Rect(88, 168, WIDTH - 176, 176)
        pygame.draw.rect(self.screen, PANEL_BG, top_bar, border_radius=22)
        pygame.draw.rect(self.screen, PANEL_ALT, top_bar.inflate(-20, -20), 2, border_radius=18)

        self._draw_decor_piece("Q", 132, 256, 96, 42)
        self._draw_decor_piece("N", WIDTH - 132, 256, 104, 34)
        self._draw_decor_piece("k", 248, 214, 54, 28)
        self._draw_decor_piece("r", WIDTH - 248, 214, 54, 24)

    def _make_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        names = [
            "segoeui",
            "segoe ui",
            "tahoma",
            "arial",
            "arial unicode ms",
            "noto sans",
            "dejavu sans",
        ]
        font_path = next((pygame.font.match_font(name, bold=bold) for name in names if pygame.font.match_font(name, bold=bold)), None)
        if font_path:
            return pygame.font.Font(font_path, size)
        return pygame.font.SysFont(None, size, bold=bold)

    def _draw_clipped_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect) -> None:
        label = font.render(self._fit_text(text, font, rect.w), True, color)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(rect)
        self.screen.blit(label, (rect.x, rect.y))
        self.screen.set_clip(previous_clip)

    def _draw_trace_row(self, row_rect: pygame.Rect, trace) -> None:
        text_y = row_rect.y + 6
        depth_rect = pygame.Rect(row_rect.x + 10, text_y, 42, 16)
        nodes_rect = pygame.Rect(row_rect.right - 92, text_y, 80, 16)
        eval_rect = pygame.Rect(nodes_rect.x - 66, text_y, 58, 16)
        best_rect = pygame.Rect(depth_rect.right + 12, text_y, eval_rect.x - depth_rect.right - 22, 16)

        self._draw_clipped_text(f"d{trace.depth}", self.font_tiny, MUTED, depth_rect)
        self._draw_clipped_text(self._format_move_arrow(trace.best_move_uci), self.font_tiny, TEXT, best_rect)
        eval_color = ACCENT if trace.eval_cp >= 0 else (255, 190, 190)
        self._draw_clipped_text(self._format_eval(trace.eval_cp), self.font_tiny, eval_color, eval_rect)
        self._draw_clipped_text(self._format_nodes(trace.nodes), self.font_tiny, MUTED, nodes_rect)

    def _draw_team_card(self, center_x: int) -> None:
        card_rect = pygame.Rect(center_x - 300, 186, 600, 136)
        inner_rect = card_rect.inflate(-22, -20)
        pygame.draw.rect(self.screen, CARD_BG, card_rect, border_radius=18)
        pygame.draw.rect(self.screen, PANEL_ALT, inner_rect, 2, border_radius=16)

        self._draw_center_text("TEAM MEMBERS", 208, self.font_big, TEXT)
        positions = [
            (center_x - 150, 240),
            (center_x + 150, 240),
            (center_x - 150, 272),
            (center_x + 150, 272),
        ]
        for member, pos in zip(self.team_members, positions):
            text_surface = self.font_small.render(member, True, TEXT)
            self.screen.blit(text_surface, text_surface.get_rect(center=pos))

        self._draw_decor_piece("B", card_rect.x + 34, card_rect.centery + 10, 42, 52)
        self._draw_decor_piece("n", card_rect.right - 34, card_rect.centery + 10, 42, 52)

    def _draw_decor_piece(self, symbol: str, cx: int, cy: int, size: int, alpha: int) -> None:
        image = self.piece_images[symbol]
        scaled = pygame.transform.smoothscale(image, (size, size))
        scaled.set_alpha(alpha)
        rect = scaled.get_rect(center=(cx, cy))
        self.screen.blit(scaled, rect)

    def _format_time(self, seconds: float) -> str:
        total = max(0, int(math.ceil(seconds)))
        return f"{total // 60:02d}:{total % 60:02d}"

    def _format_eval(self, score: int) -> str:
        return f"{score / 100:+.2f}"

    def _format_nodes(self, nodes: int) -> str:
        if nodes >= 1_000_000:
            return f"{nodes / 1_000_000:.2f}M"
        if nodes >= 1_000:
            return f"{nodes / 1_000:.1f}k"
        return str(nodes)

    def _analysis_trace_rect(self, x: int, y: int, w: int, h: int) -> pygame.Rect:
        detail_rect = pygame.Rect(x + 12, y + 318, w - 24, h - 330)
        return pygame.Rect(detail_rect.x + 14, detail_rect.y + 188, detail_rect.w - 28, detail_rect.bottom - detail_rect.y - 202)

    def _scroll_analysis_trace(self, color: chess.Color, entries: list, delta: int) -> None:
        if not entries:
            self.analysis_scroll[color] = 0
            return
        selected = min(self.analysis_selected[color], len(entries) - 1)
        entry = entries[selected]
        visible_rows = max(1, self._analysis_trace_rect(26, 118, 510, 616).h // 34)
        max_scroll = max(0, len(entry.traces) - visible_rows)
        self.analysis_scroll[color] = max(0, min(self.analysis_scroll[color] + delta, max_scroll))

    def _fit_text(self, text: str, font: pygame.font.Font, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        ellipsis = "..."
        trimmed = text
        while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
            trimmed = trimmed[:-1]
        return (trimmed + ellipsis) if trimmed else ellipsis

    def _format_move_arrow(self, move_uci: str) -> str:
        if len(move_uci) < 4:
            return move_uci
        base = f"{move_uci[:2]}->{move_uci[2:4]}"
        if len(move_uci) == 5:
            promo_map = {"q": "=Q", "r": "=R", "b": "=B", "n": "=N"}
            return base + promo_map.get(move_uci[4].lower(), f"={move_uci[4].upper()}")
        return base

    def _format_analysis_move(self, entry) -> str:
        move_no = (entry.ply + 1) // 2
        prefix = f"{move_no}." if entry.color == chess.WHITE else f"{move_no}..."
        return f"{prefix} {self._format_move_arrow(entry.move_uci)}"

    def _board_before_entry(self, target_entry) -> chess.Board:
        board = chess.Board()
        for entry in self.game.analysis_entries:
            if entry is target_entry:
                break
            move = chess.Move.from_uci(entry.move_uci)
            if move in board.legal_moves:
                board.push(move)
        return board

    def _uci_to_san(self, board: chess.Board, move_uci: str) -> str:
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            return self._format_move_arrow(move_uci)
        if move not in board.legal_moves:
            return self._format_move_arrow(move_uci)
        try:
            return board.san(move)
        except Exception:
            return self._format_move_arrow(move_uci)

    def _pv_to_san(self, board: chess.Board, pv: list[str]) -> list[str]:
        san_moves: list[str] = []
        for move_uci in pv:
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                break
            if move not in board.legal_moves:
                break
            try:
                san = board.san(move)
            except Exception:
                break
            san_moves.append(san)
            board.push(move)
        return san_moves

    def _pv_to_arrow(self, board: chess.Board, pv: list[str]) -> list[str]:
        arrow_moves: list[str] = []
        for move_uci in pv:
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                break
            if move not in board.legal_moves:
                break
            arrow_moves.append(self._format_move_arrow(move_uci))
            board.push(move)
        return arrow_moves

    def _compute_display_rect(self) -> pygame.Rect:
        window_w, window_h = self.window.get_size()
        scale = min(window_w / WIDTH, window_h / HEIGHT)
        scaled_w = max(1, int(WIDTH * scale))
        scaled_h = max(1, int(HEIGHT * scale))
        offset_x = (window_w - scaled_w) // 2
        offset_y = (window_h - scaled_h) // 2
        return pygame.Rect(offset_x, offset_y, scaled_w, scaled_h)

    def _map_mouse_pos(self, pos: tuple[int, int]) -> tuple[int, int]:
        rect = self.display_rect
        if rect.w <= 0 or rect.h <= 0:
            return pos
        x = (pos[0] - rect.x) * WIDTH / rect.w
        y = (pos[1] - rect.y) * HEIGHT / rect.h
        return max(0, min(WIDTH - 1, int(x))), max(0, min(HEIGHT - 1, int(y)))

    def _present(self) -> None:
        self.display_rect = self._compute_display_rect()
        scaled = pygame.transform.smoothscale(self.screen, self.display_rect.size)
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, self.display_rect.topleft)
        pygame.display.flip()

    def _toggle_maximize(self) -> None:
        flags = self.window.get_flags()
        if flags & pygame.WINDOWMAXIMIZED:
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        else:
            current_size = self.window.get_size()
            if current_size[0] > 0 and current_size[1] > 0:
                self.windowed_size = current_size
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE | pygame.WINDOWMAXIMIZED)
        self.display_rect = self._compute_display_rect()

    def _load_piece_images(self) -> dict[str, pygame.Surface]:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "assets", "pieces_sprite.png"),
            os.path.join(base_dir, "pieces_sprite.png"),
        ]
        sprite_path = next((path for path in candidates if os.path.exists(path)), candidates[0])
        sheet = pygame.image.load(sprite_path).convert_alpha()

        cols = 6
        rows = 2
        cell_w = sheet.get_width() // cols
        cell_h = sheet.get_height() // rows
        order = [chess.KING, chess.QUEEN, chess.BISHOP, chess.KNIGHT, chess.ROOK, chess.PAWN]

        images: dict[str, pygame.Surface] = {}
        for row in range(rows):
            color = chess.WHITE if row == 0 else chess.BLACK
            for col, piece_type in enumerate(order):
                rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
                cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                cell.blit(sheet, (0, 0), rect)
                target = int(SQUARE * 0.84)
                scaled = pygame.transform.smoothscale(cell, (target, target))
                images[chess.Piece(piece_type, color).symbol()] = scaled
        return images

    def _draw_piece_sprite(self, piece: chess.Piece, x: int, y: int) -> None:
        image = self.piece_images[piece.symbol()]
        rect = image.get_rect(center=(x + SQUARE // 2, y + SQUARE // 2))
        self.screen.blit(image, rect)

    def _draw_small_piece_sprite(self, symbol: str, cx: int, cy: int) -> None:
        image = self.piece_images[symbol]
        scaled = pygame.transform.smoothscale(image, (20, 20))
        rect = scaled.get_rect(center=(cx, cy))
        self.screen.blit(scaled, rect)
