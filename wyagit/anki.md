# Things to add into anki:

- Where & how does Git store data? Git stores data in `.git` of your repo, and it's a content-addressable store so key-value pair; object database <TODO>
- What is a git object? Git objects are binary file that represent files within a repository. These objects usually lives in '.git/object' and it's identified by a SHA-1 hash which is derived from the contents of the file. Thus git doesn't actually store files
- What happens when a file in git is modified? Instead of updating a file, a new file is created in a different location
- Why is git considered a value-value store? As the key isn't separately derived from elsewhere instead it's computed from data of a file
- How does git compute the storage path of an object? By calculating the SHA-1 hash of the file contents
- How is the storage path of an object presented? 
    - The hash is rendered as a lowercase hexadecimal string to be human readable (e.g. 7a10fcfc5e36ef9669c86367c822c88fbba5ca6c)
    - It's split into two parts: First two char which represents the directory name. The rest as the binary file name
    - E.g. 7a10fcfc5e36ef9669c86367c822c88fbba5ca6c -> .git/objects/7a/10fcfc5e36ef9669c86367c822c88fbba5ca6c
- What are the different types of objects in Git? Files, commit, tree, tags. Almost everythin is stored as an object
- What is a commit? A snapshot of the working tree
- What is a blob? It's a binary file that contains user data, without any metadata
- What is a tree? It's a directory listing of blobs and tree.
- What are some common functions that the object share? The same storage/retrieval mechanism and general header format
- What's the header format of a object? <BLANK>
- What's the decompression/compression protocol used on git binary file? zlib
- What components is extracted out of the decompressed data? Two header components: the object type and its size
- What's a GitBlob? The content of every file the user put in git
- How are the contents of a commit object formatted?
    - On a line, if the first space is surrounded by two characters. The left will be the key and the anything to the right is the value before '\n'. Key-value pair
    - If there are multi lines a space at the start is required. And this leading space needs to be removed. The terminal point of this is when the parser doesn't detect a leading space anymore on a new line
- Does a python HashMap preserve order insertion? Yes.
- What are the two rules pertaining to a object identity in Git? 
    - The same name will always refer to the same object
    - The same object will always be referred by the same name. Which means there can't be two equivalent object under different name
- What's the difference between a space and 0x00? space is the delimeter between a key-value pair, whereas 0x00 is a null byte that separates header from content
- How is a tree object content formatted? [mode] space [path] 0x00 [sha-1]
- What does a tree object represent? A folder/directory
- What is a ref? It's a human-readable name that represent a object hash or other refs
- What are the two type of refs in the contents of `.git/refs`? Indirect Reference & direct reference
- What is a indirect reference? A ref referencing another ref. E.g. ref:path/to/other/ref
- What is a direct reference? A ref with a SHA-1 object
- What is a tag? It's a ref.
- What are the two types of tag? Lightweight tag (contains just a hash) & Tag objects (same format as a commit obj)
- Where does tag live in .git? `.git/refs/tags`
- Where does branches live in .git? `.git/refs/heads`
- Where does the current/active branch live in `.git`? `.git/HEAD`, this is a ref file containing- a indirect reference aka path/to/other/ref
- How does a short hash look like? 5bd254 instead of 5bd254aa973646fa16f66d702a5826ea14a3eb45
- What is the two step process when performing a commit? A git add / git rm followed by a git commit -m <MESSAGE>
- What's the name of the stage between the last and next commit. And what's used to represent this stage?
    - The stage is called: staging area and a binary file located at .git/index is used to represent the changes in this stage
- What are the types of gitignore file and where does it live?
    - absolute: lives in '~/.config/git/ignore' or '.git/info/exclude'; global ignore file
    - scoped: lives in `<REPO>/.gitignore`
- What's the heirachy of ignore? Scope first then global
- Does a blob contain metadata? No
- What is a git repository? It's a storage system for tracking file / folder changes overtime?
- What makes a git repository? 
    - A working tree: the directory which is being tracked
    - A `.git` folder: a child directory of the working tree which contains all the information of the working tree represented in different types of object
- What is `.git/objects/`?  It's the object store, it contains different object such as trees, commit and blobs
- What is `.git/refs/`? It's the reference store which contains human-readable references to hashes. It contains two directory: `heads` and `tags`
- What is `.git/HEAD`? A reference/pointer to the current HEAD

# Ahas
* When git tracks a file within a repo, it's not actually track a file. Instead they're file objects, and the names are identified by the SHA-1 hash of the file contents
* Blob doesn't contain metadata, a file does

# Questions
- Aren't tags and commit also binary objects? So why is tree object so special?
- So what exactly is tree objects?
- Object folder contains tree, commits and tags?
- Can we say that all the object in git are identified by hashes
- All trees, commits and blob are binary files. The content might differ but they're all identified by SHA-1 hash

