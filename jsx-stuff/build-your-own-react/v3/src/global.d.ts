/**@todo figure out why this import causes an issue */
// import { Fiber } from './didact/render';

// declare var nextUnitOfWork: any
// declare var wipRoot: any
// declare var currentRoot: any
// declare var deletions: any[] | null
// declare var gWipFiber: any
// declare var hookIndex: any

interface Window {
  nextUnitOfWork: import('./didact/render').Fiber | null
  wipRoot: any
  currentRoot: any
  deletions: any[] | null
  gWipFiber: import('./didact/render').Fiber | null
  hookIndex: number | null
}