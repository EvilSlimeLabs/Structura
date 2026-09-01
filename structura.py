"""Structura's entry point: the Tk front end and the command line interface.

Importing this module has no side effects. Everything — reading settings,
parsing arguments, building the window — happens inside main().
"""
import os
import argparse
import sys
import updater
import json
import lang_parse
import version
import armor_stand_geo_class
import structura_core

from numpy import array, int32, minimum
import nbtlib
from tkinter import (
    filedialog,
    messagebox,
    OptionMenu,
    Scale,
    DoubleVar,
    HORIZONTAL,
    IntVar,
    Listbox,
    ANCHOR,
    StringVar,
    Button,
    Label,
    Entry,
    Tk,
    Checkbutton,
    END,
    ACTIVE,
)

import tech_pack
from structura_core import structura

structura_update_version = "Structura1-7"

## This fork does not publish to the upstream update server, so the button is
## hidden. The updater, the update() handler and the --update flag all still
## work; set this to True once the fork has an update source of its own.
SHOW_UPDATE_BUTTON = False

## the slider is transparency, so 0 is a solid ghost block and 100 would be
## invisible. It stops at 99 so a ghost block always has some alpha left.
DEFAULT_OPACITY = 85
DEFAULT_TRANSPARENCY = 100 - DEFAULT_OPACITY
MAX_TRANSPARENCY = 99

DEFAULT_LANGUAGE = "English"
## a placeholder column in langs.csv, useful for spotting a missing lookup but
## not something to offer in the menu
HIDDEN_LANGUAGES = {"Test"}

SETTINGS_FILE = "settings.json"

models = {}
settings = {"lang": DEFAULT_LANGUAGE}
langs = {}
lang = {}


# --- settings and translations -------------------------------------------

def language(name):
    """The strings for `name`, with English filling any gap.

    A translation column that is missing a row, or has it blank, would otherwise
    put an empty label on screen.
    """
    strings = dict(langs.get(DEFAULT_LANGUAGE, {}))
    strings.update({k: v for k, v in langs.get(name, {}).items() if v})
    return strings


def save_settings():
    with open(SETTINGS_FILE, "w+", encoding="utf-8") as file:
        json.dump(settings, file)


def load_settings():
    global settings, langs, lang
    if not os.path.exists("lookups"):
        print("getting files")
        updater.update("https://update.structuralab.com/structuraUpdate",
                       structura_update_version, "")
    langs = lang_parse.parse()
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as file:
            settings = json.load(file)
    ## an unknown or hand-edited language must not stop the program starting
    if settings.get("lang") not in langs:
        settings["lang"] = DEFAULT_LANGUAGE
    save_settings()
    lang = language(settings["lang"])


def apply_language(name):
    """Switch language and relabel the window in place."""
    global lang
    if name not in langs:
        return
    settings["lang"] = name
    save_settings()
    lang = language(name)
    for widget, key in TRANSLATABLE:
        widget.config(text=lang[key])
    box_checked()


# --- command line --------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Structura app that generates Resource packs from .mcstructure files.")
    parser.add_argument("--structure", type=str, help=".mcstructure file")
    parser.add_argument("--pack_name", type=str, help="Name of pack")
    parser.add_argument("--opacity", type=int, help="Opacity of blocks, 1-100")
    parser.add_argument("--icon", type=str, help="Icon for pack")
    parser.add_argument("--offset", type=str, help="X, Y, X")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the output file.")
    parser.add_argument("--debug", "-db", action='store_true', help='Enable debug mode')
    parser.add_argument("--update", action='store_true', help='Run updater')
    parser.add_argument("--tech_pack", action="store_true",
                        help="Bundle TechPack into the generated pack, so one pack "
                             "carries both. Both projects replace the armor stand "
                             "entity, so applying them separately loses one of them.")
    args = parser.parse_args(argv)
    ## half a command line used to fall through to the window, which on a
    ## headless machine fails somewhere much less obvious
    if bool(args.structure) != bool(args.pack_name):
        parser.error("--structure and --pack_name go together; give both to build "
                     "from the command line, or neither to open the window")
    return args


def run_cli(args):
    opacity = DEFAULT_OPACITY if args.opacity is None else args.opacity
    offset = [0, 0, 0]
    if args.offset:
        offset = [int(val) for val in args.offset.split(",")]

    pack_file = "{}.mcpack".format(args.pack_name)
    if args.overwrite and os.path.isfile(pack_file):
        os.remove(pack_file)

    structura_base = structura(args.pack_name)
    structura_base.set_opacity(min(max(opacity, 1), 100) / 100)

    if icon := args.icon:
        structura_base.set_icon(icon)

    if args.tech_pack:
        structura_base.set_tech_pack(True)

    structura_base.add_model("", args.structure)
    structura_base.set_model_offset("", offset)
    structura_base.generate_with_nametags()
    structura_base.compile_pack()


def transparency_to_alpha(transparency):
    #the slider reads as transparency: 0 is fully opaque, 100 is invisible.
    #set_opacity wants the alpha fraction, so invert and scale here.
    return (100 - transparency) / 100


# --- callbacks -----------------------------------------------------------

def browseStruct():
    #browse for a structure file.
    FileGUI.set(filedialog.askopenfilename(filetypes=(
        ("Structure File", "*.mcstructure *.MCSTRUCTURE"), )))
def browseIcon():
    #browse for a structure file.
    icon_var.set(filedialog.askopenfilename(filetypes=(
        ("Icon File", "*.png *.PNG"), )))
def update():
    lookup_version = os.path.join("lookups", "lookup_version.json")
    with open(lookup_version) as file:
        version_data = json.load(file)
    updated = updater.update(version_data["update_url"],structura_update_version,version_data["version"])
    if updated:
        with open(lookup_version) as file:
            version_data = json.load(file)
        messagebox.showinfo("Updated!", version_data["notes"])
    else:
        messagebox.showinfo("Status", "You are currently up to date.")

def box_checked():
    r = 0
    if SHOW_UPDATE_BUTTON:
        title_text.grid(row=r, column=0, columnspan=2)
        updateButton.grid(row=r, column=2)
    else:
        title_text.grid(row=r, column=0, columnspan=3)
        updateButton.grid_forget()
    if check_var.get()==0:
        modle_name_entry.grid_forget()
        modle_name_lb.grid_forget()
        deleteButton.grid_forget()
        cord_lb_big.grid_forget()
        listbox.grid_forget()
        saveButton.grid_forget()
        modelButton.grid_forget()
        cord_lb.grid_forget()
        r +=1
        file_lb.grid(row=r, column=0)
        file_entry.grid(row=r, column=1)
        packButton.grid(row=r, column=2)
        r += 1
        icon_lb.grid(row=r, column=0)
        icon_entry.grid(row=r, column=1)
        IconButton.grid(row=r, column=2)
        r += 1

        packName_lb.grid(row=r, column=0)
        packName_entry.grid(row=r, column=1)
        r += 1
        cord_lb.grid_forget()
        x_entry.grid_forget()
        y_entry.grid_forget()
        z_entry.grid_forget()
        big_build_check.grid_forget()
        get_cords_button.grid_forget()
        transparency_lb.grid(row=r, column=0)
        transparency_entry.grid(row=r, column=1, columnspan=2)
        r += 1
        advanced_check.grid(row=r, column=0)
        export_check.grid(row=r, column=1)
        saveButton.grid(row=r, column=2)
        r += 1
        if tech_pack.available():
            tech_check.grid(row=r, column=0, columnspan=2)
            r += 1
        else:
            tech_check.grid_forget()

    else:
        saveButton.grid_forget()
        get_cords_button.grid_forget()
        cord_lb.grid_forget()
        cord_lb_big.grid_forget()
        modle_name_entry.grid_forget()
        modle_name_lb.grid_forget()
        modelButton.grid_forget()
        r +=1
        file_lb.grid(row=r, column=0)
        file_entry.grid(row=r, column=1)
        packButton.grid(row=r, column=2)
        r += 1
        icon_lb.grid(row=r, column=0)
        icon_entry.grid(row=r, column=1)
        IconButton.grid(row=r, column=2)
        r += 1
        packName_lb.grid(row=r, column=0)
        packName_entry.grid(row=r, column=1)
        r += 1
        if big_build.get()==0:

            modle_name_entry.grid(row=r, column=1)
            modle_name_lb.grid(row=r, column=0)
        else:
            get_cords_button.grid(row=r, column=0,columnspan=2)
        modelButton.grid(row=r, column=2)
        r += 1
        if big_build.get()==0:
            cord_lb.grid(row=r, column=0,columnspan=3)
        else:
            cord_lb_big.grid(row=r, column=0,columnspan=3)
        r += 1
        x_entry.grid(row=r, column=0)
        y_entry.grid(row=r, column=1)
        z_entry.grid(row=r, column=2)
        r += 1
        transparency_lb.grid(row=r, column=0)
        transparency_entry.grid(row=r, column=1,columnspan=2)
        r += 1
        listbox.grid(row=r,column=1, rowspan=3)
        deleteButton.grid(row=r,column=2)
        r += 4
        advanced_check.grid(row=r, column=0)
        export_check.grid(row=r, column=1)
        saveButton.grid(row=r, column=2)
        r +=1
        big_build_check.grid(row=r, column=0,columnspan=2)
        if tech_pack.available():
            tech_check.grid(row=r, column=2)
        else:
            tech_check.grid_forget()
        r += 1
    ## the language row sits at the bottom of whichever layout is showing
    language_lb.grid(row=r, column=0)
    language_menu.grid(row=r, column=1)

def add_model():
    valid=True
    if big_build.get()==1:
        model_name_var.set(os.path.basename(FileGUI.get()))

    if len(FileGUI.get()) == 0:
        valid=False
        messagebox.showinfo(lang["error"], lang["browse file"])
    if big_build.get()==0 and len(model_name_var.get().strip()) == 0:
        messagebox.showinfo(lang["error"], lang["no name tag"])
        valid=False
    if model_name_var.get() in list(models.keys()):
        messagebox.showinfo(lang["error"], lang["unique tag"])
        valid=False

    if valid:
        name_tag=model_name_var.get()
        models[name_tag] = {}
        models[name_tag]["offsets"] = [xvar.get(),yvar.get(),zvar.get()]
        models[name_tag]["structure"] = FileGUI.get()
        listbox.insert(END,model_name_var.get())

def get_global_cords():
    mins = array([2147483647,2147483647,2147483647],dtype=int32)
    for name in models.keys():
        file = models[name]["structure"]
        struct = {}
        struct["nbt"] = nbtlib.load(file, byteorder='little')
        if "" in struct["nbt"].keys():
            struct["nbt"] = struct["nbt"][""]
        struct["mins"] = array(list(map(int,struct["nbt"]["structure_world_origin"])))
        mins = minimum(mins, struct["mins"])
        xvar.set(mins[0])
        yvar.set(mins[1])
        zvar.set(mins[2])


def delete_model():
    items = listbox.curselection()
    if len(items)>0:
        models.pop(listbox.get(ACTIVE))
    listbox.delete(ANCHOR)

def runFromGui():
    ##wrapper for a gui.
    stop = False
    if os.path.isfile("{}.mcpack".format(packName.get())):
        stop = True
        messagebox.showinfo(lang["error"], lang["pack name error"])
        ## could be fixed if temp files were used.
    if check_var.get()==0:
        if len(FileGUI.get()) == 0:
            stop = True
            messagebox.showinfo(lang["error"], lang["unique tag"])
    if len(packName.get()) == 0:
        stop = True
        messagebox.showinfo(lang["error"], lang["no pack name"])
    else:
        if len(list(models.keys()))==0 and check_var.get():
            stop = True
            messagebox.showinfo(lang["error"], lang["no structure files"])

    if not stop:
        structura_base=structura(packName.get())
        structura_base.set_opacity(transparency_to_alpha(sliderVar.get()))
        if len(icon_var.get())>0:
            structura_base.set_icon(icon_var.get())
        if tech_var.get() and tech_pack.available():
            structura_base.set_tech_pack(True)


        if not(check_var.get()):
            structura_base.add_model("",FileGUI.get())
            offset=[xvar.get(),yvar.get(),zvar.get()]
            structura_base.set_model_offset("",offset)
            structura_base.generate_with_nametags()
            if (export_list.get()==1):
                structura_base.make_nametag_block_lists()
            structura_base.compile_pack()
        elif big_build.get():
            for name_tag in models.keys():
                structura_base.add_model(name_tag,models[name_tag]["structure"])
            structura_base.make_big_model([xvar.get(),yvar.get(),zvar.get()])
            if (export_list.get()==1):
                structura_base.make_big_blocklist()
            structura_base.compile_pack()
        else:
            for name_tag in models.keys():
                structura_base.add_model(name_tag,models[name_tag]["structure"])
                structura_base.set_model_offset(name_tag,models[name_tag]["offsets"].copy())
            structura_base.generate_with_nametags()
            if (export_list.get()==1):
                structura_base.make_nametag_block_lists()
            structura_base.generate_nametag_file()
            structura_base.compile_pack()


# --- window --------------------------------------------------------------

def build_gui():
    """Create the window and every widget the callbacks reach for.

    The widgets are module level because the callbacks above are too; keeping
    them here rather than at import time is what makes this module importable.
    """
    global root, FileGUI, packName, icon_var, sliderVar, model_name_var
    global xvar, yvar, zvar, check_var, export_list, big_build, lang_var
    global listbox, title_text, file_entry, packName_entry, modle_name_lb
    global modle_name_entry, cord_lb, cord_lb_big, x_entry, y_entry, z_entry
    global icon_lb, icon_entry, updateButton, IconButton, file_lb, packName_lb
    global packButton, advanced_check, export_check, big_build_check
    global deleteButton, saveButton, modelButton, get_cords_button
    global transparency_lb, transparency_entry, language_lb, language_menu
    global tech_var, tech_check
    global TRANSLATABLE

    root = Tk()
    root.title("Structura {}".format(version.read()))
    FileGUI = StringVar()
    packName = StringVar()
    icon_var = StringVar()
    icon_var.set("lookups/pack_icon.png")
    sliderVar = DoubleVar()
    model_name_var = StringVar()
    xvar = DoubleVar()
    xvar.set(0)
    yvar = DoubleVar()
    zvar = DoubleVar()
    zvar.set(0)
    check_var = IntVar()
    export_list = IntVar()
    big_build = IntVar()
    tech_var = IntVar()
    big_build.set(0)
    sliderVar.set(DEFAULT_TRANSPARENCY)
    listbox=Listbox(root)
    title_text = Label(root, text=lang["title"])
    file_entry = Entry(root, textvariable=FileGUI)
    packName_entry = Entry(root, textvariable=packName)
    modle_name_lb = Label(root, text=lang["name tag"])
    modle_name_entry = Entry(root, textvariable=model_name_var)
    cord_lb = Label(root, text=lang["offset"])
    cord_lb_big = Label(root, text=lang["corner"])
    x_entry = Entry(root, textvariable=xvar, width=5)
    y_entry = Entry(root, textvariable=yvar, width=5)
    z_entry = Entry(root, textvariable=zvar, width=5)
    icon_lb = Label(root, text=lang["icon"])
    icon_entry = Entry(root, textvariable=icon_var)
    updateButton = Button(root, text=lang["update"], command=update)
    IconButton = Button(root, text=lang["browse"], command=browseIcon)
    file_lb = Label(root, text=lang["structurefile"])
    packName_lb = Label(root, text=lang["packname"])
    packButton = Button(root, text=lang["browse"], command=browseStruct)
    advanced_check = Checkbutton(root, text=lang["advance"], variable=check_var, onvalue=1, offvalue=0, command=box_checked)
    export_check = Checkbutton(root, text=lang["lists"], variable=export_list, onvalue=1, offvalue=0)
    big_build_check = Checkbutton(root, text=lang["bigbuild"], variable=big_build, onvalue=1, offvalue=0, command=box_checked )
    ## only offered when the submodule is actually checked out; a source
    ## checkout without submodules has nothing to bundle
    tech_check = Checkbutton(root, text=lang["techpack"], variable=tech_var, onvalue=1, offvalue=0)

    deleteButton = Button(root, text=lang["remove"], command=delete_model)
    saveButton = Button(root, text=lang["makepack"], command=runFromGui)
    modelButton = Button(root, text=lang["addmodel"], command=add_model)
    get_cords_button = Button(root, text=lang["getcords"], command=get_global_cords)
    transparency_lb = Label(root, text=lang["transparency"])
    transparency_entry = Scale(root,variable=sliderVar, length=200, from_=0, to=MAX_TRANSPARENCY,tickinterval=10,orient=HORIZONTAL)

    language_lb = Label(root, text=lang["language"])
    lang_var = StringVar(value=settings["lang"])
    choices = sorted(name for name in langs if name not in HIDDEN_LANGUAGES)
    language_menu = OptionMenu(root, lang_var, *choices, command=apply_language)

    ## widgets carrying a translated label, so a language change can relabel
    ## them without rebuilding the window
    TRANSLATABLE = [
        (title_text, "title"), (modle_name_lb, "name tag"), (cord_lb, "offset"),
        (cord_lb_big, "corner"), (icon_lb, "icon"), (updateButton, "update"),
        (IconButton, "browse"), (file_lb, "structurefile"),
        (packName_lb, "packname"), (packButton, "browse"),
        (advanced_check, "advance"), (export_check, "lists"),
        (big_build_check, "bigbuild"), (deleteButton, "remove"),
        (saveButton, "makepack"), (modelButton, "addmodel"),
        (get_cords_button, "getcords"), (transparency_lb, "transparency"),
        (tech_check, "techpack"),
        (language_lb, "language"),
    ]

    box_checked()
    root.resizable(0, 0)


def main(argv=None):
    load_settings()
    args = parse_args(argv)
    if args.debug:
        ## let an unsupported block raise instead of being collected into
        ## the skipped list, and turn on the lookup tracing
        structura_core.debug = True
        armor_stand_geo_class.debug = True
    if args.update:
        update()
    if args.structure and args.pack_name:
        run_cli(args)
        return
    build_gui()
    root.mainloop()


if __name__ == "__main__":
    main()
