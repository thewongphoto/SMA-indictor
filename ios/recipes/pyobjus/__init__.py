"""Pin the native Objective-C bridge instead of upstream's floating master."""
from kivy_ios.recipes.pyobjus import PyobjusRecipe


class PinnedPyobjusRecipe(PyobjusRecipe):
    version = "0c204ada4a5aa4f065ac65fc678c6cb35e4dcb81"


recipe = PinnedPyobjusRecipe()
