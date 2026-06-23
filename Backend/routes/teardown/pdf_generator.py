import re
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

from schemas.teardown import ProductTeardown

from .pdf_visuals import (
    draw_competitor_row,
    draw_panel,
    draw_positioning_matrix,
    draw_value_proposition_canvas,
)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

UNICODE_MAP = {
    "\u2014": "-",
    "\u2013": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u00e9": "e", "\u00e8": "e", "\u00ea": "e",
    "\u00f9": "u", "\u00e0": "a", "\u00e2": "a",
    "\u00ed": "i", "\u00f3": "o", "\u00fa": "u",
    "\u00f1": "n", "\u00e7": "c",
}
UNICODE_TRANS = str.maketrans(UNICODE_MAP)

NAVY        = (15, 32, 68)
DEEP_BLUE   = (30, 64, 120)
ACCENT      = (232, 93, 44)
ACCENT_SOFT = (255, 247, 242)
MID_GREY    = (100, 116, 139)
DARK_TEXT   = (30, 41, 59)
WHITE       = (255, 255, 255)
SUCCESS     = (22, 101, 52)
SUCCESS_BG  = (240, 253, 246)
LIGHT_BG    = (252, 253, 255)
PANEL_BORDER= (213, 222, 235)

# Card accent palette — one per content category
CARD_PAIN   = (255, 237, 233)   # light red-orange  (pain/risk)
CARD_PAIN_B = (220, 80,  40)    # border
CARD_GAIN   = (232, 244, 255)   # light blue        (gain/feature)
CARD_GAIN_B = (30,  100, 200)
CARD_TARGET = (237, 245, 237)   # light green       (target)
CARD_TGT_B  = (34,  120,  60)
CARD_FLOW_B = (232, 93,   44)   # orange flow badge

MAX_BULLETS = 3


def sanitize(text: str) -> str:
    return text.translate(UNICODE_TRANS)


def _truncate(text: str, limit: int) -> str:
    text = sanitize(text.strip())
    if len(text) <= limit:
        return text
    cut = text[: limit - 3].rsplit(" ", 1)[0]
    return cut + "..."


def _strip_md_bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def _parse_markdown(markdown_text: str) -> tuple[str, dict[str, dict]]:
    """Parse teardown markdown into section name -> {paragraph, bullets, steps}."""
    product_name = "Product Teardown"
    sections: dict[str, dict] = {}

    current = ""
    for raw in markdown_text.strip().split("\n"):
        line = raw.rstrip()
        if not line or line == "---":
            continue

        if line.startswith("# ") and not line.startswith("##"):
            title = line[2:].strip()
            if not title.lower().startswith("part "):
                product_name = title
            continue

        if line.startswith("# Part"):
            continue

        if line.startswith("## ") and not line.startswith("###"):
            current = line[3:].strip()
            sections[current] = {"paragraph": "", "bullets": [], "steps": []}
            continue

        if not current:
            continue

        if line.startswith("- ") or line.startswith("* "):
            bullet = _strip_md_bold(line[2:].strip())
            if bullet.lower().startswith("gap:"):
                sections[current]["bullets"].append(f"Gap: {bullet[4:].strip()}")
            elif bullet.lower().startswith("evidence:"):
                sections[current]["bullets"].append(f"Evidence: {bullet[9:].strip()}")
            elif bullet.lower().startswith("our angle:"):
                sections[current]["bullets"].append(f"Angle: {bullet[10:].strip()}")
            else:
                sections[current]["bullets"].append(bullet)
            continue

        numbered = re.match(r"^(\d+)\.\s+(.+)", line)
        if numbered:
            sections[current]["steps"].append(numbered.group(2).strip())
            continue

        text = _strip_md_bold(line.strip())
        if sections[current]["paragraph"]:
            sections[current]["paragraph"] += " " + text
        else:
            sections[current]["paragraph"] = text

    return product_name, sections


def _section(sections: dict, *names: str) -> dict:
    for name in names:
        if name in sections:
            return sections[name]
    return {"paragraph": "", "bullets": [], "steps": []}


class InvestorOnePager(FPDF):
    """Single-page investor snapshot — card bullets, flow arrows, dynamic panels."""

    def __init__(self):
        super().__init__()
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=False)
        self._col_x = [10, 0]
        self._col_w = 0
        self._gutter = 5

    def _init_columns(self):
        usable = self.w - self.l_margin - self.r_margin - self._gutter
        self._col_w = usable / 2
        self._col_x = [self.l_margin, self.l_margin + self._col_w + self._gutter]

    # ── Section heading bar ───────────────────────────────────────
    def _bar_heading(self, title: str, x: float, y: float, w: float,
                     bg: tuple = NAVY, fg: tuple = WHITE) -> float:
        h = 6.0
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, "F")
        # left accent stripe
        self.set_fill_color(*ACCENT)
        self.rect(x, y, 2.5, h, "F")
        self.set_xy(x + 5, y + 1.3)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*fg)
        self.cell(w - 7, 4, sanitize(title.upper()))
        return y + h + 2

    # ── Label pill ────────────────────────────────────────────────
    def _label(self, x: float, y: float, w: float, text: str,
                color: tuple = DEEP_BLUE) -> float:
        self.set_xy(x, y)
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(*color)
        self.cell(w, 4, sanitize(text.upper()))
        return y + 4.5

    # ── Card bullet ───────────────────────────────────────────────
    def _card_bullet(self, x: float, y: float, w: float, text: str,
                     fill: tuple, border: tuple, icon_color: tuple,
                     max_chars: int = 52) -> float:
        """Single card-style bullet with left color stripe."""
        card_h = 7.5
        pad = 2.5
        stripe = 3.0

        self.set_fill_color(*fill)
        self.set_draw_color(*border)
        self.set_line_width(0.25)
        self.rect(x, y, w, card_h, style="DF")

        self.set_fill_color(*icon_color)
        self.rect(x, y, stripe, card_h, "F")

        self.set_xy(x + stripe + pad, y + 1.8)
        self.set_font("Helvetica", "", 7.0)
        self.set_text_color(*DARK_TEXT)
        clipped = sanitize(text)
        if len(clipped) > max_chars:
            clipped = clipped[: max_chars - 1].rsplit(" ", 1)[0] + "..."
        self.cell(w - stripe - pad * 2, 4, clipped)
        return y + card_h + 2

    # ── Flow step with arrow ──────────────────────────────────────
    def _flow_step(self, x: float, y: float, w: float,
                   num: int, text: str, is_last: bool = False) -> float:
        badge_r = 3.5
        badge_cx = x + badge_r + 1
        badge_cy = y + badge_r + 0.5
        step_h = badge_r * 2 + 1

        self.set_fill_color(*ACCENT)
        self.ellipse(badge_cx - badge_r, badge_cy - badge_r,
                     badge_r * 2, badge_r * 2, "F")
        self.set_xy(badge_cx - badge_r, badge_cy - badge_r + 0.5)
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(*WHITE)
        self.cell(badge_r * 2, badge_r * 2 - 1, str(num), align="C")

        self.set_xy(badge_cx + badge_r + 2, y + 1.5)
        self.set_font("Helvetica", "", 7.0)
        self.set_text_color(*DARK_TEXT)
        avail = w - badge_r * 2 - 6
        txt = sanitize(text)
        if len(txt) > 50:
            txt = txt[:49].rsplit(" ", 1)[0] + "..."
        self.cell(avail, 4, txt)

        next_y = y + step_h + 2
        if not is_last:
            ax = badge_cx
            self.set_draw_color(*ACCENT)
            self.set_line_width(0.4)
            self.line(ax, next_y - 1.5, ax, next_y + 1.5)
            next_y += 1.5
        return next_y

    # ── Exec summary text ─────────────────────────────────────────
    def _exec_text(self, x: float, y: float, w: float, text: str) -> float:
        if not text:
            return y
        # Measure height without rendering
        self.set_font("Helvetica", "BI", 7.5)
        lines = self.multi_cell(w - 8, 4, sanitize(text), split_only=True)
        box_h = len(lines) * 4 + 5

        # Draw box first (correct order: background → text)
        self.set_fill_color(235, 242, 255)
        self.set_draw_color(210, 225, 245)
        self.set_line_width(0.25)
        self.rect(x, y, w, box_h, style="DF")
        self.set_fill_color(*DEEP_BLUE)
        self.rect(x, y, 2.5, box_h, "F")

        # Render text on top
        self.set_xy(x + 5, y + 2)
        self.set_font("Helvetica", "BI", 7.5)
        self.set_text_color(*DARK_TEXT)
        self.multi_cell(w - 8, 4, sanitize(text))
        return y + box_h + 2

    # ── Panel outline (drawn BEFORE content, white fill) ─────────
    def _section_panel(self, x: float, y: float, w: float, h: float) -> None:
        self.set_fill_color(*WHITE)
        self.set_draw_color(*PANEL_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, h, style="DF")

    # ── Panel outline only (drawn AFTER content) ──────────────────
    def _outline_panel(self, x: float, y: float, w: float, h: float) -> None:
        self.set_draw_color(*PANEL_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, h, style="D")

    def render(self, product_name: str, sections: dict[str, dict],
               teardown: ProductTeardown | None = None):
        self.add_page()
        self._init_columns()
        full_w = self.w - self.l_margin - self.r_margin

        # ── Top banner ────────────────────────────────────────────
        # Gradient-feel: navy bar with product name left, tagline right
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 24, "F")
        # thin accent stripe at bottom of banner
        self.set_fill_color(*ACCENT)
        self.rect(0, 23, self.w, 1.5, "F")

        self.set_xy(self.l_margin, 5.5)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*WHITE)
        self.cell(full_w * 0.52, 7, sanitize(product_name))

        self.set_xy(self.l_margin, 14)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(180, 200, 230)
        self.cell(full_w * 0.28, 4, "INVESTOR ONE-PAGER")

        pitch = _section(sections, "Elevator Pitch")
        tagline = _truncate(
            pitch["paragraph"] or (pitch["bullets"][0] if pitch["bullets"] else ""),
            100,
        )
        if tagline:
            self.set_xy(self.l_margin + full_w * 0.30, 5)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(220, 232, 250)
            self.multi_cell(full_w * 0.68, 4.5, tagline, align="R")

        # ─────────────────────────────────────────────────────────
        y = 27
        has_comps = bool(teardown and teardown.competitors)

        exec_sec = _section(sections, "Executive Summary")
        pain_sec = _section(sections, "The Problem We Solve")
        cust_sec = _section(sections, "Target Customers")
        sol      = _section(sections, "Product Overview")
        journey  = _section(sections, "User Journey")
        comp     = _section(sections, "Key Competitors")
        pos_sec  = _section(sections, "Market Positioning")
        biz      = _section(sections, "Business Model")
        moats    = _section(sections, "Competitive Moats")
        growth   = _section(sections, "Growth Opportunities")
        risks    = _section(sections, "Key Risks")

        features = sol["bullets"] or ([sol["paragraph"]] if sol["paragraph"] else [])

        gain_canvas_items = [sanitize(f) for f in features[:2] if f]
        pain_canvas_items = [sanitize(p) for p in pain_sec["bullets"][:2] if p]
        job_canvas_items  = [sanitize(j) for j in cust_sec["bullets"][:3] if j]

        # ── Row 1: Opportunity | Solution (panels auto-size) ─────
        # Render content first into a scratch pass to measure height,
        # then draw white panel with border, then render for real.
        row1_top = y
        pad_inner = 2

        # --- LEFT: Opportunity ---
        y_left = row1_top + pad_inner
        y_left = self._bar_heading("Opportunity", self._col_x[0], y_left, self._col_w)
        exec_text = _truncate(exec_sec["paragraph"], 140)
        y_left = self._exec_text(self._col_x[0] + 2, y_left, self._col_w - 4, exec_text)
        if pain_sec["bullets"]:
            y_left = self._label(self._col_x[0] + 2, y_left, self._col_w, "Key Pains", CARD_PAIN_B)
            for item in pain_sec["bullets"][:2]:
                y_left = self._card_bullet(self._col_x[0] + 2, y_left, self._col_w - 4,
                                           item, CARD_PAIN, CARD_PAIN_B, CARD_PAIN_B)
        if cust_sec["bullets"]:
            y_left = self._label(self._col_x[0] + 2, y_left, self._col_w, "Target Customers", CARD_TGT_B)
            for item in cust_sec["bullets"][:2]:
                y_left = self._card_bullet(self._col_x[0] + 2, y_left, self._col_w - 4,
                                           item, CARD_TARGET, CARD_TGT_B, CARD_TGT_B)
        y_left += pad_inner

        # --- RIGHT: Solution ---
        y_right = row1_top + pad_inner
        y_right = self._bar_heading("Solution", self._col_x[1], y_right, self._col_w,
                                    bg=DEEP_BLUE)
        if features:
            y_right = self._label(self._col_x[1] + 2, y_right, self._col_w, "Core Features", CARD_GAIN_B)
            for item in features[:3]:
                y_right = self._card_bullet(self._col_x[1] + 2, y_right, self._col_w - 4,
                                            item, CARD_GAIN, CARD_GAIN_B, CARD_GAIN_B)
        if journey["steps"]:
            y_right = self._label(self._col_x[1] + 2, y_right, self._col_w, "User Flow", ACCENT)
            steps = journey["steps"][:4]
            for i, step in enumerate(steps):
                y_right = self._flow_step(self._col_x[1] + 2, y_right, self._col_w - 4,
                                          i + 1, step, is_last=(i == len(steps) - 1))
        y_right += pad_inner

        row1_h = max(y_left, y_right) - row1_top
        # Draw panels behind content (white fill — content was drawn already, so draw border only)
        self._outline_panel(self._col_x[0], row1_top, self._col_w, row1_h)
        self._outline_panel(self._col_x[1], row1_top, self._col_w, row1_h)
        y = row1_top + row1_h + 3

        # ── Value Proposition Canvas ──────────────────────────────
        if gain_canvas_items or pain_canvas_items or job_canvas_items:
            y = draw_value_proposition_canvas(
                self, self.l_margin, y, full_w, 52,
                gain_canvas_items, pain_canvas_items, job_canvas_items,
            )
            y += 2

        # ── Value Positioning Map ─────────────────────────────────
        if has_comps:
            y = draw_positioning_matrix(
                self, self.l_margin, y, full_w, 34, product_name, teardown,
            )
            y += 2

        # ── Row 2: Competition | Business Case (auto-size) ───────
        row2_top = y

        # --- LEFT: Competition ---
        y_left = row2_top + pad_inner
        y_left = self._bar_heading("Competition", self._col_x[0], y_left, self._col_w,
                                   bg=(80, 30, 80))
        if has_comps:
            y_left = draw_competitor_row(
                self, self._col_x[0] + 2, y_left, self._col_w - 4, teardown.competitors,
            )
        comp_lines = comp["bullets"][:2]
        for item in comp_lines:
            y_left = self._card_bullet(self._col_x[0] + 2, y_left, self._col_w - 4,
                                       item, (245, 237, 250), (140, 60, 160), (140, 60, 160))
        pos_text = _truncate(pos_sec["paragraph"], 120)
        if pos_text:
            self.set_xy(self._col_x[0] + 2, y_left)
            self.set_font("Helvetica", "I", 6.5)
            self.set_text_color(*MID_GREY)
            self.multi_cell(self._col_w - 4, 3.8, sanitize(pos_text))
            y_left = self.get_y() + 2
        y_left += pad_inner

        # --- RIGHT: Business Case ----
        y_right = row2_top + pad_inner
        y_right = self._bar_heading("Business Case", self._col_x[1], y_right, self._col_w,
                                    bg=(20, 80, 50))
        biz_text = _truncate(biz["paragraph"], 120)
        if biz_text:
            self.set_xy(self._col_x[1] + 2, y_right)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*DARK_TEXT)
            self.multi_cell(self._col_w - 4, 3.8, sanitize(biz_text))
            y_right = self.get_y() + 2
        if moats["bullets"]:
            y_right = self._label(self._col_x[1] + 2, y_right, self._col_w, "Moats", (20, 80, 50))
            for item in moats["bullets"][:2]:
                y_right = self._card_bullet(self._col_x[1] + 2, y_right, self._col_w - 4,
                                            item, CARD_TARGET, CARD_TGT_B, CARD_TGT_B)
        if risks["bullets"]:
            y_right = self._label(self._col_x[1] + 2, y_right, self._col_w, "Risks", CARD_PAIN_B)
            for item in risks["bullets"][:2]:
                y_right = self._card_bullet(self._col_x[1] + 2, y_right, self._col_w - 4,
                                            item, CARD_PAIN, CARD_PAIN_B, CARD_PAIN_B)
        y_right += pad_inner

        row2_h = max(y_left, y_right) - row2_top
        self._outline_panel(self._col_x[0], row2_top, self._col_w, row2_h)
        self._outline_panel(self._col_x[1], row2_top, self._col_w, row2_h)
        y = row2_top + row2_h + 3

        # ── Verdict strip ─────────────────────────────────────────
        verdict_sec = _section(sections, "Final Recommendation")
        verdict_text = _truncate(verdict_sec["paragraph"], 260)
        if not verdict_text and verdict_sec["bullets"]:
            verdict_text = _truncate(verdict_sec["bullets"][0], 260)

        if verdict_text:
            avail = self.h - 12 - y
            if avail > 10:
                self.set_font("Helvetica", "B", 7.5)
                split = self.multi_cell(full_w - 8, 4, sanitize(verdict_text), split_only=True)
                box_h = min(avail, len(split) * 4 + 12)

                self.set_fill_color(*SUCCESS_BG)
                self.set_draw_color(*SUCCESS)
                self.set_line_width(0.5)
                self.rect(self.l_margin, y, full_w, box_h, style="DF")
                # left accent bar
                self.set_fill_color(*SUCCESS)
                self.rect(self.l_margin, y, 3, box_h, "F")

                self.set_xy(self.l_margin + 6, y + 2)
                self.set_font("Helvetica", "B", 6.5)
                self.set_text_color(*SUCCESS)
                self.cell(full_w - 10, 4, "INVESTMENT VERDICT")
                self.set_xy(self.l_margin + 6, y + 7)
                self.set_font("Helvetica", "B", 7.5)
                self.set_text_color(*DARK_TEXT)
                self.multi_cell(full_w - 10, 4, sanitize(verdict_text))

        # ── Footer ──
        self.set_y(self.h - 10)
        self.set_draw_color(*MID_GREY)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*MID_GREY)
        today = datetime.now().strftime("%b %d, %Y")
        self.cell(
            0, 4,
            sanitize(f"ShipIt AI  |  {today}  |  Confidential - for discussion only"),
            align="C",
        )


def md_to_pdf(
    markdown_text: str,
    filename: str,
    teardown: ProductTeardown | None = None,
) -> Path:
    product_name, sections = _parse_markdown(markdown_text)
    if teardown and teardown.product_name:
        product_name = teardown.product_name

    pdf = InvestorOnePager()
    pdf.render(product_name, sections, teardown=teardown)

    filepath = OUTPUT_DIR / filename
    pdf.output(str(filepath))
    return filepath

print("pdf_generated")
