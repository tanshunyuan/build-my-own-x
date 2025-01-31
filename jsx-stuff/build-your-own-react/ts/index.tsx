const clJSON = (...items: any) => console.log(JSON.stringify(items, null, 2));

type CustomProps = Record<string, string | number>;

/**@todo figure out type for children */
// children can be either objects or string in createElement
// object_children = createElement( "div", { id: "foo" }, createElement("a", null, "bar",))
// string_children = createElement("a", null, "bar")
const createElement = (
  type: string,
  props?: HTMLElement & CustomProps,
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
type Fiber = {
  type: string
  dom: Dom | null;
  // each element is a fiber
  parent?: Fiber
  child?: Fiber
  sibling?: Fiber
  alternate?: Fiber
  props: {
    children: CreateElementResults[];
  };
  effectTag: string
} | null;
// Use unit of work to split workloads
let nextUnitOfWork: Fiber = null;
let wipRoot = null
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

const filterChildrenProps = (key: string) => key !== "children";

const isEvent = key => key.startsWith("on")
const isProperty = key =>
  key !== "children" && !isEvent(key)
const isNew = (prev, next) => key =>
  prev[key] !== next[key]
const isGone = (prev, next) => key => !(key in next)

const updateDom = (dom: Dom, prevProps, nextProps) => {
  // TODO
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
    .filter(filterChildrenProps)
    .filter(isGone(prevProps, nextProps))
    .forEach(name => {
      dom[name] = ""
    })
​
  // Set new or changed properties
  Object.keys(nextProps)
    .filter(filterChildrenProps)
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

const commitRoot = () => {
  deletions.forEach(commitWork)
  // add nodes to dom
  commitWork(wipRoot.child)
  // saving a reference to the last processed fiber
  currentRoot = wipRoot
  // set it to null after processing
  wipRoot = null
}

const commitWork = (fiber: Fiber) => {
  if (!fiber) return

  const domParent = fiber.parent.dom

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
    domParent.removeChild(fiber.dom)
  }

  // recursively commit child and sibling nodes
  commitWork(fiber.child)
  commitWork(fiber.sibling)
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
  // add elements to the DOM
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }

  // causes interruption?
  // if (fiber.parent) {
  //   fiber.parent.dom.appendChild(fiber.dom);
  // }

  // create fibers for the element CHILDREN
  const elements = fiber.props.children;
  reconcileChildren(fiber, elements)
  // let index = 0;
  // let prevSibling = null;

  // while (index < elements.length) {
  //   const element = elements[index];
  //   // unit of work
  //   const newFiber = {
  //     type: element.type,
  //     props: element.props,
  //     parent: fiber,
  //     dom: null,
  //   };

  //   if (index === 0) {
  //     fiber.child = newFiber;
  //   } else {
  //     prevSibling.sibling = newFiber;
  //   }

  //   prevSibling = newFiber;
  //   index++;
  // }

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

const reconcileChildren = (wipFiber: Fiber, elements: Fiber['props']['children']) => {
  let index = 0;
  let prevFiber = wipFiber.alternate && wipFiber.alternate.child
  let prevSibling = null;

  while (index < elements.length || prevFiber != null) {
    const element = elements[index];
    let newFiber = null
    // unit of work
    // const newFiber = {
    //   type: element.type,
    //   props: element.props,
    //   parent: wipFiber,
    //   dom: null,
    // };

    const sameType = prevFiber && element && element.type == prevFiber.type

    if (sameType) {
      newFiber = {
        type: prevFiber.type,
        props: element.props,
        dom: prevFiber.dom,
        parent: wipFiber,
        alternate: prevFiber,
        effectTag: "UPDATE"
      }
    }

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

    if (prevFiber && !sameType) {
      prevFiber.effectTag = "DELETION"
      deletions.push(prevFiber)
    }

    if (prevFiber) {
      prevFiber = prevFiber.sibling
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

const updateValue = e => {
  rerender(e.target.value)
}

const rerender = value => {
  const element = (
    <div>
      <input onInput={updateValue} value={value} />
      <h2>Hello {value}</h2>
    </div>
  )
  Didact.render(element, container)
}

rerender("World")
