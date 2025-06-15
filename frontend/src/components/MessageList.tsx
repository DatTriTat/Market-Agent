import type { RefObject } from 'react'
import type { ChatMessage } from '../types/chat'
import MessageBubble from './MessageBubble'

type MessageListProps = {
  messages: ChatMessage[]
  loading: boolean
  listRef: RefObject<HTMLDivElement | null>
}

const MessageList = ({ messages, loading, listRef }: MessageListProps) => {
  return (
    <div className="messages" ref={listRef}>
      {messages.length === 0 && (
        <div className="empty">Start with: "AAPL trend today and any news?"</div>
      )}
      {messages.map((msg, index) => (
        <MessageBubble key={`${msg.role}-${index}`} {...msg} />
      ))}
      {loading && (
        <div className="message assistant skeleton">
          <span className="message__role">Agent</span>
          <p>Thinking...</p>
        </div>
      )}
    </div>
  )
}

export default MessageList
