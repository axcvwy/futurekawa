import { onBeforeUnmount, onMounted, reactive, ref, watch, type WatchSource } from "vue";

export interface UseFetchOptions {
  interval?: number;
  watchSources?: WatchSource[];
}

export function useFetch<T>(
  fn: () => Promise<T>,
  options: UseFetchOptions = {},
) {
  const data = ref<T | undefined>(undefined);
  const isLoading = ref(false);
  const isError = ref(false);
  const error = ref<Error | null>(null);
  let timer: number | undefined;

  async function executer(): Promise<void> {
    isLoading.value = true;
    try {
      data.value = await fn();
      isError.value = false;
      error.value = null;
    } catch (e) {
      isError.value = true;
      error.value = e as Error;
    } finally {
      isLoading.value = false;
    }
  }

  onMounted(() => {
    void executer();
    if (options.interval) {
      timer = window.setInterval(() => void executer(), options.interval);
    }
  });

  if (options.watchSources && options.watchSources.length > 0) {
    watch(options.watchSources, () => void executer(), { immediate: false });
  }

  onBeforeUnmount(() => {
    if (timer !== undefined) window.clearInterval(timer);
  });

  return reactive({ data, isLoading, isError, error, recharger: executer });
}
