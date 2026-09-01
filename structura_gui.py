"""The Structura window.

Built on CustomTkinter, which is tkinter underneath -- so the frozen build stays
the size it was -- but draws modern widgets and, more importantly, can follow the
desktop's own light or dark setting.

The window is one screen with no modes to hunt through. Structures stack on the
left, everything that describes the pack sits on the right, and the status line
along the bottom says what the program is doing at all times. The old basic and
advanced split is gone: a single structure simply does not need a name tag, and
the second one added asks for both.

Nothing here reaches into structura_core beyond its public calls, so the same
work can be driven from the command line or from another front end.
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter
from tkinter import filedialog

import customtkinter as ctk
import nbtlib
import numpy
from PIL import Image

import app_settings
import lang_icons
import lang_parse
import manifest
import paths
import structura_core
import tech_pack
import ui_icons
import version

try:
    import darkdetect
except ImportError:                     # optional; only used to resolve "system"
    darkdetect = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:                       # dropping is a convenience, never required
    DND_FILES = None
    TkinterDnD = None
    DND_AVAILABLE = False


# --- palette ---------------------------------------------------------------
# Taken from the app icon: the amber of the S against the cool slate of the
# hologram grid. Every colour is a (light mode, dark mode) pair.

AMBER = ("#C8891C", "#E8B23A")
AMBER_HOVER = ("#AB731A", "#F2C45C")
ON_AMBER = ("#FFFFFF", "#161A20")
SURFACE = ("#F2F3F5", "#1B1F26")
PANEL = ("#FFFFFF", "#222831")
FIELD = ("#FFFFFF", "#191D24")
BORDER = ("#D5D8DE", "#2E343E")
TEXT = ("#1B1E24", "#E9ECF2")
MUTED = ("#6B7280", "#8B94A3")
DANGER = ("#C0392B", "#F0705E")
OK = ("#2E7D46", "#6FCF8B")

## the amber the drawn glyphs use, one value rather than a light/dark pair
GLYPH_AMBER = (200, 137, 28)
GLYPH_MUTED = (139, 148, 163)

PAD = 12
TAG_FIELD_WIDTH = 200          # every name tag field is this wide, on every row
STRUCTURE_TYPES = [("Minecraft structure", "*.mcstructure"), ("All files", "*.*")]
IMAGE_TYPES = [("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]

## Where the help and about buttons point. Both are here rather than inline so
## there is one place to correct if the project moves.
GITHUB_ISSUES = "https://github.com/EvilSlimeLabs/Structura/issues"
WEBSITE = "https://evilslimelabs.com"
LOGO = os.path.join("images", "evilslimelabs-logo3.png")

## The name tag field is labelled with Minecraft's own name tag item, so it is
## recognisable before the word is read.
NAME_TAG_TEXTURE = ("Vanilla_Resource_Pack", "textures", "items", "name_tag.png")

_image_cache = {}


def load_image(path, size):
    """A CTkImage, cached: the same picture is asked for on every row."""
    key = (path, size)
    if key not in _image_cache:
        try:
            picture = Image.open(path).convert("RGBA")
        except Exception:
            return None
        _image_cache[key] = ctk.CTkImage(light_image=picture, dark_image=picture,
                                         size=(size, size))
    return _image_cache[key]


def glyph(name, size=16, colour=GLYPH_AMBER):
    """One of the drawn interface icons, as a CTkImage."""
    key = ("glyph", name, size, colour)
    if key not in _image_cache:
        picture = getattr(ui_icons, name)(size * 2, colour)
        _image_cache[key] = ctk.CTkImage(light_image=picture, dark_image=picture,
                                         size=(size, size))
    return _image_cache[key]


def open_link(url):
    import webbrowser
    try:
        webbrowser.open_new_tab(url)
    except Exception:
        pass


def _icon_path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def apply_icon(window):
    """Put the app icon on a window's title bar.

    Both routes are used because neither is reliable on its own. Tk on Windows
    keeps the .ico and the icon photo in different places -- the .ico is what the
    title bar reads -- and CustomTkinter resets the icon while it finishes
    setting a window up, which is why the caller repeats this on a delay.
    """
    ico = _icon_path("pack_icon.ico")
    if os.path.isfile(ico):
        try:
            window.wm_iconbitmap(ico)
        except Exception:
            ## non-Windows Tk refuses a .ico here; not worth failing to start over
            pass
    ## the transparent iconography, not the pack icon: a title bar composes the
    ## icon against itself, so a baked-in background reads as a square tile
    png = paths.lookup("app_icon.png")
    if not os.path.isfile(png):
        png = paths.lookup("pack_icon.png")
    if os.path.isfile(png):
        try:
            if not hasattr(window, "_structura_icon_photo"):
                window._structura_icon_photo = tkinter.PhotoImage(file=png)
            window.iconphoto(False, window._structura_icon_photo)
        except Exception:
            pass


def resolve_theme(choice):
    """Turn the stored preference into what CustomTkinter should be set to.

    "system" is handed straight to CustomTkinter, which follows the desktop --
    except where the desktop cannot be asked at all, and then a dark window is
    the safer thing to show against an unknown background.
    """
    if choice != "system":
        return choice
    if darkdetect is not None and darkdetect.theme() is not None:
        return "system"
    return app_settings.FALLBACK_THEME


class Field(ctk.CTkFrame):
    """An entry with a glyph or a letter sitting inside it, before the text.

    CustomTkinter has no way to inset an entry's text, and a picture placed over
    one covers the characters rather than moving them. So the border belongs to
    this frame and the entry inside is drawn without one; the mark and the text
    are laid out side by side, with margin between, and the whole thing reads as
    a single field.
    """

    def __init__(self, master, textvariable, icon=None, label=None,
                 width=None, height=32, **kwargs):
        super().__init__(master, fg_color=FIELD, corner_radius=8,
                         border_width=1, border_color=BORDER,
                         height=height, **kwargs)
        self.grid_propagate(False)
        if width:
            self.configure(width=width)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.mark = None
        if icon is not None or label is not None:
            self.mark = ctk.CTkLabel(self, text=label or "", width=16,
                                     text_color=MUTED,
                                     font=ctk.CTkFont(size=11, weight="bold"))
            if icon is not None:
                self.mark.configure(image=icon, text="")
            ## the margin either side is what keeps the mark clear of the text
            self.mark.grid(row=0, column=0, padx=(9, 0), sticky="w")

        self.entry = ctk.CTkEntry(self, textvariable=textvariable,
                                  border_width=0, fg_color="transparent",
                                  text_color=TEXT, height=height - 4)
        self.entry.grid(row=0, column=1, sticky="ew",
                        padx=(7 if self.mark else 4, 7))

    def set_label(self, text):
        if self.mark is not None:
            self.mark.configure(text=text)

    def flag(self, wrong):
        self.configure(border_color=DANGER if wrong else BORDER,
                       border_width=2 if wrong else 1)

    def set_enabled(self, enabled):
        """A field that cannot be typed in should not look like one that can."""
        self.entry.configure(state="normal" if enabled else "disabled")
        self.configure(fg_color=FIELD if enabled else BORDER)


class StructureRow(ctk.CTkFrame):
    """One .mcstructure in the pack: its file, its name tag and its offset.

    The offset lives on the row rather than in the settings panel because it
    belongs to this structure. The panel edits whichever row is selected.
    """

    def __init__(self, master, app, path):
        super().__init__(master, fg_color=PANEL, corner_radius=8,
                         border_width=1, border_color=BORDER)
        self.app = app
        self.path = path
        self.offset = [0, 0, 0]
        self.selected = False

        ## only the file button stretches; the name tag field is a fixed width
        ## so every row's field starts and ends in the same place
        self.grid_columnconfigure(0, weight=1)

        self.file_button = ctk.CTkButton(
            self, text="", anchor="w", height=32, corner_radius=6,
            fg_color="transparent", hover_color=FIELD, text_color=TEXT,
            image=glyph("folder", 15), compound="left",
            font=ctk.CTkFont(size=13), command=self.change_file)
        self.file_button.grid(row=0, column=0, sticky="ew", padx=(8, 6), pady=9)

        tag_icon = load_image(paths.data(*NAME_TAG_TEXTURE), 17)
        self.tag_var = tkinter.StringVar()
        self.tag_var.trace_add("write", lambda *_: self.app.revalidate())
        self.tag_field = Field(self, self.tag_var, icon=tag_icon,
                               width=TAG_FIELD_WIDTH, height=32)
        self.tag_field.grid(row=0, column=1, padx=(0, 4), pady=9)

        ## CustomTkinter never activates an entry's placeholder while the entry
        ## is bound to a textvariable, and the variable is what makes validation
        ## live, so the optional/required state is its own label instead.
        self.tag_hint = ctk.CTkLabel(self, text="", anchor="w", width=64,
                                     text_color=MUTED,
                                     font=ctk.CTkFont(size=11))
        self.tag_hint.grid(row=0, column=2, sticky="w", padx=(0, 2))

        self.remove_button = ctk.CTkButton(
            self, text="", width=30, height=30, corner_radius=6,
            image=glyph("cross", 13, GLYPH_MUTED),
            fg_color="transparent", hover_color=BORDER,
            command=lambda: self.app.remove_structure(self))
        self.remove_button.grid(row=0, column=3, padx=(2, 8), pady=9)

        self.bind("<Button-1>", lambda _e: self.app.select_row(self))
        self.refresh_file_label()

    def refresh_file_label(self):
        self.file_button.configure(text="  " + os.path.basename(self.path))

    def change_file(self):
        """Pick a different file for this row, rather than removing and re-adding."""
        self.app.select_row(self)
        chosen = filedialog.askopenfilename(
            title=self.app.text("change file"), filetypes=STRUCTURE_TYPES,
            initialdir=os.path.dirname(self.path) or None)
        if chosen:
            self.path = chosen
            self.refresh_file_label()
            self.app.set_status(self.app.text("status added",
                                              os.path.basename(chosen)))
            self.app.revalidate()

    def set_selected(self, selected):
        self.selected = selected
        self.configure(border_color=AMBER if selected else BORDER,
                       border_width=2 if selected else 1)

    def set_tag_state(self, required, wrong):
        """Show whether this row still needs a name tag, as the user types."""
        self.tag_hint.configure(
            text=self.app.text("required" if required else "optional"),
            text_color=DANGER if wrong else MUTED)
        self.tag_field.flag(wrong)

    def set_tag_enabled(self, enabled):
        self.tag_field.set_enabled(enabled)
        if not enabled:
            self.tag_hint.configure(text="")

    @property
    def tag(self):
        return self.tag_var.get().strip()


class ResultDialog(ctk.CTkToplevel):
    """What happened, once the pack is written."""

    def __init__(self, app, title, lines, folder):
        super().__init__(app)
        self.app = app
        self.folder = folder
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=SURFACE)
        self.grid_columnconfigure(0, weight=1)
        self.after(220, lambda: apply_icon(self))

        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w",
                                           padx=20, pady=(18, 4))
        for i, line in enumerate(lines, start=1):
            ctk.CTkLabel(self, text=line, text_color=MUTED, justify="left",
                         anchor="w", wraplength=420).grid(
                row=i, column=0, sticky="ew", padx=20, pady=1)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=len(lines) + 1, column=0, sticky="e", padx=16, pady=(14, 16))
        if folder:
            ctk.CTkButton(buttons, text=app.text("open folder"), width=130,
                          height=32, corner_radius=8, fg_color="transparent",
                          border_width=1, border_color=BORDER, text_color=TEXT,
                          hover_color=BORDER, command=self.open_folder
                          ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text=app.text("close"), width=110, height=32,
                      corner_radius=8, fg_color=AMBER, hover_color=AMBER_HOVER,
                      text_color=ON_AMBER, command=self.destroy).pack(side="left")

        self.after(60, self._centre)
        self.after(120, self.grab_set)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _centre(self):
        self.update_idletasks()
        x = self.app.winfo_rootx() + (self.app.winfo_width() - self.winfo_width()) // 2
        y = self.app.winfo_rooty() + (self.app.winfo_height() - self.winfo_height()) // 3
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        self.lift()
        self.focus_force()

    def open_folder(self):
        folder = os.path.abspath(self.folder)
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass


class AboutDialog(ctk.CTkToplevel):
    """Who made this, and where to go next."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(app.text("about"))
        self.resizable(False, False)
        self.configure(fg_color=SURFACE)
        self.grid_columnconfigure(0, weight=1)
        self.after(220, lambda: apply_icon(self))

        logo = load_image(paths.data(LOGO), 132)
        if logo is not None:
            ctk.CTkLabel(self, text="", image=logo).grid(row=0, column=0, pady=(18, 4))

        ctk.CTkLabel(self, text="Structura %s" % version.read(),
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT).grid(row=1, column=0, pady=(4, 0))
        ctk.CTkLabel(self, text=app.text("about body"), text_color=MUTED,
                     wraplength=340, justify="center").grid(
            row=2, column=0, padx=22, pady=(6, 2))
        ctk.CTkLabel(self, text="%s: DrAv0011, FondUnicycle, RavinMaddHatter"
                                % app.text("original authors"),
                     text_color=MUTED, wraplength=340, justify="center",
                     font=ctk.CTkFont(size=11)).grid(
            row=3, column=0, padx=22, pady=(2, 6))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=4, column=0, pady=(8, 18))
        ctk.CTkButton(buttons, text=app.text("website"), width=120, height=32,
                      corner_radius=8, fg_color="transparent", border_width=1,
                      border_color=BORDER, text_color=TEXT, hover_color=BORDER,
                      command=lambda: open_link(WEBSITE)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text=app.text("close"), width=110, height=32,
                      corner_radius=8, fg_color=AMBER, hover_color=AMBER_HOVER,
                      text_color=ON_AMBER, command=self.destroy).pack(side="left")

        self.after(60, self._centre)
        self.after(120, self.grab_set)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _centre(self):
        self.update_idletasks()
        x = self.app.winfo_rootx() + (self.app.winfo_width() - self.winfo_width()) // 2
        y = self.app.winfo_rooty() + (self.app.winfo_height() - self.winfo_height()) // 4
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        self.lift()
        self.focus_force()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.strings = app_settings.load()
        self.rows = []
        self.selected = None
        self.building = False
        self.sticky_status = False
        self.events = queue.Queue()
        self.default_icon = paths.lookup("pack_icon.png")
        self.icon_path = self.default_icon
        ## per-row offsets are put aside while big build mode borrows the three
        ## offset fields for its own single corner, and handed back afterwards
        self.big_offset = [0, 0, 0]
        self.stashed_tags = {}

        ctk.set_appearance_mode(resolve_theme(app_settings.settings["theme"]))
        ctk.set_default_color_theme("blue")

        self.title("Structura %s" % version.read())
        self.geometry("1080x790")
        self.minsize(1000, 730)
        self.configure(fg_color=SURFACE)
        for delay in (0, 200, 600, 1200):
            self.after(delay, lambda: apply_icon(self))
        self._enable_drop()

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self._build_structures_panel()
        self._build_settings_panel()
        self._build_footer()

        ## the window opens with no structures. An empty row is something the
        ## user has to notice and delete, and it made a new pack look half
        ## filled in before anything had been chosen.
        self.revalidate()
        self.after(120, self._drain_events)

    # --- chrome ----------------------------------------------------------

    def text(self, key, *args):
        value = self.strings.get(key, key)
        return value.format(*args) if args else value

    def _enable_drop(self):
        """Graft tkinterdnd2 onto the CustomTkinter root, if it is installed."""
        self.dnd_ready = False
        if not DND_AVAILABLE:
            return
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.dnd_ready = True
        except Exception:
            self.dnd_ready = False

    # --- structures panel -------------------------------------------------

    def _build_structures_panel(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew", padx=(PAD, 6), pady=(PAD, 6))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        self.structures_label = ctk.CTkLabel(
            panel, text=self.text("structures"), anchor="w", text_color=MUTED,
            font=ctk.CTkFont(size=12, weight="bold"))
        self.structures_label.grid(row=0, column=0, sticky="ew", padx=6, pady=(2, 8))

        self.list_frame = ctk.CTkScrollableFrame(
            panel, fg_color=("#E9EBEF", "#151920"), corner_radius=10)
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.drop_zone = ctk.CTkButton(
            self.list_frame, text="+   " + self.text("dropfiles"),
            height=88, corner_radius=10, fg_color="transparent",
            border_width=2, border_color=BORDER, text_color=MUTED,
            hover_color=PANEL, font=ctk.CTkFont(size=13),
            command=self.browse_structures)
        self.drop_zone.grid(row=999, column=0, sticky="ew", padx=8, pady=8)

        if self.dnd_ready:
            for widget in (self.list_frame, self.drop_zone):
                try:
                    widget.drop_target_register(DND_FILES)
                    widget.dnd_bind("<<Drop>>", self._on_drop)
                    ## a drop target that does not react looks broken while a
                    ## file is hovering over it
                    widget.dnd_bind("<<DropEnter>>", self._on_drag_enter)
                    widget.dnd_bind("<<DropLeave>>", self._on_drag_leave)
                except Exception:
                    pass

    def _highlight_drop(self, on):
        self.drop_zone.configure(border_color=AMBER if on else BORDER,
                                 text_color=TEXT if on else MUTED,
                                 fg_color=PANEL if on else "transparent")

    def _on_drag_enter(self, event):
        self._highlight_drop(True)
        return event.action

    def _on_drag_leave(self, event):
        self._highlight_drop(False)
        return event.action

    def _on_drop(self, event):
        self._highlight_drop(False)
        for path in self.tk.splitlist(event.data):
            if path.lower().endswith(".mcstructure"):
                self.add_structure_row(path)
        return event.action

    def browse_structures(self):
        chosen = filedialog.askopenfilenames(title=self.text("structurefile"),
                                             filetypes=STRUCTURE_TYPES)
        for path in chosen:
            self.add_structure_row(path)

    def add_structure_row(self, path):
        row = StructureRow(self.list_frame, self, path)
        row.grid(row=len(self.rows), column=0, sticky="ew", padx=8, pady=(8, 0))
        self.rows.append(row)
        self.set_status(self.text("status added", os.path.basename(path)))
        self.select_row(row)
        self.revalidate()
        return row

    def remove_structure(self, row):
        if row not in self.rows:
            return
        name = os.path.basename(row.path) or self.text("structures")
        self.rows.remove(row)
        row.destroy()
        for index, remaining in enumerate(self.rows):
            remaining.grid_configure(row=index)
        if self.selected is row:
            self.selected = None
            if self.rows:
                self.select_row(self.rows[0])
            else:
                self.load_offset_fields([0, 0, 0])
        self.set_status(self.text("status removed", name))
        self.revalidate()

    def select_row(self, row):
        if self.big_build.get():
            return                      # the fields belong to big build mode
        if self.selected is not None and self.selected in self.rows:
            self.selected.set_selected(False)
        self.selected = row
        row.set_selected(True)
        self.load_offset_fields(row.offset)

    # --- settings panel ---------------------------------------------------

    def _build_settings_panel(self):
        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12, width=350)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, PAD), pady=(PAD, 6))
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)
        r = 0

        self.settings_label = ctk.CTkLabel(
            panel, text=self.text("settings"), anchor="w", text_color=MUTED,
            font=ctk.CTkFont(size=12, weight="bold"))
        self.settings_label.grid(row=r, column=0, sticky="ew", padx=16,
                                 pady=(14, 10)); r += 1

        # icon preview and pack name
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.grid(row=r, column=0, sticky="ew", padx=16); r += 1
        head.grid_columnconfigure(1, weight=1)

        self.icon_button = ctk.CTkButton(
            head, text="", width=64, height=64, corner_radius=10,
            fg_color=FIELD, hover_color=BORDER, border_width=1,
            border_color=BORDER, command=self.browse_icon)
        self.icon_button.grid(row=0, column=0, rowspan=3, padx=(0, 10))

        ## only offered once a custom icon is chosen: there is nothing to clear
        ## before that, and an always-present button implies otherwise
        self.icon_clear = ctk.CTkButton(
            head, text="", width=20, height=20, corner_radius=10,
            image=glyph("cross", 10, GLYPH_MUTED),
            fg_color=PANEL, hover_color=BORDER, border_width=1,
            border_color=BORDER, command=self.clear_icon)

        self.name_label = ctk.CTkLabel(head, text=self.text("packname"), anchor="w",
                                       text_color=MUTED, font=ctk.CTkFont(size=12))
        self.name_label.grid(row=0, column=1, sticky="ew")

        self.pack_name_var = tkinter.StringVar()
        self.pack_name_var.trace_add("write", lambda *_: self.revalidate())
        self.pack_name_field = Field(head, self.pack_name_var, height=34)
        self.pack_name_field.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        self.name_hint = ctk.CTkLabel(head, text="", anchor="w", text_color=MUTED,
                                      font=ctk.CTkFont(size=11))
        self.name_hint.grid(row=2, column=1, sticky="ew", pady=(2, 0))
        self.refresh_icon_preview()

        # description
        desc = ctk.CTkFrame(panel, fg_color="transparent")
        desc.grid(row=r, column=0, sticky="ew", padx=16, pady=(12, 0)); r += 1
        desc.grid_columnconfigure(0, weight=1)
        self.desc_label = ctk.CTkLabel(desc, text=self.text("description"),
                                       anchor="w", text_color=MUTED,
                                       font=ctk.CTkFont(size=12))
        self.desc_label.grid(row=0, column=0, sticky="ew")
        self.desc_count = ctk.CTkLabel(desc, text="", anchor="e", text_color=MUTED,
                                       font=ctk.CTkFont(size=11))
        self.desc_count.grid(row=0, column=1, sticky="e")

        self.desc_var = tkinter.StringVar()
        self.desc_var.trace_add("write", lambda *_: self.on_description_typed())
        self.desc_field = Field(desc, self.desc_var, height=34)
        self.desc_field.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.on_description_typed()

        # transparency
        trans = ctk.CTkFrame(panel, fg_color="transparent")
        trans.grid(row=r, column=0, sticky="ew", padx=16, pady=(14, 0)); r += 1
        trans.grid_columnconfigure(0, weight=1)
        self.trans_label = ctk.CTkLabel(trans, text=self.text("blocktransparency"),
                                        anchor="w", text_color=MUTED,
                                        font=ctk.CTkFont(size=12))
        self.trans_label.grid(row=0, column=0, sticky="ew")
        self.trans_value = ctk.CTkLabel(trans, text="", anchor="e", text_color=TEXT,
                                        font=ctk.CTkFont(size=12, weight="bold"))
        self.trans_value.grid(row=0, column=1, sticky="e")

        self.transparency = ctk.CTkSlider(
            trans, from_=0, to=app_settings.MAX_TRANSPARENCY, height=18,
            button_color=AMBER, button_hover_color=AMBER_HOVER,
            progress_color=AMBER, fg_color=BORDER, command=self.on_transparency)
        self.transparency.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.transparency.set(app_settings.DEFAULT_TRANSPARENCY)
        self.on_transparency(app_settings.DEFAULT_TRANSPARENCY)

        # offset, or the corner of a big build
        off = ctk.CTkFrame(panel, fg_color="transparent")
        off.grid(row=r, column=0, sticky="ew", padx=16, pady=(14, 0)); r += 1
        off.grid_columnconfigure((0, 1, 2), weight=1)
        self.offset_label = ctk.CTkLabel(off, text=self.text("offset"), anchor="w",
                                         text_color=MUTED, font=ctk.CTkFont(size=12))
        self.offset_label.grid(row=0, column=0, columnspan=3, sticky="ew",
                               pady=(0, 4))
        ## the axis letter sits inside its own field rather than floating above
        ## it, so three numbers read as three labelled boxes and not six things
        self.offset_vars, self.offset_fields = [], []
        for i, axis in enumerate("xyz"):
            var = tkinter.StringVar(value="0")
            var.trace_add("write", lambda *_: self.on_offset_typed())
            field = Field(off, var, label=self.text("axis %s" % axis), height=32)
            field.grid(row=1, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            self.offset_vars.append(var)
            self.offset_fields.append(field)

        ## big build assembles several structures into one model, so its corner
        ## is the lowest world origin of all of them -- which the game already
        ## recorded inside each structure file
        self.cords_button = ctk.CTkButton(
            off, text=self.text("getcords"), height=30, corner_radius=8,
            image=glyph("corner", 14), compound="left",
            fg_color="transparent", border_width=1, border_color=BORDER,
            text_color=TEXT, hover_color=BORDER, font=ctk.CTkFont(size=12),
            command=self.get_global_cords)

        # switches
        self.tech_pack = tkinter.IntVar()
        self.big_build = tkinter.IntVar()
        self.block_lists = tkinter.IntVar()

        switches = ctk.CTkFrame(panel, fg_color="transparent")
        switches.grid(row=r, column=0, sticky="ew", padx=16, pady=(16, 0)); r += 1
        switches.grid_columnconfigure(0, weight=1)

        self.switches = [
            self._switch(switches, 0, "techpack", self.tech_pack, self.on_tech_pack),
            self._switch(switches, 1, "bigbuild", self.big_build, self.on_big_build),
            self._switch(switches, 2, "lists", self.block_lists, None),
        ]
        if not tech_pack.available():
            self.switches[0].configure(state="disabled")

        panel.grid_rowconfigure(r, weight=1); r += 1

        ## where the finished pack lands, next to the button that makes it
        out = ctk.CTkFrame(panel, fg_color="transparent")
        out.grid(row=r, column=0, sticky="ew", padx=16, pady=(0, 2)); r += 1
        out.grid_columnconfigure(0, weight=1)
        self.output_label = ctk.CTkLabel(out, text=self.text("output folder"),
                                         anchor="w", text_color=MUTED,
                                         font=ctk.CTkFont(size=12))
        self.output_label.grid(row=0, column=0, sticky="ew")
        self.output_button = ctk.CTkButton(
            out, text="", height=32, corner_radius=8, anchor="w",
            image=glyph("folder", 15), compound="left",
            fg_color=FIELD, hover_color=BORDER, border_width=1,
            border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(size=11), command=self.browse_output)
        self.output_button.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.refresh_output_button()

        self.make_button = ctk.CTkButton(
            panel, text=self.text("makepack"), height=46, corner_radius=10,
            fg_color=AMBER, hover_color=AMBER_HOVER, text_color=ON_AMBER,
            font=ctk.CTkFont(size=15, weight="bold"), command=self.make_pack)
        self.make_button.grid(row=r, column=0, sticky="ew", padx=16, pady=(12, 16))

    def _switch(self, parent, row, key, variable, command):
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.grid(row=row, column=0, sticky="ew", pady=5)
        holder.grid_columnconfigure(0, weight=1)
        label = ctk.CTkLabel(holder, text=self.text(key), anchor="w",
                             text_color=TEXT, font=ctk.CTkFont(size=13))
        label.grid(row=0, column=0, sticky="ew")
        switch = ctk.CTkSwitch(holder, text="", variable=variable, width=46,
                               progress_color=AMBER,
                               button_color=("#FFFFFF", "#E9ECF2"),
                               command=command)
        switch.grid(row=0, column=1, sticky="e")
        switch.label = label
        switch.key = key
        return switch

    # --- footer -----------------------------------------------------------

    def _build_footer(self):
        bar = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10, height=44)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(0, PAD))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(bar, text="", anchor="w", text_color=MUTED,
                                         font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="ew", padx=14, pady=10)

        self.help_button = ctk.CTkButton(
            bar, text="?", width=30, height=28, corner_radius=8,
            fg_color="transparent", hover_color=BORDER, text_color=MUTED,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.open_help)
        self.help_button.grid(row=0, column=1, padx=(4, 2), pady=8)

        self.about_button = ctk.CTkButton(
            bar, text="i", width=30, height=28, corner_radius=8,
            fg_color="transparent", hover_color=BORDER, text_color=MUTED,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: AboutDialog(self))
        self.about_button.grid(row=0, column=2, padx=(0, 6), pady=8)

        self.theme_menu = ctk.CTkOptionMenu(
            bar, width=120, height=28, corner_radius=8,
            values=[self.text(name) for name in app_settings.THEMES],
            fg_color=FIELD, button_color=FIELD, button_hover_color=BORDER,
            text_color=TEXT, dropdown_fg_color=PANEL, dropdown_text_color=TEXT,
            command=self.on_theme)
        self.theme_menu.set(self.text(app_settings.settings["theme"]))
        self.theme_menu.grid(row=0, column=3, padx=(0, 6), pady=8)

        self.language_badge = ctk.CTkLabel(bar, text="")
        self.language_badge.grid(row=0, column=4, padx=(4, 4))
        self.language_menu = ctk.CTkOptionMenu(
            bar, width=150, height=28, corner_radius=8,
            values=app_settings.choices(),
            fg_color=FIELD, button_color=FIELD, button_hover_color=BORDER,
            text_color=TEXT, dropdown_fg_color=PANEL, dropdown_text_color=TEXT,
            command=self.on_language)
        self.language_menu.set(app_settings.settings["lang"])
        self.language_menu.grid(row=0, column=5, padx=(0, 12), pady=8)
        self.refresh_language_badge()

        self.set_status(self.text("status ready"))

    def refresh_language_badge(self):
        code = lang_parse.code(app_settings.settings["lang"])
        light, dark = lang_icons.pair(code, size=22)
        self.language_badge.configure(
            image=ctk.CTkImage(light_image=light, dark_image=dark, size=(22, 22)))

    def refresh_icon_preview(self):
        """The icon button shows the icon itself, not a filename."""
        try:
            picture = Image.open(self.icon_path).convert("RGBA")
        except Exception:
            self.icon_button.configure(text="!", text_color=DANGER)
            return
        self.icon_button.configure(
            text="", image=ctk.CTkImage(light_image=picture, dark_image=picture,
                                        size=(52, 52)))
        if os.path.abspath(self.icon_path) == os.path.abspath(self.default_icon):
            self.icon_clear.grid_forget()
        else:
            ## shares the preview's grid cell and, being created later, draws on
            ## top of it -- so clearing is discoverable without costing a row
            self.icon_clear.grid(row=0, column=0, sticky="ne")

    # --- handlers ---------------------------------------------------------

    def refresh_output_button(self):
        """Show the tail of the path: the start is the same for everybody."""
        shown = app_settings.output_dir()
        if len(shown) > 36:
            shown = "..." + shown[-33:]
        self.output_button.configure(text="  " + shown)

    def browse_output(self):
        folder = filedialog.askdirectory(title=self.text("choose folder"),
                                         initialdir=app_settings.output_dir())
        if folder:
            app_settings.set_output_dir(folder)
            self.refresh_output_button()
            self.set_status(self.text("status output", folder))

    def open_help(self):
        open_link(GITHUB_ISSUES)
        self.set_status(GITHUB_ISSUES)

    def browse_icon(self):
        path = filedialog.askopenfilename(title=self.text("icon"),
                                          filetypes=IMAGE_TYPES)
        if path:
            self.icon_path = path
            self.refresh_icon_preview()
            self.set_status(self.text("status icon", os.path.basename(path)))

    def clear_icon(self):
        self.icon_path = self.default_icon
        self.refresh_icon_preview()
        self.set_status(self.text("clear icon"))

    def on_description_typed(self):
        text = self.desc_var.get()
        if len(text) > manifest.DESCRIPTION_LIMIT:
            self.desc_var.set(text[:manifest.DESCRIPTION_LIMIT])
            return
        self.desc_count.configure(
            text="%d/%d" % (len(text), manifest.DESCRIPTION_LIMIT),
            text_color=DANGER if len(text) == manifest.DESCRIPTION_LIMIT else MUTED)

    def on_transparency(self, value):
        self.trans_value.configure(text="%d%%" % round(float(value)))

    def on_offset_typed(self):
        target = self.big_offset if self.big_build.get() else (
            self.selected.offset if self.selected in self.rows else None)
        if target is None:
            return
        for i, var in enumerate(self.offset_vars):
            try:
                target[i] = int(var.get() or 0)
            except ValueError:
                target[i] = 0

    def load_offset_fields(self, offset):
        for var, value in zip(self.offset_vars, offset):
            var.set(str(value))

    def get_global_cords(self):
        """Fill the corner with the lowest world origin of every structure.

        Each .mcstructure records where in the world it was taken from. A big
        build is several of them assembled, so the corner of the whole thing is
        the smallest origin across the set -- which puts the ghost model back
        where the pieces came from, instead of making the user read coordinates
        off the structure blocks and type them in.
        """
        files = [row.path for row in self.rows if row.path]
        if not files:
            self.set_status(self.text("need structure"), warn=True)
            return
        lowest = None
        for path in files:
            try:
                data = nbtlib.load(path, byteorder="little")
                if "" in data.keys():
                    data = data[""]
                origin = numpy.array(list(map(int, data["structure_world_origin"])))
            except Exception as exc:
                self.set_status(self.text("status failed", exc), warn=True)
                return
            lowest = origin if lowest is None else numpy.minimum(lowest, origin)
        self.big_offset = [int(v) for v in lowest]
        self.load_offset_fields(self.big_offset)
        self.set_status("%s: %d, %d, %d" % ((self.text("corner"),) +
                                            tuple(self.big_offset)))

    def on_tech_pack(self):
        if self.tech_pack.get() and not tech_pack.available():
            self.tech_pack.set(0)
            return
        self.revalidate()

    def on_big_build(self):
        """Swap the offset fields and the name tags without losing either.

        Big build mode has one corner for the whole pack and names its models
        itself, so the per-structure fields have nowhere to go while it is on.
        Their values are put aside here and handed back when it is turned off,
        so flipping the switch twice leaves the window exactly as it was.
        """
        on = bool(self.big_build.get())
        if on:
            if self.selected is not None and self.selected in self.rows:
                self.selected.set_selected(False)
            for row in self.rows:
                self.stashed_tags[row] = row.tag_var.get()
                row.tag_var.set("")
                row.set_tag_enabled(False)
            self.offset_label.configure(text=self.text("corner"))
            self.load_offset_fields(self.big_offset)
            self.cords_button.grid(row=2, column=0, columnspan=3, sticky="ew",
                                   pady=(8, 0))
        else:
            for row in self.rows:
                row.set_tag_enabled(True)
                if row in self.stashed_tags:
                    row.tag_var.set(self.stashed_tags.pop(row))
            self.offset_label.configure(text=self.text("offset"))
            self.cords_button.grid_forget()
            if self.rows:
                self.select_row(self.selected if self.selected in self.rows
                                else self.rows[0])
            else:
                self.load_offset_fields([0, 0, 0])
        self.revalidate()

    def on_theme(self, shown):
        for name in app_settings.THEMES:
            if self.text(name) == shown:
                ctk.set_appearance_mode(resolve_theme(app_settings.set_theme(name)))
                self.set_status(self.text("status theme", shown))
                return

    def on_language(self, name):
        self.strings = app_settings.set_language(name)
        ## keep the menu in step: it is already right when the user picked from
        ## it, but not when the language is set from anywhere else
        self.language_menu.set(name)
        self.refresh_language_badge()
        self.retranslate()
        self.set_status(self.text("status language", name))

    def retranslate(self):
        """Relabel everything in place, without rebuilding the window."""
        self.structures_label.configure(text=self.text("structures"))
        self.settings_label.configure(text=self.text("settings"))
        self.drop_zone.configure(text="+   " + self.text("dropfiles"))
        self.name_label.configure(text=self.text("packname"))
        self.desc_label.configure(text=self.text("description"))
        self.trans_label.configure(text=self.text("blocktransparency"))
        self.offset_label.configure(text=self.text(
            "corner" if self.big_build.get() else "offset"))
        for axis, field in zip("xyz", self.offset_fields):
            field.set_label(self.text("axis %s" % axis))
        self.cords_button.configure(text=self.text("getcords"))
        self.output_label.configure(text=self.text("output folder"))
        self.make_button.configure(text=self.text("makepack"))
        for switch in self.switches:
            switch.label.configure(text=self.text(switch.key))
        self.theme_menu.configure(values=[self.text(n) for n in app_settings.THEMES])
        self.theme_menu.set(self.text(app_settings.settings["theme"]))
        self.refresh_output_button()
        self.revalidate()

    # --- validation -------------------------------------------------------

    def revalidate(self):
        """Re-check every required field and show the result as the user types.

        A name tag is optional while there is one structure and required from
        the second onwards, so adding or removing a file changes what the other
        rows are asking for -- which is why this runs over all of them rather
        than over the field that changed.
        """
        filled = [row for row in self.rows if row.path]
        tags_required = len(filled) > 1 and not self.big_build.get()

        ## a tag used twice is wrong on both rows, so both are marked
        counts = {}
        for row in filled:
            if row.tag:
                counts[row.tag] = counts.get(row.tag, 0) + 1
        duplicated = {tag for tag, n in counts.items() if n > 1}

        for row in self.rows:
            if self.big_build.get():
                ## the tags are put away in big build mode, so there is nothing
                ## for the hint to be asking for
                row.tag_hint.configure(text="")
                row.tag_field.flag(False)
                continue
            wrong = tags_required and (not row.tag or row.tag in duplicated)
            row.set_tag_state(tags_required, wrong)

        problem = None
        if not filled:
            problem = self.text("need structure")
        elif not self.pack_name_var.get().strip():
            problem = self.text("need pack name")
        elif tags_required and any(not row.tag for row in filled):
            problem = self.text("need nametag")
        elif tags_required and duplicated:
            problem = self.text("duplicate nametag")

        missing_name = not self.pack_name_var.get().strip()
        self.pack_name_field.flag(missing_name)
        self.name_hint.configure(
            text=self.text("need pack name") if missing_name else "",
            text_color=DANGER)

        self.make_button.configure(
            state="disabled" if problem else "normal",
            fg_color=BORDER if problem else AMBER,
            text_color=MUTED if problem else ON_AMBER)
        self.problem = problem
        ## a finished build's message stays until the user does something else;
        ## re-validating on the way out of a build would otherwise wipe the one
        ## line that says it worked
        if not self.building and not (self.sticky_status and problem is None):
            self.set_status(problem or self.text("status ready"),
                            warn=problem is not None)
        return problem is None

    def set_status(self, message, warn=False, good=False, sticky=False):
        """The status line always says what just happened or what is wrong.

        `sticky` holds a message in place until the next thing the user does,
        so the line reporting a finished pack is still there to read.
        """
        self.sticky_status = sticky
        colour = DANGER if warn else (OK if good else MUTED)
        self.status_label.configure(text=message, text_color=colour)

    # --- building ---------------------------------------------------------

    def make_pack(self):
        if self.building or not self.revalidate():
            return
        self.building = True
        self.make_button.configure(state="disabled")
        ## structura() takes a path, and the last part of it is the pack name,
        ## so the chosen folder simply prefixes it. The folder is created here
        ## rather than in the worker so a permissions problem is reported before
        ## anything else has been done.
        folder = app_settings.output_dir()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            self.building = False
            self.set_status(self.text("status failed", exc), warn=True)
            self.revalidate()
            return
        job = {
            "folder": folder,
            "pack_name": self.pack_name_var.get().strip(),
            "description": self.desc_var.get().strip(),
            "icon": self.icon_path,
            "alpha": app_settings.transparency_to_alpha(self.transparency.get()),
            "tech_pack": bool(self.tech_pack.get()),
            "big_build": bool(self.big_build.get()),
            "block_lists": bool(self.block_lists.get()),
            "big_offset": list(self.big_offset),
            "models": [(row.tag, row.path, list(row.offset))
                       for row in self.rows if row.path],
        }
        threading.Thread(target=self._build_worker, args=(job,), daemon=True).start()

    def _build_worker(self, job):
        """Runs off the main thread; every message goes back through the queue."""
        pack = None
        try:
            pack = structura_core.structura(
                os.path.join(job["folder"], job["pack_name"]))
            pack.set_opacity(job["alpha"])
            pack.set_description(job["description"])
            if job["icon"]:
                pack.set_icon(job["icon"])
            if job["tech_pack"]:
                pack.set_tech_pack(True)

            for index, (tag, path, offset) in enumerate(job["models"]):
                name = tag or ("" if len(job["models"]) == 1 else str(index))
                self.events.put(("status", self.text(
                    "status reading", os.path.basename(path))))
                pack.add_model(name, path)
                pack.set_model_offset(name, offset)

            self.events.put(("status", self.text("status building", job["pack_name"])))
            if job["big_build"]:
                pack.make_big_model(job["big_offset"])
                if job["block_lists"]:
                    pack.make_big_blocklist()
            else:
                pack.generate_with_nametags()
                if job["block_lists"]:
                    pack.make_nametag_block_lists()

            self.events.put(("status", self.text("status packing", job["pack_name"])))
            skipped = pack.get_skipped(write_file=True)
            path = pack.compile_pack(overwrite=True)
            self.events.put(("done", (path, skipped, job["pack_name"])))
        except Exception as exc:
            if pack is not None:
                pack.cleanup()
            self.events.put(("failed", "%s: %s" % (type(exc).__name__, exc)))

    def _drain_events(self):
        """The worker's messages, applied on the main thread where Tk wants them."""
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.set_status(payload)
                elif kind == "done":
                    self._build_finished(*payload)
                elif kind == "failed":
                    self.building = False
                    self.set_status(self.text("status failed", payload), warn=True)
                    ResultDialog(self, self.text("error"), [payload], None)
                    self.revalidate()
        except queue.Empty:
            pass
        self.after(120, self._drain_events)

    def _build_finished(self, path, skipped, pack_name):
        self.building = False
        self.set_status(self.text("status built", os.path.basename(path)),
                        good=True, sticky=True)
        lines = [os.path.abspath(path)]
        count = sum(sum(v.values()) for v in skipped.values())
        if count:
            lines.append(self.text("status skipped", count))
        ResultDialog(self, self.text("pack built"), lines,
                     os.path.dirname(os.path.abspath(path)) or ".")
        self.revalidate()


def run():
    App().mainloop()
