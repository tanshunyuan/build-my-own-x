import { cl } from "../helper"

type SetStateAction<S> = S | ((prevState: S) => S);
// this technically does accept a second argument, but it's already under a deprecation warning
// and it's not even released so probably better to not define it.
type Dispatch<A> = (value: A) => void;

interface Hook<S> {
  state: S
  queue: SetStateAction<S>[];
}

// hooks are just a queue, they're comparing their old vs new
export const useState = <S = undefined>(initial: S): [S, Dispatch<SetStateAction<S>>] => {
  cl(`useState.gWipFiber ==> `, window.gWipFiber)
  cl(`useState.hookIndex ==> `, window.hookIndex)

  let oldHook: Hook<S> | null = null

  if (window.gWipFiber !== null && window.hookIndex !== null) {
    oldHook =
      window.gWipFiber.alternate &&
      window.gWipFiber.alternate.hooks &&
      window.gWipFiber.alternate.hooks[window.hookIndex]

  }
  cl(`useState.oldHook ==> `, oldHook)

  const hook: Hook<S> = {
    // if the previous has a state we use it,
    // else we initialse a new one
    state: oldHook ? oldHook.state : initial,
    // stores the action that's going to be applied
    queue: []
  }
  cl(`useState.hook ==> `, hook)

  const actions = oldHook ? oldHook.queue : []
  actions.forEach((action) => {
    cl('leactions', { action })
    hook.state = (action as (prevState: S) => S)(hook.state)
  })

  const setState: Dispatch<SetStateAction<S>> = (action: SetStateAction<S>) => {
    hook.queue.push(action)
    window.wipRoot = {
      dom: window.currentRoot.dom,
      props: window.currentRoot.props,
      alternate: window.currentRoot
    }
    window.nextUnitOfWork = window.wipRoot
    window.deletions = []
  }

  if (window.gWipFiber && window.gWipFiber.hooks) {
    window.gWipFiber.hooks.push(hook)
  }

  if (window.hookIndex !== null) {
    window.hookIndex++
  }


  return [hook.state, setState]

}