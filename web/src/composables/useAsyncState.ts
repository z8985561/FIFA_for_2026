import { readonly, shallowRef } from 'vue'

export function useAsyncState<T>() {
  const data = shallowRef<T | null>(null)
  const loading = shallowRef(false)
  const error = shallowRef<string | null>(null)

  async function run(loader: () => Promise<T>) {
    loading.value = true
    error.value = null
    try {
      data.value = await loader()
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '请求失败'
    } finally {
      loading.value = false
    }
  }

  return {
    data: readonly(data),
    loading: readonly(loading),
    error: readonly(error),
    run,
  }
}
