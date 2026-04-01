# Quick Spec: Make File Explorer Breadcrumb Scrollable

## Problem
Current breadcrumb bar has fixed width. When folder path is long, it overflows and hides the file tree view instead of scrolling.

## Solution
Wrap breadcrumb in horizontally-scrolling `Gtk.ScrolledWindow` so long paths scroll without hiding the tree.

## Changes Required

### File: `slate/ui/panels/file_explorer_tree.py`

1. **Modify `_build_breadcrumb()` method** (around line 107):
   - Return `Gtk.ScrolledWindow` instead of `Gtk.Box`
   - Wrap internal box in ScrolledWindow with horizontal scroll policy

2. **Modify `_update_breadcrumb()` method** (around line 117):
   - Get the inner box from ScrolledWindow: `scrolled.get_child()` instead of directly using `self._breadcrumb_box`

## Implementation Details

```python
def _build_breadcrumb(self) -> Gtk.ScrolledWindow:
    """Create scrollable breadcrumb bar at top of panel."""
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_hexpand(True)
    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
    scrolled.set_max_content_height(28)
    scrolled.set_min_content_height(28)
    
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    box.set_css_classes(["breadcrumb-bar"])
    box.set_hexpand(False)
    box.set_margin_start(8)
    box.set_margin_end(8)
    box.set_margin_top(4)
    box.set_margin_bottom(4)
    scrolled.set_child(box)
    
    self._breadcrumb_inner_box = box  # Store reference for _update_breadcrumb
    return scrolled
```

```python
def _update_breadcrumb(self, path: str) -> None:
    """Update breadcrumb bar to show current folder path."""
    # Use stored inner box reference
    inner_box = self._breadcrumb_inner_box
    child = inner_box.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        inner_box.remove(child)
        child = next_child
    # ... rest of method using inner_box instead of self._breadcrumb_box
```

## Test Command
```bash
cd /home/raziur/Projects/rnd/ai-agentic-coding/slate
python3 -m pytest tests/ -v --tb=short
```

Expected: All 291 tests pass.

## Spec Compatibility
- AC 7: "breadcrumb bar shows current folder path with clickable segments" - ✓ preserved
- UX spec "Breadcrumb path" content element - ✓ preserved