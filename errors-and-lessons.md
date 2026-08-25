# Errors & Lessons Learned

> A living document of the conceptual and algorithmic mistakes made while building this project — and what was learned from each one.

---

## 1. The Self-Retrieval Bug

### What Happened
When the RAG system scanned a file, it searched the index for "related code from elsewhere in the repository" to give the AI context. Instead of finding code from *other* files, it retrieved chunks from the **same file being scanned**. The AI ended up receiving the same file twice — once as the thing it was reviewing, and once as "related context".

### Why It Happened
The index contains every file in the repository. When a file's own content is used as the search query, naturally its own chunks come back as the most similar results — because nothing is more similar to a file than itself.

### What Was Learned
Any retrieval system needs an **exclusion mechanism** — a way to say "find me related content, but not from the file I'm currently looking at". Without it, the retrieved context is circular and useless.

### How It Was Fixed
Added an `exclude_file` parameter to `retrieve_related()` that filters out any chunk whose file path matches the file currently being scanned.

---

## 2. Path Comparison Case Mismatch

### What Happened
The `exclude_file` filter was written and in place, but it wasn't working. The self-retrieval bug persisted even after the fix was added. Chunks from the file being scanned were still coming through.

### Why It Happened
The file path was being stored in ChromaDB in one format (e.g. `Seeded_repo\buggy.py`) and compared against a path in a slightly different format (e.g. `seeded_repo\buggy.py`). To a human these are the same address. To a computer doing a plain text comparison, they are two completely different strings — so the filter never matched and never excluded anything.

### What Was Learned
File path comparisons cannot be done as raw string equality checks. Two paths can point to the exact same file on disk but look different as strings due to capitalisation, relative vs absolute format, or different separators. Always normalize paths to a single consistent format before comparing them.

### How It Was Fixed
Both the stored path (at index time) and the incoming path (at query time) are now converted to their full resolved absolute format before the comparison is made. Now both sides always look identical.

---

## 3. Prompt Language Triggering Safety Filters

### What Happened
The AI model flat out refused to review `buggy.py` and responded with something like *"Sorry, I cannot fulfill your request to analyze code for vulnerabilities"*. The scan ran, the file was read, but no useful output came back.

### Why It Happened
The system prompt used heavy security-auditor language — words like "security focused code auditor", "injection", "unsafe deserialization", "hardcoded secrets", "reachable and exploitable". Combined with a file that was a concentrated list of intentional vulnerabilities, the model's safety filter interpreted the request as someone trying to learn how to exploit code rather than review it.

### What Was Learned
The *framing* of a prompt matters as much as the *intent* behind it. A model's safety filter does not understand your intent — it pattern matches on language. Security-heavy terminology in a prompt, combined with suspicious-looking code, will trigger refusals even when the use case is completely legitimate. Neutral, professional language ("senior software engineer doing a code review") gets the same job done without triggering filters.

### How It Was Fixed
Rewrote both system prompts to use neutral code review language. Replaced "security vulnerabilities" with "risky patterns", removed explicit exploit terminology, and reframed the persona from "security auditor" to "senior software engineer".

---

## 4. No Upstream Branch on First Push

### What Happened
Running `git push` on a new branch returned an error saying the branch had no upstream and the push was rejected.

### Why It Happened
The branch `feature/test-pr` was created and worked on locally but had never been pushed to GitHub before. Git didn't know where to send it because no remote tracking branch existed yet.

### What Was Learned
A local branch and a remote branch are two separate things. The first time you push a new branch, you have to explicitly tell Git where it should live on the remote with `--set-upstream origin <branch-name>`. After that first push, future `git push` commands on that branch work without any extra flags.

### How It Was Fixed
```bash
git push --set-upstream origin feature/test-pr
```
