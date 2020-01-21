CLI tool for converting Tiled TMX files to Panda3D BAM files.

Usage:
```
python convert.py path/to/tmx/file.tmx path/to/bam/file.bam
```
load the bam with panda3d like you would normally. find() important tiles by their tags and make them move about and all that. Orthographic camera recommended!


Currently supports:
* TMX file with CSV data (default)
* Custom properties as PandaNode tags
* Multiple tilesheets
* Multiple layers and Groups
* Animated tiles
* Object layer/Objects (point, poly, rectangle, text, image)

Left to do:
* Background image
* Flatten animated sprites
* Infinite maps (chunks)
* Hexagonal and Isometric tiles
* Tile render order
* Tilesheet image collection
* Embedded tilesheet in tmx
* Embed texture in bam
* Error handling
* Weird UV micro-offset
* A better readme

Mind:
* Currently The map is facing DOWN?
* Animated sprites can only have one steady framerate that you can set on the first frame in Tiled.
* Currently image resolution has to be power of two.
* Tiles are merged into a single block of geometry as much as possible. Give tiles custom properties or animations to avoid this from happening.
* The ellipse and point objects are not drawn, they're empty nodepaths.
* It might be fun if some cards where cubes instead.
* I'm not a programmer but I play one on TV.

Licensed WTFPL.

tileset.png is https://opengameart.org/content/simple-broad-purpose-tileset
