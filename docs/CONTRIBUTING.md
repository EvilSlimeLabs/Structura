# Contributing
Thank you for being interested in contributing. Structura is a program that can be used in several ways and there are a few things you should understand before Contributing. 

## Use Cases

### Desktop Application
Structura was originally only a desktop application, this comes with some baggage and some down sides. But support for using it with the gui needs to remain in place. To make this easier, the application was pulled out of the gui and mostly lives in "structura_core.py" the structura.py file is just a wrapper/gui.

### Hosted use
`structura_core.py` is the API any front end uses, including a hosted one. A service that runs Structura for other people belongs in its own project that imports this one; nothing here should know about a queue, a bucket, a bot or a user account. An earlier attempt at that lived in this repository as `lambda_function.py` and has been removed.

Two rules keep the core usable that way, and a pull request that breaks either cannot be merged:

- **Do not write outside the working directory or the caller's chosen output path.** Serverless hosts give you a read-only file system with only `/tmp` writable. The pack tree is assembled in a temporary directory, and the only things written where the caller asked are the `.mcpack` and its side reports.
- **Everything the core produces must be available as data, not only as a file.** `get_material_list()`, `get_block_lists()`, `get_nametags()` and `get_skipped(write_file=False)` exist because a service wants values, not text files it then has to read back.

#### Structura CLI
The CLI was added by contributors that wanted to make their own web services. This is allowed. Structura is MIT licensed and anyone can do anything with Structura. This CLI is kept in but not highly tested (unless someone wants to take that on.

## Blocks Definitions
Minecraft is a giant mess when it comes to naming, versioning, and block definitions. But because Structura dates back to 2020 and posted files still reference old block names, we need to be careful when updating blocks. In 2020 an effort was made to remove all hard coded block definitions. At this point, blocks are defined in 2 locations. Vanilla_Resource_pack, where the textures and texture locations are saved in a similar way to the default texture pack from Minecraft, and in lookups, where all the block geometry and nbt is defined.

### Editing Vanilla_Resource_pack 
When adding new blocks, do not remove old block definitions. Due to the project Mojang ran between 2020 and 2024 renaming all the blocks, old structures will be broken if the terrain_texture.json and blocks.json is simply copied from the new version. Instead, the old and new terrain textures must be merged. This is a bit painful, but it is what it is.

### Adding Geometry
In 2025 when Vibrant Visuals was added, the CPU cost of rendering a bone became 50-100x more expensive. For that reason, when making new geometries, we need to be respectful of cube count. Excessive use of cubes will cause excessive lag.

### Adding Blocks to all_blocks world.
When adding blocks it is helpful to add them to the all_blocks world so they can at least get tested each update. This helps when we need to do a big refactor. Simply add the block to the world where it makes the most sense. Add every block state you can to help in the future. Then remove all packs. (may need to manually removed them if they were attached to the world) and export the world and add it back into the git repo.

# Recognition
In the beginning I added the first 2 people who contributed to the manifest.json of every pack. If you stick around and help for more than a few months, I may choose to do that in the future. If you fix things you will get credit in the release notes and likely in a video covering that release.
