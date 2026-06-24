import dayjs from 'dayjs'

export function formatTime(timeStr: string): string {
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm')
}

export function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
}

export function getErrorMessage(error: unknown, fallback = '操作失败'): string {
  if (error && typeof error === 'object') {
    const resp = (error as Record<string, unknown>).response as Record<string, unknown> | undefined
    if (resp?.data) {
      const data = resp.data as Record<string, unknown>
      if (typeof data.detail === 'string') return data.detail
    }
    if (typeof (error as Record<string, unknown>).message === 'string') {
      return (error as Record<string, unknown>).message as string
    }
  }
  return fallback
}
