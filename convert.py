import os
import argparse

import xml.etree.ElementTree as ET

from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath
from panda3d.core import Texture
from panda3d.core import CardMaker
from panda3d.core import SamplerState
from panda3d.core import SequenceNode


class Converter():
    def __init__(self, input_file, output_file):
        self.cardmaker = CardMaker("image")
        self.cardmaker.set_frame(0,1,0,1)
        self.root_node = NodePath("tmx_root")


        self.dir = os.path.dirname(input_file) + "/"
        print(self.dir)
        self.depth = 0

        self.tilesheets = []    # Every tilesheet loaded.
        self.tiles = {}         # Every tile-card generated.

        self.tmx = ET.parse(input_file).getroot()
        self.load_group(self.tmx)
        self.export_bam(output_file)

    def attributes_to_tags(self, node, element):
        for key in element.keys():
            node.set_tag(key, element.get(key))

    def build_card(self, tsx, id):
        card = self.cardmaker.generate()
        card_node = NodePath(card)
        card_node.set_p(90)
        card_node.set_texture(tsx.get("texture"))
        card_node.set_transparency(True)
        # calculate UVs
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

    def sequence_tile(self, tsx, tile):
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
        sequence.set_frame_rate(1000/duration)
        sequence.loop(True)
        node.attach_new_node(sequence)
        return node

    def load_tile(self, tileset, id):
        tsx = tileset.get("tsx")
        is_special = False
        for element in tsx:
            if element.tag == "tile":
                if int(element.get("id")) == id:
                    if len(element) > 0:
                        # FIXME: if there's something in the element
                        # that means there's an animation?
                        node = self.sequence_tile(tsx, element)
                    else:
                        node = self.build_card(tsx, id)
                        node.set_tag("type", "dynamic")
                    self.attributes_to_tags(node, element)
                    is_special = True
                    break

        if not is_special:
            node = self.build_card(tsx, id)
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
        width = int(layer.get("width"))
        height = int(layer.get("height"))
        for y in range(height):
            for x in range(width):
                # get tile int in data
                global_id = int(data[(y*width) + (x%width)])
                if global_id > 0: # 0 is tileless

                    # get card from global_id
                    tileset, tile_id = self.get_tileset(global_id)
                    if global_id in self.tiles: # if card already stored
                        card = self.tiles[global_id] # use that one
                    else: # else build and store it
                        card = self.load_tile(tileset, tile_id)
                        self.tiles[global_id] = card
                    # make a copy
                    tile = NodePath("tile")
                    card.copy_to(tile)

                    # Reparent to nodes for flattening.
                    if card.get_tag("type") == "group":
                        if global_id in tile_groups:
                            group_node = tile_groups[global_id]
                        else:
                            group_node = NodePath("tile group")
                            tile_groups[global_id] = group_node
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
        layer_node.set_pos(0, 0, self.depth)
        layer_node.reparent_to(self.root_node)

    def load_objectgroup(self, layer):
        layer_node = NodePath(layer.get("name"))
        # TODO: for object in group:
            # TODO: if point: Empty PandaNode.
            # TODO: elif polygon: Linesegs.
            # TODO: elif text: TextNode.
            # TODO: elif ellipse: euhh...
            # TODO: else it's a rectangle.
            # TODO: set attributes as tags.
            # TODO: set object transform, parent to layer_node.
        layer_node.reparent_to(self.root_node)

    def load_group(self, group):
        for layer in group:
            if layer.tag == "tileset":
                self.load_tsx(layer)
            elif layer.tag == "layer":
                self.load_layer(layer)
            elif layer.tag == "objectgroup":
                self.load_objectgroup(layer)
            #elif layer.tag == "imagelayer":
            #    self.load_imagelayer(layer)
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
        tsx = ET.parse(self.dir + tsx_filename).getroot()
        # Load texture and store in tsx as well.
        img_filename = tsx[0].get("source")
        texture = Texture()
        texture.read(self.dir + img_filename)
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
