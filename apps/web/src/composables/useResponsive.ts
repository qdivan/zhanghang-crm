import { onBeforeUnmount, onMounted, ref } from "vue";

import { HANDSET_MEDIA_QUERY } from "../mobile/config";

export function useResponsive() {
  const isMobile = ref(false);

  function syncViewport() {
    if (typeof window === "undefined") return;
    isMobile.value = window.matchMedia(HANDSET_MEDIA_QUERY).matches;
  }

  onMounted(() => {
    syncViewport();
    window.addEventListener("resize", syncViewport);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", syncViewport);
  });

  return {
    isMobile,
  };
}
