import { cl } from "../helper"
import { ElementChildren, ElementNode } from "./elements"
import { updateDom } from "./reconciliation"

type Container = HTMLElement | Text

/**
 * @description This recursion method is too naive,
 * it'll hog / block the main thread from rendering 
 * if the incoming element is too big. 
 * 
 * To handle large elements, we need to break the elements
 * into smaller unit of work. See 'reconciliation.ts'
 */
// export const render = (element: ElementNode, container: Container) => {
//   // converting virtualDOM type to DOM
//   const dom = element.type === 'TEXT_ELEMENT' ?
//     document.createTextNode('') :
//     document.createElement(element.type)

//   const isProperty = (key: string) => key !== 'children'
//   if (element.props) {
//     Object.keys(element.props)
//       .filter(isProperty)
//       .forEach(name => {
//         dom[name] = element.props[name]
//       })
//   }

//   if (element.props && element.props.children) {
//     const children = element.props.children as ElementChildren[]
//     children.forEach(child => {
//       render(child, dom)
//     })
//   }

//   container.appendChild(dom)
// }

/**@see {@link https://github.dev/facebook/react/blob/ff6283340a10bb72ad0fb16ca027606a9ea1e67c/packages/react-reconciler/src/ReactInternalTypes.js} */
type Fiber = {
  dom: any
  effectTag: 'PLACEMENT' | 'UPDATE' | 'DELETE'
  type: any
  elementType: any

  /**
   * @description
   * This is a pooled version of a Fiber. Every fiber that gets updated will
   * eventually have a pair. 
   * 
   * This property is a link to the old fiber, the fiber that we committed to the DOM in the previous commit phase.
   */
  alternate: Fiber | null

  // Singly Linked List Tree structure
  child: Fiber | null
  sibling: Fiber | null
}

export const render = (element: ElementNode, container: Container) => {
  window.wipRoot = {
    dom: container,
    props: {
      children: [element]
    },
    alternate: window.currentRoot
  }
  window.deletions = []
  window.nextUnitOfWork = window.wipRoot

  cl(`render ==> `, {
    wipRoot: window.wipRoot,
    currentRoot: window.currentRoot,
    deletions: window.deletions,
    nextUnitOfWork: window.nextUnitOfWork
  })
}

export const createDom = (fiber) => {
  // converting virtualDOM type to DOM
  const dom = fiber.type === 'TEXT_ELEMENT' ?
    document.createTextNode('') :
    document.createElement(fiber.type)

  updateDom(dom, {}, fiber.props)
  return dom
}