const clJSON = (...items: any) => console.log(JSON.stringify(items, null, 2));
// reference React Code
// const element = (
//   <div id="foo">
//     <a>bar</a>
//     <b />
//   </div>
// )
// const container = document.getElementById('root')
// ReactDOM.render(element, container)

// To handle the below JSX, we need to create our own `createElement` separate from `React.createElement`
// const element = (
//   <div id="foo">
//     <a>bar</a>
//     <b />
//   </div>
// )

/**@todo figure out type for children */
// children can be either objects or string in createElement
// object = createElement( "div", { id: "foo" }, createElement("a", null, "bar",))
// string = createElement("a", null, "bar")
const createElement = (
  type: string,
  props?: Record<string, string | number>,
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

type ElementReturnType = ReturnType<typeof createElement>;

const createTextElement = (text: string) => {
  return {
    type: "TEXT_ELEMENT",
    props: {
      nodeValue: text,
      children: [],
    },
  };
};

const render = (element: ElementReturnType, container: HTMLElement | Text) => {
  const dom =
    element.type === "TEXT_ELEMENT"
      ? document.createTextNode("")
      : document.createElement(element.type);

  const filterChildrenProps = (key: string) => key !== "children";
  // Framework props should consists of the base HTMLElement props & further extend it
  // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement#instance_properties
  Object.keys(element.props)
    .filter(filterChildrenProps)
    .forEach((propName) => {
      dom[propName] = element.props[propName];
    });
  element.props.children.forEach((child) => {
    render(child, dom);
  });
  container.appendChild(dom);
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
