const initialState = {
  nextNoteId: 1,
  notes: {},
};

window.state = initialState;

const onAddNote = () => {
  const id = window.state.nextNoteId;
  window.state.notes[id] = {
    id,
    content: "",
  };
  window.state.nextNoteId++;
  renderApp();
};

const NoteApp = ({ notes }) => {
  return (
    <div>
      <ul className="note-list">
        {Object.keys(notes).map((id) => (
          // Obviously we should render something more interesting than the id.
          <li className="note-list-item" key={id}>
            {id}
          </li>
        ))}
      </ul>
      <button className="editor-button" onClick={onAddNote}>
        New Note
      </button>
    </div>
  );
};

const renderApp = () => {
  const rootNode = document.getElementById("root");
  const root = ReactDOM.createRoot(rootNode);
  root.render(<NoteApp notes={window.state.notes} />);
};

renderApp();
