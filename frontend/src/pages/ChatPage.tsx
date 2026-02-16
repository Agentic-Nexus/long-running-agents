import { useState, useCallback, useRef } from 'react';
import type { Message, QuickQuestion } from '../components/types';
import MessageList from '../components/MessageList';
import ChatWindow from '../components/ChatWindow';
import QuickQuestions from '../components/QuickQuestions';
import './ChatPage.css';

const API_BASE = '/api';

const defaultQuickQuestions: QuickQuestion[] = [
  { id: '1', question: '推荐一只低估值的股票' },
  { id: '2', question: '分析贵州茅台的投资价值' },
  { id: '3', question: '什么是K线形态？' },
  { id: '4', question: '当前市场走势如何？' },
];

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const generateId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const handleSend = useCallback(async (content: string) => {
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    const assistantMessageId = generateId();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setIsLoading(true);
    setStreamingMessageId(assistantMessageId);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: content }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: msg.content + parsed.content }
                      : msg
                  )
                );
              }
            } catch {
              // 忽略解析错误，继续处理
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // 请求被取消
        return;
      }
      console.error('Chat error:', error);

      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessageId
            ? { ...msg, content: '抱歉，发生了一些错误，请稍后重试。' }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      setStreamingMessageId(null);
      abortControllerRef.current = null;
    }
  }, []);

  const handleQuickQuestion = (question: string) => {
    handleSend(question);
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <h1>智能问答</h1>
        <p>基于AI的股票投资助手</p>
      </header>
      <div className="chat-container">
        <MessageList
          messages={messages}
          streamingMessageId={streamingMessageId}
        />
        <QuickQuestions
          questions={defaultQuickQuestions}
          onSelect={handleQuickQuestion}
        />
        <ChatWindow
          onSend={handleSend}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}

export default ChatPage;
