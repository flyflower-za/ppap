import client from './client'
import type { Note, NoteCreate } from '@/types'

export const notesApi = {
  getByFileId: (fileId: string) =>
    client.get<any, Note[]>(`/notes/file/${fileId}`),

  create: (data: NoteCreate) =>
    client.post<any, Note>('/notes', data),

  delete: (noteId: string) =>
    client.delete(`/notes/${noteId}`),
}
