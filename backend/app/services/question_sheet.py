"""Export a course's quiz questions to an Excel sheet and import them back.

One row per question. The sheet round-trips: export, edit in Excel, import. Rows are matched to
sub-topics by title, and to existing questions by the `Question ID` column (or, failing that, by identical
question text), so re-importing never duplicates.

Imports are all-or-nothing: if any row is wrong, nothing is saved and every problem is reported with its row
number, so a half-imported sheet cannot happen. `dry_run` checks the file and reports what would change.
"""

import io
import re
from dataclasses import dataclass, field
from typing import Literal

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.core import cache
from app.core.config import get_settings
from app.models import Course, Question, Subtopic, User
from app.models.base import LEVELS, new_id
from app.services.courses import CourseError, _owned

MAX_ROWS = 5000
MAX_OPTIONS = 10
MIN_OPTION_COLUMNS = 4
MAX_TEXT, MAX_OPTION = 2000, 500
MAX_REPORTED_ERRORS = 100
SHEET = "Questions"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
LETTERS = "ABCDEFGHIJ"
Mode = Literal["merge", "replace"]

FIXED_HEAD = ["Topic", "Sub-topic", "Level", "Question"]
FIXED_TAIL = ["Correct answer", "Explanation", "Question ID"]


def norm(s: str) -> str:
    """Compare text ignoring case and spacing only. Punctuation matters: in a programming course
    `i++` and `i--` are different answers."""
    return " ".join(s.lower().split())


# ------------------------------------------------------------------ export


def _put(ws, row: int, col: int, value) -> None:
    """Write text as text. openpyxl treats a string starting with "=" as a formula, which would let
    question text run as a spreadsheet formula when someone opens the file."""
    cell = ws.cell(row=row, column=col, value=value)
    if isinstance(value, str):
        cell.data_type = "s"
        cell.alignment = Alignment(wrap_text=True, vertical="top")


def _head(ws, headers: list[str]) -> None:
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="7A1F2B")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    widths = {"Topic": 22, "Sub-topic": 26, "Level": 13, "Question": 60, "Correct answer": 10,
              "Explanation": 50, "Question ID": 14}
    for i, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(h, 30 if h.startswith("Option") else 14)


def _instructions(wb: Workbook) -> None:
    ws = wb.create_sheet("Instructions")
    lines = [
        "How to use this sheet",
        "",
        "• One row per question, on the “Questions” sheet. Keep the header row as it is.",
        "• Topic and Sub-topic must match the course outline exactly (capitals do not matter).",
        f"• Level: one of {', '.join(LEVELS)}. Blank means beginner.",
        "• Fill at least two options. Leave unused option columns empty.",
        "• Correct answer: the letter of the right option, for example B.",
        "• Question ID: leave blank for a new question. Keep it on exported rows to update them.",
        "• Questions with the same text as an existing one in the same sub-topic are skipped, not duplicated.",
        "• Import “Add and update” never deletes anything. “Replace” makes each sub-topic in the file",
        "  contain exactly the questions in the file.",
        "• Save as .xlsx (not .xls or .csv).",
    ]
    for i, line in enumerate(lines, 1):
        ws.cell(row=i, column=1, value=line).font = Font(bold=(i == 1), size=13 if i == 1 else 11)
    ws.column_dimensions["A"].width = 100


def _build(rows: list[list], n_options: int) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    headers = FIXED_HEAD + [f"Option {LETTERS[i]}" for i in range(n_options)] + FIXED_TAIL
    _head(ws, headers)
    for r, row in enumerate(rows, 2):
        for c, v in enumerate(row, 1):
            _put(ws, r, c, v)
    _instructions(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_course(db: Session, user: User, course_id: str) -> tuple[bytes, str]:
    course = _owned(db, user, course_id)
    n = min(MAX_OPTIONS, max([MIN_OPTION_COLUMNS] + [len(q.options) for t in course.topics
                                                       for s in t.subtopics for q in s.questions]))
    rows = []
    for t in course.topics:
        for s in t.subtopics:
            for q in s.questions:
                opts = list(q.options)[:n] + [""] * (n - len(q.options))
                rows.append([t.title, s.title, q.level, q.text, *opts, LETTERS[q.answer_index], q.explanation, q.id])
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", course.code).strip("-") or "course"
    return _build(rows, n), f"{safe}-questions.xlsx"


def template() -> bytes:
    example = [
        ["Relational model", "Keys", "beginner", "Which key uniquely identifies a row in a table?",
         "Primary key", "Foreign key", "Candidate index", "Composite view", "A",
         "A primary key is chosen to identify each row.", ""],
        ["Relational model", "Keys", "intermediate", "What does a foreign key enforce?",
         "Sort order", "Referential integrity", "Faster joins", "Column types", "B",
         "It makes a value match a row in another table.", ""],
    ]
    return _build(example, MIN_OPTION_COLUMNS)


# ------------------------------------------------------------------ import


@dataclass
class Row:
    number: int
    topic: str
    subtopic: str
    level: str
    text: str
    options: list[str]
    answer: int
    explanation: str
    qid: str
    raw_answer: str = ""


@dataclass
class Report:
    dry_run: bool
    mode: str
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    skipped: int = 0
    errors: list[dict] = field(default_factory=list)
    total_errors: int = 0
    warnings: list[str] = field(default_factory=list)
    subtopics: list[dict] = field(default_factory=list)

    def error(self, row: int, message: str) -> None:
        self.total_errors += 1
        if len(self.errors) < MAX_REPORTED_ERRORS:
            self.errors.append({"row": row, "message": message})

    def out(self) -> dict:
        return {**self.__dict__, "saved": not self.dry_run and not self.total_errors}


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def read_rows(data: bytes, report: Report) -> list[Row]:
    limit = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise CourseError(f"The file is larger than {get_settings().max_upload_mb} MB.", 413)
    if not data[:2] == b"PK":  # .xlsx is a zip; .xls and .csv are not
        raise CourseError("Please upload an .xlsx file (Excel workbook). Save .xls or .csv files as .xlsx first.")
    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - any parse failure is just "not a usable workbook"
        raise CourseError("That file could not be read as an Excel workbook.") from e
    ws = wb[SHEET] if SHEET in wb.sheetnames else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = next(it, None)
    if header is None:
        raise CourseError("The sheet is empty.")
    cols = {_cell(h).lower(): i for i, h in enumerate(header) if _cell(h)}
    opt_cols = sorted((i, m.group(1).upper()) for h, i in cols.items() if (m := re.fullmatch(r"option ([a-j])", h)))
    missing = [h for h in ("sub-topic", "question", "correct answer") if h not in cols]
    if missing or len(opt_cols) < 2:
        need = [h.capitalize() for h in missing] + (["Option A and Option B"] if len(opt_cols) < 2 else [])
        raise CourseError("The header row is missing: " + ", ".join(need) + ". Download the template to start from.")

    def get(r, name: str) -> str:
        i = cols.get(name)
        return _cell(r[i]) if i is not None and i < len(r) else ""

    rows: list[Row] = []
    for number, r in enumerate(it, 2):
        if number - 1 > MAX_ROWS:
            raise CourseError(f"Too many rows: the limit is {MAX_ROWS} questions per file.")
        if not any(_cell(v) for v in r):
            continue
        opts = [(letter, _cell(r[i]) if i < len(r) else "") for i, letter in opt_cols]
        # Keep option positions: blank options are only allowed after the last filled one.
        filled = [(letter, t) for letter, t in opts if t]
        shown = [t for _, t in opts[: max(LETTERS.index(letter) for letter, _ in filled) + 1]] if filled else []
        raw = get(r, "correct answer")
        rows.append(Row(number, get(r, "topic"), get(r, "sub-topic"), get(r, "level").lower() or "beginner",
                        get(r, "question"), shown, _answer_index(raw, shown), get(r, "explanation"),
                        get(r, "question id"), raw))
    wb.close()
    return rows


def _answer_index(raw: str, options: list[str]) -> int:
    """A letter (B), or failing that the exact text of an option. -1 when it cannot be understood."""
    letter = raw.strip().upper().rstrip(".)")
    if len(letter) == 1 and letter in LETTERS:
        return LETTERS.index(letter)
    for i, o in enumerate(options):
        if raw and norm(o) == norm(raw):
            return i
    return -1


def _check(row: Row, report: Report) -> bool:
    n = report.total_errors
    if not row.subtopic:
        report.error(row.number, "Sub-topic is empty.")
    if not row.text:
        report.error(row.number, "Question is empty.")
    elif len(row.text) > MAX_TEXT:
        report.error(row.number, f"Question is longer than {MAX_TEXT} characters.")
    if row.level not in LEVELS:
        report.error(row.number, f"Level “{row.level}” is not one of {', '.join(LEVELS)}.")
    if len(row.options) < 2:
        report.error(row.number, "Fill in at least two options.")
    elif any(not o for o in row.options):
        report.error(row.number, "There is an empty option between filled ones. Fill it or move the later ones up.")
    elif len({norm(o) for o in row.options}) != len(row.options):
        report.error(row.number, "Two options are the same.")
    elif any(len(o) > MAX_OPTION for o in row.options):
        report.error(row.number, f"An option is longer than {MAX_OPTION} characters.")
    if not 0 <= row.answer < len(row.options):
        report.error(row.number, f"Correct answer “{row.raw_answer}” must be the letter of a filled option.")
    return report.total_errors == n


def import_sheet(db: Session, user: User, course_id: str, data: bytes, mode: Mode = "merge",
                 dry_run: bool = False) -> dict:
    course: Course = _owned(db, user, course_id)
    report = Report(dry_run=dry_run, mode=mode)
    rows = read_rows(data, report)
    if not rows:
        raise CourseError("The sheet has a header but no questions.")

    by_title: dict[tuple[str, str], list[Subtopic]] = {}
    by_sub: dict[str, list[Subtopic]] = {}
    for t in course.topics:
        for s in t.subtopics:
            by_title.setdefault((norm(t.title), norm(s.title)), []).append(s)
            by_sub.setdefault(norm(s.title), []).append(s)
    known = {q.id: (s, q) for t in course.topics for s in t.subtopics for q in s.questions}

    plan: dict[str, list[Row]] = {}
    subs: dict[str, Subtopic] = {}
    for row in rows:
        ok = _check(row, report)
        found = by_title.get((norm(row.topic), norm(row.subtopic))) if row.topic else by_sub.get(norm(row.subtopic))
        if row.subtopic and not found:
            report.error(row.number, f"No sub-topic “{row.subtopic}”"
                         + (f" in topic “{row.topic}”" if row.topic else "") + " in this course.")
        elif found and len(found) > 1:
            report.error(row.number, f"“{row.subtopic}” matches more than one sub-topic; fill in the Topic column.")
        if row.qid and row.qid not in known:
            report.error(row.number, "Question ID does not belong to this course. Clear it to add a new question.")
        elif row.qid and found and len(found) == 1 and known[row.qid][0].id != found[0].id:
            report.error(row.number, "Question ID belongs to a different sub-topic.")
        if ok and found and len(found) == 1:
            plan.setdefault(found[0].id, []).append(row)
            subs[found[0].id] = found[0]
    if report.total_errors:
        return report.out()

    touched: list[tuple[Subtopic, list[Question]]] = []
    for sid, srows in plan.items():
        sub = subs[sid]
        existing = {q.id: q for q in sub.questions}
        by_text = {norm(q.text): q for q in sub.questions}
        keep: dict[str, Question] = {}   # question id -> row object, in final order (replace mode)
        seen_texts: set[str] = set()
        new_rows: list[Question] = []
        stat = {"topic": sub.topic.title, "subtopic": sub.title, "added": 0, "updated": 0, "removed": 0}
        for row in srows:
            key = norm(row.text)
            target = existing.get(row.qid) if row.qid else None
            if target is None and mode == "replace":
                target = by_text.get(key)
            if key in seen_texts:
                report.skipped += 1
                report.warnings.append(f"Row {row.number}: same question text appears twice in “{sub.title}”; skipped.")
                continue
            seen_texts.add(key)
            if target is not None:
                same = (target.text == row.text and list(target.options) == row.options and
                        target.answer_index == row.answer and target.level == row.level and
                        target.explanation == row.explanation)
                if same:
                    report.unchanged += 1
                else:
                    target.text, target.options, target.answer_index = row.text, row.options, row.answer
                    target.level, target.explanation = row.level, row.explanation
                    report.updated += 1
                    stat["updated"] += 1
                keep[target.id] = target
            elif key in by_text:
                report.skipped += 1
                report.warnings.append(f"Row {row.number}: “{row.text[:60]}” already exists in “{sub.title}”; skipped.")
            else:
                q = Question(id=new_id(), level=row.level, type="mcq", text=row.text, options=row.options,
                             answer_index=row.answer, explanation=row.explanation, position=0)
                new_rows.append(q)
                keep[q.id] = q
                report.added += 1
                stat["added"] += 1
        if mode == "replace":
            gone = [q for q in sub.questions if q.id not in keep]
            report.removed += len(gone)
            stat["removed"] = len(gone)
            final = list(keep.values())
        else:
            final = list(sub.questions) + new_rows
        report.subtopics.append(stat)
        touched.append((sub, final))

    if dry_run:
        db.rollback()  # the in-place edits above were only to count them
        return report.out()
    for sub, final in touched:
        for i, q in enumerate(final, 1):
            q.position = i
        sub.questions = final
    db.commit()
    cache.invalidate(cache.course_key(course.id))
    return report.out()
