export type Role = 'user' | 'assistant'

export type ChatMessage = {
  role: Role
  content: string
}

export type ChatRequestPayload = {
  session_id: string
  message: string
  context: string | null
  reset: boolean
}
