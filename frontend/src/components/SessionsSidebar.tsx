import type { SessionItem } from '../lib/session'
import SessionList from './SessionList'

type SessionsSidebarProps = {
  sessions: SessionItem[]
  activeSessionId: string
  onSelect: (sessionId: string) => void
  onNew: () => void
  collapsed: boolean
  onToggle: () => void
}

const SessionsSidebar = ({
  sessions,
  activeSessionId,
  onSelect,
  onNew,
  collapsed,
  onToggle,
}: SessionsSidebarProps) => {
  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      <div className="sidebar__header">
        <div>
          <h3>Sessions</h3>
        </div>
        <div className="sidebar__actions">
          <button className="ghost" type="button" onClick={onNew}>
            New
          </button>
          <button className="ghost icon" type="button" onClick={onToggle} aria-label="Toggle sessions">
            {collapsed ? '☰' : '×'}
          </button>
        </div>
      </div>
      {!collapsed && (
        <SessionList
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={onSelect}
        />
      )}
    </aside>
  )
}

export default SessionsSidebar
