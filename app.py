import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from models import db, Test, Question, Response
from pdf_parser import parse_and_merge

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'upsc-test-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///upsc_test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

db.init_app(app)

with app.app_context():
    db.create_all()
    from seed import seed_tests
    seed_tests()


# --- Public Routes ---

@app.route('/')
def index():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    return render_template('index.html', tests=tests)


@app.route('/login/<int:test_id>', methods=['GET', 'POST'])
def login(test_id):
    test = Test.query.get_or_404(test_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()

        if not name or not email:
            flash('Please enter both name and email.', 'error')
            return render_template('login.html', test=test)

        # Check if already submitted
        existing = Response.query.filter_by(
            test_id=test_id, candidate_email=email
        ).first()
        if existing:
            flash('You have already taken this test. Redirecting to your result.', 'info')
            return redirect(url_for('result', response_id=existing.id))

        session['candidate_name'] = name
        session['candidate_email'] = email
        session['test_id'] = test_id
        session['start_time'] = datetime.utcnow().isoformat()
        return redirect(url_for('take_test', test_id=test_id))

    return render_template('login.html', test=test)


@app.route('/test/<int:test_id>')
def take_test(test_id):
    test = Test.query.get_or_404(test_id)

    if session.get('test_id') != test_id or not session.get('candidate_email'):
        return redirect(url_for('login', test_id=test_id))

    questions = Question.query.filter_by(test_id=test_id).order_by(Question.question_number).all()
    start_time = session.get('start_time', datetime.utcnow().isoformat())

    return render_template('test.html', test=test, questions=questions, start_time=start_time)


@app.route('/api/submit/<int:test_id>', methods=['POST'])
def submit_test(test_id):
    test = Test.query.get_or_404(test_id)

    if session.get('test_id') != test_id or not session.get('candidate_email'):
        return jsonify({'error': 'Unauthorized'}), 401

    # Check if already submitted
    existing = Response.query.filter_by(
        test_id=test_id, candidate_email=session['candidate_email']
    ).first()
    if existing:
        return jsonify({'redirect': url_for('result', response_id=existing.id)})

    data = request.get_json()
    answers = data.get('answers', {})
    time_taken = data.get('time_taken_seconds', 0)

    # Calculate score
    questions = Question.query.filter_by(test_id=test_id).all()
    correct_count = 0
    wrong_count = 0
    total_attempted = 0

    for q in questions:
        user_answer = answers.get(str(q.question_number))
        if user_answer:
            total_attempted += 1
            if user_answer == q.correct_answer:
                correct_count += 1
            else:
                wrong_count += 1

    score = (correct_count * test.marks_correct) - (wrong_count * test.marks_negative)
    score = round(score, 2)

    response = Response(
        test_id=test_id,
        candidate_name=session['candidate_name'],
        candidate_email=session['candidate_email'],
        answers_json=json.dumps(answers),
        score=score,
        total_attempted=total_attempted,
        correct_count=correct_count,
        wrong_count=wrong_count,
        time_taken_seconds=time_taken,
    )
    db.session.add(response)
    db.session.commit()

    # Clear session
    session.pop('test_id', None)
    session.pop('start_time', None)

    return jsonify({'redirect': url_for('result', response_id=response.id)})


@app.route('/result/<int:response_id>')
def result(response_id):
    response = Response.query.get_or_404(response_id)
    test = response.test
    questions = Question.query.filter_by(test_id=test.id).order_by(Question.question_number).all()
    answers = json.loads(response.answers_json)
    max_marks = test.total_questions * test.marks_correct

    return render_template('result.html',
                           response=response, test=test,
                           questions=questions, answers=answers,
                           max_marks=max_marks)


# --- Admin Routes ---

@app.route('/admin')
def admin():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    return render_template('admin.html', tests=tests)


@app.route('/admin/upload', methods=['POST'])
def admin_upload():
    test_name = request.form.get('test_name', '').strip()
    duration = int(request.form.get('duration', 120))
    question_file = request.files.get('question_pdf')
    answer_file = request.files.get('answer_pdf')

    if not test_name or not question_file or not answer_file:
        flash('Please fill all fields and upload both PDFs.', 'error')
        return redirect(url_for('admin'))

    # Save uploaded files
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    q_path = os.path.join(app.config['UPLOAD_FOLDER'], f'q_{test_name}.pdf')
    a_path = os.path.join(app.config['UPLOAD_FOLDER'], f'a_{test_name}.pdf')
    question_file.save(q_path)
    answer_file.save(a_path)

    # Parse PDFs
    try:
        parsed = parse_and_merge(q_path, a_path)
    except Exception as e:
        flash(f'Error parsing PDFs: {str(e)}', 'error')
        return redirect(url_for('admin'))

    # Create test
    test = Test(
        name=test_name,
        duration_minutes=duration,
        total_questions=len(parsed),
    )
    db.session.add(test)
    db.session.flush()

    # Create questions
    for q in parsed:
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
    flash(f'Test "{test_name}" created with {len(parsed)} questions!', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/responses/<int:test_id>')
def admin_responses(test_id):
    test = Test.query.get_or_404(test_id)
    responses = Response.query.filter_by(test_id=test_id).order_by(Response.submitted_at.desc()).all()

    # Analytics
    if responses:
        scores = [r.score for r in responses]
        avg_score = round(sum(scores) / len(scores), 2)
        max_score = max(scores)
        min_score = min(scores)
    else:
        avg_score = max_score = min_score = 0

    # Question-wise accuracy
    questions = Question.query.filter_by(test_id=test_id).order_by(Question.question_number).all()
    q_accuracy = {}
    for q in questions:
        correct = 0
        attempted = 0
        for r in responses:
            ans = json.loads(r.answers_json)
            user_ans = ans.get(str(q.question_number))
            if user_ans:
                attempted += 1
                if user_ans == q.correct_answer:
                    correct += 1
        accuracy = round((correct / attempted * 100), 1) if attempted > 0 else 0
        q_accuracy[q.question_number] = {'accuracy': accuracy, 'attempted': attempted}

    return render_template('admin_responses.html',
                           test=test, responses=responses,
                           avg_score=avg_score, max_score=max_score,
                           min_score=min_score, q_accuracy=q_accuracy,
                           questions=questions)


@app.route('/admin/delete/<int:test_id>', methods=['POST'])
def admin_delete_test(test_id):
    test = Test.query.get_or_404(test_id)
    Question.query.filter_by(test_id=test_id).delete()
    Response.query.filter_by(test_id=test_id).delete()
    db.session.delete(test)
    db.session.commit()
    flash(f'Test "{test.name}" deleted.', 'success')
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
