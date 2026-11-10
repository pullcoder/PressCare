import { describe, expect, it } from 'vitest'
import { assertPublicKey } from './env'

describe('Supabase 키 검사', () => {
  it('secret 키는 막는다', () => {
    expect(() => assertPublicKey('sb_secret_abc')).toThrow(/secret/)
  })
  it('publishable 키는 통과', () => {
    expect(() => assertPublicKey('sb_publishable_abc')).not.toThrow()
  })
})
