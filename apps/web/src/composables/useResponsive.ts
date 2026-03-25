import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { HANDSET_MEDIA_QUERY } from "../mobile/config";

const sharedIsMobile = ref(false);

let mediaQueryList: MediaQueryList | null = null;
let mediaQueryListenerAttached = false;
let responsiveConsumerCount = 0;
let mediaQueryChangeHandler: ((event: MediaQueryListEvent) => void) | null = null;

function getMediaQueryList(): MediaQueryList | null {
  if (typeof window === "undefined") return null;
  if (!mediaQueryList) {
    mediaQueryList = window.matchMedia(HANDSET_MEDIA_QUERY);
  }
  return mediaQueryList;
}

function syncViewport(matches?: boolean) {
  const query = getMediaQueryList();
  if (!query) return;
  sharedIsMobile.value = typeof matches === "boolean" ? matches : query.matches;
}

function attachViewportListener() {
  const query = getMediaQueryList();
  if (!query || mediaQueryListenerAttached) return;

  syncViewport(query.matches);
  mediaQueryChangeHandler = (event) => {
    sharedIsMobile.value = event.matches;
  };

  if (typeof query.addEventListener === "function") {
    query.addEventListener("change", mediaQueryChangeHandler);
  } else {
    query.addListener(mediaQueryChangeHandler);
  }

  mediaQueryListenerAttached = true;
}

function detachViewportListener() {
  if (responsiveConsumerCount > 0) return;

  const query = mediaQueryList;
  const handler = mediaQueryChangeHandler;
  if (!query || !mediaQueryListenerAttached || !handler) {
    mediaQueryListenerAttached = false;
    mediaQueryChangeHandler = null;
    return;
  }

  if (typeof query.removeEventListener === "function") {
    query.removeEventListener("change", handler);
  } else {
    query.removeListener(handler);
  }

  mediaQueryChangeHandler = null;
  mediaQueryListenerAttached = false;
}

export function useResponsive() {
  const isMobile = computed(() => sharedIsMobile.value);

  onMounted(() => {
    responsiveConsumerCount += 1;
    attachViewportListener();
    syncViewport();
  });

  onBeforeUnmount(() => {
    responsiveConsumerCount = Math.max(0, responsiveConsumerCount - 1);
    detachViewportListener();
  });

  return {
    isMobile,
  };
}
