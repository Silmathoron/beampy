# -*- coding: utf-8 -*-
"""
Created on Sun Oct 25 19:05:18 2015

@author: hugo
"""

from beampy import document
from beampy.modules.figure import figure
from beampy.modules.core import beampy_module
import tempfile
import os

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.formatters import SvgFormatter
    is_pigment = True
except:
    is_pigment = False

class code(beampy_module):
    #Transform the code to svg using pigment and then use the classic render for figure

    def __init__(self, codetext, x='center', y='auto', width=None, height=None, langage=None, size="14px" ):
        """
            Color a given code using python pygment

            option
            ------

            langage[None]: try to infer the lexer from codetext

            size['9px']: size of the text

        """

        self.type = 'svg'
        self.content = codetext

        if width == None:
            self.width = document._width
        else:
            self.width = width

        if height == None:
            self.height = document._height
        else:
            self.height = height

        self.args = {"langage": langage, 'font_size': size }
        self.langage = langage
        self.font_size = size

        #TODO: Move this function to pre-render to be managed by cache
        #and not run at each beampy run
        # self.code2svg()

        if is_pigment:
            self.register()
        else:
            print("Python pygment is not installed, I can't translate code into svg...")


    def code2svg(self):
        """
            function to render code to svg
        """

        inkscapecmd=document._external_cmd['inkscape']
        codein = self.content


        #Try to infer the lexer
        if self.langage == None:
            lexer = guess_lexer(codein)
        else:
            lexer = get_lexer_by_name(self.langage, stripall=True)

        #Convert code to svgfile
        svgcode = highlight(codein, lexer, SvgFormatter(fontsize=self.font_size, style='tango'))

        #Create a tmpfile
        tmpfile, tmpname = tempfile.mkstemp(prefix='beampytmp_CODE')
        #tmppath = tmpname.replace(os.path.basename(tmpname),'')

        with open( tmpname+'.svg', 'w' ) as f:
            f.write(svgcode)

        #Convert svgfile with inkscape to transform text to path
        cmd = inkscapecmd + ' -z -T -l=%s %s'%(tmpname+'_good.svg', tmpname+'.svg')

        req = os.popen(cmd)
        req.close()

        #Read the good svg
        # with open(tmpname+'_good.svg','r') as f:
        #    goodsvg = f.read()

        f = figure(tmpname+'_good.svg', width=self.width, height=self.height)
        f.positionner = self.positionner
        f.render()
        self.svgout = f.svgout
        self.positionner = f.positionner
        self.width = f.width
        self.height = f.height

        f.delete()

        #remove files
        os.remove(tmpname+'.svg')
        os.remove(tmpname+'_good.svg')
        os.remove(tmpname)


    def render(self):
        self.code2svg()
        self.rendered = True
