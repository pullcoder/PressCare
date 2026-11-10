import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from './client'

afterEach(() => vi.unstubAllGlobals())

const reply = (status: number, body: unknown) =>
  vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))

describe('apiRequest', () => {
  it('성공하면 JSON 을 돌려준다', async () => {
    vi.stubGlobal('fetch', reply(200, { status: 'ok' }))
    await expect(apiRequest('/health')).resolves.toEqual({ status: 'ok' })
  })
  it('backend 오류 형식을 ApiError 로 바꾼다', async () => {
    vi.stubGlobal(
      'fetch',
      reply(503, { error: { code: 'SUPABASE_NOT_CONFIGURED', message: '설정 필요' } }),
    )
    await expect(apiRequest('/x')).rejects.toMatchObject({
      code: 'SUPABASE_NOT_CONFIGURED',
      status: 503,
    })
  })
  it('서버가 꺼져 있으면 NETWORK_ERROR', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed')))
    const err = await apiRequest('/x').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('NETWORK_ERROR')
  })
})
