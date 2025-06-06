import type { FormEvent, KeyboardEvent, RefObject } from 'react'
import type { ChatMessage } from '../types/chat'
import Composer from './Composer'
import MessageList from './MessageList'

type ChatPanelProps = {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
  input: string
  listRef: RefObject<HTMLDivElement | null>
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
}

const ChatPanel = ({
  messages,
  loading,
  error,
  input,
  listRef,
  onInputChange,
  onSubmit,
  onKeyDown,
}: ChatPanelProps) => {
  return (
    <main className="panel">
      <div className="panel__header">
        <div>
          <h2>Chat</h2>
        </div>
      </div>

      <MessageList messages={messages} loading={loading} listRef={listRef} />

      {error && <div className="error">Error: {error}</div>}

      <Composer
        input={input}
        loading={loading}
        onChange={onInputChange}
        onSubmit={onSubmit}
        onKeyDown={onKeyDown}
      />
    </main>
  )
}

export default ChatPanel
