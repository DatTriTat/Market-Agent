import type { SessionItem } from '../lib/session'

type SessionListProps = {
  sessions: SessionItem[]
  activeSessionId: string
  onSelect: (sessionId: string) => void
}

const SessionList = ({
  sessions,
  activeSessionId,
  onSelect,
}: SessionListProps) => {
  return (
    <div className="session-list">
      <div className="session-list__items">
        {sessions.length === 0 && (
          <div className="session-empty">No sessions yet.</div>
        )}
        {sessions.map((session) => {
          const active = session.id === activeSessionId
          return (
            <button
              key={session.id}
              type="button"
              className={`session-item${active ? ' active' : ''}`}
              onClick={() => onSelect(session.id)}
            >
              <span className="session-item__title">{session.label}</span>
              <span className="session-item__meta">
                {session.id.slice(0, 8)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default SessionList
