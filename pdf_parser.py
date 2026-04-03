import re
import pdfplumber


def extract_text_from_pdf(pdf_path, two_column=False):
    """Extract text from PDF, handling two-column layout if needed."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if two_column:
                mid = page.width / 2
                left = page.crop((0, 0, mid, page.height))
                right = page.crop((mid, 0, page.width, page.height))
                left_text = left.extract_text() or ""
                right_text = right.extract_text() or ""
                text += left_text + "\n" + right_text + "\n"
            else:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    return text


def clean_text(text):
    """Remove headers, footers, and noise from extracted text."""
    text = re.sub(r'Forum Learning Centre:.*?\n', '\n', text)
    text = re.sub(r'9311740\d+.*?\n', '\n', text)
    text = re.sub(r'PTS 2026 \| Test Code:.*?\|', '', text)
    text = re.sub(r'Page \d+', '', text)
    text = re.sub(r': \d{6} \|', '', text)
    # Remove partial footer fragments
    text = re.sub(r'Canal Road,.*?(?=\n|$)', '', text)
    text = re.sub(r'usa Road,.*?(?=\n|$)', '', text)
    text = re.sub(r'RTC X Rd,.*?(?=\n|$)', '', text)
    text = re.sub(r'admissions@.*?(?=\n|$)', '', text)
    text = re.sub(r'helpdesk@.*?(?=\n|$)', '', text)
    text = re.sub(r'https://academy\.forumias\.com', '', text)
    return text


def parse_questions(pdf_path):
    """Parse question PDF (two-column layout) and return list of question dicts."""
    text = extract_text_from_pdf(pdf_path, two_column=True)
    text = clean_text(text)

    # Split into question blocks using Q.\d+)
    pattern = r'Q\.(\d+)\)'
    parts = re.split(pattern, text)

    questions = []
    for i in range(1, len(parts) - 1, 2):
        q_num = int(parts[i])
        q_content = parts[i + 1].strip()

        # Extract options a) b) c) d)
        # Match options at the start of a line or after newline
        option_pattern = r'(?:^|\n)\s*([a-d])\)\s*'
        option_splits = re.split(option_pattern, q_content)

        question_text = option_splits[0].strip()

        options = {}
        for j in range(1, len(option_splits) - 1, 2):
            letter = option_splits[j]
            opt_text = option_splits[j + 1].strip()
            opt_text = ' '.join(opt_text.split())
            options[letter] = opt_text

        question_text = ' '.join(question_text.split())

        questions.append({
            'number': q_num,
            'text': question_text,
            'option_a': options.get('a', ''),
            'option_b': options.get('b', ''),
            'option_c': options.get('c', ''),
            'option_d': options.get('d', ''),
        })

    # Sort by question number
    questions.sort(key=lambda q: q['number'])
    return questions


def parse_answer_key(pdf_path):
    """Parse answer key PDF and return dict of {question_number: {answer, explanation}}."""
    # Answer key PDFs are typically single-column
    text = extract_text_from_pdf(pdf_path, two_column=False)
    text = clean_text(text)
    text = re.sub(r'-?\s*Solutions?\s*\|', '', text)

    # Split by Q.\d+)
    pattern = r'Q\.(\d+)\)'
    parts = re.split(pattern, text)

    answers = {}
    for i in range(1, len(parts) - 1, 2):
        q_num = int(parts[i])
        content = parts[i + 1].strip()

        # Extract answer letter
        ans_match = re.search(r'Ans\)\s*([a-d])', content)
        answer = ans_match.group(1) if ans_match else None

        # Extract explanation (everything after Exp))
        exp_match = re.search(r'Exp\)\s*(.*)', content, re.DOTALL)
        explanation = ''
        if exp_match:
            explanation = exp_match.group(1).strip()
            explanation = re.sub(r'\n{3,}', '\n\n', explanation)
            # Remove Source/Subject/Topic metadata at the end
            explanation = re.sub(r'Source:\).*$', '', explanation, flags=re.DOTALL).strip()
            explanation = re.sub(r'Subject:\).*$', '', explanation, flags=re.DOTALL).strip()

        answers[q_num] = {
            'answer': answer,
            'explanation': explanation,
        }

    return answers


def parse_and_merge(question_pdf_path, answer_pdf_path):
    """Parse both PDFs and return merged list of questions with answers."""
    questions = parse_questions(question_pdf_path)
    answers = parse_answer_key(answer_pdf_path)

    for q in questions:
        q_num = q['number']
        if q_num in answers:
            q['correct_answer'] = answers[q_num]['answer']
            q['explanation'] = answers[q_num]['explanation']
        else:
            q['correct_answer'] = None
            q['explanation'] = ''

    return questions


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: python pdf_parser.py <question_pdf> <answer_pdf>")
        sys.exit(1)

    questions = parse_and_merge(sys.argv[1], sys.argv[2])
    print(f"Parsed {len(questions)} questions")

    # Verify all questions have answers
    missing = [q['number'] for q in questions if not q.get('correct_answer')]
    if missing:
        print(f"WARNING: Missing answers for questions: {missing}")

    for q in questions[:5]:
        print(f"\nQ.{q['number']}) {q['text'][:100]}...")
        print(f"  a) {q['option_a'][:80]}")
        print(f"  b) {q['option_b'][:80]}")
        print(f"  c) {q['option_c'][:80]}")
        print(f"  d) {q['option_d'][:80]}")
        print(f"  Answer: {q['correct_answer']}")
