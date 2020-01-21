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


class Converter():
    def __init__(self, input_file, output_file):
        self.dir = os.path.dirname(input_file)
        self.depth = 0
        # generators
        self.cardmaker = CardMaker("image")
        self.cardmaker.set_frame(0, 1, -1, 0)
        self.linesegs = LineSegs()
        self.textnode = TextNode("text")
        # storage
        self.tilesheets = []    # Every tsx file loaded.
        self.tiles = {}         # Every tile-card generated.
        self.root_node = NodePath("tmx_root")

        self.tmx = ET.parse(input_file).getroot()
        self.xscale = int(self.tmx.get("tilewidth"))
        self.yscale = int(self.tmx.get("tileheight"))
        self.load_group(self.tmx)

        # debug center
        sq = NodePath(self.build_rectangle(1, 1))
        sq.reparent_to(self.root_node)
        sq.set_pos(-0.5, -0.5, 0)

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
        points = object[0].get("points").split(" ")
        points = [tuple(map(float, i.split(","))) for i in points]
        self.linesegs.reset()
        self.linesegs.move_to(points[0][0]/self.xscale, points[0][1]/self.yscale, 0)
        for point in points:
            self.linesegs.draw_to(point[0]/self.xscale, point[1]/self.yscale, 0)
        self.linesegs.draw_to(points[0][0]/self.xscale, points[0][1]/self.yscale, 0)
        return self.linesegs.create()

    def build_rectangle(self, w, h):
        self.linesegs.reset()
        self.linesegs.move_to(0, 0, 0)
        self.linesegs.draw_to(w, 0, 0)
        self.linesegs.draw_to(w, h, 0)
        self.linesegs.draw_to(0, h, 0)
        self.linesegs.draw_to(0, 0, 0)
        return self.linesegs.create()

    def build_card(self, tsx, id):
        card = self.cardmaker.generate()
        card_node = NodePath(card)
        card_node.set_texture(tsx.get("texture"))
        card_node.set_transparency(True)
        # calculate UVs
        # FIXME, it's not nearly precise enough!
        w = int(tsx.get("tilewidth"))/int(tsx[0].get("width"))
        h = int(tsx.get("tileheight"))/int(tsx[0].get("height"))
        rows = 1/w
        collumns = 1/h
        u = (id%rows)*w
        v = 1-(((id/collumns)*h)+h)
        # set UVs
        stage = card_node.find_all_texture_stages()[0]
        card_node.set_tex_scale(stage, w, h)
        card_node.set_tex_offset(stage, (u, v))
        return card_node

    def animated_tile(self, tsx, tile):
        node = NodePath("animated tile")
        sequence = SequenceNode("animated tile")
        duration = int(tile[0][0].get("duration"))
        if duration > 0:
            node.set_tag("type", "group")
        else:
            node.set_tag("type", "dynamic")
        for frame in tile[0]:
            tileid = int(frame.get("tileid"))
            tile_node = self.build_card(tsx, tileid)
            sequence.add_child(tile_node.node())
        if duration == 0:
            sequence.set_frame_rate = 0
        else:
            sequence.set_frame_rate(1000/duration)
        sequence.loop(True)
        node.attach_new_node(sequence)
        return node

    def get_tile(self, map_id):
        # map_id is as it is in map data
        # set_id is as it is in tileset
        tileset, set_id = self.get_tileset(map_id)
        tsx = tileset.get("tsx")
        if map_id in self.tiles: # if card is already stored
            node = self.tiles[map_id] # use that one
        else: # else build and store it
            is_special = False
            for element in tsx:
                if element.tag == "tile":
                    if int(element.get("id")) == set_id:
                        if len(element) > 0:
                            node = self.animated_tile(tsx, element)
                        else:
                            node = self.build_card(tsx, set_id)
                            node.set_tag("type", "dynamic")
                        self.attributes_to_tags(node, element)
                        is_special = True
                        break
            if not is_special:
                node = self.build_card(tsx, set_id)
            self.tiles[map_id] = node
        node.set_p(90)
        return node

    def load_layer(self, layer):
        layer_node = NodePath(layer.get("name"))
        static_tiles = NodePath("static")   # doesn't change (f.e. walls)
        dynamic_tiles = NodePath("unique")  # changes individually (f.e. doors)
        tile_groups = {}                    # changes in groups (f.e. water)

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
                    if card.get_tag("type") == "group":
                        if id in tile_groups:
                            group_node = tile_groups[id]
                        else:
                            group_node = NodePath("tile group")
                            tile_groups[id] = group_node
                        tile.reparent_to(group_node)
                    elif card.get_tag("type") == "dynamic":
                        print("a dynamic tile found")
                        tile.reparent_to(dynamic_tiles)
                    else: # it's static
                        tile.reparent_to(static_tiles)
                    tile.set_pos(x, y, 0)

        # flatten all static cards,
        static_tiles.flattenStrong()
        static_tiles.reparent_to(layer_node)
        # flatten each tile-group seperately
        for group in tile_groups:
            tile_group = tile_groups[group]
            tile_group.flattenStrong()
            tile_group.reparent_to(layer_node)
        # dynamic tiles each do their own thing, so we leave them alone
        dynamic_tiles.reparent_to(layer_node)
        layer_node.set_z(self.depth)
        layer_node.reparent_to(self.root_node)

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
        layer_node.reparent_to(self.root_node)

    def load_imagelayer(self, imagelayer):
        image = imagelayer[0]
        right = int(image.get("width"))/self.xscale
        down = int(image.get("height"))/self.yscale
        self.cardmaker.set_frame(0, right, -down, 0)
        node = NodePath(self.cardmaker.generate())
        self.cardmaker.set_frame(0, 1, -1, 0)
        texture = Texture()
        texture.read(os.path.join(self.dir, image.get("source")))
        node.set_texture(texture)
        node.set_transparency(True)
        node.reparent_to(self.root_node)
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
        # Load texture and store in tsx as well.
        img_filename = tsx[0].get("source")
        texture = Texture()
        texture.read(os.path.join(self.dir, img_filename))
        texture.setMagfilter(SamplerState.FT_nearest)
        texture.setMinfilter(SamplerState.FT_nearest)
        tsx.set("texture", texture)
        layer.set("tsx", tsx)
        self.tilesheets.append(layer)

    def export_bam(self, filename):
        print("Exporting as {}".format(filename))
        self.root_node.writeBamFile("{}".format(filename))

def main():
    parser = argparse.ArgumentParser(
        description='CLI tool to convert Tiled TMX files to Panda3D BAM files'
    )

    parser.add_argument('src', type=str, help='source path to .tmx')
    parser.add_argument('dst', type=str, help='destination path to .bam')

    args = parser.parse_args()

    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)

    Converter(src, dst)

if __name__ == "__main__":
    main()
