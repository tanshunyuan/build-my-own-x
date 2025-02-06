import { cl } from "../helper"

type ElementType = string
/**@todo figure out why this works */
type ElementProps = Partial<HTMLElement> & Record<string, any> | null | { children: ElementChildren[] }

export type ElementChildren = string | ElementNode

export type ElementNode = {
  type: ElementType
  props: ElementProps
}
/**
 * @description createElement is used to transform JSX to valid JS
 * The transpiler will break the JSX into three parts
 * type - Indicates the type of the element, is it a string or a function
 * props - properties of the JSX
 * children 
 * @example
 * JSX
 * const element = <div id="foo">
 *   <a>bar</a>
 *   <b />
 * </div>
 * Transpiler breaking JSX into three parts
 * const element = React.createElement(
 *   "div",
 *   { id: "foo" },
 *   React.createElement("a", null, "bar"),
 *   React.createElement("b")
 * )
 * 
 * @returns
 * {
 *   "type": "div",
 *   "props": {
 *     "id": "foo",
 *     "children": [
 *       {
 *         "type": "a",
 *         "props": {
 *           "children": [
 *             "bar"
 *           ]
 *         }
 *       },
 *       {
 *         "type": "b",
 *         "props": {
 *           "children": []
 *         }
 *       }
 *     ]
 *   }
 * }
 */
export const createElement = (type: ElementType, props?: ElementProps, ...children: ElementChildren[]) => {
  const results = {
    type,
    props: {
      ...props,
      children: children.map(child => typeof child === 'object' ? child : createTextElement(child))
    }
  }
  cl('createElement.results ==> ',JSON.stringify(results, null, 2))
  return results
}

/**
 * @description
 * as `type` can be string or function, we need to handle the string type
 * which is dom elements 
 */
const createTextElement = (text: string) => {
  const results = {
    type: 'TEXT_ELEMENT',
    props: {
      nodeValue: text,
      children: []
    }
  }

  cl('createTextElement.results ==> ',JSON.stringify(results, null, 2))
  return results
}