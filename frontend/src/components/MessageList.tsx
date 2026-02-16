import { useEffect, useRef } from 'react';
import type { Message } from './types';
import MessageItem from './MessageItem';
import './MessageList.css';

interface MessageListProps {
  messages: Message[];
  streamingMessageId?: string | null;
}

function MessageList({ messages, streamingMessageId }: MessageListProps) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, streamingMessageId]);

  return (
    <div className="message-list" ref={listRef}>
      {messages.length === 0 ? (
        <div className="message-list-empty">
          <div className="empty-icon">AI</div>
          <p>你好！我是智能股票助手，有什么可以帮你的吗？</p>
        </div>
      ) : (
        messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            isStreaming={message.id === streamingMessageId}
          />
        ))
      )}
    </div>
  );
}

export default MessageList;
