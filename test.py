from tmx2bam import Tmx2Bam
from direct.showbase.ShowBase import ShowBase

base = ShowBase()
tmx_map = Tmx2Bam("path/to/tmx/file.tmx")
tmx_map.node.reparent_to(render)
base.run()