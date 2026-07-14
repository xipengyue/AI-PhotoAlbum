import request from '@/utils/request'
import type { PhotoItem, PhotoListResponse, PhotoDetail } from '@/types/photo'

export interface PhotoListParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export const photoApi = {
  /** 上传照片 */
  upload(file: File, onProgress?: (pct: number) => void) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<PhotoDetail>('/photos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total))
      },
    })
  },

  /** 照片列表 */
  list(params: PhotoListParams = {}) {
    return request.get<PhotoListResponse>('/photos', { params })
  },

  /** 照片详情 */
  getById(id: string) {
    return request.get<PhotoDetail>(`/photos/${id}`)
  },

  /** 软删除 */
  delete(id: string) {
    return request.delete(`/photos/${id}`)
  },

  /** 恢复 */
  restore(id: string) {
    return request.post(`/photos/${id}/restore`)
  },

  /** 获取 EXIF 元数据 */
  getMetadata(id: string) {
    return request.get(`/photos/${id}/metadata`)
  },

  /** 缩略图 URL */
  thumbnailUrl(id: string) {
    return `/api/medias/${id}/thumbnail`
  },

  /** 原始文件 URL */
  fileUrl(id: string) {
    return `/api/medias/${id}/file`
  },

  // ── 回收站 ────────────────────────────

  /** 回收站列表 */
  getRecycleBin() {
    return request.get<PhotoListResponse>('/photos/recycle-bin/list')
  },

  /** 永久删除 */
  permanentDelete(id: string) {
    return request.delete(`/photos/recycle-bin/${id}/permanent`)
  },

  /** 清空回收站 */
  emptyRecycleBin() {
    return request.post('/photos/recycle-bin/empty')
  },

  /** 剩余天数 */
  daysLeft(deletedAt: string): number {
    const deleted = new Date(deletedAt)
    const expire = new Date(deleted.getTime() + 7 * 24 * 3600 * 1000)
    const now = new Date()
    return Math.max(0, Math.ceil((expire.getTime() - now.getTime()) / (24 * 3600 * 1000)))
  },
}
