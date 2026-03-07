import { onBeforeUnmount, onMounted, ref } from "vue";

const MOBILE_BREAKPOINT_QUERY = "(max-width: 900px)";

export function useResponsive() {
  const isMobile = ref(false);

  function syncViewport() {
    if (typeof window === "undefined") return;
    isMobile.value = window.matchMedia(MOBILE_BREAKPOINT_QUERY).matches;
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
