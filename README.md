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

load the bam with panda3d like you would normally. find() important tiles by their properties/tags and make them move about and all that. Orthographic camera recommended!

Currently supports:
* TMX file with CSV data (default)
* Custom properties as PandaNode tags
* Multiple tilesheets
* Multiple layers and Groups
* Animated tiles
* Object layer/Objects (point, poly, rectangle, text, image)
* Background images
* Merge animated sprites

Left to do:
* Fix wonky UV calculation
* Infinite maps (chunks)
* Hexagonal and Isometric tiles
* Tile render order
* Tilesheet image collection
* Embedded tilesheet in tmx
* Embed texture in bam
* Tiled features I'm not aware of
* Error handling
* A better readme

Mind:
* The map is facing DOWN the Z
* Animated sprites can only have one steady framerate that you can set on the first frame in Tiled.
* Currently the image resolutions have to be power of two.
* Tiles are merged into a single block of geometry as much as possible. Give tiles properties other then their ID to avoid this from happening.
* The ellipse and point objects are not drawn, they're empty nodepaths.
* It might be fun if some cards where cubes instead.
* I'm not a programmer but I play one on TV. Your mileage may vary.

Licensed WTFPL.

tileset.png is https://opengameart.org/content/simple-broad-purpose-tileset
