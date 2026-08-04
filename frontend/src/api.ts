export class ApiError extends Error {
  constructor(public status: number, public body: { error?: string; enabled?: boolean }) {
    super(body.error ?? `HTTP ${status}`)
  }
}

async function handle<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, body ?? {})
  return body as T
}

export const fetchJson = <T,>(path: string) => fetch(path).then(r => handle<T>(r))
export const postJson = <T,>(path: string, body: unknown) =>
  fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' },
                body: JSON.stringify(body) }).then(r => handle<T>(r))
