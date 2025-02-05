import * as Didact from './didact'
// const Didact = {
//   createElement,
//   render,
//   useState,
// };

// under the hood
// const element = Didact.createElement(
//   "div",
//   { id: "foo" },
//   Didact.createElement("a", null, "bar"),
//   Didact.createElement("b")
// )

// official
// /**@jsx Didact.createElement*/
// function Counter() {
//   const [state, setState] = Didact.useState(1);
//   return (
//     <h1 onClick={() => setState(c => c + 1)} >
//       Count: {state}
//     </h1>
//   );
// }
// const element = <Counter />;
// const container = document.getElementById("root");
// Didact.render(element, container);

const container = document.getElementById("root")!;

// const element = <div id="foo">
//   <a>bar</a>
//   <b />
// </div>
// under the hood, the JSX is handled by createElement
/**@jsx Didact.createElement*/
const element = <div id="foo">
  <a>bar</a>
  <b />
</div>

console.log(JSON.stringify(element, null, 2))

// createRoot(container).render(element)