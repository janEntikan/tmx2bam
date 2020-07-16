import os
import sys
import argparse

import xml.etree.ElementTree as ET

from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath
from panda3d.core import Texture
from panda3d.core import CardMaker
from panda3d.core import SamplerState
from panda3d.core import SequenceNode
from panda3d.core import LineSegs
from panda3d.core import TextNode
from panda3d.core import Loader


def clear_all_tags(nodepath):
    for key in nodepath.get_tag_keys():
        nodepath.clear_tag(key)
    for child in nodepath.get_children():
        clear_all_tags(child)


class Tmx2Bam():
    def __init__(self, input_file, output_file=None, prefabs=""):
        self.dir = os.path.dirname(input_file)
        self.depth = 0
        self.cardmaker = CardMaker("image")
        self.cardmaker.set_frame(-0.5, 0.5, -0.5, 0.5)
        self.linesegs = LineSegs()
        self.textnode = TextNode("text")

        self.tilesheets = []    # Every tsx file loaded.
        self.tiles = {}         # Every unique tile/card.
        self.node = NodePath("tmx_root")

        # load prefab models
        self.prefabs = {}
        if prefabs:
            loader = Loader.get_global_ptr()
            for prefab_node in loader.load_sync(prefabs).get_children():
                prefab_node.clear_transform()
                self.prefabs[prefab_node.name] = NodePath(prefab_node)

        self.tmx = ET.parse(input_file).getroot()
        self.xscale = int(self.tmx.get("tilewidth"))
        self.yscale = int(self.tmx.get("tileheight"))

        self.load_group(self.tmx)
        if output_file:
            self.export_bam(output_file)

    def attributes_to_tags(self, node, element):
        if not element == None:
            for property in element:
                node.set_tag(property.get("name"), property.get("value"))
            for key in element.keys():
                node.set_tag(key, element.get(key))

    def build_text(self, object):
        self.textnode.set_text(object[0].text)
        # TODO: set color
        # TODO: set wrap
        return self.textnode.generate()

    def build_polygon(self, object):
        self.linesegs.reset()
        points = object[0].get("points").split(" ")
        points = [tuple(map(float, i.split(","))) for i in points]
        startx = points[0][0]/self.xscale
        starty = points[0][1]/self.yscale
        self.linesegs.move_to(startx, -starty, 0)
        for point in points:
            x, y = point[0]/self.xscale, point[1]/self.yscale
            self.linesegs.draw_to(x, -y, 0)
        self.linesegs.draw_to(startx, -starty, 0)
        return self.linesegs.create()

    def build_rectangle(self, w, h):
        self.linesegs.reset()
        self.linesegs.move_to(0, 0, 0)
        self.linesegs.draw_to(w, 0, 0)
        self.linesegs.draw_to(w, -h, 0)
        self.linesegs.draw_to(0, -h, 0)
        self.linesegs.draw_to(0, 0, 0)
        return self.linesegs.create()

    def build_tile(self, tsx, id):
        tile = None
        # Cross-reference with self.prefabs in case there's a shape
        # corresponding with a tile's type
        use_prefab = False
        for tile in tsx.findall("tile"):
            if int(tile.get("id")) == id:
                type = tile.get("type")
                if type in self.prefabs:
                    geometry_node = NodePath(str(id))
                    self.prefabs[type].copy_to(geometry_node)
                    use_prefab = True
                break
        # Else we generate a card
        if not use_prefab:
            geometry = self.cardmaker.generate()
            geometry_node = NodePath(geometry)
            geometry_node.set_texture(tsx.get("texture"), 1)
            geometry_node.set_p(-90)
        geometry_node.set_transparency(True)
        # scale and offset UVs for single sprite
        columns = int(tsx.get("columns"))
        rows = int(tsx.get("rows"))
        w, h = 1/columns, 1/rows
        tile_x, tile_y = int(id%columns), int(id/rows)
        u, v = (tile_x*w), 1-((tile_y*h)+h)
        for stage in geometry_node.find_all_texture_stages():
            geometry_node.set_texture(stage, tsx.get("texture"), 1)
            geometry_node.set_tex_scale(stage, w, h)
            geometry_node.set_tex_offset(stage, (u, v))
        self.attributes_to_tags(geometry_node, tile)
        #geometry_node.set_tag("type", tile.get("type"))

        return geometry_node

    def animated_tile(self, tsx, tile):
        node = NodePath("animated tile")
        sequence = SequenceNode("animated tile")
        duration = int(tile[0][0].get("duration"))
        if duration >= 9000:
            sequence.set_frame_rate(0)
        else:
            sequence.set_frame_rate(1000/duration)

        for frame in tile[0]:
            tileid = int(frame.get("tileid"))
            tile_node = self.build_tile(tsx, tileid)
            sequence.add_child(tile_node.node())
        sequence.loop(True)
        node.attach_new_node(sequence)
        return node

    def get_tile(self, map_id):
        tileset, set_id = self.get_tileset(map_id)
        tsx = tileset.get("tsx")
        if map_id in self.tiles: # if card is already stored
            node = self.tiles[map_id] # use that one
        else: # else build and store it
            is_special = False
            node = self.build_tile(tsx, set_id)
            for element in tsx:
                if element.tag == "tile":
                    if int(element.get("id")) == set_id:
                        # if it contains an element, it's always an animation
                        if len(element) > 0:
                            node = self.animated_tile(tsx, element)
                        self.attributes_to_tags(node, element)
                        break
            self.tiles[map_id] = node
        return node

    def load_layer(self, layer):
        layer_node = NodePath(layer.get("name"))
        static_tiles = NodePath("static")    # Static tiles to flatten
        flat_animated_tiles = NodePath("animated") # Animated tiles to flatten
        dynamic_tiles = NodePath("dynamic")  # All tiles unless otherwise specified (don't flatten)
        tile_groups = {}
        # should we flatten this layer
        store_data = flatten = False
        properties = layer.find("properties")
        if properties:
            for property in properties:
                if property.get("name") == "flatten":
                    flatten = True
                if property.get("name") == "store_data":
                    store_data = True
        # build all tiles in data as a grid of cards
        data = layer.find("data").text
        data = data.replace('\n', '')
        data = data.split(",")
        collumns = int(layer.get("width"))
        rows = int(layer.get("height"))
        for y in range(rows):
            for x in range(collumns):
                id = int(data[(y*collumns) + (x%collumns)])
                data[(y*collumns) + (x%collumns)] = id
                if id > 0:
                    tile = NodePath("tile")
                    self.get_tile(id).copy_to(tile)
                    if flatten:
                        if tile.find("**/+SequenceNode"):
                            tile.reparent_to(flat_animated_tiles)
                        else:
                            tile.reparent_to(static_tiles)
                    else:
                        tile.reparent_to(dynamic_tiles)
                    tile.set_pos(x, -y, 0)
        if static_tiles.get_num_children() > 0:
            clear_all_tags(static_tiles)
            static_tiles.flatten_strong()
        if flat_animated_tiles.get_num_children() > 0:
            clear_all_tags(flat_animated_tiles)
            flat_animated_tiles = self.flatten_animated_tiles(flat_animated_tiles)
        for t in (static_tiles, flat_animated_tiles, dynamic_tiles):
            t.reparent_to(layer_node)
        if store_data:
            layer_node.set_python_tag("data", data)
        self.append_layer(layer_node, properties)

    def flatten_animated_tiles(self, group_node):
        # FIXME: hard to read: get_child() everywhere
        # Makes a new node for each frame using all its tiles
        # flatten the s*** out of the node and add to a new SequenceNode.
        tiles =  group_node.get_children()
        flattened_sequence = SequenceNode(tiles[0].name)
        for a, animation in enumerate(tiles[0].node().get_children()):
            for f, frame in enumerate(animation.get_child(0).get_children()):
                combined_frame = NodePath("frame " + str(f))
                for tile in tiles:
                    new_np = NodePath("frame")
                    new_np.set_pos(tile.get_pos())
                    animation = tile.node().get_child(a).get_child(0)
                    new_np.attach_new_node(animation.get_child(f))
                    new_np.reparent_to(combined_frame)
                combined_frame.flattenStrong()
                flattened_sequence.add_child(combined_frame.node())
        framerate = animation.get_frame_rate()
        flattened_sequence.set_frame_rate(framerate)
        flattened_sequence.loop(True)
        return NodePath(flattened_sequence)

    def load_objectgroup(self, objectgroup):
        layer_node = NodePath(objectgroup.get("name"))
        for object in objectgroup:
            name = object.get("name")
            if not name: name = "object"
            node = NodePath(name)
            if len(object) > 0:
                # Has a type, so it's either a polygon, text, point or ellipse
                # Points and ellipses are just an empty for now.
                kind = object[0].tag
                if kind == "polygon":
                    node.attach_new_node(self.build_polygon(object))
                elif kind == "text":
                    node.attach_new_node(self.build_text(object))
                    node.set_p(-90)
                self.attributes_to_tags(node, object[0])
            else: # Doesn't have a type, so it's either an image or a rectangle
                node = NodePath(name)
                w = float(object.get("width"))/self.xscale
                h = float(object.get("height"))/self.yscale
                if object.get("gid"): # Has a gid, so it's an image
                    self.get_tile(int(object.get("gid"))).copy_to(node)
                    node.set_scale(w, h, 1)
                else: # It's none of the above, so it's a rectangle
                    node.attach_new_node(self.build_rectangle(w, h))
            x = y = 0
            if object.get("x"):
                x = float(object.get("x"))/self.xscale
            if object.get("y"):
                y = float(object.get("y"))/self.yscale
            node.set_pos(x, -y, 0)
            self.attributes_to_tags(node, object)
            node.reparent_to(layer_node)
        self.append_layer(layer_node, objectgroup.find("properties"))

    def load_imagelayer(self, imagelayer):
        # FIXME: A lot of this stuff is repeated in build_tilcard
        image = imagelayer[0]
        right = int(image.get("width"))/self.xscale
        down = int(image.get("height"))/self.yscale
        self.cardmaker.set_frame(0, right, -down, 0)
        node = NodePath(self.cardmaker.generate())
        self.cardmaker.set_frame(0, 1, -1, 0)
        texture = Texture()
        texture.read(os.path.join(self.dir, image.get("source")))
        texture.setMagfilter(SamplerState.FT_nearest)
        texture.setMinfilter(SamplerState.FT_nearest)
        node.set_texture(texture)
        node.set_transparency(True)
        node.reparent_to(self.node)
        ox = imagelayer.get("offsetx")
        x, y = 0, 0
        if ox:
            x = float(ox)/self.xscale
        oy = imagelayer.get("offsety")
        if oy:
            y = float(oy)/self.yscale
        node.set_pos((x, -y, self.depth))
        node.set_p(-90)

    def load_group(self, group):
        for layer in group:
            if layer.tag == "tileset":
                self.load_tsx(layer)
            elif layer.tag == "layer":
                self.load_layer(layer)
            elif layer.tag == "objectgroup":
                self.load_objectgroup(layer)
            elif layer.tag == "imagelayer":
                self.load_imagelayer(layer)
            elif layer.tag == "group":
               self.load_group(layer)

    def append_layer(self, node, properties):
        self.attributes_to_tags(node, properties)
        node.set_z(self.depth)
        self.depth += 1
        if properties:
            for property in properties:
                if property.get("name") == "z":
                    node.set_z(int(property.get("value")))
                    self.depth -= 1
                    break
        node.reparent_to(self.node)

    def get_tileset(self, id):
        for tilesheet in self.tilesheets:
            if int(tilesheet.get("firstgid")) > id:
                break
            else:
                last = tilesheet
        id_in_sheet = id - int(last.get("firstgid"))
        return last, id_in_sheet,

    def load_tsx(self, layer):
        tsx_filename = layer.get("source")
        tsx = ET.parse(os.path.join(self.dir, tsx_filename)).getroot()
        # Load texture and store in the element tree.
        img_filename = tsx[0].get("source")
        texture = Texture()
        dir =  os.path.join(self.dir, tsx_filename)
        place = os.path.join(os.path.split(dir)[0], img_filename)
        texture.read(place)
        texture.setMagfilter(SamplerState.FT_nearest)
        texture.setMinfilter(SamplerState.FT_nearest)
        tsx.set("texture", texture)
        columns = int(tsx.get("columns"))
        rows = int(tsx.get("tilecount"))//columns
        tsx.set("rows", str(rows))
        layer.set("tsx", tsx)
        self.tilesheets.append(layer)

    def export_bam(self, filename):
        print("Exporting as {}".format(filename))
        self.node.writeBamFile("{}".format(filename))

def main():
    parser = argparse.ArgumentParser(
        description='CLI tool to convert Tiled TMX files to Panda3D BAM files'
    )
    parser.add_argument('src', type=str, help='source path to .tmx')
    parser.add_argument('dst', type=str, help='destination path to .bam')
    parser.add_argument('--prefabs', type=str, default=None, help=
            '.bam file whos node`s names correspond to a tsx`s tiles "type".'
            'This node will be used instead of a generated card')
    args = parser.parse_args()
    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)
    if args.prefabs:
        prefabs = os.path.abspath(args.prefabs)
    else:
        prefabs = None
    tmx2bam = Tmx2Bam(src, dst, prefabs)


if __name__ == "__main__":
    main()
