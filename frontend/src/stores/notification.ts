import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '@/api/client'

export const useNotificationStore = defineStore('notification', () => {
  const unreadCount = ref(0)
  let pollTimer: ReturnType<typeof setTimeout> | null = null

  async function fetchUnreadCount() {
    try {
      const res = await client.get('/notifications?limit=1', { skipGlobalError: true, skipCancel: true } as any) as any
      unreadCount.value = res.unread_count ?? 0
    } catch {
      // silent
    }
    pollTimer = setTimeout(fetchUnreadCount, 60_000)
  }

  function startPolling() {
    stopPolling()
    fetchUnreadCount()
  }

  function stopPolling() {
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  function setUnreadCount(count: number) {
    unreadCount.value = count
  }

  function markAllRead() {
    unreadCount.value = 0
  }

  function decrementUnread() {
    if (unreadCount.value > 0) {
      unreadCount.value--
    }
  }

  return {
    unreadCount,
    startPolling,
    stopPolling,
    setUnreadCount,
    markAllRead,
    decrementUnread,
  }
})
