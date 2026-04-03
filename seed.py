"""Seed the database with tests from pre-parsed JSON files in questions/ folder.
Run automatically on app startup if no tests exist."""

import os
import json
from models import db, Test, Question


def seed_tests():
    """Load tests from JSON files if database is empty."""
    if Test.query.count() > 0:
        print("Database already has tests, skipping seed.")
        return

    questions_dir = os.path.join(os.path.dirname(__file__), 'questions')

    for filename in sorted(os.listdir(questions_dir)):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(questions_dir, filename)
        with open(filepath) as f:
            data = json.load(f)

        test = Test(
            name=data['name'],
            duration_minutes=data.get('duration_minutes', 120),
            total_questions=len(data['questions']),
        )
        db.session.add(test)
        db.session.flush()

        for q in data['questions']:
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
        print(f"Loaded: {data['name']} ({len(data['questions'])} questions)")

    print("Seeding complete!")
