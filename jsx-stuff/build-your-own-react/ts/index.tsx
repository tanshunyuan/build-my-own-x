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
type Fibre = {
  dom: Dom | null;
  // each element is a fibre
  parent?: Fibre
  child?: Fibre
  sibling?: Fibre
  props: {
    children: CreateElementResults[];
  };
} | null;
// Use unit of work to split workloads
let nextUnitOfWork: Fibre = null;

const createDom = (fiber): Dom => {
  const dom =
    fiber.type === "TEXT_ELEMENT"
      ? document.createTextNode("")
      : document.createElement(fiber.type);

  const filterChildrenProps = (key: string) => key !== "children";

  // Framework props should consists of the base HTMLElement props & further extend it
  // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement#instance_properties
  Object.keys(fiber.props)
    .filter(filterChildrenProps)
    .forEach((propName) => {
      dom[propName] = fiber.props[propName];
    });

  return dom;
};

const render = (element: CreateElementResults, container: Dom) => {
  // root fibre tree
  nextUnitOfWork = {
    dom: container,
    parent: null,
    props: {
      children: [element],
    },
  };
};

const workLoop = (deadline: IdleDeadline) => {
  let shouldYield = false;
  // while there's a unit of work & it should not yield
  while (nextUnitOfWork && !shouldYield) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
    shouldYield = deadline.timeRemaining() < 1;
  }
  requestIdleCallback(workLoop); // <-- recursive call?
};

// https://developer.mozilla.org/en-US/docs/Web/API/Window/requestIdleCallback
// It's called whenever the main thread/browser is idle
requestIdleCallback(workLoop);

// Processes the unit of work and selects the next one
const performUnitOfWork = (fiber: Fibre) => {
  // add elements to the DOM
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }

  if (fiber.parent) {
    fiber.parent.dom.appendChild(fiber.dom);
  }

  // create fibers for the element CHILDREN
  const elements = fiber.props.children;
  let index = 0;
  let prevSibling = null;

  while (index < elements.length) {
    const element = elements[index];
    // unit of work
    const newFiber = {
      type: element.type,
      props: element.props,
      parent: fiber,
      dom: null,
    };

    if (index === 0) {
      fiber.child = newFiber;
    } else {
      prevSibling.sibling = newFiber;
    }

    prevSibling = newFiber;
    index++;
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
const element = (
  <div id="foo">
    <a>bar</a>
    <b />
  </div>
);
const container = document.getElementById("root");
Didact.render(element, container);
