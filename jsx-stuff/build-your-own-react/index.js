// https://pomb.us/build-your-own-react/

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
      children: children.map((item) =>
        typeof item === "object" ? item : createTextElement(item)
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
const render = (element, container) => {
  const dom =
    element.type == "TEXT_ELEMENT"
      ? document.createTextNode("")
      : document.createElement(element.type);

  const propsKey = Object.keys(element.props)
  propsKey.forEach(key => {
    if(key !== 'children') {
      dom[key] = element.props[key]
    }
  })

  element.props.children.forEach((child) => render(child, dom));
  container.appendChild(dom);
};

const Didact = {
  createElement,
  render,
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
const element = (
  <div style="background: salmon">
    <h1>Hello World</h1>
    <h2 style="text-align:right">from Didact</h2>
  </div>
);
const container = document.getElementById("root");
Didact.render(element, container);