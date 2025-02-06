import { cl } from "../helper"
import { createDom } from "./render"

// goals of a fiber tree
// 1. Easy to find the next unit of work as each fiber is linked to its child, next sibling and parent
//    - if a fiber work is finished, it'll select the child as the next unit of work
//    - if it doesn't have a child, we choose the sibling
//    - if it doesn't have a child or a sibling, we choose the SIBLING of the parent


const commitRoot = () => {
  deletions.forEach(commitWork)
  /**@description recursively append all the nodes to the dom */
  commitWork(window.wipRoot.child)
  window.currentRoot = window.wipRoot
  window.wipRoot = null
}

/**@description check if it's events */
const isEvent = key => key.startsWith('on')

/**@description skip over children & events as it's a special prop */
const isProperty = (key: string) => key !== 'children' && !isEvent(key)

/**@description compare against prev and incoming Props to determine new props */
const isNewProps = (prev, next) => key => prev[key] !== next[key]

/**@description compare against prev and incoming Props to determine old props  */
const isOldProps = (prev, next) => key => !(key in next)


/**
 * @description
 * Given a dom node, compare it's previous props
 * against the incoming props
 */
export const updateDom = (dom, prevProps, nextProps) => {
  cl(`updateDom.dom ==> `, dom)
  //Remove old or changed event listeners
  Object.keys(prevProps)
    .filter(isEvent)
    .filter(
      key =>
        !(key in nextProps) ||
        isNewProps(prevProps, nextProps)(key)
    )
    .forEach(name => {
      const eventType = name
        .toLowerCase()
        .substring(2)
      dom.removeEventListener(
        eventType,
        prevProps[name]
      )
    })

  // remove old properties
  Object.keys(prevProps)
    .filter(isProperty)
    .filter(isOldProps(prevProps, nextProps))
    .forEach(name => {
      dom[name] = ""
    })


  // Set new or changed properties
  Object.keys(nextProps)
    .filter(isProperty)
    .filter(isNewProps(prevProps, nextProps))
    // .filter(key => prevProps[key] !== nextProps[key]) // Directly check for changes w/o isNewProps
    .forEach(name => {
      dom[name] = nextProps[name]
    })

  // Add event listeners
  Object.keys(nextProps)
    .filter(isEvent)
    .filter(isNewProps(prevProps, nextProps))
    .forEach(name => {
      const eventType = name
        .toLowerCase()
        .substring(2)
      dom.addEventListener(
        eventType,
        nextProps[name]
      )
    })
}

const commitWork = (fiber) => {
  cl('commitWork.fiber ==> ', fiber)
  if (!fiber) return

  let domParentFiber = fiber.parent
  while (!domParentFiber.dom) {
    domParentFiber = domParentFiber.parent
  }
  const domParent = domParentFiber.dom

  if (fiber.effectTag === "PLACEMENT" && fiber.dom !== null) {
    domParent.appendChild(fiber.dom)
  } else if (
    fiber.effectTag === "UPDATE" &&
    fiber.dom !== null
  ) {
    updateDom(
      fiber.dom,
      fiber.alternate.props,
      fiber.props
    )
  } else if (fiber.effectTag === "DELETION") {
    commitDeletion(fiber, domParent)
  }

  commitWork(fiber.child)
  commitWork(fiber.silbing)
}

const commitDeletion = (fiber, domParent) => {
  if (fiber.dom) {
    domParent.removeChild(fiber.dom)
  } else {
    commitDeletion(fiber.child, domParent)
  }
}

const workLoop = (deadline: IdleDeadline) => {
  // cl('workLoop ==> ', {
  //   nextUnitOfWork: window.nextUnitOfWork,
  //   wipRoot: window.wipRoot
  // })
  let shouldYield = false

  while (window.nextUnitOfWork && !shouldYield) {
    window.nextUnitOfWork = performUnitOfWork(window.nextUnitOfWork)
    // should stop the rendering process and pass it back
    // to the browser
    shouldYield = deadline.timeRemaining() < 1
  }

  if (!window.nextUnitOfWork && window.wipRoot) {
    commitRoot()
  }

  // schedule the next call
  requestIdleCallback(workLoop)
}

// initialise the call
requestIdleCallback(workLoop)

const performUnitOfWork = (fiber: any) => {
  cl('performUnitOfWork.fiber ==> ', fiber)

  const isFunctionComponent = fiber.type instanceof Function
  if (isFunctionComponent) {
    updateFunctionComponent(fiber)
  } else {
    updateHostComponent(fiber)
  }

  /**
   * @step3 select the next unit of work 
   * Check if there's a child, if not try the siblings,then with the uncle, lastly the parent
   * The fiber tree heirachy is: child -> sibling -> uncle (siblings of the parent) -> parent
   */
  if (fiber.child) {
    return fiber.child
  }

  let nextFiber = fiber
  while (nextFiber) {
    if (nextFiber.sibling) {
      return nextFiber.sibling
    }
    nextFiber = nextFiber.parent
  }
}

const updateFunctionComponent = (fiber) => {
  /**
   * @description 
   * A functional component doesn't have a dom node and the children comes from
   * running the function instead of the `props` attribute
   */
  gWipFiber = fiber
  hookIndex = 0
  gWipFiber.hooks = []
  const children = [fiber.type(fiber.props)]
  reconcileChildren(fiber, children)
}

const updateHostComponent = (fiber) => {
  /**@step1 add element to the DOM */
  if (!fiber.dom) {
    fiber.dom = createDom(fiber)
  }

  /**@step2 Create fiber for the element children */
  const elements = fiber.props.children
  reconcileChildren(fiber, elements)
}


const reconcileChildren = (wipFiber, elements) => {
  cl('reconcileChildren ==> ', { wipFiber, elements })
  let index = 0
  let oldFiber = wipFiber.alternate && wipFiber.alternate.child
  let prevSibling = null

  /**
   * @important
   * element VS oldFiber
   * Element is what we want to render
   * Old Fiber is what we rendered last time
   * 
   * We need to compare them to see if there is any changes
   * to apply to the DOM
   */
  while (index < elements.length || oldFiber !== null) {
    const element = elements[index]
    let newFiber = null

    /**@start compare oldFiber to element */
    const sameType = oldFiber && element && oldFiber.type === element.type

    /**
     * @description
     * If oldFiber & element is the same type,
     * keep the DOM node and update with the new props
     */
    if (sameType) {
      newFiber = {
        // keep the type
        type: oldFiber.type,
        // change the props
        props: element.props,
        // keep the dom node
        dom: oldFiber.dom,
        parent: wipFiber,
        alternate: oldFiber,
        effectTag: "UPDATE",
      }
    }

    /**
     * @description
     * If type is different and there is a new element
     * we need to create a new DOM node
     */
    if (element && !sameType) {
      newFiber = {
        type: element.type,
        props: element.props,
        dom: null,
        parent: wipFiber,
        alternate: null,
        effectTag: "PLACEMENT",
      }
    }

    /**
     * @description
     * If types are different & oldFiber exists
     * need to remove the old node
     */
    if (oldFiber && !sameType) {
      oldFiber.effectTag = "DELETION"
      deletions.push(oldFiber)
    }
    /**@end compare oldFiber to element */

    if (oldFiber) {
      oldFiber = oldFiber.sibling
    }

    // building a singly linked list
    if (index === 0) {
      // first child is always at the 0th index
      wipFiber.child = newFiber
    } else if (element) {
      prevSibling.sibling = newFiber
    }

    prevSibling = newFiber
    index++
  }
}