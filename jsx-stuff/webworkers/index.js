const worker = new Worker('./worker.js');

worker.postMessage({
  your: 'face',
  is: 'not cool'
})

function handleMessage(e) {
  console.log('receiving...')
  console.log(e.data)
  worker.removeEventListener('message', () => {})
}

worker.addEventListener('message', handleMessage)