# Things to add into anki:
 1. How are git files named? The name of a git file is mathematically derived from it's content
 2. you don’t modify a file in git, you create a new file in a different location
 3. Why is git considered a value-value store? Because the filename (key) is computed from data
 5. How is the path where git stores a object computed? By calculating the SHA-1 hash of its content
 6. How is the path name represented? The hash is lowercase and split into two parts: the first two characters and the rest.
       First part is the directory name, rest as filename.
       E.g. Hash = e673d1b7eaa0aa01b5bc2442d570a765bdaae751
            Hash Expanded = First Two Char + / + Remaining Hash character = .git/objects/e6/73d1b7eaa0aa01b5bc2442d570a765bdaae751
 7. Despite the different types of object in Git, what are some common function it shares? The same storage/retrieval mechanism
       and the same general header format
 8. What are the different type of objects in git? Files, commit, tree, tags. Almost everything in git is stored as an object
 9. What compression format is used for git files? zlib
 10. What is extracted out of the decompressed data?  we extract the two header components: the object type and its size
 11. What is a GitBlob? The content of every file the user put in git
 12. How is a commit object formatted?
       - On a line, if the first space is surrounded by two characters. The left will be the key and the anything to the right is the value before '\n'
       - If there are multi lines a space at the start is required. And this leading space needs to be removed. The terminal point of this is when the parser
         doesn't detect a leading space anymore on a new line
 13. Does a python HashMap preserve order insertion? Yes.
 14. What are the two rules pertaining to object identity in Git?
       - The same name will always refer to the same object
       - The same object will always be reffered by the same name. Which means there can't be two equivalent object under different name
 15. What's the difference between a space and 0x00? space is the delimeter between a key-value pair, whereas 0x00 is a null byte that separates header from content
 16. How is a tree object formatted? [mode] space [path] 0x00 [sha-1]
 17. What does a tree object represent? A folder
 18. What is a indirect reference? A ref referencing another ref. E.g. ref:path/to/other/ref
 19. What is a direct reference? A ref with a SHA-1 object
 20. What is a ref? It's a human-readable name that represent a object hash or other refs
 21. What is a tag? It's a ref.
 22. What are the two types of tag? Lightweight tag & Tag objects (same format as a commit obj)
 23. What is a branch? It's a ref to a commit (hash)
 24. Where does tag live in .git? `.git/refs/tags`
 25. Where does branches live in .git? `.git/refs/heads`
 26. Where does the current/active branch live in .git? `.git/HEAD`, this is a ref file containing
       a indirect reference aka path/to/other/ref
 27. How does a short hash look like? 5bd254 instead of 5bd254aa973646fa16f66d702a5826ea14a3eb45
 28. What is the two step process when performing a commit? A git add / git rm followed by a git commit -m <MESSAGE>
 29. What's the name of the intermediate stage between the last and next commit. And what's used to represent this stage?
       The stage is called: staging area and a binary file located at .git/index is used to represent the changes in this stage
 30. What are the types of gitignore file and where does it live?
   absolute - lives in '~/.config/git/ignore' or '.git/info/exclude'; global ignore file
   scoped - lives in `<REPO>/.gitignore`
 31. What's the heirachy of ignore? Scope first then global