import * as Didact from './didact'
import { cl } from './helper'

window.nextUnitOfWork = null
window.wipRoot = null
window.currentRoot = null
window.deletions = null
window.gWipFiber = null
window.hookIndex = null



/** @jsx Didact.createElement */
function Counter() {
  const [state, setState] = Didact.useState(1);
  return (
    <h1 onClick={() => {
      cl('h1.onClick')
      setState(c => c + 1)
    }} style="user-select: none">
      Count: {state}
    </h1>
  );
}
const element = <Counter />;
const container = document.getElementById("root");
Didact.render(element, container);
