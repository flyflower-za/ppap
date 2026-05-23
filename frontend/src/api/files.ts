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

  getDownloadUrl: (id: string) =>
    client.get<any, { download_url: string }>(`/files/${id}/download`),

  delete: (id: string) =>
    client.delete(`/files/${id}`),

  batchDelete: (ids: string[]) =>
    client.post('/files/batch-delete', { file_ids: ids }),
}
