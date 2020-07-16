CLI tool for converting Tiled TMX files to Panda3D BAM files.

Usage:
```
$ pip install panda3d-tmx2bam
$ tmx2bam path/to/tmx/file.tmx path/to/bam/file.bam -prefabs=path/to/prefabs.bam
```
or
```
from tmx2bam import Tmx2Bam
from direct.showbase.ShowBase import ShowBase

base = ShowBase()
tmx_map = Tmx2Bam("path/to/tmx/file.tmx", prefabs="path/to/prefabs.bam")
tmx_map.node.reparent_to(render)
base.run()
```
Prefabs are optional. Without them all tiles will be cards.
Find important tiles and their properties like so:
```
tiles_with_my_property = tmx_map.node.find_all_matches('**/=my_property_name')
for tile in tiles_with_my_property:
  my_property_value = tile.get_tag("my_property_name")
```
You can read more about searching Panda3d's scene graph here:
https://docs.panda3d.org/1.10/python/programming/scene-graph/searching-scene-graph


Currently supports:
* TMX file with CSV data (default)
* Custom properties as PandaNode tags
* Multiple tilesheets
* Multiple layers and Groups
* Animated tiles
* Object layer/Objects (point, poly, rectangle, text, image)
* Background images
* Merge animated sprites
* Allow more shapes than just cards

Left to do:
* Infinite maps (chunks)
* Hexagonal and Isometric tiles
* Tile render order
* Tilesheet image collection
* Embedded tilesheet in tmx
* Embedding texture in bam
* Tiled features I'm not aware of
* Error handling
* A better readme

Exporter specific custom layer properties:
* "flatten" will flatten_strong() the layer
* "store_data" will store the data in the layer with set_python_tag()
* "z" set's the layer's z height.

Prefabs:
To use prefabs, simply make a bam (with blender and blend2bam for example),
where each root object is a nodepath named after a type in the spritesheet's
tsx. Tmx2bam will then replace the tiles or objects that have this type assigned
with this nodepath.

Mind:
* The Y axis is inverted in panda3d.
* Animated sprites can only have one steady frame-rate that you can set on the first frame in Tiled.
* Currently the image resolutions have to be power of two.
* Rendering tons of individual tiles is slow. Use the "flatten" property as much as possible.
* The ellipse and point objects are not drawn at this time, they're empty nodepaths.
* I'm not a programmer but I play one on TV. Your mileage may vary.

Fun snippets:
* Adding a "repeat" property to a "cube" prefabed tile to make towers and large walls and things.
```
for layer in tmx2bam.node.find_all_matches("**/=repeat"):
    repetitions = layer.get_tag("repeat")
    repeats_node = NodePath(layer.name+"-repeat")
    for repetition in range(int(repetitions)):
        repeat = NodePath("repeat")
        layer.copy_to(repeat)
        repeat.set_z(layer.get_z()+repetition-1)
        repeat.reparent_to(repeats_node)
    repeats_node.flatten_strong()
    repeats_node.reparent_to(layer)
```

Licensed WTFPL.
