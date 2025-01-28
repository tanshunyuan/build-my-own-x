/**
 * @description return result of React.createElement.
 * Given <h1 title="foo">Hello</h1>
 */
var element = {
    type: "h1",
    props: {
        title: 'foo',
        children: 'Hello'
    }
};
var root = document.getElementById('root');
var node = document.createElement(element.type);
node['title'] = element.props.title;
var text = document.createTextNode('');
text['nodeValue'] = element.props.children;
node.appendChild(text);
root === null || root === void 0 ? void 0 : root.appendChild(node);
