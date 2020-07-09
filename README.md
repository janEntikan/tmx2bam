CLI tool for converting Tiled TMX files to Panda3D BAM files.

Usage:
```
$ pip install panda3d-tmx2bam
$ tmx2bam path/to/tmx/file.tmx path/to/bam/file.bam
```
or
```
from tmx2bam import Tmx2Bam
from direct.showbase.ShowBase import ShowBase

base = ShowBase()
tmx_map = Tmx2Bam("path/to/tmx/file.tmx")
tmx_map.node.reparent_to(render)
base.run()
```

find() important tiles by their properties/tags and make them move about and all that. Orthographic camera recommended!

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

Mind:
* The Y axis is inverted in panda3d.
* Animated sprites can only have one steady frame-rate that you can set on the first frame in Tiled.
* Currently the image resolutions have to be power of two.
* Rendering individual tiles is slow. Add a custom property named "flatten" to layers to merge them.
* The ellipse and point objects are not drawn, they're empty nodepaths.
* I'm not a programmer but I play one on TV. Your mileage may vary.

Licensed WTFPL.
