function handleMessage(e) {
  if (e.data.is === "cool") {
    postMessage("yes");
  } else {
    postMessage("how dare you?");
  }
  // cleanup
  self.removeEventListener('message', undefined)
}
// https://developer.mozilla.org/en-US/docs/Web/API/Window/message_event
self.addEventListener('message', handleMessage)