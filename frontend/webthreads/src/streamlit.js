/**
 * Streamlit Custom Component Communication Helper
 */
export const Streamlit = {
  setComponentReady: () => {
    window.parent.postMessage({
      isStreamlitMessage: true,
      type: "streamlit:componentReady",
      apiVersion: 1,
    }, "*");
  },
  setFrameHeight: (height) => {
    const h = height || document.documentElement.scrollHeight || window.innerHeight || 800;
    window.parent.postMessage({
      isStreamlitMessage: true,
      type: "streamlit:setFrameHeight",
      height: h,
    }, "*");
  },
  setComponentValue: (value) => {
    window.parent.postMessage({
      isStreamlitMessage: true,
      type: "streamlit:setComponentValue",
      value: value,
    }, "*");
  },
  onRender: (callback) => {
    const handler = (event) => {
      if (event.data && event.data.isStreamlitMessage && event.data.type === "streamlit:render") {
        callback(event.data.args);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  },
};
