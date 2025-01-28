/**
 * @description return result of React.createElement.
 * Given <h1 title="foo">Hello</h1>
 */
const element = {
  type: "h1",
  props: {
    title: 'foo',
    children: 'Hello'
  }
}

const root = document.getElementById('root');

const node = document.createElement(element.type)
node['title'] = element.props.title

const text = document.createTextNode('')
text['nodeValue'] = element.props.children

node.appendChild(text)
root?.appendChild(node)
