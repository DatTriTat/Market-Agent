import { useEffect, useMemo, useRef, useState } from 'react'
import ChatHeader from './components/ChatHeader'
import ChatPanel from './components/ChatPanel'
import SessionsSidebar from './components/SessionsSidebar'
import { fetchChatHistory, sendChatRequest } from './lib/chatApi'
import {
  createNewSession,
  getActiveSessionId,
  getSessionList,
  setActiveSessionId,
  touchSession,
} from './lib/session'
import type { SessionItem } from './lib/session'
import type { ChatMessage } from './types/chat'
import './App.css'

function App() {
  const apiBase = useMemo(
    () => import.meta.env.VITE_API_URL || 'http://localhost:8000',
    [],
  )

  const [sessionId, setSessionId] = useState<string>(() => getActiveSessionId())
  const [sessions, setSessions] = useState<SessionItem[]>(() => getSessionList())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const listRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!listRef.current) return
    listRef.current.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, loading])

  useEffect(() => {
    let active = true
    setLoadingHistory(true)
    fetchChatHistory(apiBase, sessionId)
      .then((history) => {
        if (active) {
          setMessages(history)
        }
      })
      .catch(() => {
        if (active) {
          setMessages([])
        }
      })
      .finally(() => {
        if (active) {
          setLoadingHistory(false)
        }
      })

    return () => {
      active = false
    }
  }, [apiBase, sessionId])

  const sendMessage = async () => {
    const trimmed = input.trim()
    if (!trimmed || loading || loadingHistory) return

    setError(null)
    setLoading(true)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }])

    try {
      const result = await sendChatRequest(apiBase, {
        session_id: sessionId,
        message: trimmed,
        context: null,
        reset: false,
      })

      if (result.history.length > 0) {
        setMessages(result.history)
      } else if (result.reply) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: result.reply },
        ])
      }
      setSessions(touchSession(sessionId))
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Unable to reach the server'
      setError(message)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, the server is not responding.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void sendMessage()
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  const handleSelectSession = (nextId: string) => {
    if (!nextId || nextId === sessionId) return
    setError(null)
    setSessionId(nextId)
    setSessions(setActiveSessionId(nextId))
  }

  const handleNewChat = () => {
    const result = createNewSession()
    setSessionId(result.sessionId)
    setSessions(result.sessions)
    setMessages([])
    setError(null)
  }

  const busy = loading || loadingHistory

  return (
    <div className={`app${sidebarOpen ? '' : ' sidebar-closed'}`}>
      <ChatHeader apiBase={apiBase} sessionId={sessionId} />
      <div className="layout">
        <SessionsSidebar
          sessions={sessions}
          activeSessionId={sessionId}
          onSelect={handleSelectSession}
          onNew={handleNewChat}
          collapsed={!sidebarOpen}
          onToggle={() => setSidebarOpen((prev) => !prev)}
        />
        {!sidebarOpen && (
          <button
            className="sidebar-toggle"
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sessions"
          >
            ☰
          </button>
        )}
        <ChatPanel
          messages={messages}
          loading={busy}
          error={error}
          input={input}
          listRef={listRef}
          onInputChange={setInput}
          onSubmit={handleSubmit}
          onKeyDown={handleKeyDown}
        />
      </div>
    </div>
  )
}

export default App
