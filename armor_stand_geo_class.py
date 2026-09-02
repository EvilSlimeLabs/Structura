try:
    import ujson as json
except ImportError:
    print("using built in json, but that is much slower, consider installing ujson")
    import json
from PIL import Image
from numpy import array, ones, uint8, zeros
from operator import add
import copy
import os
import time
import re

import paths
debug = False##used in API test to force errors and break error handler, should remain false.

## Blocks that never become geometry. structura_core needs the same list in the
## namespaced form the structure files store it, so it derives it from here
## rather than keeping a second copy.
EXCLUDED_BLOCKS = ("air", "structure_block")

## Alpha the ghost blocks are drawn at when nothing sets one. The texture's
## alpha channel is multiplied by this, so it is a fraction, not a percentage.
## It is the counterpart of app_settings.DEFAULT_TRANSPARENCY: a caller that
## sets nothing has to get the same ghost block the slider's default gives, and
## a test asserts the two stay in step.
DEFAULT_ALPHA = 0.35

class armorstandgeo:
    def __init__(self, name, alpha = DEFAULT_ALPHA,offsets=None, size=[64, 64, 64], ref_pack=None):
        self.ref_resource_pack = ref_pack or paths.vanilla_pack()
        ## we load all of these items containing the mapping of blocks to some property that is either hidden, implied or just not clear
        with open("{}/blocks.json".format(self.ref_resource_pack)) as f:
            ## defines the blocks from the NBT name tells us sides vs textures
            self.blocks_def = json.load(f)
        with open("{}/textures/terrain_texture.json".format(self.ref_resource_pack)) as f:
            ##maps textures names to texture files.
            self.terrain_texture = json.load(f)
        with open(paths.lookup("block_rotation.json")) as f:
            ## custom look up table i wrote to help with rotations, error messages dump if something has undefined rotations 
            self.block_rotations = json.load(f)
        with open(paths.lookup("variants.json")) as f:
            ## custom lookup table mapping the assumed array location in the terrain texture to the relevant blocks IE log2 index 2 implies a specific wood type not captured anywhere
            self.block_variants = json.load(f)
        with open(paths.lookup("block_definition.json")) as f:
            self.defs = json.load(f)
        with open(paths.lookup("block_shapes.json")) as f:
            self.block_shapes = json.load(f)
        with open(paths.lookup("block_uv.json")) as f:
            self.block_uv = json.load(f)
        self.name = name.replace(" ","_").lower()
        self.stand = {}
        ## a copy, because the half-block shift below is applied in place and
        ## the caller keeps using the list it passed in
        self.offsets = [0, 0, 0] if offsets is None else list(offsets)
        self.offsets[0] += 0.5
        self.offsets[2] -= 0.5
        self.alpha=alpha
        self.texture_list = []
        self.geometry = {}
        self.stand_init()
        self.uv_map = {}
        self.blocks = {}
        self.size = size
        self.bones = []
        self.errors={}
        self.layers=[]
        self.uv_array = None
        self.pre_gen_blocks={}
        self.excluded = EXCLUDED_BLOCKS

    def export(self, pack_folder):
        start = time.time()
        ## This exporter just packs up the armorstand json files and dumps them where it should go. as well as exports the UV file
        self.add_blocks_to_bones()
        self.geometry["description"]["texture_height"] = len(
            self.uv_map.keys())
        self.stand["minecraft:geometry"] = [self.geometry] ## this is insuring the geometries are imported, there is an implied reference other places.
        path_to_geo = "{}/models/entity/armor_stand.ghost_blocks_{}.geo.json".format(
            pack_folder,self.name)
        os.makedirs(os.path.dirname(path_to_geo), exist_ok=True)
        i=0
        
        for index in range(len(self.stand["minecraft:geometry"][0]["bones"])):
            if "name" not in self.stand["minecraft:geometry"][0]["bones"][index].keys():
                self.stand["minecraft:geometry"][0]["bones"][index]["name"]="empty_row+{}".format(i)
                self.stand["minecraft:geometry"][0]["bones"][index]["parent"]="ghost_blocks"
                self.stand["minecraft:geometry"][0]["bones"][index]["pivot"]=[0.5,0.5,0.5]
                i+=1
        start=time.time()
        with open(path_to_geo, "w+") as json_file:
            json.dump(self.stand, json_file)
        texture_name = "{}/textures/entity/ghost_blocks_{}.png".format(
            pack_folder,self.name)
        os.makedirs(os.path.dirname(texture_name), exist_ok=True)
        self.save_uv(texture_name)
        
    def export_big(self, pack_folder):
        ## This exporter just packs up the armorstand json files and dumps them where it should go. as well as exports the UV file
        self.stand["minecraft:geometry"] = []
        size=list(map(int,self.size))
        #offset=[-size[0]//2,0,-size[2]//2]
        geometries={}
        geometries["default"]={}
        geometries["default"]["description"]={}
        geometries["default"]["description"]["identifier"] = "geometry.armor_stand.default"
        geometries["default"]["description"]["texture_width"] = 1
        geometries["default"]["description"]["texture_height"] = 1
        geometries["default"]["description"]["visible_bounds_width"] = 5120
        geometries["default"]["description"]["visible_bounds_height"] = 5120
        geometries["default"]["description"]["visible_bounds_offset"] = [0, 1.5, 0]     
        geometries["default"]["bones"]=[{"name":"ghost_blocks","pivot": [-8, 0, 8],"origin":[0,0,0]}]
        default_geo=[{"size": size,
                        "uv": {
                                "north": {"uv": [0, 0], "uv_size": [1, 1]},
                                "east": {"uv": [0, 0], "uv_size": [1, 1]},
                                "south": {"uv": [0, 0], "uv_size": [1, 1]},
                                "west": {"uv": [0, 0], "uv_size": [1, 1]},
                                "up": {"uv": [1, 1], "uv_size": [-1, -1]},
                                "down": {"uv": [1, 1], "uv_size": [-1, -1]}
                        }},
                     {
                        "size": size,
                        "uv": {
                                "north": {"uv": [0, 3], "uv_size": [1, -1]},
                                "east": {"uv": [0, 3], "uv_size": [1, -1]},
                                "south": {"uv": [0, 3], "uv_size": [1, -1]},
                                "west": {"uv": [0, 3], "uv_size": [1, -1]},
                                "up": {"uv": [0, 1], "uv_size": [1, -1]},
                                "down": {"uv": [0, 3], "uv_size": [1, -1]}
                        }}]
        geometries["default"]["bones"][0]["cubes"]=default_geo
        for i in range(len(self.layers)):
            layer_name=self.layers[i]
            geometries[layer_name] = {}
            geometries[layer_name]["description"] = {}
            geometries[layer_name]["description"]["identifier"] = "geometry.armor_stand.ghost_blocks_{}".format(i)
            geometries[layer_name]["description"]["texture_width"] = 1
            geometries[layer_name]["description"]["texture_height"] = len(self.uv_map.keys())
            geometries[layer_name]["description"]["visible_bounds_width"] = 5120
            geometries[layer_name]["description"]["visible_bounds_height"] = 5120
            geometries[layer_name]["description"]["visible_bounds_offset"] = [0, 1.5, 0]
            geometries[layer_name]["bones"]=[{"name": "ghost_blocks","pivot": [0, 0, 0]},## I am not sure this should be this value for pivot
                                             {"name": layer_name,"parent": "ghost_blocks","pivot": [0, 0, 0]}]## I am not sure this should be this value for pivot
        
        for key in self.blocks.keys():
            layer_name = self.blocks[key]["parent"]
            if layer_name in geometries.keys():
                geometries[layer_name]["bones"].append(self.blocks[key])
        self.stand["minecraft:geometry"].append(geometries["default"])
        for layer_name in self.layers:
            self.stand["minecraft:geometry"].append(geometries[layer_name])
            
        path_to_geo = "{}/models/entity/armor_stand.ghost_blocks_{}.geo.json".format(pack_folder,self.name)
        os.makedirs(os.path.dirname(path_to_geo), exist_ok=True)            
        with open(path_to_geo, "w+") as json_file:
            json.dump(self.stand, json_file, indent=2)
        
        
        ## Every layer gets its own texture file even though they are identical:
        ## make_big_model declares one texture short name per layer on the armor
        ## stand entity, and a declared texture that resolves to nothing is a
        ## content-log error.
        for i in range(len(self.layers)):
            texture_name = "{}/textures/entity/ghost_blocks_{}.png".format(pack_folder,i)
            os.makedirs(os.path.dirname(texture_name), exist_ok=True)
            self.save_uv(texture_name)

    
    def make_layer(self, y):
        # sets up a layer for us to reference in the animation controller later. Layers are moved during the poses 
        layer_name = "layer_{}".format(y)
        self.geometry["bones"].append(
            {"name": layer_name, "parent": "ghost_blocks"})#, "pivot": [-8, 0, 8]})

    def make_block(self, x, y, z, block_name, rot=None, top=False,data=0, trap_open=False, parent=None,variant="default", big = False, hinge=False):
        # make_block handles all the block processing, This function does need cleanup and probably should be broken into other helperfunctions for legibility.
        block_type = self.defs[block_name]
        if block_type!="ignore":
            slice_name = "slice_{}".format(y)
            ghost_block_coordinates = "block_{}_{}_{}".format(x, y, z)
            temp_block_group = {}
            temp_block_group["name"] = slice_name
            
            layer_name = "layer_{}".format(y % (12))
            if layer_name not in self.layers:
                self.layers.append(layer_name)
            
            temp_block_group["parent"] = layer_name
            block_type = self.defs[block_name]
            
            ## Settle on one variant name, then read both tables with it. The
            ## shape and the UV window describe the same cubes, so reading them
            ## with different names is how a half-height cube ends up wearing a
            ## full-height texture.
            shape_variant="default"
            if block_type == "hopper" and rot is not None and rot != 0:
                shape_variant="side"
            elif block_type == "door" and trap_open:
                ## a door that is standing open is a different shape, not the
                ## closed one turned: open_bit was being read and thrown away,
                ## so every open door was drawn shut. Which way it swings is the
                ## hinge, which decides which side of the frame it folds back
                ## against -- two doors of one facing and opposite hinges open
                ## into different blocks.
                shape_variant = "open_hinged" if hinge else "open"
            elif block_type == "trapdoor" and trap_open:
                shape_variant = "open"
            elif block_type == "lever" and trap_open:
                shape_variant = "on"
            elif top:
                shape_variant = "top"

            ## a numeric state - snow depth, repeater delay, sea pickle count -
            ## names its own variant and outranks the flags above
            if str(data) in self.block_shapes[block_type] or str(data) in self.block_uv[block_type]:
                shape_variant = str(data)

            ## a shape family that does not describe this variant falls back to
            ## its default rather than raising, which would drop the block into
            ## the skipped list. A double slab has a vertical_half state it does
            ## not use, and used to disappear whenever that state read "top".
            if shape_variant not in self.block_shapes[block_type]:
                shape_variant = "default"

            if data!=0 and debug:
                print(data)

            block_shapes = self.block_shapes[block_type][shape_variant]
            block_uv = self.block_uv[block_type].get(shape_variant,
                                                     self.block_uv[block_type]["default"])

            temp_block_group["pivot"] = [ block_shapes["center"][0] - (x + self.offsets[0]) \
                                        , block_shapes["center"][1] +  y + self.offsets[1]  \
                                        , block_shapes["center"][2] +  z + self.offsets[2] ]
            #temp_block_group["inflate"] = -0.03

            ## a rotation table that does not describe this state leaves the
            ## block unrotated rather than raising. The tables are keyed by the
            ## state's value, and a family can carry a rotation state it has no
            ## entry for -- soul_campfire reads direction 0 against a table that
            ## only listed 1, and the block was dropped every time it faced that
            ## way.
            rotation = None
            if block_type in self.block_rotations.keys() and rot is not None:
                rotation = self.block_rotations[block_type].get(str(rot))
                if rotation is None and debug:
                    print("no rotation {} for block type {}".format(rot, block_type))
            if rotation is not None:
                temp_block_group["rotation"] = copy.deepcopy(rotation)
                if big:
                    temp_block_group["rotation"][1] += 180
            elif debug:
                print("no rotation for block type {} found".format(block_type))
            temp_block_group["cubes"] = []
            uv_idx = 0
            
            
            for i in range(len(block_shapes["size"])):
                uv = self.block_name_to_uv(block_name,variant=variant,shape_variant=shape_variant,index=i)
                block={}
                if len(block_uv["uv_sizes"]["up"])>i:
                    uv_idx=i
                xoff = 0
                yoff = 0
                zoff = 0
                if "offsets" in block_shapes.keys():
                    xoff = block_shapes["offsets"][i][0]
                    yoff = block_shapes["offsets"][i][1]
                    zoff = block_shapes["offsets"][i][2]
                block["origin"] = [-1*(x + self.offsets[0]) + xoff, y + yoff + self.offsets[1], z + zoff + self.offsets[2]]
                block["size"] = block_shapes["size"][i]

                if "rotation" in block_shapes.keys():
                    block["rotation"] = block_shapes["rotation"][i]
                    

                blockUV=dict(uv)
                for dir in ["up", "down", "east", "west", "north", "south"]:
                    blockUV[dir]["uv"][0] += block_uv["offset"][dir][uv_idx][0]
                    blockUV[dir]["uv"][1] += block_uv["offset"][dir][uv_idx][1]
                    blockUV[dir]["uv_size"] = block_uv["uv_sizes"][dir][uv_idx]
                
                block["uv"] = blockUV
                temp_block_group["cubes"].append(block)
            ## next i
            
            for eachGroup in [ temp_block_group ]:
                hasNestedRotation = 0
                copiedGroups = []

                isRotatedGroup = ( "rotation" in eachGroup.keys() ) and ( "pivot" in eachGroup.keys() )
                if( isRotatedGroup and ( eachGroup["rotation"] is None or len( eachGroup["rotation"] ) != 3 ) ):
                    isRotatedGroup = False
                if( isRotatedGroup and ( eachGroup["pivot"]    is None or len( eachGroup["pivot"] ) != 3 ) ):
                    isRotatedGroup = False
                
                for eachCube in temp_block_group["cubes"]:
                    isCubeReadyToWrite = False
                    
                    isRotatedCube = ( "rotation" in eachCube.keys() ) and ( "pivot" in eachCube.keys() )
                    if( isRotatedCube and ( eachCube["rotation"] is None or len( eachCube["rotation"] ) != 3 ) ):
                        isRotatedCube = False
                    if( isRotatedCube and ( eachCube["pivot"]    is None or len( eachCube["pivot"] ) != 3 ) ):
                        isRotatedCube = False
                    
                    isOnlyRotatedCube = ( "rotation" in eachCube.keys() )
                    if( isOnlyRotatedCube and ( eachCube["rotation"] is None or len( eachCube["rotation"] ) != 3 ) ):
                        isOnlyRotatedCube = False
                    
                    if( isOnlyRotatedCube ):
                        ## If cube has "rotation" but is missing "pivot" point,  instead use center of the cube
                        ##    "https://learn.microsoft.com/en-us/minecraft/creator/reference/content/schemasreference/schemas/minecraftschema_geometry_1.16.0?view=minecraft-bedrock-stable#:~:text=%2F%2F%20If%20this%20field%20is%20specified%2C%20rotation%20of%20this%20cube%20occurs%20around%20this%20point%2C%20otherwise%20its%20rotation%20is%20around%20the%20center%20of%20the%20box%2E"
                        eachCube["pivot"] = [ eachCube["origin"][0] + eachCube["size"][0] / 2.0 \
                                            , eachCube["origin"][1] + eachCube["size"][1] / 2.0 \
                                            , eachCube["origin"][2] + eachCube["size"][2] / 2.0 ]
                        isRotatedCube = True
                    
                    
                    if( not(isRotatedCube) and isRotatedGroup ):
                        ## Apply group's "rotation" and "pivot" to cube
                        eachCube["rotation"] = [ eachGroup["rotation"][0], eachGroup["rotation"][1], eachGroup["rotation"][2] ]
                        eachCube["pivot"]    = [ eachGroup["pivot"   ][0], eachGroup["pivot"   ][1], eachGroup["pivot"   ][2] ]
                    #elif( not(isRotatedGroup) and isRotatedCube ):
                        ## Keep existing cube "rotation" and "pivot"
                    elif( isRotatedGroup and isRotatedCube and  eachCube["pivot"] == eachGroup["pivot"] ):
                        ## Same "pivot" point...  Matrix-Sum cube and group "rotation" value arrays
                        eachCube["rotation"] = [ eachGroup["rotation"][0] + eachCube["rotation"][0], eachGroup["rotation"][1] + eachCube["rotation"][1], eachGroup["rotation"][2] + eachCube["rotation"][2] ]
                    elif( isRotatedGroup and isRotatedCube ):
                        #TODO: Merge cube rotation with group rotation,  around cube's ["pivot"] point...  not a lot of fun math
                        hasNestedRotation += 1
                        newGroup =  { "parent": eachGroup["name"], "name": eachGroup["name"] + "___" + ghost_block_coordinates + "___" + str(hasNestedRotation) }
                        
                        for primitiveKey in [ "mirror", "inflate", "debug", "render_group_id", "binding" ]:
                            if primitiveKey in eachGroup.keys():
                                newGroup[primitiveKey] = eachGroup[primitiveKey]
                        
                        for objectKey in [ "pivot", "rotation", "locators", "poly_mesh", "texture_meshes" ]:
                            if objectKey in eachGroup.keys():
                                newGroup[objectKey] = copy.deepcopy( eachGroup[objectKey] )
                        
                        newGroup["cubes"] = []
                        newGroup["cubes"].append( copy.deepcopy( eachCube ) )
                        copiedGroups.append( newGroup )
                        eachCube["flag_unnest_from_group"] = True
                
                ## next eachCube
                
                
                if eachGroup["name"] in self.blocks.keys():
                    for eachCube in temp_block_group["cubes"]:
                        if( hasNestedRotation == 0 or ( ( "flag_unnest_from_group" not in eachCube.keys() ) and ( eachCube["flag_unnest_from_group"] != True ) ) ):
                            #TOCONSIDER: Git rid of unnecessary deepcopies
                            self.blocks[eachGroup["name"]]["cubes"].append( copy.deepcopy(eachCube) )
                else:
                    if "rotation" in eachGroup.keys():
                        del eachGroup["rotation"]
                    if "pivot" in eachGroup.keys():
                        del eachGroup["pivot"]
                    #TOCONSIDER: Git rid of unnecessary deepcopies
                    self.blocks[eachGroup["name"]] = copy.deepcopy( eachGroup )
                
                for newChildGroup in copiedGroups:
                    #TOCONSIDER: Git rid of unnecessary deepcopies
                    self.blocks[newChildGroup["name"]] = copy.deepcopy( newChildGroup )
            
            ## next eachGroup


    def save_uv(self, name):
        # saves the texture file where you tell it to
        if self.uv_array is None:
            print("No Blocks Were found")
        else:
            im = Image.fromarray(self.uv_array)
            im.save(name)

    def stand_init(self):
        # helper function to initialize the dictionary that will be exported as the json object
        self.stand["format_version"] = "1.16.0"
        self.geometry["description"] = {
            "identifier": "geometry.armor_stand.ghost_blocks_{}".format(self.name)}
        self.geometry["description"]["texture_width"] = 1
        self.geometry["description"]["visible_bounds_offset"] = [
            0.0, 1.5, 0.0]
        # Changed render distance of the block geometry
        self.geometry["description"]["visible_bounds_width"] = 5120
        # Changed render distance of the block geometry
        self.geometry["description"]["visible_bounds_height"] = 5120
        self.geometry["bones"] = []
        self.stand["minecraft:geometry"] = [self.geometry]
        self.geometry["bones"] = [
                                    {"name": "ghost_blocks",
                                     "pivot": [-8, 0, 8]}]

    def extend_uv_image(self, new_image_filename):
        # helper function that just appends to the uv array to make things

        # Fallback to a tga
        if not os.path.isfile(new_image_filename):
            new_image_filename = new_image_filename.split(".")[0] + ".tga"

        image = Image.open(new_image_filename).convert("RGBA")
        impt = array(image)
        shape=list(impt.shape)
        if shape[0]>16:
            shape[0]=16
            impt=impt[0:16,:,:]
        if shape[1]>16:
            shape[1]=16
            impt=impt[:,0:16,:]
        image_array = ones([16, 16, 4],uint8)*255
        image_array[0:shape[0], 0:shape[1], 0:impt.shape[2]] = impt
        image_array[:, :, 3] = image_array[:, :, 3] * self.alpha
        if type(self.uv_array) is type(None):
            self.uv_array = image_array
        else:
            startshape = list(self.uv_array.shape)
            endshape = startshape.copy()
            endshape[0] += image_array.shape[0]
            temp_new = zeros(endshape, uint8)
            temp_new[0:startshape[0], :, :] = self.uv_array
            temp_new[startshape[0]:, :, :] = image_array
            self.uv_array = temp_new

    def block_name_to_uv(self, block_name, variant = "",shape_variant="default",index=0,data=0):
        
        # helper function maps the section of the uv file to the side of the block
        temp_uv = {}
        if block_name not in self.excluded:  # if you dont want a block to be rendered, exclude the UV

            block_type = self.defs[block_name]
            
            texture_files = self.get_block_texture_paths(block_name, variant = variant)

            corrected_textures={}
            if shape_variant in self.block_uv[block_type].keys():
                if "overwrite" in self.block_uv[block_type][shape_variant].keys():
                    corrected_textures = self.block_uv[block_type][shape_variant]["overwrite"]
            else:
                if "overwrite" in self.block_uv[block_type]["default"].keys():
                    corrected_textures = self.block_uv[block_type]["default"]["overwrite"]
            
            ## An overwrite entry names the texture a particular cube of a
            ## particular face should use. A literal path is used as given; a
            ## value written "@up", "@down" or "@north" means "the texture this
            ## block already declares for that face", which is how one family
            ## can put a different texture on each part of a multi-part model
            ## without knowing any block's texture names. A door is the reason:
            ## every door declares its lower half on "down" and its upper half
            ## on "side", and the model is two stacked cubes.
            declared = dict(texture_files)
            for side in corrected_textures.keys():
                if len(corrected_textures[side])>index:
                    chosen = corrected_textures[side][index]
                    if chosen == "default":
                        continue
                    if isinstance(chosen, str) and chosen.startswith("@"):
                        chosen = declared.get(chosen[1:])
                        if chosen is None:
                            continue
                    texture_files[side]=chosen
                    if debug:
                        print("{}: {}".format(side,texture_files[side]))
            for key in texture_files.keys():
                if texture_files[key] not in self.uv_map.keys():
                    try:
                        self.extend_uv_image(
                            "{}/{}.png".format(self.ref_resource_pack, texture_files[key]))
                        self.uv_map[texture_files[key]] = len(self.uv_map.keys())
                    except Exception as e:
                        raise RuntimeError("Failed to load texture {}".format(texture_files[key]))
                temp_uv[key] = {
                    "uv": [0, self.uv_map[texture_files[key]]], "uv_size": [1, 1]}

        return temp_uv

    def add_blocks_to_bones(self):
        # helper function for adding all of the bars, this is called during the writing step
        for key in self.blocks.keys():
            #TODO: add merging logic for slice group
            self.geometry["bones"].append(self.blocks[key])

    def get_block_texture_paths(self, blockName, variant = ""):
        # helper function for getting the texture locations from the vanilla files.
        textureLayout = self.blocks_def[blockName]["textures"]
        texturedata = self.terrain_texture["texture_data"]
        textures = {}

        if type(textureLayout) is dict:
            if "side" in textureLayout.keys():
                textures["east"] = textureLayout["side"]
                textures["west"] = textureLayout["side"]
                textures["north"] = textureLayout["side"]
                textures["south"] = textureLayout["side"]
            if "east" in textureLayout.keys():
                textures["east"] = textureLayout["east"]
            if "west" in textureLayout.keys():
                textures["west"] = textureLayout["west"]
            if "north" in textureLayout.keys():
                textures["north"] = textureLayout["north"]
            if "south" in textureLayout.keys():
                textures["south"] = textureLayout["south"]
            if "down" in textureLayout.keys():
                textures["down"] = textureLayout["down"]
            if "up" in textureLayout.keys():
                textures["up"] = textureLayout["up"]
        elif type(textureLayout) is str:
            textures["east"] = textureLayout
            textures["west"] = textureLayout
            textures["north"] = textureLayout
            textures["south"] = textureLayout
            textures["up"] = textureLayout
            textures["down"] = textureLayout
        for key in textures.keys():
            
            if type(texturedata[textures[key]]["textures"]) is str:
                textures[key] = texturedata[textures[key]]["textures"]
            elif type(texturedata[textures[key]]["textures"]) is list:
                index=0
                if variant[0] in self.block_variants.keys():
                    index=self.block_variants[variant[0]][variant[1] ]
                if debug:
                    print(index)
                    print(key)
                    print(texturedata[textures[key]]["textures"])
                    print(texturedata[textures[key]]["textures"][index])
                textures[key] = texturedata[textures[key]]["textures"][index]

            
        return textures
