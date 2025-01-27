const createFakeApi = () => {
  let _id = 0;
  const createNote = () =>
    new Promise((resolve) =>
      setTimeout(() => {
        _id++;
        resolve({
          id: `${_id}`,
        });
      }, 1000)
    );
  return {
    createNote,
  };
};

const api = createFakeApi();

const initialState = {
  openNoteId: null,
  notes: {},
  isLoading: false,
};

// Reducer: must be P U R E, do not mutate state directly
// create a copy, update the copied state and return it
const CREATE_NOTE = "CREATE_NOTE";
const UPDATE_NOTE = "UPDATE_NOTE";
const OPEN_NOTE = "OPEN_NOTE";
const CLOSE_NOTE = "CLOSE_NOTE";

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case CREATE_NOTE: {
      if (!action.id) {
        return { ...state, isLoading: true };
      }
      const newNote = {
        id: action.id,
        content: "",
      };
      return {
        // unfurl current state
        ...state,
        // below will override the current state
        notes: {
          ...state.notes,
          [action.id]: newNote,
        },
        openNoteId: action.id,
        isLoading: false,
      };
    }
    case UPDATE_NOTE: {
      const { id, content } = action;
      const editedNote = {
        ...state.notes[id],
        content,
      };
      return {
        ...state,
        notes: {
          ...state.notes,
          [id]: editedNote,
        },
      };
    }
    case OPEN_NOTE: {
      return {
        ...state,
        openNoteId: action.id,
      };
    }
    case CLOSE_NOTE: {
      return {
        ...state,
        openNoteId: null,
      };
    }
    default:
      return state;
  }
};

const validateAction = (action) => {
  const isActionNotObject =
    !action || typeof action !== "object" || Array.isArray(action);
  if (isActionNotObject) throw new Error("Action must be an object!");
  if (!action.type) throw new Error("Action must have a type");
};

const createStore = (reducer, middleware) => {
  // in memory state
  let state = undefined;
  const subscribers = [];
  const coreDispatch = (action) => {
    validateAction(action);
    state = reducer(state, action);
    subscribers.forEach((handler) => handler());
  };
  const getState = () => state;
  const store = {
    dispatch: coreDispatch,
    getState,
    subscribe: (handler) => {
      subscribers.push(handler);
      // cleanup/unsubscribe function
      return () => {
        const index = subscribers.indexOf(handler);
        if (index > 0) {
          subscribers.splice(index, 1);
        }
      };
    },
  };
  // if there's a middleware, wrap the current store with it
  if (middleware) {
    const dispatch = (action) => store.dispatch(action);
    store.dispatch = middleware({
      dispatch,
      getState,
    })(coreDispatch);
  }
  coreDispatch({ type: "@@redux/INIT" });
  return store;
};

/**@question what's the next for? If it's gg to be undefined*/
const delayMiddleware = () => (next) => (action) => {
  console.log(`next ${JSON.stringify(next, null, 2)}`);
  console.log(`action ${JSON.stringify(action, null, 2)}`);
  setTimeout(() => {
    next(action);
  }, 1000);
};

const loggingMiddleware =
  ({ getState }) =>
  (next) =>
  (action) => {
    console.info("before", getState());
    console.info("action", action);
    const result = next(action);
    console.info("after", getState());
    return result;
  };

const thunkMiddleware =
  ({ dispatch, getState }) =>
  (next) =>
  (action) => {
    console.log(`thunk next: ${next}`)
    if (typeof action === "function") {
      return action(dispatch, getState);
    }
    return next(action);
  };

const applyMiddleware =
  (...middlewares) =>
  (store) => {
    if (middlewares.length === 0) {
      return (dispatch) => dispatch;
    }
    if (middlewares.length === 1) {
      return middlewares[0](store);
    }
    const boundMiddlewares = middlewares.map((middleware) => middleware(store));
    return boundMiddlewares.reduce((a, b) => (next) => a(b(next)));
  };

const store = createStore(
  reducer,
  applyMiddleware(thunkMiddleware, loggingMiddleware)
);

const NoteEditor = ({ note, onChangeNote, onCloseNote }) => (
  <div>
    <div>
      <textarea
        className="editor-content"
        autoFocus
        value={note.content}
        onChange={(event) => onChangeNote(note.id, event.target.value)}
        rows={10}
        cols={80}
      />
    </div>
    <button className="editor-button" onClick={onCloseNote}>
      Close
    </button>
  </div>
);

const NoteTitle = ({ note }) => {
  const title = note.content.split("\n")[0].replace(/^\s+|\s+$/g, "");
  if (title === "") {
    return <i>Untitled</i>;
  }
  return <span>{title}</span>;
};

const NoteLink = ({ note, onOpenNote }) => (
  <li className="note-list-item">
    <a href="#" onClick={() => onOpenNote(note.id)}>
      <NoteTitle note={note} />
    </a>
  </li>
);

const NoteList = ({ notes, onOpenNote }) => (
  <ul className="note-list">
    {Object.keys(notes).map((id) => (
      <NoteLink key={id} note={notes[id]} onOpenNote={onOpenNote} />
    ))}
  </ul>
);
const NoteApp = ({
  notes,
  openNoteId,
  onAddNote,
  onChangeNote,
  onOpenNote,
  onCloseNote,
}) => (
  <div>
    {openNoteId ? (
      <NoteEditor
        note={notes[openNoteId]}
        onChangeNote={onChangeNote}
        onCloseNote={onCloseNote}
      />
    ) : (
      <div>
        <NoteList notes={notes} onOpenNote={onOpenNote} />
        <button className="editor-button" onClick={onAddNote}>
          New Note
        </button>
      </div>
    )}
  </div>
);

// change to functional
// class NoteAppContainer extends React.Component {
//   constructor(props) {
//     super();
//     this.state = props.store.getState();
//     this.onAddNote = this.onAddNote.bind(this);
//     this.onChangeNote = this.onChangeNote.bind(this);
//     this.onOpenNote = this.onOpenNote.bind(this);
//     this.onCloseNote = this.onCloseNote.bind(this);
//   }
//   componentWillMount() {
//     this.unsubscribe = this.props.store.subscribe(() =>
//       // setState here is exposed when extending React.Component
//       this.setState(this.props.store.getState())
//     );
//   }
//   componentWillUnmount() {
//     this.unsubscribe();
//   }
//   onAddNote() {
//     this.props.store.dispatch({
//       type: CREATE_NOTE,
//     });
//   }
//   onChangeNote(id, content) {
//     this.props.store.dispatch({
//       type: UPDATE_NOTE,
//       id,
//       content,
//     });
//   }
//   onOpenNote(id) {
//     this.props.store.dispatch({
//       type: OPEN_NOTE,
//       id,
//     });
//   }
//   onCloseNote() {
//     this.props.store.dispatch({
//       type: CLOSE_NOTE,
//     });
//   }
//   render() {
//     return (
//       <NoteApp
//         {...this.state}
//         onAddNote={this.onAddNote}
//         onChangeNote={this.onChangeNote}
//         onOpenNote={this.onOpenNote}
//         onCloseNote={this.onCloseNote}
//       />
//     );
//   }
// }

class Provider extends React.Component {
  getChildContext() {
    return {
      store: this.props.store,
    };
  }
  render() {
    return this.props.children;
  }
}

Provider.childContextTypes = {
  store: PropTypes.object,
};

const connect =
  (mapStateToProps = () => ({}), mapDispatchToProps = () => ({})) =>
  (Component) => {
    class Connected extends React.Component {
      onStoreOrPropsChange(props) {
        // custom FN
        const { store } = this.context;
        const state = store.getState();
        const stateProps = mapStateToProps(state, props);
        const dispatchProps = mapDispatchToProps(store.dispatch, props);
        this.setState({
          ...stateProps,
          ...dispatchProps,
        });
      }
      componentWillMount() {
        const { store } = this.context;
        this.onStoreOrPropsChange(this.props);
        this.unsubscribe = store.subscribe(() =>
          this.onStoreOrPropsChange(this.props)
        );
      }
      componentWillReceiveProps(nextProps) {
        this.onStoreOrPropsChange(nextProps);
      }
      componentWillUnmount() {
        this.unsubscribe();
      }
      render() {
        return <Component {...this.props} {...this.state} />;
      }
    }

    Connected.contextTypes = {
      store: PropTypes.object,
    };

    return Connected;
  };

const mapStateToProps = (state) => ({
  notes: state.notes,
  openNoteId: state.openNoteId,
});

const mapDispatchToProps = (dispatch) => ({
  onAddNote: () =>
    dispatch((dispatch) => {
      dispatch({
        type: CREATE_NOTE,
      });
      api.createNote().then(({ id }) => {
        dispatch({
          type: CREATE_NOTE,
          id,
        });
      });
    }),
  onChangeNote: (id, content) =>
    dispatch({
      type: UPDATE_NOTE,
      id,
      content
    }),
  onOpenNote: (id) =>
    dispatch({
      type: OPEN_NOTE,
      id,
    }),
  onCloseNote: () =>
    dispatch({
      type: CLOSE_NOTE,
    }),
});

const NoteAppContainer = connect(mapStateToProps, mapDispatchToProps)(NoteApp);

const rootNode = document.getElementById("root");
const root = ReactDOM.createRoot(rootNode);
root.render(
  <Provider store={store}>
    <NoteAppContainer />
  </Provider>
);
