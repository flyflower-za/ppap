import dayjs from 'dayjs'

export function formatTime(timeStr: string): string {
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm')
}

export function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
