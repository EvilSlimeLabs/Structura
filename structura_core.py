import json
import os
import shutil
import tempfile
import time
from shutil import copyfile

import nbtlib.nbt

import animation_class
import armor_stand_class
import armor_stand_geo_class as asgc
import big_render_controller as brc
import manifest
import render_controller_class as rcc
import structure_reader
import tech_pack

debug=False

class UnsupportedBlock:
    """
    Holds all the properties of an unsupported block.
    Can be compared to filter.
    """
    def __init__(self, pos: tuple[int, int, int], block: nbtlib.nbt.Compound, variant: str):
        self.pos = pos
        self.block = block
        self.variant = variant

    def __str__(self):
        return "x:{} Y:{} Z:{}, Block:{}, Variant: {}".format(
        self.pos[0], self.pos[1],self.pos[2],
            self.block["name"],
            self.variant
        )
    def __eq__(self, other):
        if not isinstance(other, UnsupportedBlock):
            return NotImplemented
        return self.block["name"] == other.block["name"] and self.variant == other.variant

    def __hash__(self):
        return hash((frozenset(self.block["name"]), self.variant))

with open("lookups/nbt_defs.json") as f:
    nbt_def = json.load(f)
class structura:
    def __init__(self,pack_name):
        ## pack_name names the outputs the user gets; the pack tree itself is
        ## assembled somewhere disposable. Building it in a folder of the
        ## user's choosing meant a run that failed part way left that folder
        ## behind, and the next run with the same name died on makedirs.
        self.timers={"start":time.time(),"previous":time.time()}
        self.pack_name=pack_name
        self.display_name=os.path.basename(pack_name.rstrip("/\\")) or pack_name
        ## a pack name may carry a directory ("tmp/my_pack"); the outputs go
        ## there, so it has to exist even though the tree no longer does
        parent=os.path.dirname(pack_name)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.work_dir=tempfile.mkdtemp(prefix="structura-")
        self.structure_files={}
        self.rc=rcc.render_controller()
        self.armorstand_entity = armor_stand_class.armorstand()
        visual_name=pack_name
        self.animation = animation_class.animations()
        self.exclude_list=["minecraft:{}".format(name) for name in asgc.EXCLUDED_BLOCKS]
        self.opacity=asgc.DEFAULT_ALPHA
        self.longestY=0
        self.unsupported_blocks=[]
        self.all_blocks={}
        self.icon="lookups/pack_icon.png"
        self.dead_blocks={}
        self.tech_pack=False
        self._tech_pack_merged=False
    def cleanup(self):
        """Drop the working tree. Safe to call twice; callers may use it in
        a finally so a failed build leaves nothing behind."""
        if self.work_dir and os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
        self.work_dir=None
    def set_icon(self,icon):
        self.icon=icon
    def set_tech_pack(self,enabled=True):
        """Bundle the Bedrock Technical Resource Pack into this pack.

        Both projects replace the armor stand client entity, and a resource pack
        replaces that file rather than merging with it, so applying Structura
        and TechPack side by side loses whichever sits lower in the player's
        list. Folding TechPack's declarations and assets into the generated pack
        is the only arrangement that runs both. Raises when the submodule is not
        checked out, rather than quietly producing a pack without it."""
        if enabled and not tech_pack.available():
            raise FileNotFoundError(
                "be_tech_pack is not available; run "
                "'git submodule update --init be_tech_pack'")
        self.tech_pack=bool(enabled)
    def _apply_tech_pack(self):
        """Merge TechPack into the armor stand before it is exported.

        The entity file is rewritten once per model, so this guards itself
        rather than relying on the merge being harmless to repeat."""
        if self.tech_pack and not self._tech_pack_merged:
            self.armorstand_entity.merge_description(tech_pack.description())
            self._tech_pack_merged=True
    def set_opacity(self,opacity):
        ## an alpha fraction, not a slider position. Out of range values used
        ## to reach the uint8 alpha multiply and wrap around, which looked
        ## like a working control with a sawtooth response.
        self.opacity=min(max(float(opacity),0.0),1.0)
    def add_model(self,name,file_name):
        self.structure_files[name]={}
        self.structure_files[name]["file"]=file_name
        self.structure_files[name]["offsets"]=None
    def set_model_offset(self,name,offset):
        self.structure_files[name]["offsets"]=offset
    def generate_nametag_file(self):
        ## temp folder would be a good idea
        name_tags=self.structure_files.keys()
        fileName="{} Nametags.txt".format(self.pack_name)
        with open(fileName,"w+") as text_file:
            text_file.write("These are the nametags used in this file\n")
            for name in name_tags:
                text_file.write("{}\n".format(name))
    def make_big_model(self,offset):
        self.rc=brc.render_controller()
        file_names=[]
        for name in list(self.structure_files.keys()):
            file_names.append(self.structure_files[name]["file"])
        struct2make=structure_reader.combined_structures(file_names,exclude_list=self.exclude_list)
        self.structure_files[""]={}
        self.structure_files[""]["offsets"]=[0,0,0]
        self.structure_files[""]["offsets"][1]= 0
        layers=12
        if (struct2make.get_size()[1]<=12):
            layers=struct2make.get_size()[1]
        for i in range(layers):
            self.armorstand_entity.add_model(str(i))
            self.rc.add_geometry(str(i))
        self.armorstand_entity.add_scale()#scale animation was removed from normal build this needs to be added back for big builds
        self.big_offset=offset
        self.all_blocks=self._add_blocks_to_geo(struct2make,"",export_big=True)
        self._apply_tech_pack()
        self.armorstand_entity.export(self.work_dir)
    def generate_with_nametags(self):
        update_animation=True
        for model_name in self.structure_files.keys():
            if self.structure_files[model_name]["offsets"] is None:
                self.structure_files[model_name]["offsets"]=[0,0,0]
            self.rc.add_model(model_name)
            self.armorstand_entity.add_model(model_name)
            if debug:
                print(self.structure_files[model_name]['offsets'])
            struct2make = structure_reader.process_structure(self.structure_files[model_name]["file"])
            blocks=self._add_blocks_to_geo(struct2make,model_name)
            self.structure_files[model_name]["block_list"]=blocks
            ##consider temp folder
            self._apply_tech_pack()
            self.armorstand_entity.export(self.work_dir)## this may be in the wrong spot, but transferred from 1.5
        
    def make_nametag_block_lists(self):
        ## consider temp file
        file_names=[]
        for model_name in self.structure_files.keys():
            file_name="{}-{} block list.txt".format(self.pack_name,model_name)
            file_names.append(file_name)
            all_blocks = self.structure_files[model_name]["block_list"]
            with open(file_name,"w+") as text_file:
                text_file.write("This is a list of blocks, there is a known issue with variants, all blocks are reported as minecraft stores them\n")
                for name in all_blocks.keys():
                    commonName = name.replace("minecraft:","")
                    text_file.write("{}: {}\n".format(commonName,all_blocks[name]))

                text_file.write("_"*10 + "\n")
                text_file.write("Lookup version: {}\n".format(self.get_lookup_version()))
        return file_names
    def make_big_blocklist(self):
        ## consider temp file
        file_name="{} block list.txt".format(self.pack_name)
        with open(file_name,"w+") as text_file:
            text_file.write("This is a list of blocks, there is a known issue with variants, all blocks are reported as minecraft stores them\n")
            for name in self.all_blocks.keys():
                commonName = name.replace("minecraft:","")
                
                text_file.write("{}: {}\n".format(commonName,self.all_blocks[name]))

    def _add_blocks_to_geo(self,struct2make,model_name,export_big=False):
        [xlen, ylen, zlen] = struct2make.get_size()
        if export_big:
            self.structure_files[model_name]['offsets'][0]-=xlen.item()+7
            self.structure_files[model_name]['offsets'][2]-=zlen.item()+7
        armorstand = asgc.armorstandgeo(model_name,alpha = self.opacity, size=[xlen, ylen, zlen], offsets=self.structure_files[model_name]['offsets'])

        ## the animation only needs the layers of the tallest model; a
        ## shorter one that follows needs a subset of what is already there
        if ylen > self.longestY:
            update_animation=True
            self.longestY = ylen
        else:
            update_animation=False
        for y in range(ylen):
            
            #creates the layer for controlling. Note there is implied formatting here
            #for layer names
            if y<12:
                armorstand.make_layer(y)
                #adds links the layer name to an animation
                if update_animation and not export_big:
                    self.animation.insert_layer(y)
            non_air=struct2make.get_layer_blocks(y)
            for loc in non_air:
                x=int(loc[0])
                z=int(loc[1])
                block = struct2make.get_block(x, y, z)
                blk_name=block["name"].replace("minecraft:", "")
                blockProp=self._process_block(block)
                rot = blockProp[0]
                top = blockProp[1]
                variant = blockProp[2]
                open_bit = blockProp[3]
                data = blockProp[4]
                if debug:
                    armorstand.make_block(x, y, z, blk_name, rot = rot, top = top,variant = variant, trap_open=open_bit, data=data, big = export_big)
                else:
                    try:
                        armorstand.make_block(x, y, z, blk_name, rot = rot, top = top,variant = variant, trap_open=open_bit, data=data, big = export_big)
                    except Exception as e:
                        unsupported = UnsupportedBlock((x,y,z), block, variant)
                        self.unsupported_blocks.append(unsupported)
                        if block["name"] not in self.dead_blocks.keys():
                            self.dead_blocks[block["name"]]={}
                        if type(variant) is list:
                            variant="_".join(variant)
                        if variant not in self.dead_blocks[block["name"]].keys():
                            self.dead_blocks[block["name"]][variant]=0
                        self.dead_blocks[block["name"]][variant]+=1
            ## consider temp file
        if export_big:
            armorstand.export_big(self.work_dir)
            self.animation.export_big(self.work_dir,self.big_offset)
        else:
            armorstand.export(self.work_dir)
            self.animation.export(self.work_dir)
        return struct2make.get_block_list()
    def compile_pack(self, overwrite=False):
        ## consider temp file
        nametags=list(self.structure_files.keys())
        if len(nametags)>1:
            manifest.export(self.work_dir,self.display_name,nameTags=nametags)
        else:
            manifest.export(self.work_dir,self.display_name)
        copyfile(self.icon, f"{self.work_dir}/pack_icon.png")
        larger_render = "lookups/armor_stand.larger_render.geo.json"
        larger_render_path = f"{self.work_dir}/models/entity/armor_stand.larger_render.geo.json"
        os.makedirs(os.path.dirname(larger_render_path), exist_ok=True)
        copyfile(larger_render, larger_render_path)
        self.rc.export(self.work_dir)
        ## after Structura's own files, so a name both projects use keeps
        ## Structura's copy and the collision is reported rather than silent
        if self.tech_pack:
            written,skipped=tech_pack.copy_assets(self.work_dir)
            if debug:
                print("TechPack {}: {} files, {} skipped".format(
                    tech_pack.version(),written,len(skipped)))
        shutil.make_archive("{}".format(self.pack_name), 'zip', self.work_dir)
        if overwrite and os.path.isfile(f'{self.pack_name}.mcpack'):
            os.remove(f'{self.pack_name}.mcpack')
        os.rename(f'{self.pack_name}.zip',f'{self.pack_name}.mcpack')
        self.cleanup()
        self.timers["finished"]=time.time()-self.timers["previous"]
        self.timers["total"]=time.time()-self.timers["start"]

        
        return f'{self.pack_name}.mcpack'
    def _process_block(self,block):
        rot = None
        top = False
        open_bit = False
        data=0
        variant="default"
        for key in nbt_def.keys():
            if nbt_def[key]== "variant" and key in block["states"].keys():
                variant = [key,block["states"][key]]
            if nbt_def[key] == "rot" and key in block["states"].keys():
                try:
                    rot = int(block["states"][key])
                except (TypeError, ValueError):
                    rot = str(block["states"][key])
                
            if nbt_def[key]== "top" and key in block["states"].keys():
                top_state = block["states"][key]
                if key == "minecraft:vertical_half":
                    top = str(top_state).lower() == "top"
                else:
                    top = bool(top_state)
            if nbt_def[key]== "open_bit" and "open_bit" in block["states"].keys():
                open_bit = bool(block["states"][key])
            if nbt_def[key]== "data" and key in block["states"].keys():
                data = int(block["states"][key])
            if key == "rail_direction" and key in block["states"].keys():
                data = str(block["states"][key].as_unsigned)
                if "rail_data_bit" in block["states"].keys():
                    data += "-"+str(block["states"]["rail_data_bit"].as_unsigned)

        if "wood_type" in block["states"].keys():
            variant = ["wood_type",block["states"]["wood_type"]]
            if block["name"] == "minecraft:wood":
                keys = block["states"]["wood_type"]
                if bool(block["states"]["stripped_bit"]):
                    keys+="_stripped"
                variant = ["wood",keys]
        return [rot, top, variant, open_bit, data]
    def get_nametags(self):
        """The name tags in this pack, in the order they were added."""
        return list(self.structure_files.keys())
    def get_block_lists(self):
        """{name tag: {block: count}} for every model, as data rather than as
        the text files make_nametag_block_lists writes. Populated by
        generate_with_nametags."""
        return {name: dict(info["block_list"])
                for name, info in self.structure_files.items()
                if "block_list" in info}
    def get_material_list(self):
        """Every block the finished pack needs and how many, summed over all
        models. A big build reports the combined total it already holds."""
        if self.all_blocks:
            return dict(self.all_blocks)
        totals={}
        for blocks in self.get_block_lists().values():
            for block, count in blocks.items():
                totals[block]=totals.get(block,0)+count
        return totals
    def get_skipped(self, write_file=True):
        """{block: {variant: count}} for everything that could not be built.
        write_file also drops a "<pack> skipped.txt" beside the pack; a caller
        that only wants the data should pass False."""
        if write_file and len(self.unsupported_blocks)>0:
            fileName="{} skipped.txt".format(self.pack_name)
            with open(fileName,"w+") as text_file:
                text_file.write("These are the skipped blocks\n")
                for skipped in self.unsupported_blocks:
                    text_file.write(f"{skipped}\n")
        return self.dead_blocks

    def get_unique_blocks_count(self):
        count = 0
        if self.structure_files:
            for k, v in self.structure_files.items():
                count += len(list(v["block_list"].keys()))

        return count

    def get_lookup_version(self) -> str:
        """
        Get the version from lookup_version.json.
        :return:
        """
        look_up_path = os.path.join("lookups", "lookup_version.json")
        if os.path.isfile(look_up_path):
            with open(look_up_path) as file:
                version_data = json.load(file)
                return version_data["version"]
        return "No version found"
