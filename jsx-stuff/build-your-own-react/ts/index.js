var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var clJSON = function () {
    var items = [];
    for (var _i = 0; _i < arguments.length; _i++) {
        items[_i] = arguments[_i];
    }
    return console.log(JSON.stringify(items, null, 2));
};
// reference React Code
// const element = (
//   <div id="foo">
//     <a>bar</a>
//     <b />
//   </div>
// )
// const container = document.getElementById('root')
// ReactDOM.render(element, container)
// To handle the below JSX, we need to create our own `createElement` separate from `React.createElement`
// const element = (
//   <div id="foo">
//     <a>bar</a>
//     <b />
//   </div>
// )
/**@todo figure out type for children */
// children can be either objects or string in createElement
// object = createElement( "div", { id: "foo" }, createElement("a", null, "bar",))
// string = createElement("a", null, "bar")
var createElement = function (type, props) {
    var children = [];
    for (var _i = 2; _i < arguments.length; _i++) {
        children[_i - 2] = arguments[_i];
    }
    children = children.map(function (child) {
        return typeof child === "object" ? child : createTextElement(child);
    });
    return {
        type: type,
        props: __assign(__assign({}, props), { children: children }),
    };
};
var createTextElement = function (text) {
    return {
        type: "TEXT_ELEMENT",
        props: {
            nodeValue: text,
            children: [],
        },
    };
};
var render = function (element, container) {
    var dom = element.type === "TEXT_ELEMENT"
        ? document.createTextNode("")
        : document.createElement(element.type);
    var filterChildrenProps = function (key) { return key !== "children"; };
    // Framework props should consists of the base HTMLElement props & further extend it
    // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement#instance_properties
    Object.keys(element.props)
        .filter(filterChildrenProps)
        .forEach(function (propName) {
        dom[propName] = element.props[propName];
    });
    element.props.children.forEach(function (child) {
        render(child, dom);
    });
    container.appendChild(dom);
};
var Didact = {
    createElement: createElement,
    render: render,
};
// under the hood
// const element = Didact.createElement(
//   "div",
//   { id: "foo" },
//   Didact.createElement("a", null, "bar"),
//   Didact.createElement("b")
// )
// official
/**@jsx Didact.createElement*/
var element = (<div id="foo">
    <a>bar</a>
    <b />
  </div>);
var container = document.getElementById("root");
Didact.render(element, container);
