type ElementType = string | Function | object
/**@todo figure out why this works */
type ElementProps = Partial<HTMLElement> & Record<string, any> | null | { children: ElementChildren[]}

type ElementNode = {
  type: ElementType
  props: ElementProps 
}

type ElementChildren = string | ElementNode

/**
 * @description createElement is used to transform JSX to valid JS
 * The transpiler will break the JSX into three parts
 * type - Indicates the type of the element, is it a string or a function
 * props - properties of the JSX
 * children 
 * @example
 * <div id="foo">
 *   <a>bar</a>
 *   <b />
 * </div>
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
  return {
    type,
    props: {
      ...props,
      children: children.map(child => typeof child === 'object' ? child : createTextElement(child))
    }
  }
}

/**
 * @description
 * as `type` can be string or function, we need to handle the string type
 * which is dom elements 
 */
const createTextElement = (text: string) => {
  return {
    type: 'TEXT_ELEMENT',
    props: {
      nodeValue: text,
      children: []
    }
  }

}