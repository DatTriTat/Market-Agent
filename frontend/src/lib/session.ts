export type SessionItem = {
  id: string
  label: string
  createdAt: number
  lastUsed: number
}

const LIST_KEY = 'market_agent_sessions'
const ACTIVE_KEY = 'market_agent_active_session'
const LEGACY_KEY = 'market_agent_session'

const now = () => Date.now()

export const createSessionId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `session-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

const normalizeSession = (item: Partial<SessionItem>): SessionItem | null => {
  if (!item.id) return null
  const createdAt = typeof item.createdAt === 'number' ? item.createdAt : now()
  const lastUsed = typeof item.lastUsed === 'number' ? item.lastUsed : createdAt
  const label = item.label || `Session ${item.id.slice(0, 8)}`
  return { id: item.id, label, createdAt, lastUsed }
}

const loadSessions = (): SessionItem[] => {
  if (typeof window === 'undefined') return []
  const raw = window.localStorage.getItem(LIST_KEY)
  let list: SessionItem[] = []
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Partial<SessionItem>[]
      if (Array.isArray(parsed)) {
        list = parsed
          .map((item) => normalizeSession(item))
          .filter((item): item is SessionItem => item !== null)
      }
    } catch {
      list = []
    }
  }
  const legacy = window.localStorage.getItem(LEGACY_KEY)
  if (legacy && !list.some((item) => item.id === legacy)) {
    list.push(normalizeSession({ id: legacy }) as SessionItem)
  }
  return list
}

const saveSessions = (sessions: SessionItem[]) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(LIST_KEY, JSON.stringify(sessions))
}

const sortSessions = (sessions: SessionItem[]) =>
  [...sessions].sort((a, b) => b.lastUsed - a.lastUsed)

const ensureSession = (sessionId: string) => {
  const sessions = loadSessions()
  const existing = sessions.find((item) => item.id === sessionId)
  if (existing) return sessions
  const item = normalizeSession({ id: sessionId })
  if (item) {
    sessions.push(item)
  }
  return sessions
}

export const getSessionList = () => sortSessions(loadSessions())

export const getActiveSessionId = () => {
  if (typeof window === 'undefined') {
    return createSessionId()
  }
  const stored = window.localStorage.getItem(ACTIVE_KEY)
  if (stored) {
    saveSessions(ensureSession(stored))
    return stored
  }
  const fallback = window.localStorage.getItem(LEGACY_KEY)
  if (fallback) {
    window.localStorage.setItem(ACTIVE_KEY, fallback)
    saveSessions(ensureSession(fallback))
    return fallback
  }
  const nextId = createSessionId()
  window.localStorage.setItem(ACTIVE_KEY, nextId)
  saveSessions(ensureSession(nextId))
  return nextId
}

export const setActiveSessionId = (sessionId: string) => {
  if (typeof window === 'undefined') return getSessionList()
  window.localStorage.setItem(ACTIVE_KEY, sessionId)
  const sessions = ensureSession(sessionId)
  const updated = sessions.map((item) =>
    item.id === sessionId ? { ...item, lastUsed: now() } : item,
  )
  saveSessions(updated)
  return sortSessions(updated)
}

export const createNewSession = () => {
  const sessionId = createSessionId()
  const sessions = setActiveSessionId(sessionId)
  return { sessionId, sessions }
}

export const touchSession = (sessionId: string) => {
  const sessions = ensureSession(sessionId).map((item) =>
    item.id === sessionId ? { ...item, lastUsed: now() } : item,
  )
  saveSessions(sessions)
  return sortSessions(sessions)
}
