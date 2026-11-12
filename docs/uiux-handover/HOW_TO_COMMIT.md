# Commit this handover to GitHub

The design tool could only read the repository, so these files were exported for you to commit.

From your local clone of thewongphoto/SMA-indictor:

```sh
git fetch origin
git switch -c design/uiux-handover origin/main   # if it exists: design/uiux-handover-2
# copy the docs/ folder from this export into the repo root, so files land in docs/uiux-handover/
git add docs/uiux-handover
git commit -m "docs: add UI/UX design handover for Android and iPhone web"
git push -u origin design/uiux-handover
```

Then open:
- Branch: https://github.com/thewongphoto/SMA-indictor/tree/design/uiux-handover
- README: https://github.com/thewongphoto/SMA-indictor/blob/design/uiux-handover/docs/uiux-handover/README.md

Do not merge into main until the open decisions are settled.
