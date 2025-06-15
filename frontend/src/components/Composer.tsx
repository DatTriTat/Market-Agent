import type { FormEvent, KeyboardEvent } from 'react'

type ComposerProps = {
  input: string
  loading: boolean
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
}

const Composer = ({
  input,
  loading,
  onChange,
  onSubmit,
  onKeyDown,
}: ComposerProps) => {
  return (
    <form className="composer" onSubmit={onSubmit}>
      <textarea
        placeholder="Ask about a stock symbol like AAPL.US"
        value={input}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        rows={3}
      />
      <div className="composer__actions">
        <span className="hint">{input.length} / 1000</span>
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </form>
  )
}

export default Composer
