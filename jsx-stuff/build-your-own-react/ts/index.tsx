const clJSON = (...items: any) => console.log(JSON.stringify(items, null, 2));

/**@todo figure out type for children */
// children can be either objects or string in createElement
// object_children = createElement( "div", { id: "foo" }, createElement("a", null, "bar",))
// string_children = createElement("a", null, "bar")
const createElement = (
  type: string,
  props?: HTMLElement & Record<string, string | number>,
  ...children: any[]
) => {
  children = children.map((child) =>
    typeof child === "object" ? child : createTextElement(child),
  );
  return {
    type,
    props: {
      ...props,
      children,
    },
  };
};

const createTextElement = (text: string) => {
  return {
    type: "TEXT_ELEMENT",
    props: {
      nodeValue: text,
      children: [],
    },
  };
};

type CreateElementResults = ReturnType<typeof createElement>;

type Dom = HTMLElement | Text

// each element is a fiber
type Fiber = {
  type: string | Function
  dom: Dom | null;
  parent?: Fiber
  child?: Fiber
  sibling?: Fiber
  alternate?: Fiber
  props: {
    children: CreateElementResults[];
  };
  effectTag: 'PLACEMENT' | 'UPDATE' | 'DELETION'
} | null;

// Use unit of work to split workloads
let nextUnitOfWork: Fiber = null;
/**@description new root that is being processed*/
let wipRoot = null
/**@description previous root that was processed. Diffing occurs between this and fiber.alternate*/
let currentRoot = null
let deletions = null

const createDom = (fiber): Dom => {
  const dom =
    fiber.type === "TEXT_ELEMENT"
      ? document.createTextNode("")
      : document.createElement(fiber.type);


  updateDom(dom, {}, fiber.props)

  return dom;
};

/**@description filters out props starting with on, for separate handling */
const isEvent = key => key.startsWith("on")
/**@description filters out children and event props to prevent double processing */
const isProperty = key =>
  key !== "children" && !isEvent(key)
const isNew = (prev, next) => key =>
  prev[key] !== next[key]
const isGone = (prev, next) => key => !(key in next)

const updateDom = (dom: Dom, prevProps, nextProps) => {
  //Remove old or changed event listeners
  Object.keys(prevProps)
    .filter(isEvent)
    .filter(
      key =>
        !(key in nextProps) ||
        isNew(prevProps, nextProps)(key)
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

  // Remove old properties
  Object.keys(prevProps)
    .filter(isProperty)
    .filter(isGone(prevProps, nextProps))
    .forEach(name => {
      dom[name] = ""
    })

  // Set new or changed properties
  Object.keys(nextProps)
    .filter(isProperty)
    .filter(isNew(prevProps, nextProps))
    .forEach(name => {
      dom[name] = nextProps[name]
    })
  // Add event listeners
  Object.keys(nextProps)
    .filter(isEvent)
    .filter(isNew(prevProps, nextProps))
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

/**
 * @description render fn coordinates the preparation and assignment of the next unit of work 
 */
const render = (element: CreateElementResults, container: Dom) => {
  // root fiber tree
  wipRoot = {
    dom: container,
    parent: null,
    props: {
      children: [element],
    },
    alternate: currentRoot
  };

  deletions = []
  nextUnitOfWork = wipRoot
};

/**@description commit the whole fiber tree to dom, recursively appends all nodes to it */
const commitRoot = () => {
  deletions.forEach(commitWork)
  // add nodes to dom
  commitWork(wipRoot.child)
  // saving a reference to the last processed fiber
  currentRoot = wipRoot
  // set it to null after processing
  wipRoot = null
}

/**@description a helper function to ?? */
const commitWork = (fiber: Fiber) => {
  if (!fiber) return

  let domParentFiber = fiber.parent
  while (!domParentFiber) {
    domParentFiber = domParentFiber.parent
  }

  const domParent = domParentFiber.dom

  if (
    fiber.effectTag === "PLACEMENT" &&
    fiber.dom != null
  ) {
    domParent.appendChild(fiber.dom)
  } else if (
    fiber.effectTag === "UPDATE" &&
    fiber.dom != null
  ) {
    updateDom(
      fiber.dom,
      fiber.alternate.props,
      fiber.props
    )
  } else if (fiber.effectTag === "DELETION") {
    commitDeletion(fiber, domParent)
  }

  // recursively commit child and sibling nodes
  commitWork(fiber.child)
  commitWork(fiber.sibling)
}

// why need to be recursive?
const commitDeletion = (fiber, domParent) => {
  if (fiber.dom) {
    domParent.removeChild(fiber.dom)
  } else {
    commitDeletion(fiber.child, domParent)
  }
}

const workLoop = (deadline: IdleDeadline) => {
  let shouldYield = false;
  // while there's a unit of work & it should not yield
  while (nextUnitOfWork && !shouldYield) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
    shouldYield = deadline.timeRemaining() < 1;
  }

  // check if there's a root WIP, don't want to disturb it
  if (!nextUnitOfWork && wipRoot) {
    commitRoot()
  }
  requestIdleCallback(workLoop); // <-- recursive call?
};

// https://developer.mozilla.org/en-US/docs/Web/API/Window/requestIdleCallback
// It's called whenever the main thread/browser is idle
requestIdleCallback(workLoop);

// Processes the unit of work and selects the next one
const performUnitOfWork = (fiber: Fiber) => {
  const isFunctionComponent = fiber.type instanceof Function

  if (isFunctionComponent) {
    updateFunctionComponent(fiber)
  } else {
    updateHostComponent(fiber)
  }

  if (fiber.child) {
    return fiber.child;
  }

  let nextFiber = fiber;
  while (nextFiber) {
    if (nextFiber.sibling) {
      return nextFiber.sibling;
    }
    nextFiber = nextFiber.parent;
  }
};

let hookIndex = null
let wipFiber = null
const updateFunctionComponent = (fiber) => {
  wipFiber = fiber
  hookIndex = 0
  wipFiber.hooks = []
  // running the Function to get the children
  const children = [fiber.type(fiber.props)]
  reconcileChildren(fiber, children)
}

// why is it called host compoent?
const updateHostComponent = (fiber) => {
  // add elements to the DOM
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }

  // create fibers for the element CHILDREN
  const elements = fiber.props.children;
  reconcileChildren(fiber, elements)
}


const useState = (initial) => {
  const oldHook =
    wipFiber.alternate &&
    wipFiber.alternate.hooks &&
    wipFiber.alternate.hooks[hookIndex]

  const hook = {
    state: oldHook ? oldHook.state : initial,
    queue: []
  }
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

  wipFiber.hooks.push(hook)
  hookIndex++
  return [hook.state, setState]
}

const reconcileChildren = (wipFiber: Fiber, elements: Fiber['props']['children']) => {
  let index = 0;
  let oldFiber = wipFiber.alternate && wipFiber.alternate.child
  let prevSibling = null;

  while (index < elements.length || oldFiber != null) {
    const element = elements[index];
    let newFiber = null

    const sameType = oldFiber && element && element.type == oldFiber.type

    if (sameType) {
      // after diffing, if the root type is the same, but
      // there are some changes to the props apply it
      newFiber = {
        type: oldFiber.type,
        props: element.props,
        dom: oldFiber.dom,
        parent: wipFiber,
        alternate: oldFiber,
        effectTag: "UPDATE"
      }
    }

    // after diffing, if the root type isn't the same.
    // destroy the tree & re-render it
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

    if (oldFiber && !sameType) {
      oldFiber.effectTag = "DELETION"
      deletions.push(oldFiber)
    }

    if (oldFiber) {
      oldFiber = oldFiber.sibling
    }

    if (index === 0) {
      wipFiber.child = newFiber;
    } else {
      prevSibling.sibling = newFiber;
    }

    prevSibling = newFiber;
    index++;
  }
}

const Didact = {
  createElement,
  render,
  useState,
};

// under the hood
// const element = Didact.createElement(
//   "div",
//   { id: "foo" },
//   Didact.createElement("a", null, "bar"),
//   Didact.createElement("b")
// )

// official
/**@jsx Didact.createElement*/
const container = document.getElementById("root")
const Counter = () => {
  const [state, setState] = Didact.useState(1)
  return <h1 onClick={() => setState(c => c++)}>
    Count: {state}
  </h1>
}

const element = <Counter />

Didact.render(element, container)

