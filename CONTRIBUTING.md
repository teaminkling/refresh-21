# Contributing

## Getting Started

- [Ensure you have a GitHub account][join].
- Feel free to [open an issue][report] to report any bugs or make a change request.
  - Before you do this, try to look for similar issues that report the same thing.
    - If there are, don't respond `+1` but react to the post to indicate your support!

## The Basics

### For Content Editors

There's a good chance that you're reading this because you want to make a change to a submission post. Go to the page
you want to change and click `Suggest edits.` on the page to be taken to an editing screen:



### For Developers

> Maintainers may push directly to `main` for minor documentation fixes.

1. Fork the repository.
2. Branch from `main` in your fork.
3. Open pull requests (PRs) from your fork's new branch to our repository's `main` branch.
  a. A branch has exactly one corresponding issue and contributor.
4. The branch should be named `issue-#`, e.g., `issue-31`.

Note that any code must be in American English and any comments should be in Australian English. Errors will not be
rejected in PR but likely will be overwritten in later code changes.

## Issue Correspondence

An issue has:

- Exactly one assignee.
  - You should add a comment that you're working on something and you might be assigned to the issue related to it.
- Ideally one branch.
- A milestone.
  - Added by the maintainer after merging and before closing.

## Slightly More Advanced Rules

1. Nobody else will modify your branch.
  a. If you want to hand over the branch to somebody else, they must rebase your changes on their own branch. You
     will then either close your own branch, or it will be closed when stale.
2. If `main` is ahead of your branch, make yourself level with `main` by rebasing before submitting a pull request.
3. Once it is on `main`, that's the truth. No more rewriting history!
4. If anything goes stale, it may be closed at the maintainer's discretion.

## Quality Control

There are quality control standards.

- Run your code under as many code quality checks as possible.
- Make sure it is readable and well-documented.
- Make sure it adheres to language/framework-specific conventions.

[join]: https://github.com/join
[report]: /issues/new
[flow]: https://github.com/teaminkling/doc-flow
