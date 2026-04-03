"""Seed the database with tests from PDFs in uploads/ folder.
Run automatically on app startup if no tests exist."""

import os
from models import db, Test, Question
from pdf_parser import parse_and_merge

TESTS = [
    {
        'name': 'PTS 2026 GS Simulator Test 2',
        'question_pdf': 'PTS-2026-GS-Simulator-Test-2_311412-QP-Eng.pdf',
        'answer_pdf': 'PTS-2026-GS-Simulator-Test-2_311412-Sol-Eng.pdf',
        'duration_minutes': 120,
    },
    {
        'name': 'PTS 2026 GS Simulator Test 4',
        'question_pdf': 'PTS-2026-GS-Simulator-Test-4_311414-QP-Eng.pdf',
        'answer_pdf': 'PTS-2026-GS-Simulator-Test-4_311414-Sol-Eng.pdf',
        'duration_minutes': 120,
    },
]


def seed_tests():
    """Load tests from PDFs if database is empty."""
    if Test.query.count() > 0:
        print("Database already has tests, skipping seed.")
        return

    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')

    for t in TESTS:
        q_path = os.path.join(uploads_dir, t['question_pdf'])
        a_path = os.path.join(uploads_dir, t['answer_pdf'])

        if not os.path.exists(q_path) or not os.path.exists(a_path):
            print(f"Skipping {t['name']}: PDF files not found")
            continue

        questions = parse_and_merge(q_path, a_path)

        test = Test(
            name=t['name'],
            duration_minutes=t['duration_minutes'],
            total_questions=len(questions),
        )
        db.session.add(test)
        db.session.flush()

        for q in questions:
            question = Question(
                test_id=test.id,
                question_number=q['number'],
                question_text=q['text'],
                option_a=q['option_a'],
                option_b=q['option_b'],
                option_c=q['option_c'],
                option_d=q['option_d'],
                correct_answer=q.get('correct_answer'),
                explanation=q.get('explanation', ''),
            )
            db.session.add(question)

        db.session.commit()
        print(f"Loaded: {t['name']} ({len(questions)} questions)")

    print("Seeding complete!")
