import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('kahvecell.accessToken')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function getErrorMessage(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  if (error?.code === 'ECONNABORTED' || !error?.response) {
    return 'Backend’e ulaşılamıyor. FastAPI sunucusunun çalıştığını kontrol edin.'
  }
  return 'Bir sorun oluştu. Lütfen tekrar deneyin.'
}
