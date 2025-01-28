const cl = (...items) => console.log(...items);
const clJSON = (...items) => console.log(JSON.stringify(...items, null, 2));

// STEP 1: The `createElement` Function

// Create your own createElement fn
// use rest operator on children to accept any other children
// use spread operator on props to expand all other props
const createElement = (type, props, ...children) => {
  return {
    type,
    props: {
      ...props,
      // Other than objects, children can contain string & number
      children: children.map((child) =>
        typeof child === "object" ? child : createTextElement(child)
      ),
    },
  };
};

const createTextElement = (text) => {
  return {
    type: "TEXT_ELEMENT",
    props: {
      nodeValue: text,
      children: [],
    },
  };
};

// STEP 2: The `render` Function
/**@warn superceeded by unit of work */
// const render = (element, container) => {
//   const dom =
//     element.type == "TEXT_ELEMENT"
//       ? document.createTextNode("")
//       : document.createElement(element.type);

//   const propsKey = Object.keys(element.props)
//   propsKey.forEach(key => {
//     if(key !== 'children') {
//       dom[key] = element.props[key]
//     }
//   })

//   element.props.children.forEach((child) => render(child, dom));
//   container.appendChild(dom);
// };

// STEP 3: Concurrent mode

const createDom = (fiber) => {
  const dom =
    fiber.type === "TEXT_ELEMENT"
      ? document.createTextNode("")
      : document.createElement(fiber.type);

  updateDom(dom, {}, fiber.props);
  return dom;
};

const isEvent = (key) => key.startsWith("on");
const isProperty = (key) => key !== "children" && !isEvent(key);
const isNew = (prev, next) => (key) => prev[key] !== next[key];
const isGone = (prev, next) => (key) => !(key in next);

const updateDom = (dom, prevProps, nextProps) => {
  Object.keys(prevProps)
    .filter(isEvent)
    .filter((key) => !(key in nextProps) || isNew(prevProps, nextProps)(key))
    .forEach((name) => {
      const eventType = name.toLowerCase().substring(2); // wai substring(2)?
      cl("eventType ==> ", eventType);
      dom.removeEventListener(eventType, prevProps[name]);
    });

  Object.keys(prevProps)
    .filter(isProperty)
    .filter(isGone(prevProps, nextProps))
    .forEach((name) => {
      dom[name] = "";
    });

  Object.keys(nextProps)
    .filter(isProperty)
    .filter(isNew(prevProps, nextProps))
    .forEach((name) => {
      dom[name] = nextProps[name];
    });

  Object.keys(nextProps)
    .filter(isEvent)
    .filter(isNew(prevProps, nextProps))
    .forEach((name) => {
      const eventType = name.toLowerCase().substring(2);
      dom.addEventListener(eventType, nextProps[name]);
    });
};

const commitRoot = () => {
  deletions.forEach(commitWork);
  commitWork(wipRoot.child);
  currentRoot = wipRoot;
  wipRoot = null;
};

const commitWork = (fiber) => {
  if (!fiber) return;

  let domParentFiber = fiber.parent;
  while (!domParentFiber.dom) {
    domParentFiber = domParentFiber.parent
  }
  const domParent = domParentFiber.dom

  if (fiber.effectTag === "PLACEMENT" && fiber.dom !== null) {
    domParent.appendChild(fiber.dom);
  } else if (fiber.effectTag === "UPDATE" && fiber.dom !== null) {
    updateDom(fiber.dom, fiber.alternate.props, fiber.props);
  } else if (fiber.effectTag === "DELETION") {
    if (fiber.dom) {
      domParent.removeChild(fiber.dom)
    } else {
      domParent.removeChild(fiber, domParent);
    }
  }
  commitWork(fiber.child);
  commitWork(fiber.sibling);
};

/**
 * @description Co-ordinate the setting of next unit of work
 */
const render = (element, container) => {
  wipRoot = {
    dom: container,
    props: {
      children: [element],
    },
    alternate: currentRoot,
  };
  deletions = [];
  nextUnitOfWork = wipRoot;
};

// The current implementation of render uses recursion, which only stops once the whole tree is rendered.
// If the element tree is huge, it can block the main thread. Thus, we need to break the
// rendering work to smaller chunks to allow the thread to handle other stuff too
/**
 * @todo research unit of work
 * @description the first unit of work will be the root fibre
 * aka nextUnitOfWork is a fibre 'type'
 */
let nextUnitOfWork = null;
let wipRoot = null;
let currentRoot = null;
let deletions = null;

/**
 * @param {*} deadline - comes from `requestIdleCallback`
 */
const workLoop = (deadline) => {
  let shouldYield = false;
  while (nextUnitOfWork && !shouldYield) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
    shouldYield = deadline.timeRemaining() < 1;
  }

  if (!nextUnitOfWork && wipRoot) {
    commitRoot();
  }
  requestIdleCallback(workLoop);
};

requestIdleCallback(workLoop);

const reconcileChildren = (wipFiber, elements) => {
  let index = 0;
  let oldFiber = wipFiber.alternate && wipFiber.alternate.child;
  let prevSibling = null;

  while (index < elements.length || oldFiber != null) {
    const element = elements[index];
    let newFiber = null;

    const sameType = oldFiber && element && element.type === oldFiber.type;

    if (sameType) {
      newFiber = {
        type: oldFiber.type,
        props: element.props,
        dom: oldFiber.dom,
        parent: wipFiber,
        alternate: oldFiber,
        effectTag: "UPDATE",
      };
    }

    if (element && !sameType) {
      newFiber = {
        type: element.type,
        props: element.props,
        dom: null,
        parent: wipFiber,
        alternate: null,
        effectTag: "PLACEMENT",
      };
    }

    if (oldFiber && !sameType) {
      oldFiber.effectTag = "DELETION";
      deletions.push(oldFiber);
    }

    if (oldFiber) {
      oldFiber = oldFiber.sibling;
    }

    if (index === 0) {
      wipFiber.child = newFiber;
    } else {
      prevSibling.sibling = newFiber;
    }

    prevSibling = newFiber;
    index++;
  }
};

/**
 * @description this will
 * - add the element to DOM
 * - create fiber for the element children
 * - select the nextUnitOfWork
 */
const performUnitOfWork = (fiber) => {
  const isFunctionalComponent = fiber.type instanceof Function;

  if (isFunctionalComponent) {
    updateFunctionComponent(fiber);
  } else {
    updateHostComponent(fiber);
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

let wipFiber = null
let hookIndex = null

const updateFunctionComponent = (fiber) => {
  wipFiber = fiber
  hookIndex = 0
  wipFiber.hooks = []
  const children = [fiber.type(fiber.props)]
  reconcileChildren(fiber,children)
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

const updateHostComponent = (fiber) => {
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }

  reconcileChildren(fiber, fiber.props.children);
};

const Didact = {
  createElement,
  render,
  useState
};

// const element = Didact.createElement(
//   "div",
//   { id: "foo" },
//   Didact.createElement("a", null, "bar"),
//   Didact.createElement("b")
// );

// Instructing babel to use our Didact fn, now everytime
// babel sees a JSX it'll call Didact.createElement

/** @jsx Didact.createElement */
// const container = document.getElementById("root")
// const updateValue = e => {
//   rerender(e.target.value)
// }

// const rerender = value => {
//   const element = (
//     <div>
//       <input onInput={updateValue} value={value} />
//       <h2>Hello {value}</h2>
//     </div>
//   )
//   Didact.render(element, container)
// }

// rerender("World")

// Using Fn component instead of raw HTML
/** @jsx Didact.createElement */
function Counter() {
  const [state, setState] = Didact.useState(1)
  return (
    <h1 onClick={() => setState(c => c + 1)}>
      Count: {state}
    </h1>
  )
}
const element = <Counter />
const container = document.getElementById("root");
Didact.render(element, container);
