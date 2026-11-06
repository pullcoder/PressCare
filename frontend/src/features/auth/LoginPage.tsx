/** 로그인 화면 자리. Supabase Auth(이메일) 연결은 T4 에서 한다. (D-009) */
export function LoginPage() {
  return (
    <section className="mx-auto max-w-sm rounded-xl bg-white p-6 shadow-sm">
      <h2 className="text-xl font-bold">로그인</h2>
      <p className="mt-2 text-sm text-gray-600">Supabase 연결 후 이메일 로그인이 들어갑니다.</p>
    </section>
  )
}
