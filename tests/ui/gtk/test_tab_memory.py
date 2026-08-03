"""Memory-leak probes for tab open/close cycles.

Run with: xvfb-run -a pytest tests/ui/gtk/test_tab_memory.py -v -s
"""

import gc

import pytest
from gi.repository import GtkSource

from slate.ui.editor.editor_view import EditorView


def _vmrss_kb() -> int:
    """Return current resident set size in KB from /proc/self/status."""
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return 0


def _count_instances(cls) -> int:
    """Count live instances tracked by the Python GC (generator, no refs)."""
    return sum(1 for o in gc.get_objects() if isinstance(o, cls))


def _write_sample_files(directory, count, lines):
    """Create count Python source files each ~lines lines long."""
    paths = []
    for i in range(count):
        p = directory / f"sample_{i:03d}.py"
        body = "\n".join(f"def function_{i}_{j}(x): return x + {j}  # fill" for j in range(lines))
        p.write_text(body + "\n")
        paths.append(str(p))
    return paths


@pytest.mark.timeout(120)
@pytest.mark.gtk
def test_tab_open_close_cycles_do_not_leak_editor_views(
    gtk_app_activated, pump_main_loop, tmp_path
):
    """Open and close many tabs repeatedly; assert no instance accumulation."""
    window = gtk_app_activated
    paths = _write_sample_files(tmp_path, 20, 120)

    def snapshot(label):
        gc.collect()
        data = {
            "rss_kb": _vmrss_kb(),
            "views": _count_instances(EditorView),
            "buffers": _count_instances(GtkSource.Buffer),
        }
        print(f"  [{label}] rss={data['rss_kb']}KB views={data['views']} buffers={data['buffers']}")
        return data

    # Warm up singletons (language manager, css provider, GObject types).
    for path in paths[:3]:
        window._tab_manager.open_tab(path)
    for path in paths[:3]:
        window._close_tab(path, snapshot=False)
    pump_main_loop(0.2)

    baseline = snapshot("baseline")

    for cycle in range(3):
        for path in paths:
            window._tab_manager.open_tab(path)
        pump_main_loop(0.1)
        snapshot(f"cycle{cycle} opened")

        for path in paths:
            window._close_tab(path, snapshot=False)
        pump_main_loop(0.2)
        snapshot(f"cycle{cycle} closed")

    final = snapshot("final")

    delta_views = final["views"] - baseline["views"]
    delta_buffers = final["buffers"] - baseline["buffers"]
    print(f"  DELTAS after 3 cycles: views={delta_views} buffers={delta_buffers}")
    assert delta_views <= 2, f"{delta_views} EditorView instances leaked"
    assert delta_buffers <= 2, f"{delta_buffers} GtkSource.Buffer instances leaked"
