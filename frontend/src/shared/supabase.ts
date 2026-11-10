import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { assertPublicKey, env } from './env'

let client: SupabaseClient | null | undefined

export function isSupabaseConfigured(): boolean {
  return Boolean(env.supabaseUrl && env.supabaseKey)
}

/** Supabase 클라이언트. .env 에 값이 없으면 null (팀장이 프로젝트를 만들기 전, T0-3). */
export function getSupabase(): SupabaseClient | null {
  if (client !== undefined) return client
  if (!isSupabaseConfigured()) {
    client = null
    return client
  }
  assertPublicKey(env.supabaseKey)
  client = createClient(env.supabaseUrl, env.supabaseKey)
  return client
}
