import { cl } from "../helper"

// hooks are just a queue, they're comparing their old vs new
export const useState = <Type>(initial: Type) => {
  cl(`useState.gWipFiber ==> `, gWipFiber)
  const oldHook =
    gWipFiber.alternate &&
    gWipFiber.alternate.hooks &&
    gWipFiber.alternate.hooks[hookIndex]

  const hook = {
    // if the previous has a state we use it,
    // else we initialse a new one
    state: oldHook ? oldHook.state : initial,
    // stores the action that's going to be applied
    queue: []
  }
  cl(`useState.hook ==> `, hook)

  const actions = oldHook ? oldHook.queue : []
  actions.forEach(action => {
    hook.state = action(hook.state)
  })

  const setState = action => {
    hook.queue.push(action)
    wipRoot = {
      dom: currentRoot.dom,
      props: currentRoot.props,
      alternate: currentRoot
    }
    nextUnitOfWork = wipRoot
    deletions = []
  }

  gWipFiber.hooks.push(hook)
  hookIndex++

  return [hook.state, setState]

}