type ChatHeaderProps = {
  apiBase: string
  sessionId: string
}

const ChatHeader = ({ apiBase, sessionId }: ChatHeaderProps) => {
  const shortSession = sessionId ? sessionId.slice(0, 8) : 'new'

  return (
    <header className="hero">
      <div className="hero__row">
        <span className="hero__tag">Market Agent</span>
        <div className="hero__meta">
          <div className="pill">Session: {shortSession}</div>
        </div>
      </div>
      <h1>Conversation-first stock assistant</h1>
    </header>
  )
}

export default ChatHeader
