"""Source Control panel widget — displays git status with badges and branch dropdown."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gtk, Pango  # noqa: E402

from slate.core.events import FolderOpenedEvent, GitStatusChangedEvent  # noqa: E402
from slate.core.models import BranchInfo  # noqa: E402

if TYPE_CHECKING:
    from slate.core.event_bus import EventBus
    from slate.core.plugin_api import HostUIBridge
    from slate.services.git_service import GitService

logger = logging.getLogger(__name__)


class FileStatusItem(GObject.Object):
    """Wrapper for file status data used by Gtk.ListView."""

    def __init__(
        self,
        path: str,
        status: str,
        display_path: str | None = None,
    ) -> None:
        super().__init__()
        self.path = path
        self.status = status
        self.display_path = display_path or path


class SourceControlPanel(Gtk.Box):
    """Panel widget for displaying git status with badges and branch dropdown."""

    def __init__(
        self,
        git_service: GitService | None = None,
        event_bus: EventBus | None = None,
        host_bridge: HostUIBridge | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._git_service = git_service
        self._event_bus = event_bus
        self._host_bridge = host_bridge
        self._current_path: str | None = None
        self._current_branch: str | None = None
        self._status_items: list[FileStatusItem] = []
        self._branches: list[BranchInfo] = []

        # Build UI
        self._header_box = self._build_header()
        self.append(self._header_box)

        self._error_label = Gtk.Label()
        self._error_label.set_css_classes(["error-label"])
        self._error_label.set_xalign(0)
        self._error_label.set_hexpand(True)
        self._error_label.set_halign(Gtk.Align.FILL)
        self._error_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._error_label.set_single_line_mode(True)
        self._error_label.set_visible(False)
        self._error_label.set_margin_start(8)
        self._error_label.set_margin_end(8)
        self._error_label.set_margin_bottom(4)
        self.append(self._error_label)

        # Status list
        self._status_list = Gtk.ListView()
        self._status_list.set_hexpand(True)
        self._status_list.set_vexpand(True)

        # Create list model
        self._status_store = Gio.ListStore.new(FileStatusItem)
        self._selection_model = Gtk.SingleSelection.new(self._status_store)
        self._status_list.set_model(self._selection_model)
        self._status_list.set_factory(self._create_factory())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self._status_list)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_margin_start(8)
        scrolled.set_margin_end(8)
        scrolled.set_margin_top(4)
        scrolled.set_margin_bottom(8)
        self.append(scrolled)

        # Connect events
        if self._event_bus:
            self._event_bus.subscribe(GitStatusChangedEvent, self._on_git_status_changed)
            self._event_bus.subscribe(FolderOpenedEvent, self._on_folder_opened)
            self.connect("unrealize", self._on_unrealize)

    def _on_unrealize(self, widget: Gtk.Widget) -> None:
        """Clean up EventBus subscription when widget is destroyed."""
        if self._event_bus:
            self._event_bus.unsubscribe(GitStatusChangedEvent, self._on_git_status_changed)
            self._event_bus.unsubscribe(FolderOpenedEvent, self._on_folder_opened)

    def _on_folder_opened(self, event: FolderOpenedEvent) -> None:
        """Handle folder opened event - update current path and refresh git status."""
        self.set_current_path(event.path)

    def _build_header(self) -> Gtk.Box:
        """Create header with branch dropdown and menu button."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_box.set_hexpand(True)
        header_box.set_margin_start(8)
        header_box.set_margin_end(8)
        header_box.set_margin_top(4)
        header_box.set_margin_bottom(4)

        # Branch dropdown row
        branch_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        branch_row.set_hexpand(True)

        branch_label = Gtk.Label(label="Branch:")
        branch_label.set_xalign(0)

        self._branch_dropdown = Gtk.ComboBoxText()
        self._branch_dropdown.set_hexpand(True)
        self._branch_dropdown.connect("changed", self._on_branch_changed)

        branch_row.append(branch_label)
        branch_row.append(self._branch_dropdown)

        # Menu button row (right-aligned)
        menu_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        menu_row.set_hexpand(True)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        self._menu_button = Gtk.MenuButton()
        self._menu_button.set_icon_name("view-more-symbolic")
        self._menu_button.set_tooltip_text("Source control options")
        self._menu_button.set_css_classes(["flat"])

        popover = Gtk.Popover()
        self._menu_button.set_popover(popover)

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        popover_box.set_margin_start(12)
        popover_box.set_margin_end(12)
        popover_box.set_margin_top(8)
        popover_box.set_margin_bottom(8)

        refresh_button = Gtk.Button(label="Refresh Status")
        refresh_button.connect("clicked", self._on_refresh_clicked)
        popover_box.append(refresh_button)

        popover.set_child(popover_box)

        menu_row.append(spacer)
        menu_row.append(self._menu_button)

        header_box.append(branch_row)
        header_box.append(menu_row)

        return header_box

    def _create_factory(self) -> Gtk.SignalListItemFactory:
        """Create factory that binds status items to row widgets."""
        factory = Gtk.SignalListItemFactory()

        def setup(_factory: Any, list_item: Any) -> None:
            box = Gtk.Box(spacing=8)
            box.set_hexpand(True)
            box.set_margin_start(4)
            box.set_margin_end(4)
            box.set_margin_top(2)
            box.set_margin_bottom(2)

            status_badge = Gtk.Label()
            status_badge.set_width_chars(3)

            path_label = Gtk.Label(xalign=0)
            path_label.set_hexpand(True)
            path_label.set_ellipsize(Pango.EllipsizeMode.START)

            box.append(status_badge)
            box.append(path_label)
            list_item.set_child(box)

            list_item._slate_widgets = {
                "box": box,
                "status_badge": status_badge,
                "path_label": path_label,
            }

        def bind(_factory: Any, list_item: Any) -> None:
            widgets = getattr(list_item, "_slate_widgets", None)
            if not widgets:
                return

            # With Gio.ListStore + SignalListItemFactory, get_item() returns the model item directly
            item = list_item.get_item()
            if not isinstance(item, FileStatusItem):
                return

            # Set status badge with color
            color = self._get_status_color(item.status)
            widgets["status_badge"].set_markup(f'<span color="{color}">{item.status}</span>')

            # Set path label
            widgets["path_label"].set_text(item.display_path or item.path)

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        return factory

    def _get_status_color(self, status_code: str) -> str:
        """Get color for status badge."""
        color_map = {
            "M": "#f6c177",  # yellow (modified)
            "A": "#a0e57c",  # green (added)
            "D": "#e06c75",  # red (deleted)
            "R": "#61afef",  # blue (renamed)
            "C": "#c678dd",  # purple (copied)
            "U": "#e06c75",  # red (unmerged/conflict)
            "?": "#cccccc",  # gray for untracked
        }
        return color_map.get(status_code, "#cccccc")

    def _on_branch_changed(self, dropdown: Gtk.ComboBoxText) -> None:
        """Handle branch dropdown selection."""
        active_index = dropdown.get_active()
        if active_index < 0:
            return

        branch_name = dropdown.get_active_text()
        if not branch_name:
            return

        # Strip " (current)" suffix if present
        if branch_name.endswith(" (current)"):
            branch_name = branch_name[:-10]

        # Validate branch name exists in branches list
        if not any(b.name == branch_name for b in self._branches):
            logger.warning(f"Invalid branch name selected: {branch_name}")
            self._update_branch_dropdown()
            return

        # Check if working tree is dirty
        if self._is_working_tree_dirty() and not self._show_dirty_warning_dialog():
            # Reset dropdown to previous selection
            self._update_branch_dropdown()
            return

        # Switch branch
        if self._git_service and self._current_path:
            try:
                self._git_service.switch_branch(self._current_path, branch_name)
                self._current_branch = branch_name
                self.refresh_status()
            except Exception as e:
                logger.error(f"Failed to switch branch: {e}")
                self._show_error(f"Failed to switch branch: {e}")

    def _on_refresh_clicked(self, button: Gtk.Button) -> None:
        """Handle refresh button click."""
        self.refresh_status()

    def _on_git_status_changed(self, event: GitStatusChangedEvent) -> None:
        """Handle git status changed event."""
        if self._current_path and event.path == self._current_path:
            self.refresh_status()

    def _is_working_tree_dirty(self) -> bool:
        """Check if working tree has uncommitted changes."""
        if not self._git_service or not self._current_path:
            return False

        try:
            # Get current status to check if there are changes
            status = self._git_service.get_status(self._current_path)
            return len(status) > 0
        except Exception:
            return False

    def _show_dirty_warning_dialog(self) -> bool:
        """Show warning dialog for dirty working tree. Returns True if user proceeds."""
        parent = self.get_root() if hasattr(self, "get_root") else None
        dialog = Gtk.MessageDialog(
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Working tree has uncommitted changes",
        )
        dialog.format_secondary_text("Switch branch anyway? Changes will be preserved.")
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _show_error(self, message: str) -> None:
        """Show error message in error label."""
        self._error_label.set_text(message)
        self._error_label.set_visible(True)

    def _hide_error(self) -> None:
        """Hide error label."""
        self._error_label.set_visible(False)

    def _update_branch_dropdown(self) -> None:
        """Update branch dropdown with current branches."""
        self._branch_dropdown.remove_all()

        if not self._branches:
            return

        current_branch_index = -1
        for i, branch in enumerate(self._branches):
            display_name = branch.name
            if branch.is_current:
                display_name = f"{branch.name} (current)"
                current_branch_index = i
            self._branch_dropdown.append_text(display_name)

        if current_branch_index >= 0:
            self._branch_dropdown.set_active(current_branch_index)
        elif self._branches:
            self._branch_dropdown.set_active(0)

    def set_current_path(self, path: str) -> None:
        """Set current repository path and refresh."""
        self._current_path = path
        self._hide_error()
        self.refresh_status()

    def refresh_status(self) -> None:
        """Refresh git status and branches."""
        if not self._current_path or not self._git_service:
            self._show_error("Git service not available")
            return

        try:
            # Get status
            status_list = self._git_service.get_status(self._current_path)

            # Get branches
            self._branches = self._git_service.get_branches(self._current_path)

            # Update UI
            self._update_branch_dropdown()

            # Update status list
            self._status_store.remove_all()
            for status_item in status_list:
                item = FileStatusItem(
                    path=status_item["path"],
                    status=status_item["status"],
                    display_path=status_item.get("display_path"),
                )
                self._status_store.append(item)

            # Update activity badge
            if self._host_bridge:
                self._host_bridge.set_activity_badge("source_control", str(len(status_list)))

            self._hide_error()

        except RuntimeError as e:
            if "git is not installed" in str(e).lower():
                # Platform-specific install instructions
                import platform

                system = platform.system().lower()
                if system == "linux":
                    install_cmd = "sudo apt install git (Debian/Ubuntu), sudo dnf install git (Fedora), sudo pacman -S git (Arch)"
                elif system == "darwin":
                    install_cmd = "brew install git or download from git-scm.com"
                elif system == "windows":
                    install_cmd = "Download Git for Windows from git-scm.com"
                else:
                    install_cmd = "Install git from git-scm.com"

                self._show_error(
                    f"Git is not installed. Please install git to use source control.\nInstall: {install_cmd}"
                )
                # Clear stale UI state
                self._branch_dropdown.remove_all()
                self._status_store.remove_all()
            else:
                self._show_error(f"Git error: {e}")
        except Exception as e:
            logger.error(f"Failed to refresh git status: {e}")
            self._show_error(f"Failed to refresh git status: {e}")
            # Clear stale UI state
            self._branch_dropdown.remove_all()
            self._status_store.remove_all()
