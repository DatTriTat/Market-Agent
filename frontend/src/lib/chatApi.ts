import type { ChatMessage, ChatRequestPayload } from '../types/chat'

type RawChatResponse = {
  session_id?: string
  reply?: string
  history?: Array<{ role?: string; content?: string }>
  detail?: string
}

const normalizeHistory = (
  history: RawChatResponse['history'],
): ChatMessage[] => {
  if (!Array.isArray(history)) return []
  return history.map((item) => ({
    role: item.role === 'assistant' ? 'assistant' : 'user',
    content: String(item.content ?? ''),
  }))
}

export const sendChatRequest = async (
  apiBase: string,
  payload: ChatRequestPayload,
): Promise<{ reply: string; history: ChatMessage[] }> => {
  const response = await fetch(`${apiBase}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const data: RawChatResponse = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail =
      typeof data.detail === 'string' ? data.detail : 'Request failed'
    throw new Error(detail)
  }

  return {
    reply: typeof data.reply === 'string' ? data.reply : '',
    history: normalizeHistory(data.history),
  }
}

export const resetChatSession = async (
  apiBase: string,
  sessionId: string,
) => {
  await fetch(`${apiBase}/api/chat/${sessionId}`, { method: 'DELETE' })
}

export const fetchChatHistory = async (
  apiBase: string,
  sessionId: string,
): Promise<ChatMessage[]> => {
  const response = await fetch(`${apiBase}/api/chat/${sessionId}`)
  const data: RawChatResponse = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail =
      typeof data.detail === 'string' ? data.detail : 'Request failed'
    throw new Error(detail)
  }
  return normalizeHistory(data.history)
}
