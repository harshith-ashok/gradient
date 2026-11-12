"""Deterministic model replies for tests. It parses the prompt it is given, so the pipeline can be
exercised end to end (including blind verification) with no model server."""

import re


class DefaultResponder:
    def __init__(self) -> None:
        self.keys: dict[str, int] = {}  # question stem -> index of the correct option
        self.counter = 0

    def __call__(self, messages: list[dict], schema: str):
        user = messages[1]["content"]  # the original request, even when the last message is a repair note
        return getattr(self, f"_{schema}")(user)

    # ---- topics
    def _TopicList(self, user: str):
        body = re.search(r"<syllabus>\n(.*?)\n</syllabus>", user, re.S)
        text = body.group(1) if body else user
        titles = []
        for line in text.splitlines():
            m = re.match(r"^\s*(?:#+\s*|\d+[.)]\s*|(?:Topic|Unit|Week)\s*\d*[:.-]?\s*)(.{3,80})$", line)
            if m and not line.strip().startswith("-"):
                titles.append(m.group(1).strip())
        titles = titles[:12] or [(text.strip().splitlines() or ["Course content"])[0][:80] or "Course content"]
        return {"topics": [{"title": t, "summary": f"Covers {t} in the course."} for t in titles]}

    def _SubtopicList(self, user: str):
        topic = re.search(r"Course topic: (.*)", user).group(1)
        return {"subtopics": [
            {"title": f"{topic}: {facet}", "description": f"{facet} of {topic}.",
             "key_points": [f"{facet} point one about {topic}", f"{facet} point two about {topic}"]}
            for facet in ("Foundations", "Core ideas", "Common pitfalls")
        ]}

    def _MaterialDraft(self, user: str):
        sub = re.search(r"Sub-topic: (.*)", user).group(1)
        levels = re.findall(r"^- (beginner|intermediate|advanced|expert):", user, re.M)
        return {
            "flashcards": [
                {"level": lvl, "front": f"What is idea {i} of {sub} ({lvl})?", "back": f"Answer {i} for {lvl}."}
                for lvl in levels for i in range(1, 4)
            ],
            "remediation": {
                "explanation": f"Think of {sub} as a set of small steps; work through each in order.",
                "steps": ["Re-read the summary.", "Write the key idea in your own words.", "Try one example."],
            },
        }

    def _LeveledSummaries(self, user: str):
        sub = re.search(r"Sub-topic: (.*)", user).group(1)
        levels = re.findall(r"^- (beginner|intermediate|advanced|expert):", user, re.M)
        return {"summaries": [
            {"level": lvl, "paragraphs": [
                f"At the {lvl} level, {sub} is explained with the depth that suits this kind of reader.",
                f"A second paragraph for the {lvl} level connects {sub} to the rest of the course material.",
            ]} for lvl in levels
        ]}

    def _QuestionSet(self, user: str):
        sub = re.search(r"Sub-topic: (.*)", user).group(1)
        level = re.search(r"at the (\w+) level", user).group(1).lower()
        out = []
        for i in range(4):
            self.counter += 1
            stem = f"Question {self.counter} about {sub} at {level} level: which statement is correct?"
            correct = (self.counter + i) % 4
            options = [f"Wrong option {self.counter}-{j}" for j in range(4)]
            options[correct] = f"Right option {self.counter}"
            self.keys[stem] = correct
            out.append({"text": stem, "options": options, "answer_index": correct,
                        "explanation": f"Because option {correct} is the correct statement."})
        return {"questions": out}

    def _PlanProposal(self, user: str):
        rows = re.findall(r"^- (\S+) \| .*?\| pretest (\d+)% \| mastery (\d+)%", user, re.M)
        budget = int(re.search(r"close to (\d+)", user).group(1))
        weak = [(int(m), sid) for sid, _, m in rows]
        total = sum(100 - m + 20 for m, _ in weak) or 1
        items = []
        for rank, (m, sid) in enumerate(sorted(weak), 1):
            minutes = max(10, min(90, round(budget * (100 - m + 20) / total / 5) * 5))
            items.append({"subtopic_id": sid, "study_minutes": minutes, "priority": rank,
                          "start_level": "beginner" if m < 50 else "intermediate",
                          "focus": "Concentrate on the ideas you found hardest."})
        return {"summary": "More time goes to the weakest sub-topics, which are studied first.", "items": items}

    def _BlindAnswers(self, user: str):
        answers = []
        for num, stem in re.findall(r"Question (\d+): (.*)", user):
            answers.append({"question_number": int(num), "chosen_index": self.keys.get(stem, 0)})
        return {"answers": answers}


def default_responder(messages: list[dict], schema: str):
    # A fresh responder per call would lose the answer key, so keep one per process.
    global _shared
    if "_shared" not in globals():
        _shared = DefaultResponder()
    return _shared(messages, schema)
