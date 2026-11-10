import { env } from '../env'

/** backend 오류 형식: { "error": { "code", "message" } } (API.md) */
export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

function readError(body: unknown): { code?: string; message?: string } {
  if (typeof body === 'object' && body !== null && 'error' in body) {
    const err = (body as { error: unknown }).error
    if (typeof err === 'object' && err !== null) return err as { code?: string; message?: string }
  }
  return {}
}

/** 모든 backend 호출은 이 함수를 거친다. 컴포넌트에서 fetch 를 직접 쓰지 않는다. (CONVENTIONS 4장) */
export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${env.apiBaseUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    })
  } catch {
    throw new ApiError('NETWORK_ERROR', '서버에 연결할 수 없습니다.', 0)
  }
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const err = readError(body)
    throw new ApiError(
      err.code ?? 'HTTP_ERROR',
      err.message ?? `요청 실패 (${res.status})`,
      res.status,
    )
  }
  return body as T
}
