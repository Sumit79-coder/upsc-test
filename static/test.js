// State
const totalQuestions = parseInt(document.getElementById('totalQuestions').value);
const durationMinutes = parseInt(document.getElementById('durationMinutes').value);
const testId = document.getElementById('testId').value;
const startTime = document.getElementById('startTime').value;

let currentQuestion = 1;
let answers = {};
let markedForReview = new Set();
let timerInterval;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    startTimer();
    updateNavButtons();
    highlightCurrentBtn();
});

// Timer
function startTimer() {
    const start = new Date(startTime + 'Z');
    const endTime = new Date(start.getTime() + durationMinutes * 60 * 1000);

    timerInterval = setInterval(() => {
        const now = new Date();
        const remaining = Math.max(0, endTime - now);

        if (remaining <= 0) {
            clearInterval(timerInterval);
            autoSubmit();
            return;
        }

        const mins = Math.floor(remaining / 60000);
        const secs = Math.floor((remaining % 60000) / 1000);
        const timerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        document.getElementById('timerText').textContent = timerText;

        const timerDisplay = document.getElementById('timer');
        if (mins < 5) {
            timerDisplay.className = 'timer-display danger';
        } else if (mins < 15) {
            timerDisplay.className = 'timer-display warning';
        }
    }, 1000);
}

// Question Navigation
function goToQuestion(num) {
    document.getElementById(`q${currentQuestion}`).style.display = 'none';
    document.getElementById(`q${num}`).style.display = 'block';

    document.getElementById(`qbtn${currentQuestion}`)?.classList.remove('active');
    currentQuestion = num;
    document.getElementById(`qbtn${currentQuestion}`)?.classList.add('active');

    updateNavButtons();
}

function navigateQuestion(dir) {
    const next = currentQuestion + dir;
    if (next >= 1 && next <= totalQuestions) {
        goToQuestion(next);
    }
}

function updateNavButtons() {
    document.getElementById('prevBtn').disabled = currentQuestion === 1;
    document.getElementById('nextBtn').disabled = currentQuestion === totalQuestions;
}

function highlightCurrentBtn() {
    document.getElementById(`qbtn${currentQuestion}`)?.classList.add('active');
}

// Answer Selection
function selectAnswer(qNum, letter) {
    answers[qNum] = letter;

    // Highlight selected option
    ['a', 'b', 'c', 'd'].forEach(l => {
        const el = document.getElementById(`opt_${qNum}_${l}`);
        if (el) el.classList.remove('selected');
    });
    document.getElementById(`opt_${qNum}_${letter}`)?.classList.add('selected');

    // Update question button
    updateQuestionBtn(qNum);
    updateCounts();
}

function clearAnswer(qNum) {
    delete answers[qNum];

    // Uncheck radio
    const radios = document.querySelectorAll(`input[name="q${qNum}"]`);
    radios.forEach(r => r.checked = false);

    // Remove highlight
    ['a', 'b', 'c', 'd'].forEach(l => {
        const el = document.getElementById(`opt_${qNum}_${l}`);
        if (el) el.classList.remove('selected');
    });

    updateQuestionBtn(qNum);
    updateCounts();
}

// Mark for Review
function markForReview(qNum) {
    const btn = document.getElementById(`reviewBtn${qNum}`);
    if (markedForReview.has(qNum)) {
        markedForReview.delete(qNum);
        btn.textContent = 'Mark for Review';
    } else {
        markedForReview.add(qNum);
        btn.textContent = 'Unmark Review';
    }
    updateQuestionBtn(qNum);
    updateCounts();
}

function updateQuestionBtn(qNum) {
    const btn = document.getElementById(`qbtn${qNum}`);
    if (!btn) return;

    btn.className = 'q-btn';
    if (markedForReview.has(qNum)) {
        btn.classList.add('q-review');
    } else if (answers[qNum]) {
        btn.classList.add('q-answered');
    } else {
        btn.classList.add('q-unanswered');
    }

    if (qNum === currentQuestion) {
        btn.classList.add('active');
    }
}

function updateCounts() {
    const answered = Object.keys(answers).length;
    document.getElementById('answeredCount').textContent = answered;
    document.getElementById('unansweredCount').textContent = totalQuestions - answered;
    document.getElementById('reviewCount').textContent = markedForReview.size;
}

// Submit
function submitTest() {
    const answered = Object.keys(answers).length;
    const unanswered = totalQuestions - answered;

    const msg = `You have answered ${answered} out of ${totalQuestions} questions.\n${unanswered} questions are unanswered.\n\nAre you sure you want to submit?`;

    if (!confirm(msg)) return;

    sendSubmission();
}

function autoSubmit() {
    alert('Time is up! Your test is being submitted automatically.');
    sendSubmission();
}

function sendSubmission() {
    // Remove beforeunload handler so redirect works
    window.onbeforeunload = null;
    window.removeEventListener('beforeunload', beforeUnloadHandler);

    const start = new Date(startTime + 'Z');
    const timeTaken = Math.floor((new Date() - start) / 1000);

    fetch(`/api/submit/${testId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            answers: answers,
            time_taken_seconds: timeTaken,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.redirect) {
            window.location.href = data.redirect;
        } else if (data.error) {
            alert('Error: ' + data.error);
        }
    })
    .catch(err => {
        alert('Failed to submit. Please try again.');
        console.error(err);
    });
}

// Prevent accidental page leave
function beforeUnloadHandler(e) {
    e.preventDefault();
    e.returnValue = '';
}
window.addEventListener('beforeunload', beforeUnloadHandler);
