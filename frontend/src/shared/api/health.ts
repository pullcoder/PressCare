import { apiRequest } from './client'

export type HealthResponse = {
  status: 'ok'
  app_env: string
  supabase: 'not_configured' | 'connected' | 'unreachable'
}

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health')
}
