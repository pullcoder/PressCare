/**
 * 알림 확인·수동 기록에 남길 간호사 이름. 로그인(T4) 전 임시로 이 브라우저에만 저장한다.
 * 저장이 막힌 환경(시크릿 창 등)에서도 화면은 동작해야 하므로 실패는 무시한다.
 */
const KEY = 'presscare.nurseName'
const DEFAULT_NAME = '간호사'

export function getNurseName(): string {
  try {
    return localStorage.getItem(KEY) || DEFAULT_NAME
  } catch {
    return DEFAULT_NAME
  }
}

export function setNurseName(name: string): void {
  try {
    localStorage.setItem(KEY, name.trim().slice(0, 20) || DEFAULT_NAME)
  } catch {
    // 저장 못 해도 이번 화면에서는 입력값을 그대로 쓴다
  }
}

export function getPref(key: string, fallback: string): string {
  try {
    return localStorage.getItem(`presscare.${key}`) ?? fallback
  } catch {
    return fallback
  }
}

export function setPref(key: string, value: string): void {
  try {
    localStorage.setItem(`presscare.${key}`, value)
  } catch {
    // 무시
  }
}
