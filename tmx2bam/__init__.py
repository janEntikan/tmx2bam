import os
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


class Tmx2Bam():
    def __init__(self, input_file, output_file=None):
        self.dir = os.path.dirname(input_file)
        self.depth = 0

        self.cardmaker = CardMaker("image")
        self.cardmaker.set_frame(0, 1, -1, 0)
        self.linesegs = LineSegs()
        self.textnode = TextNode("text")

        self.tilesheets = []    # Every tsx file loaded.
        self.tiles = {}         # Every unique tile/card.
        self.node = NodePath("tmx_root")

        self.tmx = ET.parse(input_file).getroot()
        self.xscale = int(self.tmx.get("tilewidth"))
        self.yscale = int(self.tmx.get("tileheight"))

        self.load_group(self.tmx)
        if output_file:
            self.export_bam(output_file)

    def attributes_to_tags(self, node, element):
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
        self.linesegs.move_to(startx, starty, 0)
        for point in points:
            x, y = point[0]/self.xscale, point[1]/self.yscale
            self.linesegs.draw_to(x, y, 0)
        self.linesegs.draw_to(startx, starty, 0)
        return self.linesegs.create()

    def build_rectangle(self, w, h):
        self.linesegs.reset()
        self.linesegs.move_to(0, 0, 0)
        self.linesegs.draw_to(w, 0, 0)
        self.linesegs.draw_to(w, h, 0)
        self.linesegs.draw_to(0, h, 0)
        self.linesegs.draw_to(0, 0, 0)
        return self.linesegs.create()

    def build_tilecard(self, tsx, id):
        card = self.cardmaker.generate()
        card_node = NodePath(card)
        card_node.set_texture(tsx.get("texture"))
        card_node.set_transparency(True)
        stage = card_node.find_all_texture_stages()[0]
        # size of sheet in tiles
        columns = int(tsx.get("columns")) # = 80
        rows = int(tsx.get("rows")) # = 80
        # size of a single tile in UV
        w = float(tsx.get("uv_xscale"))
        h = float(tsx.get("uv_yscale"))
        # pos of tile in sheet in pixels
        tile_x = int(id%columns)
        tile_y = int(id/rows)
        # pos of a single tile in UV
        u = (tile_x*w)
        v = 1-((tile_y*h)+h)
        # set UVs
        card_node.set_tex_scale(stage, w, h)
        card_node.set_tex_offset(stage, (u, v))
        return card_node

    def animated_tile(self, tsx, tile):
        node = NodePath("animated tile")
        sequence = SequenceNode("animated tile")
        duration = int(tile[0][0].get("duration"))
        if duration > 0:
            sequence.set_frame_rate(1000/duration)
        else:
            sequence.set_frame_rate = 0
        for frame in tile[0]:
            tileid = int(frame.get("tileid"))
            tile_node = self.build_tilecard(tsx, tileid)
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
            for element in tsx:
                if element.tag == "tile":
                    if int(element.get("id")) == set_id:
                        # if it contains an element, it's always an animation
                        if len(element) > 0:
                            node = self.animated_tile(tsx, element)
                            # if it has properties other then ID, don't flatten
                            if len(element.keys()) > 1:
                                node.set_tag("_flatten", "dynamic")
                            else:
                                node.set_tag("_flatten", "group")
                        else:
                            node.set_tag("_flatten", "dynamic")
                            node = self.build_tilecard(tsx, set_id)
                        self.attributes_to_tags(node, element)
                        is_special = True
                        break
            if not is_special:
                node = self.build_tilecard(tsx, set_id)
            self.tiles[map_id] = node
        node.set_p(90)
        return node

    def load_layer(self, layer):
        layer_node = NodePath(layer.get("name"))
        static_tiles = NodePath("static")   # Static tiles without properties (flatten)
        dynamic_tiles = NodePath("unique")  # Any tile with a property (don't flatten)
        tile_groups = {}                    # Animated tiles without properties (flatten)

        # build all tiles in data as a grid of cards
        data = layer[0].text
        data = data.replace('\n', '')
        data = data.split(",")
        collumns = int(layer.get("width"))
        rows = int(layer.get("height"))
        for y in range(rows):
            for x in range(collumns):
                id = int(data[(y*collumns) + (x%collumns)])
                if id > 0:
                    # make a copy
                    tile = NodePath("tile")
                    card = self.get_tile(id)
                    card.copy_to(tile)
                    # Reparent to nodes for flattening.
                    if card.get_tag("_flatten") == "group":
                        if id in tile_groups:
                            group_node = tile_groups[id]
                        else:
                            group_node = NodePath("tile group")
                            tile_groups[id] = group_node
                        tile.reparent_to(group_node)
                    elif card.get_tag("_flatten") == "dynamic":
                        tile.reparent_to(dynamic_tiles)
                    else: # it's static
                        tile.reparent_to(static_tiles)
                    tile.set_pos(x, y, 0)

        # flatten all static cards,
        static_tiles.flattenStrong()
        static_tiles.reparent_to(layer_node)
        # flatten each tile-group seperately (if animated)
        for group in tile_groups:
            tile_groups[group] = self.flatten_animated_tiles(tile_groups[group])
            tile_groups[group].reparent_to(layer_node)
        # dynamic tiles each do their own thing, so we leave them alone
        if dynamic_tiles.get_num_children() > 0:
            dynamic_tiles.reparent_to(layer_node)
        layer_node.set_z(self.depth)
        layer_node.reparent_to(self.node)

    def flatten_animated_tiles(self, group_node):
        # FIXME: hard to read: get_child() everywhere
        # Makes a new node for each frame taking all its tiles
        # flatten the s*** out of the node and add to a new SequenceNode.
        tiles =  group_node.get_children()
        flattened_sequence = SequenceNode(tiles[0].name)
        for a, animation in enumerate(tiles[0].node().get_children()):
            for f, frame in enumerate(animation.get_child(0).get_children()):
                combined_frame = NodePath("frame " + str(f))
                for tile in tiles:
                    new_np = NodePath("frame")
                    new_np.set_pos(tile.get_pos())
                    new_np.set_p(90)
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
                # Has a type, it's a polygon, text, point or ellipse
                # Points and ellipses stay empty for now.
                kind = object[0].tag
                if kind == "polygon":
                    node.attach_new_node(self.build_polygon(object))
                elif kind == "text":
                    node.attach_new_node(self.build_text(object))
                    node.set_p(90)
                self.attributes_to_tags(node, object[0])
            else: # Doesn't have a type, it's either an image or a rectangle
                node = NodePath(name)
                w = float(object.get("width"))/self.xscale
                h = float(object.get("height"))/self.yscale
                if object.get("gid"): # Has a gid, it's an image
                    self.get_tile(int(object.get("gid"))).copy_to(node)
                    node.set_scale(w, h, 1)
                else: # It's a rectangle
                    node.attach_new_node(self.build_rectangle(w, h))

            x = float(object.get("x"))/self.xscale
            y = float(object.get("y"))/self.yscale
            node.set_pos(x, y, 0)
            self.attributes_to_tags(node, object)
            node.reparent_to(layer_node)
        layer_node.set_z(self.depth)
        layer_node.reparent_to(self.node)

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
        x = float(imagelayer.get("offsetx"))/self.xscale
        y = float(imagelayer.get("offsety"))/self.yscale
        node.set_pos((x, y, self.depth))
        node.set_p(90)

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
            self.depth -= 1

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
        texture.read(os.path.join(self.dir, img_filename))
        # texture.setWrapU(Texture.WM_clamp)
        # texture.setWrapV(Texture.WM_clamp)
        texture.setMagfilter(SamplerState.FT_nearest)
        texture.setMinfilter(SamplerState.FT_nearest)
        tsx.set("texture", texture)
        # Calculate individual tile size in UV
        # Store it in the element tree
        columns = int(tsx.get("columns"))
        rows = int(tsx.get("tilecount"))//columns
        uv_xscale = 1/columns
        uv_yscale = 1/rows
        tsx.set("rows", str(rows))
        tsx.set("uv_xscale", str(uv_xscale))
        tsx.set("uv_yscale", str(uv_yscale))
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

    args = parser.parse_args()

    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)

    tmx2bam = Tmx2Bam(src, dst)


if __name__ == "__main__":
    main()