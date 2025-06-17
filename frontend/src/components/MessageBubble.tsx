import type { ChatMessage } from '../types/chat'

type MessageBubbleProps = ChatMessage

const formatAssistantContent = (text: string) => {
  if (!text) return text
  if (!/(Symbol:|As of:|Price:|Trend:|News:)/.test(text)) {
    return text
  }

  let out = text.trim()
  out = out.replace(/\s+(As of:|Price:|Trend:|News:)/g, '\n$1')
  out = out.replace(/News:\s*-\s*/g, 'News:\n- ')
  out = out.replace(/\s+-\s+/g, '\n- ')
  return out
}

const MessageBubble = ({ role, content }: MessageBubbleProps) => {
  const displayText = role === 'assistant' ? formatAssistantContent(content) : content

  return (
    <div className={`message ${role}`}>
      <span className="message__role">{role === 'user' ? 'You' : 'Agent'}</span>
      <p>{displayText}</p>
    </div>
  )
}

export default MessageBubble
