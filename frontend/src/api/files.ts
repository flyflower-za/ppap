import client from './client'
import type { File, FileListResponse, FileDetail, FileFilter } from '@/types'

export const filesApi = {
  upload: (file: File, file_type?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (file_type) {
      formData.append('file_type', file_type)
    }
    return client.post<any, File>('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (params: FileFilter) =>
    client.get<any, FileListResponse>('/files', { params }),

  getDetail: (id: string) =>
    client.get<any, FileDetail>(`/files/${id}`),

  getDownloadUrl: async (id: string) => {
    const res = await client.get<any, { download_url: string }>(`/files/${id}/download`)
    // Rewrite internal Docker MinIO URL to relative path for Nginx proxying
    if (res && res.download_url && res.download_url.startsWith('http://minio:9000')) {
      res.download_url = res.download_url.replace('http://minio:9000', '')
    }
    return res
  },

  delete: (id: string) =>
    client.delete(`/files/${id}`),

  reverify: (id: string) =>
    client.post<any, FileDetail>(`/files/${id}/reverify`),

  batchDelete: (ids: string[]) =>
    client.post('/files/batch-delete', { file_ids: ids }),

  resolveReview: (id: string, data: { action: 'approve' | 'reject'; comment?: string }) =>
    client.post<any, FileDetail>(`/files/${id}/resolve_review`, data),
}
