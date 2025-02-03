// this file contains examples or unoptimised code for reference

// REFERENCE: Usual React Code
// const element = (
//   <div id="foo">
//     <a>bar</a>
//     <b />
//   </div>
// )
// const container = document.getElementById('root')
// ReactDOM.render(element, container)

/** To handle the below JSX, we need to create our own `createElement` separate from `React.createElement` */
// const element = (
//   <div id="foo">
//     <a>bar</a>
//     <b />
//   </div>
// )
// const createElement = (
//   type: string,
//   props?: HTMLElement & CustomProps,
//   ...children: any[]
// ) => {
//   children = children.map((child) =>
//     typeof child === "object" ? child : createTextElement(child),
//   );
//   return {
//     type,
//     props: {
//       ...props,
//       children,
//     },
//   };
// };

/**
 * As the `render` function is recursively called, it won't stop rendering until the complete
 * element tree is proccessed, this can block the main thread from rendering other elements if
 * the current element is big
 */
// const render = (element: ElementReturnType, container: HTMLElement | Text) => {
//   const dom =
//     element.type === "TEXT_ELEMENT"
//       ? document.createTextNode("")
//       : document.createElement(element.type);

//   const filterChildrenProps = (key: string) => key !== "children";

//   // Framework props should consists of the base HTMLElement props & further extend it
//   // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement#instance_properties
//   Object.keys(element.props)
//     .filter(filterChildrenProps)
//     .forEach((propName) => {
//       dom[propName] = element.props[propName];
//     });
//   element.props.children.forEach((child) => {
//     render(child, dom); <-- fella is inefficient
//   });
//   container.appendChild(dom);
// };
