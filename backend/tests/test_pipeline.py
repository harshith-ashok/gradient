from datetime import timedelta

import pytest
from sqlalchemy import select

from app.agents.llm import FakeLLM, LLMError, set_llm
from app.core import clock
from app.models import Course, Flashcard, Job, Mastery, Question, Subtopic, SyllabusUpload
from app.services import jobs
from app.services.pipeline import HANDLERS
from tests.files import SYLLABUS_TEXT, make_docx, make_pdf, make_scanned_pdf
from tests.test_learning import enroll, sheet, start

RAO = ("ananya.rao@gradient.edu", "faculty123", "staff")
LEE = ("marcus.lee@gradient.edu", "faculty123", "staff")
HALE = ("richard.hale@gradient.edu", "admin123", "staff")
MEERA = ("meera.iyer@gradient.edu", "student123", "student")
FATIMA = ("fatima.khan@gradient.edu", "student123", "student")
LEVELS = {"beginner", "intermediate", "advanced", "expert"}


def run_jobs(db) -> list[Job]:
    """What the worker does: claim queued jobs and run them to completion."""
    done = []
    while (job := jobs.claim_next(db)) is not None:
        done.append(jobs.run_job(db, job, HANDLERS))
    return done


def upload_text(c, text=SYLLABUS_TEXT, **form):
    data = {"course_code": "CS 330", "course_title": "Databases", "text": text, **form}
    return c.post("/api/v1/faculty/syllabus", data=data)


def upload_file(c, name, blob, **form):
    data = {"course_code": "CS 330", "course_title": "Databases", **form}
    return c.post("/api/v1/faculty/syllabus", data=data, files={"file": (name, blob)})


def job(c, job_id):
    return c.get(f"/api/v1/jobs/{job_id}").json()


@pytest.fixture
def rao(as_user):
    return as_user(*RAO)


def analysed(rao, db, text=SYLLABUS_TEXT):
    created = upload_text(rao, text).json()
    run_jobs(db)
    return created


def derived(rao, db, topics=("Relational model", "SQL")):
    created = analysed(rao, db)
    r = rao.post(f"/api/v1/faculty/syllabus/{created['upload_id']}/derive", json={"topics": list(topics)})
    assert r.status_code == 202, r.text
    run_jobs(db)
    return created


# ------------------------------------------------------------------ upload


def test_uploading_text_creates_a_draft_course_and_a_queued_job(rao, db):
    r = upload_text(rao)
    assert r.status_code == 202
    created = r.json()
    course = db.get(Course, created["course_id"])
    assert course.status == "draft" and course.owner_id == "u-rao" and course.code == "CS 330"
    j = job(rao, created["job_id"])
    assert j["status"] == "queued" and j["type"] == "analyze"
    up = rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()
    assert up["status"] == "uploaded" and up["topics"] is None


def test_analysis_finds_topics(rao, db):
    created = analysed(rao, db)
    j = job(rao, created["job_id"])
    assert j["status"] == "succeeded" and j["result"]["topics"] == 3 and j["progress"]["step"] == "Done"
    up = rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()
    assert up["status"] == "topics_ready" and up["indexed"] is True and up["characters"] > 100
    assert [t["title"] for t in up["topics"]] == ["Relational model", "SQL", "Transactions"]
    assert up["job"]["id"] == created["job_id"]


@pytest.mark.parametrize(("name", "blob", "ocr"), [
    ("syllabus.pdf", make_pdf(["# Indexing\nB-trees and hash indexes\n\n# Recovery\nLogging and checkpoints"]), False),
    ("syllabus.docx", make_docx(), False),
    ("scan.pdf", make_scanned_pdf(["x"]), True),
    ("notes.md", b"# Normal forms\n\nFirst, second and third normal form explained.\n\n# Joins\nAll joins.", False),
])
def test_files_of_every_kind_are_analysed(rao, db, name, blob, ocr):
    created = upload_file(rao, name, blob).json()
    run_jobs(db)
    up = rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()
    assert up["status"] == "topics_ready", up
    assert up["ocr_used"] is ocr and up["topics"]


def test_handwritten_scan_text_comes_from_the_vision_model(rao, db, fake_ai):
    fake_ai.ocr_texts = ["# Week 1: Pointers\n# Week 2: Memory management"]
    created = upload_file(rao, "handwritten.pdf", make_scanned_pdf(["scribble"])).json()
    run_jobs(db)
    up = rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()
    assert up["ocr_used"] is True and "Pointers" in [t["title"] for t in up["topics"]][0]


@pytest.mark.parametrize(("form", "files", "status", "text"), [
    ({"text": ""}, None, 400, "file or paste"),
    ({"text": "short"}, None, 400, "between 20"),
    ({"text": SYLLABUS_TEXT}, {"file": ("a.txt", b"some text for the file upload to carry")}, 400, "not both"),
    ({"course_code": " "}, None, 400, "required"),
    ({"text": None}, {"file": ("virus.exe", b"MZ\x90\x00")}, 415, "Unsupported"),
    ({"text": None}, {"file": ("data.txt", b"\x00\x01binary" * 100)}, 415, "binary"),
])
def test_upload_validation(rao, form, files, status, text):
    data = {"course_code": "CS 1", "course_title": "T", "text": SYLLABUS_TEXT, **form}
    data = {k: v for k, v in data.items() if v is not None}
    r = rao.post("/api/v1/faculty/syllabus", data=data, files=files)
    assert r.status_code == status and text in r.json()["detail"]


def test_oversized_files_are_refused(rao, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)
    r = upload_file(rao, "big.txt", b"x" * (1024 * 1024 + 10))
    assert r.status_code == 413 and "1 MB" in r.json()["detail"]


def test_uploaded_files_are_stored_under_a_safe_name(rao, tmp_path, db):
    created = upload_file(rao, "../../etc/pass wd.txt", b"# Topic\nSome content that is long enough here.").json()
    up = db.get(SyllabusUpload, created["upload_id"])
    assert ".." not in up.file_ref and up.file_ref.startswith(created["upload_id"])
    assert (tmp_path / "uploads" / up.file_ref).read_bytes().startswith(b"# Topic")


def test_students_cannot_upload(as_user):
    assert upload_text(as_user(*MEERA)).status_code == 403


def test_anonymous_gets_401(client):
    assert upload_text(client).status_code == 401
    assert client.get("/api/v1/jobs/x").status_code == 401


# ------------------------------------------------------------ failure paths


def test_unreadable_file_fails_the_job_with_a_clear_message(rao, db, fake_ai):
    fake_ai.ocr_texts = [""]
    created = upload_file(rao, "blank.pdf", make_scanned_pdf(["blank"])).json()
    run_jobs(db)
    j = job(rao, created["job_id"])
    up = rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()
    assert j["status"] == "failed" and "No readable text" in j["error"]
    assert up["status"] == "failed" and "No readable text" in up["error"]


def test_a_model_outage_is_reported_without_internals(rao, db):
    class Down(FakeLLM):
        def _chat(self, *a, **k):
            raise LLMError("Could not reach the model server: refused")

    set_llm(Down())
    created = analysed(rao, db)
    j = job(rao, created["job_id"])
    assert j["status"] == "failed" and "Could not reach the model server" in j["error"]


def test_unexpected_errors_do_not_leak_details(rao, db):
    class Crash(FakeLLM):
        def _chat(self, *a, **k):
            raise ZeroDivisionError("secret internal detail /srv/app/x.py")

    set_llm(Crash())
    created = analysed(rao, db)
    j = job(rao, created["job_id"])
    assert j["status"] == "failed" and "secret" not in j["error"] and "Please try again" in j["error"]
    assert rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()["error"] is None


def test_a_missing_uploaded_file_is_reported(rao, db, tmp_path):
    created = upload_file(rao, "a.txt", b"# Topic one\nSome content that is long enough here.").json()
    up = db.get(SyllabusUpload, created["upload_id"])
    (tmp_path / "uploads" / up.file_ref).unlink()
    run_jobs(db)
    assert "missing" in job(rao, created["job_id"])["error"]


# ------------------------------------------------------------------- derive


def test_derive_builds_the_course_tree_for_chosen_topics(rao, db):
    created = derived(rao, db)
    course = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()
    assert [t["title"] for t in course["topics"]] == ["Relational model", "SQL"]  # "Transactions" was not chosen
    subs = course["topics"][0]["subtopics"]
    assert len(subs) == 3 and all(len(s["points"]) >= 2 and s["description"] for s in subs)
    assert all(s["questions"] == [] and s["flashcards"] == [] for s in subs)  # content comes next
    up = rao.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").json()
    assert up["status"] == "derived"


def test_derive_is_idempotent_while_a_job_is_pending(rao, db):
    created = analysed(rao, db)
    body = {"topics": ["SQL"]}
    first = rao.post(f"/api/v1/faculty/syllabus/{created['upload_id']}/derive", json=body).json()
    second = rao.post(f"/api/v1/faculty/syllabus/{created['upload_id']}/derive", json=body).json()
    assert first["job_id"] == second["job_id"]  # a double click does not double the model work
    assert db.scalars(select(Job).where(Job.type == "derive")).all().__len__() == 1


def test_derive_validation(rao, db):
    created = upload_text(rao).json()
    url = f"/api/v1/faculty/syllabus/{created['upload_id']}/derive"
    assert rao.post(url, json={"topics": ["SQL"]}).status_code == 409  # analysis not finished
    run_jobs(db)
    assert rao.post(url, json={"topics": ["Nonsense"]}).status_code == 400
    assert rao.post(url, json={"topics": []}).status_code == 422


def test_existing_topics_are_kept_unless_replace_is_requested(rao, db):
    created = derived(rao, db, topics=("SQL",))
    course_id = created["course_id"]
    sql = rao.get(f"/api/v1/faculty/courses/{course_id}").json()["topics"][0]
    url = f"/api/v1/faculty/syllabus/{created['upload_id']}/derive"
    jid = rao.post(url, json={"topics": ["SQL"]}).json()["job_id"]
    run_jobs(db)
    assert job(rao, jid)["result"]["skipped_existing"] == ["SQL"]
    same = rao.get(f"/api/v1/faculty/courses/{course_id}").json()["topics"][0]
    assert same["id"] == sql["id"]  # untouched

    jid = rao.post(url, json={"topics": ["SQL"], "replace": True}).json()["job_id"]
    run_jobs(db)
    assert job(rao, jid)["result"]["topics_created"] == 1
    new = rao.get(f"/api/v1/faculty/courses/{course_id}").json()["topics"]
    assert len(new) == 1 and new[0]["id"] != sql["id"]


def test_one_topic_failing_does_not_lose_the_others(rao, db, fake_ai):
    from app.agents.fake_responder import DefaultResponder

    base = DefaultResponder()

    def flaky(messages, schema):
        if schema == "SubtopicList" and "Course topic: SQL" in messages[1]["content"]:
            return "garbage"
        return base(messages, schema)

    set_llm(FakeLLM(flaky))
    created = derived(rao, db)
    derive_job = db.scalars(select(Job).where(Job.type == "derive")).one()
    assert derive_job.status == "succeeded"
    assert derive_job.result["topics_created"] == 1 and derive_job.result["errors"][0]["topic"] == "SQL"
    titles = [t["title"] for t in rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()["topics"]]
    assert titles == ["Relational model"]


def test_derive_fails_if_nothing_could_be_derived(rao, db):
    set_llm(FakeLLM(lambda m, s: "garbage" if s == "SubtopicList" else FakeLLM().responder(m, s)))
    created = analysed(rao, db)
    jid = rao.post(f"/api/v1/faculty/syllabus/{created['upload_id']}/derive", json={"topics": ["SQL"]}).json()["job_id"]
    run_jobs(db)
    assert job(rao, jid)["status"] == "failed" and "Could not break down" in job(rao, jid)["error"]


# ----------------------------------------------------------------- generate


def generate(rao, db, course_id, **body):
    r = rao.post(f"/api/v1/faculty/courses/{course_id}/generate", json=body)
    assert r.status_code == 202, r.text
    run_jobs(db)
    return job(rao, r.json()["job_id"])


def test_generation_fills_every_sub_topic(rao, db):
    created = derived(rao, db)
    j = generate(rao, db, created["course_id"])
    assert j["status"] == "succeeded" and j["result"]["generated"] == 6 and j["result"]["failed"] == []
    course = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()
    for topic in course["topics"]:
        for s in topic["subtopics"]:
            assert len(s["summary"]) >= 1 and s["remediation"]["steps"]
            assert set(s["summaries"]) == LEVELS  # one summary per level
            assert s["summary"] == s["summaries"]["beginner"]  # the baseline mirrors the beginner level
            assert len({" ".join(v) for v in s["summaries"].values()}) == 4
            assert {q["level"] for q in s["questions"]} == LEVELS
            assert {f["level"] for f in s["flashcards"]} == LEVELS
            for q in s["questions"]:
                assert len(q["options"]) == 4 and 0 <= q["answer_index"] < 4 and q["explanation"]


def test_generated_course_can_be_published_and_studied(rao, db, as_user):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    r = rao.post(f"/api/v1/faculty/courses/{created['course_id']}/status", json={"status": "published"})
    assert r.status_code == 200  # publishing requires questions on every sub-topic; the AI supplied them

    fatima = as_user(*FATIMA)
    cid = created["course_id"]
    assert cid in [c["id"] for c in fatima.get("/api/v1/student/catalog").json()]
    res = enroll(fatima, db, cid, right=lambda q: True)  # pre-test over AI-written questions
    assert res["score"] == 100 and res["plan"]["tasks"] >= 6
    sub_id = fatima.get(f"/api/v1/student/courses/{cid}").json()["topics"][0]["subtopics"][0]["id"]
    quiz = start(fatima, cid, "subtopic", subtopic_id=sub_id).json()
    assert len(quiz["questions"]) == 4
    done = fatima.post(f"/api/v1/student/quizzes/{quiz['quiz_id']}/submit",
                       json={"answers": sheet(db, quiz["quiz_id"])}).json()
    assert done["passed"] is True and done["by_subtopic"][0]["promoted"] is True
    view = fatima.get(f"/api/v1/student/courses/{cid}/subtopics/{sub_id}").json()
    assert view["subtopic"]["summary"] and view["subtopic"]["flashcards"]


def card_levels(client, course_id, sub_id):
    view = client.get(f"/api/v1/student/courses/{course_id}/subtopics/{sub_id}").json()
    return {f["level"] for f in view["subtopic"]["flashcards"]}


def test_students_get_flashcards_at_their_own_level(rao, db, as_user):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    rao.post(f"/api/v1/faculty/courses/{created['course_id']}/status", json={"status": "published"})
    fatima, cid = as_user(*FATIMA), created["course_id"]
    sub_id = fatima.get(f"/api/v1/student/courses/{cid}").json()["topics"][0]["subtopics"][0]["id"]
    assert card_levels(fatima, cid, sub_id) == {"beginner"}  # not enrolled: starts easy
    enroll(fatima, db, cid, right=lambda q: False)
    assert card_levels(fatima, cid, sub_id) == {"beginner"}
    m = db.scalar(select(Mastery).where(Mastery.subtopic_id == sub_id))
    m.level = "advanced"
    db.commit()
    assert card_levels(fatima, cid, sub_id) == {"advanced"}


def test_nearest_level_is_used_when_the_exact_level_has_no_cards(db, as_user):
    # Seeded cards are all 'beginner'; add one 'advanced' card.
    db.add(Flashcard(id="fx", subtopic_id="c-vars", position=9, level="advanced", front="Adv question?", back="Adv"))
    db.commit()
    db.expire_all()  # the seed's in-memory card list predates this card; a real request starts fresh
    fatima = as_user(*FATIMA)
    assert card_levels(fatima, "c-cs101", "c-vars") == {"beginner"}
    enroll(fatima, db, "c-cs101", right=lambda q: True)  # known sub-topics start at 'intermediate'
    assert card_levels(fatima, "c-cs101", "c-vars") == {"beginner"}  # equidistant: the easier set wins
    db.scalar(select(Mastery).where(Mastery.subtopic_id == "c-vars")).level = "expert"
    db.commit()
    assert card_levels(fatima, "c-cs101", "c-vars") == {"advanced"}  # nearest to expert


# ------------------------------------------------- summaries by student level


def summary_view(client, cid, sub_id):
    v = client.get(f"/api/v1/student/courses/{cid}/subtopics/{sub_id}").json()["subtopic"]
    return v["summary_level"], " ".join(v["summary"])


def test_students_read_the_summary_for_their_level_as_they_progress(rao, db, as_user):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    rao.post(f"/api/v1/faculty/courses/{created['course_id']}/status", json={"status": "published"})
    fatima, cid = as_user(*FATIMA), created["course_id"]
    sub_id = fatima.get(f"/api/v1/student/courses/{cid}").json()["topics"][0]["subtopics"][0]["id"]
    sub = db.get(Subtopic, sub_id)

    level, text = summary_view(fatima, cid, sub_id)  # not enrolled yet: starts at the easiest
    assert level == "beginner" and text == " ".join(sub.summaries["beginner"])

    # A weak pre-test starts the student at beginner; a strong one at intermediate.
    enroll(fatima, db, cid, right=lambda q: True)
    level, text = summary_view(fatima, cid, sub_id)
    assert level == "intermediate" and text == " ".join(sub.summaries["intermediate"])

    # Passing the quiz moves them up one level, and the summary follows.
    quiz = start(fatima, cid, "subtopic", subtopic_id=sub_id).json()
    res = fatima.post(f"/api/v1/student/quizzes/{quiz['quiz_id']}/submit",
                      json={"answers": sheet(db, quiz["quiz_id"])}).json()
    assert res["by_subtopic"][0]["level"] == "advanced"
    level, text = summary_view(fatima, cid, sub_id)
    assert level == "advanced" and text == " ".join(sub.summaries["advanced"])

    # Failing keeps the level (extra material is added instead of an easier summary).
    quiz = start(fatima, cid, "subtopic", subtopic_id=sub_id).json()
    fatima.post(f"/api/v1/student/quizzes/{quiz['quiz_id']}/submit",
                json={"answers": sheet(db, quiz["quiz_id"], right=lambda q: False)})
    assert summary_view(fatima, cid, sub_id)[0] == "advanced"


def test_a_weak_pretest_gets_the_beginner_summary(rao, db, as_user):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    rao.post(f"/api/v1/faculty/courses/{created['course_id']}/status", json={"status": "published"})
    fatima, cid = as_user(*FATIMA), created["course_id"]
    sub_id = fatima.get(f"/api/v1/student/courses/{cid}").json()["topics"][0]["subtopics"][0]["id"]
    enroll(fatima, db, cid, right=lambda q: False)
    assert summary_view(fatima, cid, sub_id)[0] == "beginner"


def test_the_nearest_written_level_is_used_when_a_level_is_missing(db, as_user):
    sub = db.get(Subtopic, "c-vars")
    sub.summaries = {"advanced": ["An advanced treatment of variables and types for experienced readers."]}
    db.commit()
    fatima = as_user(*FATIMA)
    assert summary_view(fatima, "c-cs101", "c-vars")[0] == "beginner"  # the hand-written baseline
    enroll(fatima, db, "c-cs101", right=lambda q: True)  # starts at intermediate
    assert summary_view(fatima, "c-cs101", "c-vars")[0] == "beginner"  # equidistant: the easier wins
    db.scalar(select(Mastery).where(Mastery.subtopic_id == "c-vars")).level = "expert"
    db.commit()
    assert summary_view(fatima, "c-cs101", "c-vars")[0] == "advanced"


def test_hand_written_courses_without_level_summaries_still_work(as_user):
    level, text = summary_view(as_user(*FATIMA), "c-cs101", "c-vars")
    assert level == "beginner" and "named piece of memory" in text


def test_staff_edits_keep_the_level_summaries(rao, db):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    full = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()
    first = full["topics"][0]["subtopics"][0]
    first["summaries"]["advanced"] = ["Edited by faculty: a more careful treatment for advanced learners."]
    saved = rao.put(f"/api/v1/faculty/courses/{created['course_id']}", json=full).json()
    assert saved == full  # lossless round trip, summaries included
    assert saved["topics"][0]["subtopics"][0]["summaries"]["advanced"][0].startswith("Edited by faculty")


def test_levels_added_later_fill_in_summaries_cards_and_questions(rao, db):
    created = derived(rao, db)
    sub_ids = [s["id"] for t in rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()["topics"]
               for s in t["subtopics"]][:1]
    generate(rao, db, created["course_id"], subtopic_ids=sub_ids, levels=["beginner"])
    before = db.get(Subtopic, sub_ids[0])
    first = {"summary": list(before.summaries["beginner"]), "cards": {f.id for f in before.flashcards},
             "questions": {q.id for q in before.questions}, "remediation": before.remediation[0].id}
    j = generate(rao, db, created["course_id"], subtopic_ids=sub_ids)  # now every level
    assert j["result"]["generated"] == 1
    db.expire_all()
    sub = db.get(Subtopic, sub_ids[0])
    assert set(sub.summaries) == LEVELS and {f.level for f in sub.flashcards} == LEVELS
    assert {q.level for q in sub.questions} == LEVELS
    assert sub.summaries["beginner"] == first["summary"]  # the first level was not rewritten
    assert first["cards"] <= {f.id for f in sub.flashcards} and first["questions"] <= {q.id for q in sub.questions}
    assert sub.remediation[0].id == first["remediation"]


def test_existing_flashcards_survive_when_only_remediation_is_missing(rao, db):
    created = derived(rao, db)
    sub_id = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()["topics"][0]["subtopics"][0]["id"]
    generate(rao, db, created["course_id"], subtopic_ids=[sub_id])
    sub = db.get(Subtopic, sub_id)
    cards = {f.id for f in sub.flashcards}
    sub.remediation = []
    db.commit()
    j = generate(rao, db, created["course_id"], subtopic_ids=[sub_id])
    db.expire_all()
    sub = db.get(Subtopic, sub_id)
    assert j["result"]["generated"] == 1 and sub.remediation  # the gap was filled
    assert {f.id for f in sub.flashcards} == cards  # nothing else was rewritten


def test_generation_is_cached_and_never_redone_silently(rao, db, fake_ai):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    calls = len(fake_ai.calls)
    again = generate(rao, db, created["course_id"])
    assert again["result"]["generated"] == 0 and again["result"]["skipped"] == 6
    assert len(fake_ai.calls) == calls  # no model calls at all


def test_force_regenerates(rao, db, fake_ai):
    created = derived(rao, db)
    generate(rao, db, created["course_id"])
    before = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()["topics"][0]["subtopics"][0]
    forced = generate(rao, db, created["course_id"], force=True)
    assert forced["result"]["generated"] == 6
    after = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()["topics"][0]["subtopics"][0]
    assert [q["text"] for q in after["questions"]] != [q["text"] for q in before["questions"]]
    assert {q["level"] for q in after["questions"]} == LEVELS


def test_generation_adds_to_existing_content_without_touching_it(db, as_user):
    """Seeded CS 101 has hand-written beginner questions; AI fills the missing levels beside them."""
    rao = as_user(*RAO)
    before = {q.id: q.text for q in db.scalars(select(Question).where(Question.subtopic_id == "c-vars"))}
    cards_before = [f.id for f in db.scalars(select(Flashcard).where(Flashcard.subtopic_id == "c-vars"))]
    summary_before = list(db.get(Subtopic, "c-vars").summary)
    j = generate(rao, db, "c-cs101", subtopic_ids=["c-vars"])
    assert j["result"]["generated"] == 1
    qs = db.scalars(select(Question).where(Question.subtopic_id == "c-vars")).all()
    assert before.items() <= {q.id: q.text for q in qs}.items()  # every hand-written question is intact
    assert {q.level for q in qs} == LEVELS and len(qs) > len(before)  # the missing levels were added
    cards = db.scalars(select(Flashcard).where(Flashcard.subtopic_id == "c-vars")).all()
    assert set(cards_before) <= {f.id for f in cards}  # every hand-written card is intact
    assert {f.level for f in cards} == LEVELS  # the other levels were added beside them
    sub = db.get(Subtopic, "c-vars")
    assert sub.summary == summary_before  # the hand-written summary is the beginner level and stays
    assert set(sub.summaries) == LEVELS - {"beginner"}  # AI wrote only the other levels


def test_only_requested_levels_and_subtopics(rao, db):
    created = derived(rao, db)
    sub = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()["topics"][0]["subtopics"][0]
    j = generate(rao, db, created["course_id"], subtopic_ids=[sub["id"]], levels=["beginner", "advanced"])
    assert j["result"]["generated"] == 1
    course = rao.get(f"/api/v1/faculty/courses/{created['course_id']}").json()
    done = course["topics"][0]["subtopics"][0]
    assert {q["level"] for q in done["questions"]} == {"beginner", "advanced"}
    assert all(not s["questions"] for t in course["topics"] for s in t["subtopics"] if s["id"] != sub["id"])


def test_a_failing_subtopic_does_not_lose_the_rest(rao, db):
    from app.agents.fake_responder import DefaultResponder

    base = DefaultResponder()

    def flaky(messages, schema):
        if schema == "MaterialDraft" and "Sub-topic: Relational model: Core ideas" in messages[1]["content"]:
            return "garbage"
        return base(messages, schema)

    created = derived(rao, db)
    set_llm(FakeLLM(flaky))
    j = generate(rao, db, created["course_id"])
    assert j["status"] == "succeeded" and j["result"]["generated"] == 5
    assert [f["title"] for f in j["result"]["failed"]] == ["Relational model: Core ideas"]
    assert "invalid output" in j["result"]["failed"][0]["error"]


def test_generation_fails_when_nothing_works(rao, db):
    created = derived(rao, db)
    set_llm(FakeLLM(lambda m, s: "garbage"))
    j = generate(rao, db, created["course_id"])
    assert j["status"] == "failed" and "Nothing could be generated" in j["error"]


def test_generate_validation(rao, db):
    created = analysed(rao, db)
    url = f"/api/v1/faculty/courses/{created['course_id']}/generate"
    assert rao.post(url, json={}).status_code == 409  # no sub-topics yet
    derived_ = derived(rao, db)
    url = f"/api/v1/faculty/courses/{derived_['course_id']}/generate"
    assert rao.post(url, json={"subtopic_ids": ["nope"]}).status_code == 400
    assert rao.post(url, json={"levels": ["wizard"]}).status_code == 422


def test_progress_is_reported_while_generating(rao, db):
    created = derived(rao, db)
    r = rao.post(f"/api/v1/faculty/courses/{created['course_id']}/generate", json={})
    jid = r.json()["job_id"]
    seen = []
    orig = jobs.set_progress

    def spy(db_, job_, step, done=None, total=None):
        orig(db_, job_, step, done, total)
        seen.append((step, done, total))

    jobs.set_progress, pipeline_ref = spy, __import__("app.services.pipeline", fromlist=["x"])
    pipeline_ref.set_progress = spy
    try:
        run_jobs(db)
    finally:
        jobs.set_progress = orig
        pipeline_ref.set_progress = orig
    totals = {t for _, _, t in seen if t}
    assert totals == {6} and [d for _, d, _ in seen if d is not None][:3] == [0, 1, 2]
    assert job(rao, jid)["progress"]["step"] == "Done"


# ------------------------------------------------------------ permissions


def test_other_faculty_cannot_touch_someones_upload_or_course(rao, db, as_user):
    created = analysed(rao, db)
    lee = as_user(*LEE)
    assert lee.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").status_code == 403
    derive_url = f"/api/v1/faculty/syllabus/{created['upload_id']}/derive"
    assert lee.post(derive_url, json={"topics": ["SQL"]}).status_code == 403
    assert lee.post(f"/api/v1/faculty/courses/{created['course_id']}/generate", json={}).status_code == 403
    assert lee.get(f"/api/v1/jobs/{created['job_id']}").status_code == 404  # others' jobs look nonexistent


def test_admin_can_follow_any_job(rao, db, as_user):
    created = analysed(rao, db)
    admin = as_user(*HALE)
    assert admin.get(f"/api/v1/jobs/{created['job_id']}").status_code == 200
    assert admin.get(f"/api/v1/faculty/syllabus/{created['upload_id']}").status_code == 200


def test_students_cannot_use_ai_endpoints(as_user):
    meera = as_user(*MEERA)
    for method, url, kw in [("get", "/api/v1/faculty/ai/health", {}), ("get", "/api/v1/jobs/x", {}),
                            ("post", "/api/v1/faculty/courses/c-cs101/generate", {"json": {}})]:
        assert getattr(meera, method)(url, **kw).status_code == 403


def test_unknown_upload_and_job(rao):
    assert rao.get("/api/v1/faculty/syllabus/nope").status_code == 404
    assert rao.get("/api/v1/jobs/nope").status_code == 404


def test_ai_health(rao):
    assert rao.get("/api/v1/faculty/ai/health").json() == {"ok": True, "provider": "fake", "url": None, "error": None,
                                                          "text_model": None, "vision_model": None, "embed_model": None}


# --------------------------------------------------------------- job queue


def test_jobs_are_claimed_oldest_first_and_only_once(rao, db):
    a = upload_text(rao).json()["job_id"]
    b = upload_text(rao, course_code="CS 331").json()["job_id"]
    first, second = jobs.claim_next(db), jobs.claim_next(db)
    assert (first.id, second.id) == (a, b) and first.status == "running" and first.attempts == 1
    assert jobs.claim_next(db) is None


def test_stale_running_jobs_are_requeued_then_failed(rao, db):
    jid = upload_text(rao).json()["job_id"]
    j = jobs.claim_next(db)
    assert jobs.requeue_stale(db) == 0  # a fresh heartbeat is left alone
    j.heartbeat_at = clock.now() - timedelta(hours=1)
    db.commit()
    assert jobs.requeue_stale(db) == 1 and db.get(Job, jid).status == "queued"
    for _ in range(2):  # attempts 2 and 3
        j = jobs.claim_next(db)
        j.heartbeat_at = clock.now() - timedelta(hours=1)
        db.commit()
        jobs.requeue_stale(db)
    failed = db.get(Job, jid)
    assert failed.status == "failed" and "worker stopped" in failed.error and failed.attempts == 3


def test_a_restarted_worker_picks_up_orphaned_jobs(rao, db):
    jid = upload_text(rao).json()["job_id"]
    jobs.claim_next(db)  # a worker takes it and dies
    jobs.reset_stuck(db)
    assert db.get(Job, jid).status == "queued"


def test_finished_jobs_are_not_deduplicated(rao, db):
    created = analysed(rao, db)
    url = f"/api/v1/faculty/syllabus/{created['upload_id']}/derive"
    first = rao.post(url, json={"topics": ["SQL"]}).json()["job_id"]
    run_jobs(db)
    second = rao.post(url, json={"topics": ["SQL"], "replace": True}).json()["job_id"]
    assert first != second
