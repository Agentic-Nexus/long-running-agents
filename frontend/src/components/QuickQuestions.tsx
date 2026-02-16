import { QuickQuestion } from './types';
import './QuickQuestions.css';

interface QuickQuestionsProps {
  questions: QuickQuestion[];
  onSelect: (question: string) => void;
}

function QuickQuestions({ questions, onSelect }: QuickQuestionsProps) {
  if (questions.length === 0) return null;

  return (
    <div className="quick-questions">
      <div className="quick-questions-label">常见问题</div>
      <div className="quick-questions-list">
        {questions.map((q) => (
          <button
            key={q.id}
            className="quick-question-btn"
            onClick={() => onSelect(q.question)}
          >
            {q.question}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QuickQuestions;
