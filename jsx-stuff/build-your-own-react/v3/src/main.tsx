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
  const [toggle, setToggle] = Didact.useState(false)
  const [state, setState] = Didact.useState<number>(1);
  return (
    <div>
      <button onClick={() => {
        cl('button.onClick')
        setToggle(prev => !prev)
      }}>Toggle Count</button>
      {toggle ?
        <h1 onClick={() => {
          cl('h1.onClick')
          setState(c => c + 1)
        }}>
          Count: {state}
        </h1> : null
      }
    </div>
  );
}
const element = <Counter />;
const container = document.getElementById("root")!;
Didact.render(element, container);
