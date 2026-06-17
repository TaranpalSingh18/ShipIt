import re
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Unicode Sanitizer ──────────────────────────────────────────
# fpdf2 built-in Helvetica font only supports Latin-1 characters.
# Map common Unicode chars to ASCII-safe equivalents.

UNICODE_MAP = {
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2022": "-",   # bullet
    "\u2026": "...", # ellipsis
    "\u00e9": "e", "\u00e8": "e", "\u00ea": "e",
    "\u00f9": "u", "\u00e0": "a", "\u00e2": "a",
    "\u00ed": "i", "\u00f3": "o", "\u00fa": "u",
    "\u00f1": "n", "\u00e7": "c",
}
UNICODE_TRANS = str.maketrans(UNICODE_MAP)


def sanitize(text: str) -> str:
    return text.translate(UNICODE_TRANS)


# ── Color Palette ──────────────────────────────────────────────
NAVY = (25, 45, 75)
MID_BLUE = (50, 85, 140)
LIGHT_GREY = (235, 235, 240)
DARK_GREY = (80, 80, 80)
ACCENT = (210, 85, 45)
WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
SECTION_BG = (240, 242, 248)  # subtle light blue for section fills


class TeardownPDF(FPDF):
    """Professional teardown PDF with cover page, headers, footers, and clean typography."""

    def __init__(self):
        super().__init__()
        self._section_count = 0
        self._toc_entries: list[tuple[str, int]] = []

    # ── Header / Footer ──────────────────────────────────────────

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*DARK_GREY)
        self.cell(0, 8, sanitize("Product Teardown Report"), align="L", new_x="LMARGIN")
        self.cell(0, 8, "Confidential", align="R", new_x="LMARGIN")
        self.ln(2)
        self.set_draw_color(*MID_BLUE)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*DARK_GREY)
        self.cell(0, 10, f"Page {self.page_no() - 1}", align="C")

    # ── Cover Page ───────────────────────────────────────────────

    def add_cover(self, product_name: str):
        self.add_page()

        # top accent bar
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 8, "F")

        # vertical spacing
        self.ln(50)

        # product title
        self.set_text_color(*NAVY)
        self.set_font("Helvetica", "B", 28)
        self.multi_cell(0, 14, sanitize(product_name), align="C")
        self.ln(4)

        # subtitle
        self.set_text_color(*MID_BLUE)
        self.set_font("Helvetica", "", 14)
        self.cell(0, 10, "Product Teardown & Competitive Analysis", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

        # separator line
        self.set_draw_color(*ACCENT)
        self.set_line_width(1)
        line_x = self.w / 2 - 25
        self.line(line_x, self.get_y(), line_x + 50, self.get_y())
        self.ln(10)

        # metadata
        self.set_text_color(*DARK_GREY)
        self.set_font("Helvetica", "", 10)
        today = datetime.now().strftime("%B %d, %Y")
        self.cell(0, 8, sanitize(f"Generated: {today}"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "Powered by ShipIt AI", align="C", new_x="LMARGIN", new_y="NEXT")

        # confidentiality notice
        self.ln(20)
        self.set_text_color(*DARK_GREY)
        self.set_font("Helvetica", "I", 8)
        self.multi_cell(0, 5, "CONFIDENTIAL - This document contains proprietary analysis.", align="C")

        # bottom bar
        self.set_fill_color(*NAVY)
        self.rect(0, self.h - 8, self.w, 8, "F")

    # ── Table of Contents ────────────────────────────────────────

    def add_toc_page(self):
        self.add_page()
        self.set_text_color(*NAVY)
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_draw_color(*MID_BLUE)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(8)

        for title, page_num in self._toc_entries:
            self.set_text_color(*BLACK)
            self.set_font("Helvetica", "", 11)
            text_w = self.get_string_width(title) + 2
            self.cell(text_w, 8, sanitize(title))
            dots_w = self.w - self.l_margin - self.r_margin - text_w - self.get_string_width(str(page_num)) - 4
            dot_count = max(0, int(dots_w / self.get_string_width(".")))
            self.set_text_color(*DARK_GREY)
            self.cell(dots_w, 8, "." * dot_count, align="R")
            self.set_text_color(*MID_BLUE)
            self.cell(0, 8, str(page_num), align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    # ── Section Helpers ──────────────────────────────────────────

    def add_section_heading(self, title: str, level: int = 1):
        self._section_count += 1
        page_num = self.page_no()
        self._toc_entries.append((title, page_num))

        if level == 1:
            self.ln(4)
            # filled bar background for main headings
            self.set_fill_color(*NAVY)
            self.set_text_color(*WHITE)
            self.set_font("Helvetica", "B", 15)
            self.cell(0, 10, f"  {sanitize(title)}", fill=True, new_x="LMARGIN", new_y="NEXT")
            self.ln(4)
        elif level == 2:
            self.ln(3)
            self.set_text_color(*MID_BLUE)
            self.set_font("Helvetica", "B", 13)
            self.cell(0, 8, sanitize(title), new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*MID_BLUE)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.l_margin + 30, self.get_y())
            self.ln(4)

    def add_body_text(self, text: str):
        self.set_text_color(*BLACK)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, sanitize(text))
        self.ln(2)

    def add_bullet(self, text: str, indent: int = 5):
        x = self.l_margin + indent
        self.set_x(x)
        self.set_text_color(*BLACK)
        self.set_font("Helvetica", "", 10)
        self.cell(self.get_string_width("- "), 5.5, "- ")

        parts = re.split(r"(\*\*.*?\*\*)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                bold_text = sanitize(part[2:-2])
                self.set_font("Helvetica", "B", 10)
                self.write(5.5, bold_text + " ")
            else:
                self.set_font("Helvetica", "", 10)
                self.write(5.5, sanitize(part) + " ")
        self.ln(5.5)

    def add_bold_line(self, label: str, value: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*BLACK)
        cleaned_label = sanitize(label)
        label_w = self.get_string_width(cleaned_label + " ") + 1
        self.cell(label_w, 6, cleaned_label + " ")
        self.set_font("Helvetica", "", 10)
        remaining_w = self.w - self.l_margin - self.r_margin - label_w
        self.multi_cell(remaining_w, 6, sanitize(value))
        self.ln(1)

    def render_markdown(self, markdown_text: str):
        """
        Parse markdown from the Jinja2 template and render using PDF helpers.
        """
        lines = markdown_text.strip().split("\n")
        i = 0
        while i < len(lines):
            raw = lines[i].rstrip()
            if not raw:
                i += 1
                continue

            # ── H1 headings ──
            if raw.startswith("# ") and not raw.startswith("##"):
                title = raw[2:].strip()
                if title.lower() != "table of contents":
                    self.add_section_heading(title, level=1)
                i += 1

            # ── H2 headings ──
            elif raw.startswith("## ") and not raw.startswith("###"):
                self.add_section_heading(raw[3:].strip(), level=2)
                i += 1

            # ── H3 headings ──
            elif raw.startswith("### "):
                self.set_text_color(*BLACK)
                self.set_font("Helvetica", "B", 11)
                self.ln(2)
                self.cell(0, 7, sanitize(raw[4:].strip()), new_x="LMARGIN", new_y="NEXT")
                self.ln(1)
                i += 1

            # ── Bullet points ──
            elif raw.startswith("- ") or raw.startswith("* "):
                self.add_bullet(raw[2:].strip())
                i += 1

            # ── Regular paragraph ──
            else:
                text = sanitize(raw)
                bold_match = re.match(r"^\*\*(.+?)\*\*:\s*(.*)", text)
                if bold_match:
                    self.add_bold_line(bold_match.group(1) + ":", bold_match.group(2))
                else:
                    self.add_body_text(text)
                i += 1


def md_to_pdf(markdown_text: str, filename: str) -> Path:
    """
    Convert markdown teardown text to a professionally structured PDF.

    Structure:
      1. Cover Page (product name, date)
      2. Table of Contents (auto-generated from headings)
      3. Content pages with styled sections, bullets, and body text

    Args:
        markdown_text: Raw markdown from the Jinja2 template.
        filename: Desired PDF filename (e.g. 'MyProduct_abc123.pdf').

    Returns:
        Absolute path to the generated PDF file.
    """
    # ── Extract product name ──
    product_name = "Product Teardown"
    for line in markdown_text.strip().split("\n"):
        if line.startswith("# ") and not line.startswith("##"):
            product_name = line[2:].strip()
            break

    # ── Pass 1: Render all content (builds TOC entry list) ──
    pdf = TeardownPDF()
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_cover(product_name)
    pdf.render_markdown(markdown_text)

    # ── Pass 2: Build final PDF with TOC inserted ──
    final_pdf = TeardownPDF()
    final_pdf.set_auto_page_break(auto=True, margin=22)

    # Cover
    final_pdf.add_cover(product_name)

    # TOC
    final_pdf._toc_entries = pdf._toc_entries
    final_pdf.add_toc_page()

    # Content
    final_pdf.render_markdown(markdown_text)

    filepath = OUTPUT_DIR / filename
    final_pdf.output(str(filepath))
    return filepath