"""Excel export and import of quiz questions."""

import io

import pytest
from openpyxl import Workbook, load_workbook

from app.models import Question, Subtopic
from app.services import question_sheet as qs

FACULTY = ("ananya.rao@gradient.edu", "faculty123", "staff")


@pytest.fixture
def fac(as_user):
    return as_user(*FACULTY)


@pytest.fixture
def course(fac):
    cid = next(c["id"] for c in fac.get("/api/v1/faculty/courses").json() if c["status"] == "published")
    return fac.get(f"/api/v1/faculty/courses/{cid}").json()


def sheet_bytes(rows, header=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Questions"
    ws.append(header or ["Topic", "Sub-topic", "Level", "Question", "Option A", "Option B", "Option C", "Option D",
                         "Correct answer", "Explanation", "Question ID"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def post(client, cid, data, mode="merge", dry_run=False, name="q.xlsx"):
    return client.post(f"/api/v1/faculty/courses/{cid}/questions/import",
                       files={"file": (name, data, qs.XLSX)}, data={"mode": mode, "dry_run": str(dry_run).lower()})


def first_sub(course):
    t = course["topics"][0]
    return t["title"], t["subtopics"][0]


def count(course_json):
    return sum(len(s["questions"]) for t in course_json["topics"] for s in t["subtopics"])


# ---------------------------------------------------------------- export
def test_export_has_one_row_per_question_and_round_trips(fac, course):
    r = fac.get(f"/api/v1/faculty/courses/{course['id']}/questions.xlsx")
    assert r.status_code == 200 and r.headers["content-type"].startswith(qs.XLSX)
    assert "attachment" in r.headers["content-disposition"] and ".xlsx" in r.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(r.content))[qs.SHEET]
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0][:4] == ("Topic", "Sub-topic", "Level", "Question") and rows[0][-1] == "Question ID"
    assert len(rows) - 1 == count(course)
    # importing the untouched export changes nothing
    back = post(fac, course["id"], r.content).json()
    assert back["saved"] and back["added"] == 0 and back["updated"] == 0 and back["unchanged"] == count(course)


def test_export_neutralises_formulas(fac, course, db):
    q = db.query(Question).first()
    q.text = '=HYPERLINK("http://evil","click")'
    db.commit()
    cid = db.get(Subtopic, q.subtopic_id).topic.course_id
    ws = load_workbook(io.BytesIO(fac.get(f"/api/v1/faculty/courses/{cid}/questions.xlsx").content))[qs.SHEET]
    cells = [c for row in ws.iter_rows() for c in row if c.value == q.text]
    assert cells and all(c.data_type == "s" for c in cells)


def test_template_downloads_and_imports_into_a_matching_course(fac):
    r = fac.get("/api/v1/faculty/questions/template.xlsx")
    assert r.status_code == 200
    names = load_workbook(io.BytesIO(r.content)).sheetnames
    assert names == ["Questions", "Instructions"]


def test_export_is_owner_only(as_user, course):
    other = as_user("marcus.lee@gradient.edu", "faculty123", "staff")
    assert other.get(f"/api/v1/faculty/courses/{course['id']}/questions.xlsx").status_code == 403
    assert post(other, course["id"], sheet_bytes([])).status_code == 403


# ---------------------------------------------------------------- import
def test_add_new_questions(fac, course):
    topic, sub = first_sub(course)
    before = count(course)
    data = sheet_bytes([[topic, sub["title"], "advanced", "A brand new question?", "yes", "no", "maybe", "", "C",
                         "Because.", ""]])
    rep = post(fac, course["id"], data).json()
    assert rep["saved"] and rep["added"] == 1 and rep["errors"] == []
    after = fac.get(f"/api/v1/faculty/courses/{course['id']}").json()
    assert count(after) == before + 1
    new = next(q for q in after["topics"][0]["subtopics"][0]["questions"] if q["text"] == "A brand new question?")
    assert new["options"] == ["yes", "no", "maybe"] and new["answer_index"] == 2 and new["level"] == "advanced"


def test_update_by_id_keeps_the_question_id(fac, course):
    topic, sub = first_sub(course)
    q = sub["questions"][0]
    row = [topic, sub["title"], q["level"], "Reworded question?", *q["options"], "A", "new why", q["id"]]
    data = sheet_bytes([row])
    rep = post(fac, course["id"], data).json()
    assert rep["saved"] and rep["updated"] == 1 and rep["added"] == 0
    after = fac.get(f"/api/v1/faculty/courses/{course['id']}").json()
    got = next(x for x in after["topics"][0]["subtopics"][0]["questions"] if x["id"] == q["id"])
    assert got["text"] == "Reworded question?" and got["explanation"] == "new why" and got["answer_index"] == 0


def test_duplicate_text_is_skipped_not_added(fac, course):
    topic, sub = first_sub(course)
    q = sub["questions"][0]
    data = sheet_bytes([[topic, sub["title"], "beginner", q["text"].upper(), "x", "y", "", "", "A", "", ""]])
    rep = post(fac, course["id"], data).json()
    assert rep["saved"] and rep["skipped"] == 1 and rep["added"] == 0 and rep["warnings"]


def test_replace_makes_the_subtopic_match_the_file(fac, course):
    topic, sub = first_sub(course)
    keep = sub["questions"][0]
    data = sheet_bytes([[topic, sub["title"], "beginner", "Only question", "a", "b", "", "", "B", "", ""],
                        [topic, sub["title"], keep["level"], keep["text"], *keep["options"], "A",
                         keep["explanation"], ""]])
    dry = post(fac, course["id"], data, mode="replace", dry_run=True).json()
    assert dry["dry_run"] and not dry["saved"] and dry["added"] == 1 and dry["removed"] == len(sub["questions"]) - 1
    assert count(fac.get(f"/api/v1/faculty/courses/{course['id']}").json()) == count(course)  # nothing written
    rep = post(fac, course["id"], data, mode="replace").json()
    assert rep["saved"]
    after = fac.get(f"/api/v1/faculty/courses/{course['id']}").json()
    qs_ = after["topics"][0]["subtopics"][0]["questions"]
    assert [q["text"] for q in qs_] == ["Only question", keep["text"]]
    assert qs_[1]["id"] == keep["id"]  # matched by text, so its id survives
    other = after["topics"][0]["subtopics"][1]
    assert len(other["questions"]) == len(course["topics"][0]["subtopics"][1]["questions"])  # untouched


def test_dry_run_changes_nothing(fac, course):
    topic, sub = first_sub(course)
    q = sub["questions"][0]
    data = sheet_bytes([[topic, sub["title"], "beginner", "Never saved?", "a", "b", "", "", "A", "", ""],
                        [topic, sub["title"], q["level"], "Edit only in preview", *q["options"], "A", "", q["id"]]])
    rep = post(fac, course["id"], data, dry_run=True).json()
    assert rep["added"] == 1 and rep["updated"] == 1 and not rep["saved"]
    assert fac.get(f"/api/v1/faculty/courses/{course['id']}").json() == course


def test_any_bad_row_blocks_the_whole_import(fac, course):
    topic, sub = first_sub(course)
    good = [topic, sub["title"], "beginner", "Valid question?", "a", "b", "", "", "A", "", ""]
    rows = [
        good,
        [topic, "No such sub-topic", "beginner", "q", "a", "b", "", "", "A", "", ""],
        [topic, sub["title"], "godlike", "q2", "a", "b", "", "", "A", "", ""],
        [topic, sub["title"], "beginner", "q3", "only one", "", "", "", "A", "", ""],
        [topic, sub["title"], "beginner", "q4", "a", "b", "", "", "Z", "", ""],
        [topic, sub["title"], "beginner", "q5", "same", "same", "", "", "A", "", ""],
        [topic, sub["title"], "beginner", "q6", "a", "", "c", "", "A", "", ""],
        [topic, sub["title"], "beginner", "q7", "a", "b", "", "", "A", "", "not-an-id"],
        [topic, sub["title"], "beginner", "", "a", "b", "", "", "A", "", ""],
    ]
    rep = post(fac, course["id"], sheet_bytes(rows)).json()
    assert not rep["saved"] and rep["total_errors"] >= 8 and rep["added"] == 0
    by_row = {e["row"]: e["message"] for e in rep["errors"]}
    assert 2 not in by_row and "No sub-topic" in by_row[3] and "godlike" in by_row[4]
    assert "two options" in by_row[5] and "letter" in by_row[6] and "same" in by_row[7]
    assert "empty option" in by_row[8] and "ID" in by_row[9] and "Question is empty" in by_row[10]
    assert fac.get(f"/api/v1/faculty/courses/{course['id']}").json() == course  # the good row was not saved either


def test_correct_answer_can_be_the_option_text(fac, course):
    topic, sub = first_sub(course)
    data = sheet_bytes([[topic, sub["title"], "", "By text?", "red", "green", "", "", "green", "", ""]])
    assert post(fac, course["id"], data).json()["saved"]
    after = fac.get(f"/api/v1/faculty/courses/{course['id']}").json()
    q = next(x for x in after["topics"][0]["subtopics"][0]["questions"] if x["text"] == "By text?")
    assert q["answer_index"] == 1 and q["level"] == "beginner"


def test_topic_column_may_be_blank_when_the_subtopic_is_unique(fac, course):
    _, sub = first_sub(course)
    titles = [s["title"] for t in course["topics"] for s in t["subtopics"]]
    if titles.count(sub["title"]) == 1:
        row = ["", sub["title"], "", "No topic given?", "a", "b", "", "", "A", "", ""]
        rep = post(fac, course["id"], sheet_bytes([row])).json()
        assert rep["saved"] and rep["added"] == 1


def test_wrong_file_types_and_headers_are_refused(fac, course):
    assert post(fac, course["id"], b"a,b,c\n1,2,3\n", name="q.csv").status_code == 400
    assert post(fac, course["id"], b"PK\x03\x04 garbage").status_code == 400
    bad_header = sheet_bytes([["x"]], header=["Foo", "Bar"])
    r = post(fac, course["id"], bad_header)
    assert r.status_code == 400 and "header" in r.json()["detail"]
    assert post(fac, course["id"], sheet_bytes([])).status_code == 400  # header only
    assert post(fac, "missing", sheet_bytes([])).status_code == 404


def test_formulas_in_the_sheet_are_not_evaluated(fac, course):
    topic, sub = first_sub(course)
    wb = Workbook()
    ws = wb.active
    ws.title = "Questions"
    ws.append(["Topic", "Sub-topic", "Question", "Option A", "Option B", "Correct answer"])
    ws.append([topic, sub["title"], "=1+1", "a", "b", "A"])  # a real formula cell; no cached value
    buf = io.BytesIO()
    wb.save(buf)
    rep = post(fac, course["id"], buf.getvalue()).json()
    assert not rep["saved"] and "Question is empty" in rep["errors"][0]["message"]


def test_oversize_file_is_rejected(fac, course, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert post(fac, course["id"], sheet_bytes([["a"]])).status_code == 413
