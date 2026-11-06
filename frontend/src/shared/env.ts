/** 브라우저에서 읽는 설정값. 루트 .env 의 VITE_ 값만 들어온다. */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL || '',
  supabaseKey: import.meta.env.VITE_SUPABASE_ANON_KEY || '',
}

/** secret 키가 브라우저에 들어오면 RLS 가 무시되므로 바로 멈춘다. (SECURITY.md) */
export function assertPublicKey(key: string): void {
  if (key.startsWith('sb_secret_')) {
    throw new Error(
      'VITE_SUPABASE_ANON_KEY 에 secret 키를 넣으면 안 됩니다. publishable 키(sb_publishable_...)를 넣으세요.',
    )
  }
}
